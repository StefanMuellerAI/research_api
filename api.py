import os
import uuid
import sys
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from typing import Optional, List
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Behandlung des openai-agents-python-Moduls
# Versuche, das Modul direkt zu importieren
try:
    from research_manager import AsyncResearchManager, ResearchRequest, ResearchResponse, ResearchStatus
except ImportError:
    # Für lokale Entwicklung, füge das Verzeichnis zum Pfad hinzu
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    openai_agents_dir = os.path.join(parent_dir, 'openai-agents-python')
    if os.path.exists(openai_agents_dir) and openai_agents_dir not in sys.path:
        sys.path.append(openai_agents_dir)
    from research_manager import AsyncResearchManager, ResearchRequest, ResearchResponse, ResearchStatus

# Importiere den OpenAI-Runner
try:
    import openai_agent
    print("OpenAI-Agent importiert und aktiv")
except ImportError:
    print("WARNUNG: OpenAI-Agent konnte nicht importiert werden")
except Exception as e:
    print(f"WARNUNG: Fehler beim Importieren des OpenAI-Agents: {str(e)}")

# Überprüfe, ob der OpenAI API-Schlüssel gesetzt ist
if not os.environ.get("OPENAI_API_KEY"):
    print("WARNUNG: OPENAI_API_KEY ist nicht gesetzt, API wird möglicherweise nicht korrekt funktionieren.")

# API-Key-Konfiguration
API_KEY_NAME = "X-API-Key"
API_KEY_NAME_ALT = "RESEARCH_API_KEY"  # Alternativer Header-Name (für Frontend-Kompatibilität)
API_KEY = os.environ.get("RESEARCH_API_KEY")
if not API_KEY:
    print("WARNUNG: RESEARCH_API_KEY ist nicht gesetzt. Verwende Standardschlüssel 'test-api-key'")
    API_KEY = "test-api-key"  # Standardschlüssel für Entwicklung

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_header_alt = APIKeyHeader(name=API_KEY_NAME_ALT, auto_error=False)

# CORS-Konfiguration
allowed_origins = [
    "https://stefanai.de",           # Hauptdomain
    "https://researchapi.stefanai.de",  # API-Subdomain selbst
    "https://app.stefanai.de",       # App-Subdomain
    "https://www.stefanai.de",       # WWW-Subdomain
    "https://ideas.stefanai.de",     # Ideas-Subdomain (falls vorhanden)
    "https://ideas-generator.stefanai.de", # Möglicherweise andere Subdomain
    "https://dev.stefanai.de",       # Dev-Subdomain
    "http://localhost:3000",         # Lokale Entwicklung für Frontend
    "http://localhost:8000",         # Lokale Entwicklung für Backend
    "*"                              # Alles andere (Fallback)
]

# Erstelle die FastAPI-Anwendung
app = FastAPI(
    title="Research Bot API",
    description="Eine API für den OpenAI Agents Research Bot mit Unterstützung für Trend-Analysen",
    version="1.0.0",
)

# Füge CORS-Middleware hinzu
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Erstelle den Research Manager
research_manager = AsyncResearchManager()

# Dependency für API-Key-Validierung
async def get_api_key(
    api_key: str = Header(None, alias=API_KEY_NAME),
    api_key_alt: str = Header(None, alias=API_KEY_NAME_ALT),
    request: Request = None
):
    # Unterstütze beide Header-Namen
    used_key = api_key or api_key_alt
    
    if used_key is None:
        raise HTTPException(
            status_code=401,
            detail=f"API-Key fehlt. Bitte füge den Header '{API_KEY_NAME}' oder '{API_KEY_NAME_ALT}' hinzu."
        )
    if used_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Ungültiger API-Key"
        )
    return used_key


@app.get("/")
async def root():
    """Root-Endpunkt für die API."""
    return {
        "message": "Research Bot API ist aktiv",
        "version": "1.0.0",
        "documentation": "/docs",
        "modes": ["report", "trends"],
        "auth": f"API-Key erforderlich ('{API_KEY_NAME}' oder '{API_KEY_NAME_ALT}' Header)"
    }


@app.post("/research", response_model=ResearchResponse, dependencies=[Depends(get_api_key)])
async def create_research(request: ResearchRequest):
    """Startet einen neuen Research-Prozess."""
    research_id = str(uuid.uuid4())
    
    # Überprüfe, ob der Mode gültig ist
    if request.mode not in ["report", "trends"]:
        raise HTTPException(status_code=400, detail=f"Ungültiger Modus: {request.mode}. Erlaubte Modi: report, trends")
    
    response = research_manager.start_research(research_id, request.query, request.mode)
    
    # Aktualisiere die Antwort mit der Trace-ID
    status = research_manager.get_status(research_id)
    if status and status.trace_id:
        response.trace_id = status.trace_id
    
    return response


@app.get("/research/{research_id}", response_model=ResearchStatus, dependencies=[Depends(get_api_key)])
async def get_research_status(research_id: str):
    """Gibt den Status eines Research-Prozesses zurück."""
    status = research_manager.get_status(research_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Research mit ID {research_id} nicht gefunden")
    
    return status


@app.get("/research/{research_id}/report", dependencies=[Depends(get_api_key)])
async def get_research_report(research_id: str):
    """Gibt den fertigen Bericht eines Research-Prozesses zurück."""
    status = research_manager.get_status(research_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Research mit ID {research_id} nicht gefunden")
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail="Research ist noch nicht abgeschlossen")
    
    if not status.report_markdown:
        raise HTTPException(status_code=400, detail="Kein Bericht verfügbar. Möglicherweise wurde dieser Research im 'trends' Modus durchgeführt.")
    
    return JSONResponse({
        "research_id": research_id,
        "summary": status.report_summary,
        "report": status.report_markdown,
        "follow_up_questions": status.follow_up_questions
    })


@app.get("/research/{research_id}/trends", dependencies=[Depends(get_api_key)])
async def get_research_trends(research_id: str):
    """Gibt die Trends eines Research-Prozesses zurück."""
    status = research_manager.get_status(research_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Research mit ID {research_id} nicht gefunden")
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail="Research ist noch nicht abgeschlossen")
    
    if not status.trends:
        raise HTTPException(status_code=400, detail="Keine Trends verfügbar. Möglicherweise wurde dieser Research im 'report' Modus durchgeführt.")
    
    return JSONResponse({
        "research_id": research_id,
        "topic": status.topic,
        "summary": status.summary,
        "trends": [{"title": t.title, "description": t.description} for t in status.trends]
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 