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

# Trenne Imports für bessere Fehlerbehandlung
try:
    from agents import Agent, RunResult, gen_trace_id
except ImportError:
    print("agents-Modul konnte nicht importiert werden. Verwende lokale Implementierungen.")

# Typ-Variablen für generische Funktionen
T = TypeVar('T', bound=BaseModel)

class OpenAIRunner:
    """
    Implementierung des Runners, der mit der OpenAI-API kommuniziert.
    """
    
    @staticmethod
    async def run(agent: Any, input_text: str) -> Any:
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
            
            # Erstelle ein RunResult-Objekt (wenn die RunResult-Klasse verfügbar ist)
            # Andernfalls gib nur das Ergebnis zurück
            try:
                return RunResult(agent, result)
            except NameError:
                return {"agent": agent.name, "result": result}
        except Exception as e:
            print(f"Fehler bei der Ausführung des Agenten {agent.name}: {str(e)}")
            try:
                return RunResult(agent, {"error": str(e)})
            except NameError:
                return {"agent": agent.name, "error": str(e)}
    
    @staticmethod
    def run_streamed(agent: Any, input_text: str) -> Any:
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
            try:
                run_result = RunResult(agent, result)
                # Mache das Ergebnis iterable für die Kompatibilität mit dem ursprünglichen Code
                run_result.stream_events = lambda: [1]  # Einfacher Iterator für einen Durchlauf
                return run_result
            except NameError:
                result_obj = {"agent": agent.name, "result": result}
                result_obj["stream_events"] = lambda: [1]
                return result_obj
        except Exception as e:
            print(f"Fehler bei der Ausführung des Agenten {agent.name}: {str(e)}")
            try:
                result = RunResult(agent, {"error": str(e)})
                result.stream_events = lambda: []  # Leerer Iterator
                return result
            except NameError:
                result_obj = {"agent": agent.name, "error": str(e)}
                result_obj["stream_events"] = lambda: []
                return result_obj


# Patch die Runner-Klasse im agents-Modul, um die OpenAI-Implementierung zu verwenden
# Nur durchführen, wenn die Klasse erfolgreich importiert wurde
try:
    # Versuche, den Runner aus dem agents-Modul zu importieren
    from agents import Runner
    
    # Speichere die Original-Methoden
    original_run = getattr(Runner, "run", None)
    original_run_streamed = getattr(Runner, "run_streamed", None)
    
    # Überschreibe die Methoden nur, wenn sie als Klassenmethoden existieren
    if hasattr(Runner, "run") and callable(getattr(Runner, "run")):
        Runner.run = OpenAIRunner.run
        
    if hasattr(Runner, "run_streamed") and callable(getattr(Runner, "run_streamed")):
        Runner.run_streamed = OpenAIRunner.run_streamed
    
    print("OpenAI Runner erfolgreich installiert.")
except ImportError:
    print("Warnung: Konnte den Runner nicht patchen, da das agents-Modul nicht importiert werden konnte.")
except Exception as e:
    print(f"Fehler beim Patchen des Runners: {str(e)}") 