"""
OpenAI Agent-Implementierung für die Research API
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

import openai
from openai import OpenAI

from agents import Agent, RunResult, gen_trace_id

# Typ-Variablen für generische Funktionen
T = TypeVar('T', bound=BaseModel)

class OpenAIRunner:
    """
    Implementierung des Runners, der mit der OpenAI-API kommuniziert.
    """
    
    @staticmethod
    async def run(agent: Agent, input_text: str) -> RunResult:
        """
        Führt einen Agenten mit dem angegebenen Eingabetext aus.
        
        Args:
            agent: Der auszuführende Agent
            input_text: Der Eingabetext für den Agenten
            
        Returns:
            Ein RunResult-Objekt
        """
        try:
            # OpenAI-Client-Instanz erstellen
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # System-Nachricht mit den Anweisungen erstellen
            system_message = agent.instructions
            
            # Anfrage an die OpenAI-API senden
            response = client.chat.completions.create(
                model=agent.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # Antwort verarbeiten
            content = response.choices[0].message.content
            
            # Wenn ein Ausgabetyp definiert ist, versuche, die Antwort zu parsen
            if agent.output_type:
                try:
                    # Versuche, JSON zu extrahieren
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        data = json.loads(json_str)
                        result = agent.output_type(**data)
                    else:
                        # Fallback: Erstelle ein leeres Objekt vom Ausgabetyp
                        print(f"Warnung: Konnte keine JSON-Daten in der Antwort finden: {content}")
                        result = {"error": "Konnte keine gültigen Daten aus der Antwort extrahieren"}
                except Exception as e:
                    print(f"Fehler beim Parsen der OpenAI-Antwort: {str(e)}")
                    print(f"Antwort: {content}")
                    result = {"error": f"Parsing error: {str(e)}"}
            else:
                # Wenn kein Ausgabetyp definiert ist, gib den Rohtext zurück
                result = content
            
            return RunResult(agent, result)
        except Exception as e:
            print(f"Fehler bei der Ausführung des Agenten {agent.name}: {str(e)}")
            return RunResult(agent, {"error": str(e)})
    
    @staticmethod
    def run_streamed(agent: Agent, input_text: str) -> RunResult:
        """
        Führt einen Agenten mit dem angegebenen Eingabetext aus und streamt die Ergebnisse.
        
        Args:
            agent: Der auszuführende Agent
            input_text: Der Eingabetext für den Agenten
            
        Returns:
            Ein RunResult-Objekt
        """
        try:
            # OpenAI-Client-Instanz erstellen
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # System-Nachricht mit den Anweisungen erstellen
            system_message = agent.instructions
            
            # Anfrage an die OpenAI-API senden (nicht-streamend für Vercel)
            response = client.chat.completions.create(
                model=agent.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # Antwort verarbeiten
            content = response.choices[0].message.content
            
            # Wenn ein Ausgabetyp definiert ist, versuche, die Antwort zu parsen
            if agent.output_type:
                try:
                    # Versuche, JSON zu extrahieren
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        data = json.loads(json_str)
                        result = agent.output_type(**data)
                    else:
                        # Fallback: Erstelle ein leeres Objekt vom Ausgabetyp
                        print(f"Warnung: Konnte keine JSON-Daten in der Antwort finden: {content}")
                        result = {"error": "Konnte keine gültigen Daten aus der Antwort extrahieren"}
                except Exception as e:
                    print(f"Fehler beim Parsen der OpenAI-Antwort: {str(e)}")
                    print(f"Antwort: {content}")
                    result = {"error": f"Parsing error: {str(e)}"}
            else:
                # Wenn kein Ausgabetyp definiert ist, gib den Rohtext zurück
                result = content
            
            # Erstelle das Ergebnis
            run_result = RunResult(agent, result)
            
            # Mache das Ergebnis iterable für die Kompatibilität mit dem ursprünglichen Code
            run_result.stream_events = lambda: [1]  # Einfacher Iterator für einen Durchlauf
            
            return run_result
        except Exception as e:
            print(f"Fehler bei der Ausführung des Agenten {agent.name}: {str(e)}")
            result = RunResult(agent, {"error": str(e)})
            result.stream_events = lambda: []  # Leerer Iterator
            return result


# Patch die Runner-Klasse im agents-Modul, um die OpenAI-Implementierung zu verwenden
try:
    from agents import Runner
    
    # Überschreibe die run-Methode
    Runner.run = OpenAIRunner.run
    
    # Überschreibe die run_streamed-Methode
    Runner.run_streamed = OpenAIRunner.run_streamed
    
    print("OpenAI Runner erfolgreich installiert.")
except ImportError:
    print("Warnung: Konnte den Runner nicht patchen.")
except Exception as e:
    print(f"Fehler beim Patchen des Runners: {str(e)}") 