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


async def test_trends_analysis():
    """Testet die Trend-Analyse-Funktionalität direkt (ohne API)."""
    print("Starte Trend-Analyse-Test...")
    
    # Erstelle den Research Manager
    manager = AsyncResearchManager()
    
    # Starte eine Forschungsanfrage im Trend-Modus
    research_id = "test-trends-123"
    query = "Personalmanagement in KMU"
    
    print(f"Starte Trend-Analyse zu: '{query}'")
    manager.start_research(research_id, query, mode="trends")
    
    # Überwache den Status
    while True:
        status = manager.get_status(research_id)
        if not status:
            print("Fehler: Status nicht gefunden")
            break
        
        print(f"Status: {status.status}, Fortschritt: {status.progress}%, Nachricht: {status.progress_message}")
        
        if status.status == "completed":
            print("\n--- TREND-ANALYSE ERGEBNIS ---")
            print(f"Thema: {status.topic}")
            print(f"Zusammenfassung: {status.summary}")
            
            print("\n--- TOP 10 TRENDS ---")
            if status.trends:
                for i, trend in enumerate(status.trends, 1):
                    print(f"\n{i}. {trend.title}")
                    print(f"   {trend.description}")
            else:
                print("Keine Trends gefunden.")
            
            # Speichere die Trends in einer JSON-Datei
            if status.trends:
                trends_data = {
                    "topic": status.topic,
                    "summary": status.summary,
                    "trends": [{"title": t.title, "description": t.description} for t in status.trends]
                }
                
                with open("trends_result.json", "w", encoding="utf-8") as f:
                    json.dump(trends_data, f, ensure_ascii=False, indent=2)
                
                print("\nTrends wurden in 'trends_result.json' gespeichert.")
            
            break
        
        await asyncio.sleep(2)  # Warte 2 Sekunden zwischen Statusabfragen


if __name__ == "__main__":
    asyncio.run(test_trends_analysis()) 