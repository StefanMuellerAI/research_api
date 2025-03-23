import requests
import json
import time
import os
from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Konfiguration
API_BASE_URL = "http://localhost:8000"
API_KEY = os.environ.get("RESEARCH_API_KEY", "test-api-key")  # Verwende den Standard-Key, wenn keiner gesetzt ist

# Headers für die Authentifizierung
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def test_api_with_auth():
    """Testet die API mit API-Key-Authentifizierung."""
    print(f"Teste API mit API-Key: {API_KEY}")
    
    # 1. Überprüfe, ob die API aktiv ist
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"API-Status: {response.json()}")
    except Exception as e:
        print(f"Fehler: API ist nicht erreichbar. {str(e)}")
        print("Stelle sicher, dass die API mit 'python api.py' oder './run.sh' gestartet wurde.")
        return
    
    # 2. Starte eine Forschungsanfrage (Test mit dem Trend-Modus)
    query = "Digitale Transformation im Einzelhandel"
    request_body = {
        "query": query,
        "mode": "trends"
    }
    
    print(f"\nStarte Trend-Analyse zu: '{query}'")
    response = requests.post(
        f"{API_BASE_URL}/research",
        headers=headers,
        json=request_body
    )
    
    # Überprüfe auf Authentifizierungsfehler
    if response.status_code in [401, 403]:
        print(f"Authentifizierungsfehler: {response.json()['detail']}")
        return
    
    if response.status_code != 200:
        print(f"Fehler: {response.status_code} - {response.text}")
        return
    
    research_data = response.json()
    research_id = research_data["research_id"]
    print(f"Research ID: {research_id}")
    
    # 3. Überwache den Status der Forschung
    completed = False
    while not completed:
        status_response = requests.get(
            f"{API_BASE_URL}/research/{research_id}",
            headers=headers
        )
        
        if status_response.status_code != 200:
            print(f"Fehler beim Abrufen des Status: {status_response.status_code} - {status_response.text}")
            break
        
        status = status_response.json()
        print(f"Status: {status['status']}, Fortschritt: {status['progress']}%, Nachricht: {status['progress_message']}")
        
        if status["status"] == "completed":
            completed = True
        else:
            time.sleep(5)  # Warte 5 Sekunden zwischen den Status-Abfragen
    
    # 4. Rufe die Ergebnisse ab, wenn die Forschung abgeschlossen ist
    if completed:
        trends_response = requests.get(
            f"{API_BASE_URL}/research/{research_id}/trends",
            headers=headers
        )
        
        if trends_response.status_code != 200:
            print(f"Fehler beim Abrufen der Trends: {trends_response.status_code} - {trends_response.text}")
            return
        
        trends_data = trends_response.json()
        
        print("\n--- TREND-ANALYSE ERGEBNIS ---")
        print(f"Thema: {trends_data['topic']}")
        print(f"Zusammenfassung: {trends_data['summary']}")
        
        print("\n--- TOP 10 TRENDS ---")
        for i, trend in enumerate(trends_data["trends"], 1):
            print(f"\n{i}. {trend['title']}")
            print(f"   {trend['description']}")
        
        # Speichere die Trends in einer JSON-Datei
        with open("api_trends_result.json", "w", encoding="utf-8") as f:
            json.dump(trends_data, f, ensure_ascii=False, indent=2)
        
        print("\nTrends wurden in 'api_trends_result.json' gespeichert.")


if __name__ == "__main__":
    test_api_with_auth() 