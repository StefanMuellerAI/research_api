import asyncio
import json
import sys

# Setze den PYTHONPATH, um die Module zu finden
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
openai_agents_dir = os.path.join(parent_dir, 'openai-agents-python')
if openai_agents_dir not in sys.path:
    sys.path.append(openai_agents_dir)

from dotenv import load_dotenv
load_dotenv()

# Überprüfe den OpenAI API Key
if not os.environ.get("OPENAI_API_KEY"):
    print("FEHLER: OPENAI_API_KEY ist nicht gesetzt. Bitte in der .env-Datei konfigurieren.")
    sys.exit(1)

from research_manager import AsyncResearchManager


async def test_research():
    """Testet die Research-Funktionalität direkt (ohne API)."""
    print("Starte Research-Test...")
    
    # Erstelle den Research Manager
    manager = AsyncResearchManager()
    
    # Starte eine Forschungsanfrage
    research_id = "test-123"
    query = "Was sind die neuesten Trends in erneuerbaren Energien?"
    
    print(f"Starte Forschung: '{query}'")
    manager.start_research(research_id, query)
    
    # Überwache den Status
    while True:
        status = manager.get_status(research_id)
        if not status:
            print("Fehler: Status nicht gefunden")
            break
        
        print(f"Status: {status.status}, Fortschritt: {status.progress}%, Nachricht: {status.progress_message}")
        
        if status.status == "completed":
            print("\n--- ERGEBNIS ---")
            print(f"Zusammenfassung: {status.report_summary}")
            print("\nFollow-up Fragen:")
            for question in status.follow_up_questions or []:
                print(f"- {question}")
            
            # Speichere den Bericht in einer Datei
            with open("test_report.md", "w") as f:
                f.write(status.report_markdown or "Kein Bericht verfügbar")
            print("\nBericht wurde in 'test_report.md' gespeichert.")
            
            break
        
        await asyncio.sleep(2)  # Warte 2 Sekunden zwischen Statusabfragen


if __name__ == "__main__":
    asyncio.run(test_research()) 