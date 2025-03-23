# Research Bot API

Eine API für den OpenAI Agents Research Bot, basierend auf dem original Research Bot aus der OpenAI Agents Python Repository. Die API unterstützt zwei Modi:

1. **Report-Modus**: Generiert einen ausführlichen Bericht zum angegebenen Thema
2. **Trend-Modus**: Analysiert die 10 wichtigsten Trends zum angegebenen Thema

## Setup

1. Stelle sicher, dass du das OpenAI Agents Python Repository installiert hast:
   ```
   git clone https://github.com/openai/openai-agents-python.git
   cd openai-agents-python
   python -m venv env
   source env/bin/activate
   pip install -e ".[voice]"
   ```

2. Installiere die zusätzlichen Abhängigkeiten für die API:
   ```
   pip install fastapi uvicorn python-dotenv
   ```

3. Setze deinen OpenAI API Key in der `.env` Datei:
   ```
   # Bearbeite die .env Datei
   nano research_api/.env
   ```

4. Konfiguriere einen API-Key für die Authentifizierung in deiner `.env` Datei:
   ```
   # .env Datei
   OPENAI_API_KEY=your-openai-api-key
   RESEARCH_API_KEY=your-secure-api-key
   ```
   
   Wenn kein API-Key angegeben wird, wird standardmäßig "test-api-key" verwendet (nur für Entwicklung!).

## Starten der API

```
cd research_api
./run.sh
```

oder manuell:

```
python api.py
```

Die API ist dann unter `http://localhost:8000` erreichbar. Die API-Dokumentation findest du unter `http://localhost:8000/docs`.

## Authentifizierung

Alle API-Endpunkte (außer der Root-Endpunkt) erfordern einen API-Key für die Authentifizierung.
Der API-Key muss im HTTP-Header `X-API-Key` übergeben werden.

Beispiel:
```
curl -H "X-API-Key: your-secure-api-key" http://localhost:8000/research/123
```

## API-Endpunkte

### 1. Forschung starten

**Endpunkt:** `POST /research`

**Headers:**
```
X-API-Key: your-secure-api-key
```

**Request-Body für Report-Modus:**
```json
{
  "query": "Wie wirkt sich künstliche Intelligenz auf die Zukunft der Arbeit aus?",
  "mode": "report"
}
```

**Request-Body für Trend-Modus:**
```json
{
  "query": "Personalmanagement in KMU",
  "mode": "trends"
}
```

**Antwort:**
```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "trace_id": "thread_abcdefg12345"
}
```

### 2. Status abrufen

**Endpunkt:** `GET /research/{research_id}`

**Headers:**
```
X-API-Key: your-secure-api-key
```

**Antwort:**
```json
{
  "trace_id": "thread_abcdefg12345",
  "status": "searching",
  "progress": 45,
  "progress_message": "Searching... 6/10 completed",
  "report_summary": null,
  "report_markdown": null,
  "follow_up_questions": null,
  "topic": null,
  "trends": null,
  "summary": null
}
```

### 3. Fertigen Bericht abrufen (Report-Modus)

**Endpunkt:** `GET /research/{research_id}/report`

**Headers:**
```
X-API-Key: your-secure-api-key
```

**Antwort:**
```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary": "Zusammenfassung des Berichts...",
  "report": "# Vollständiger Bericht in Markdown\n\n## Einleitung\n\n...",
  "follow_up_questions": [
    "Wie können Arbeitnehmer sich auf die KI-Revolution vorbereiten?",
    "Welche Branchen werden am stärksten von KI betroffen sein?"
  ]
}
```

### 4. Trend-Analyse abrufen (Trend-Modus)

**Endpunkt:** `GET /research/{research_id}/trends`

**Headers:**
```
X-API-Key: your-secure-api-key
```

**Antwort:**
```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "topic": "Personalmanagement in KMU",
  "summary": "Aktuelle Entwicklungen im Personalmanagement für kleine und mittlere Unternehmen...",
  "trends": [
    {
      "title": "KI-gestützte Rekrutierungsverfahren",
      "description": "Kleine und mittlere Unternehmen setzen zunehmend auf KI-Tools zur Vorauswahl von Bewerbern. Diese Technologien ermöglichen es, Bewerberpools effizienter zu durchsuchen und passende Kandidaten zu identifizieren."
    },
    {
      "title": "Remote-Work als Standard",
      "description": "Nach der Pandemie haben viele KMU hybride Arbeitsmodelle dauerhaft etabliert. Dies erfordert neue Kompetenzen im Personalmanagement zur Führung verteilter Teams und zur Förderung der Unternehmenskultur auf Distanz."
    },
    // ... 8 weitere Trends
  ]
}
```

## Test-Skripte

Die API enthält zwei Test-Skripte:

1. **test_api.py**: Testet den Report-Modus
   ```
   python test_api.py
   ```

2. **test_trends.py**: Testet den Trend-Modus
   ```
   python test_trends.py
   ```

## Integrationsbeispiel (JavaScript)

```javascript
// API-Key für die Authentifizierung
const API_KEY = "your-secure-api-key";

// Headers für alle Anfragen
const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
};

// Starte eine Forschungsanfrage im Trend-Modus
async function startTrendsAnalysis(topic) {
  const response = await fetch('http://localhost:8000/research', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ 
      query: topic,
      mode: "trends" 
    })
  });
  return await response.json();
}

// Prüfe den Status
async function checkStatus(researchId) {
  const response = await fetch(`http://localhost:8000/research/${researchId}`, {
    headers: headers
  });
  return await response.json();
}

// Hole die Trend-Analyse
async function getTrends(researchId) {
  const response = await fetch(`http://localhost:8000/research/${researchId}/trends`, {
    headers: headers
  });
  return await response.json();
}

// Beispiel für eine vollständige Implementierung
async function analyzeTrends(topic) {
  console.log(`Starte Trend-Analyse für "${topic}"...`);
  
  // Starte die Forschung
  const { research_id } = await startTrendsAnalysis(topic);
  
  // Prüfe den Status alle 5 Sekunden
  const statusInterval = setInterval(async () => {
    const status = await checkStatus(research_id);
    console.log(`Status: ${status.status}, Fortschritt: ${status.progress}%`);
    
    if (status.status === "completed") {
      clearInterval(statusInterval);
      
      // Hole die Trend-Analyse
      const trends = await getTrends(research_id);
      console.log("Zusammenfassung:", trends.summary);
      
      // Zeige die Trends an
      console.log("\nTOP 10 TRENDS:");
      trends.trends.forEach((trend, i) => {
        console.log(`\n${i+1}. ${trend.title}`);
        console.log(`   ${trend.description}`);
      });
    }
  }, 5000);
}

// Verwendungsbeispiel
analyzeTrends("Personalmanagement in KMU");
``` 