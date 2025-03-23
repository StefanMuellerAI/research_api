from __future__ import annotations

import asyncio
import time
import sys
import os
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

# Versuche, die benötigten Module zu importieren
try:
    from agents import Runner, custom_span, gen_trace_id, trace, Agent
except ImportError:
    # Für lokale Entwicklung, füge das Verzeichnis zum Pfad hinzu
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    openai_agents_dir = os.path.join(parent_dir, 'openai-agents-python')
    if os.path.exists(openai_agents_dir) and openai_agents_dir not in sys.path:
        sys.path.append(openai_agents_dir)
    try:
        from agents import Runner, custom_span, gen_trace_id, trace, Agent
    except ImportError:
        print("FEHLER: Die 'agents' Module konnten nicht importiert werden.")
        print("Stelle sicher, dass das openai-agents-python Paket installiert ist.")
        # Definiere Fallback-Klassen für Tests/Development
        class Runner:
            @staticmethod
            async def run(*args, **kwargs):
                return None
            
            @staticmethod
            def run_streamed(*args, **kwargs):
                return None
        
        def custom_span(name):
            class DummySpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return DummySpan()
        
        def gen_trace_id():
            import uuid
            return f"trace_{uuid.uuid4().hex[:8]}"
        
        def trace(name, trace_id=None):
            class DummyTrace:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return DummyTrace()
        
        class Agent:
            def __init__(self, **kwargs):
                self.name = kwargs.get('name', 'DummyAgent')

# Versuche, die Research Bot Module zu importieren
try:
    from examples.research_bot.agents.planner_agent import WebSearchItem, WebSearchPlan, planner_agent
    from examples.research_bot.agents.search_agent import search_agent
    from examples.research_bot.agents.writer_agent import ReportData, writer_agent
except ImportError:
    # Fallback-Definitionen für Vercel-Deployment
    class WebSearchItem(BaseModel):
        query: str = Field(..., description="Die Suchanfrage")
        reason: str = Field(..., description="Grund für die Suche")
    
    class WebSearchPlan(BaseModel):
        searches: List[WebSearchItem] = Field(..., description="Liste der geplanten Suchen")
    
    class ReportData(BaseModel):
        short_summary: str = Field(..., description="Kurze Zusammenfassung")
        markdown_report: str = Field(..., description="Vollständiger Bericht in Markdown")
        follow_up_questions: List[str] = Field(..., description="Weiterführende Fragen")
    
    # Dummy-Agenten für Tests/Development
    planner_agent = Agent(name="PlannerAgent")
    search_agent = Agent(name="SearchAgent")
    writer_agent = Agent(name="WriterAgent")


# Neue Modelle für die Trend-Analyse
class Trend(BaseModel):
    title: str = Field(..., description="Titel des Trends")
    description: str = Field(..., description="Kurze Beschreibung des Trends (2-3 Sätze)")


class TrendAnalysisData(BaseModel):
    topic: str = Field(..., description="Das analysierte Thema")
    trends: List[Trend] = Field(..., description="Liste der Top-10-Trends zu diesem Thema")
    summary: str = Field(..., description="Eine kurze Zusammenfassung des Themas und der aktuellen Lage")


# Neuer Agent für die Trend-Analyse
trends_writer_agent = Agent(
    name="TrendsWriterAgent",
    instructions="""Du bist ein Experte für die Analyse aktueller Trends. 
    Basierend auf den Suchergebnissen identifiziere genau 10 aktuelle und wichtige Trends zum angegebenen Thema.
    Jeder Trend sollte einen aussagekräftigen Titel und eine kurze Beschreibung von 2-3 Sätzen haben.
    Halte dich strikt an das vorgegebene Ausgabeformat mit genau 10 Trends.
    Die Trends sollten innovativ, aktuell und relevant für das Thema sein.
    Nutze die Suchergebnisse als Grundlage, aber ergänze durch Experteneinschätzungen, falls notwendig.
    
    Achte darauf, dass die Trends:
    1. Aktuell sind (aus den letzten 1-2 Jahren)
    2. Relevant für das spezifische Thema sind
    3. Gut verständlich beschrieben sind
    4. Einen praktischen Wert für die Zielgruppe haben
    """,
    model="gpt-4o",
    output_type=TrendAnalysisData,
)


class ResearchStatus(BaseModel):
    """Status des Research-Prozesses."""
    trace_id: Optional[str] = None
    status: str = "pending"
    progress: int = 0
    progress_message: str = "Waiting to start..."
    # Felder für den Bericht
    report_summary: Optional[str] = None
    report_markdown: Optional[str] = None
    follow_up_questions: Optional[List[str]] = None
    # Felder für die Trend-Analyse
    topic: Optional[str] = None
    trends: Optional[List[Trend]] = None
    summary: Optional[str] = None


class ResearchRequest(BaseModel):
    """Eine Anfrage für die Research API."""
    query: str = Field(..., description="Die Forschungsfrage, die beantwortet werden soll")
    callback_url: Optional[str] = Field(None, description="URL für Callback-Updates (optional)")
    mode: str = Field("report", description="Modus der Anfrage: 'report' für ausführlichen Bericht oder 'trends' für Trend-Analyse")


class ResearchResponse(BaseModel):
    """Die Antwort der Research API."""
    research_id: str
    status: str = "processing"
    trace_id: Optional[str] = None


class AsyncResearchManager:
    """Eine asynchrone Version des Research Managers für API-Verwendung."""
    
    def __init__(self):
        self.research_tasks: Dict[str, asyncio.Task] = {}
        self.research_statuses: Dict[str, ResearchStatus] = {}
        
    def start_research(self, research_id: str, query: str, mode: str = "report") -> ResearchResponse:
        """Startet einen neuen Research-Prozess."""
        
        # Initialisiere den Status
        self.research_statuses[research_id] = ResearchStatus()
        
        # Starte den Research-Prozess als Task
        self.research_tasks[research_id] = asyncio.create_task(
            self._run_research(research_id, query, mode)
        )
        
        # Erstelle die Antwort
        return ResearchResponse(
            research_id=research_id,
            status="processing"
        )
    
    def get_status(self, research_id: str) -> Optional[ResearchStatus]:
        """Gibt den aktuellen Status eines Research-Prozesses zurück."""
        return self.research_statuses.get(research_id)
    
    async def _run_research(self, research_id: str, query: str, mode: str = "report") -> None:
        """Führt den Research-Prozess asynchron aus."""
        status = self.research_statuses[research_id]
        
        try:
            trace_id = gen_trace_id()
            status.trace_id = trace_id
            
            with trace("Research trace", trace_id=trace_id):
                self._update_status(research_id, "starting", 5, "Starting research...")
                
                # Plane die Suchen
                search_plan = await self._plan_searches(research_id, query)
                
                # Führe die Suchen durch
                search_results = await self._perform_searches(research_id, search_plan)
                
                # Verarbeite die Ergebnisse je nach Modus
                if mode == "trends":
                    # Erstelle eine Trend-Analyse
                    trends_data = await self._analyze_trends(research_id, query, search_results)
                    
                    # Aktualisiere den Status mit den Trend-Daten
                    self._update_status(
                        research_id=research_id,
                        status="completed",
                        progress=100,
                        message="Trend analysis completed",
                        trends_data=trends_data
                    )
                else:
                    # Erstelle einen ausführlichen Bericht (Standardverhalten)
                    report = await self._write_report(research_id, query, search_results)
                    
                    # Aktualisiere den Status mit dem fertigen Bericht
                    self._update_status(
                        research_id=research_id,
                        status="completed",
                        progress=100,
                        message="Research completed",
                        report_data=report
                    )
        except Exception as e:
            # Fehlerbehandlung für den gesamten Forschungsprozess
            error_message = f"Error in research process: {str(e)}"
            print(error_message)
            self._update_status(research_id, "error", 0, error_message)
    
    def _update_status(
        self, 
        research_id: str, 
        status: str, 
        progress: int, 
        message: str,
        report_data: Optional[ReportData] = None,
        trends_data: Optional[TrendAnalysisData] = None
    ) -> None:
        """Aktualisiert den Status eines Research-Prozesses."""
        if research_id in self.research_statuses:
            self.research_statuses[research_id].status = status
            self.research_statuses[research_id].progress = progress
            self.research_statuses[research_id].progress_message = message
            
            # Update für Report-Daten
            if report_data is not None:
                self.research_statuses[research_id].report_summary = report_data.short_summary
                self.research_statuses[research_id].report_markdown = report_data.markdown_report
                self.research_statuses[research_id].follow_up_questions = report_data.follow_up_questions
            
            # Update für Trend-Daten
            if trends_data is not None:
                self.research_statuses[research_id].topic = trends_data.topic
                self.research_statuses[research_id].trends = trends_data.trends
                self.research_statuses[research_id].summary = trends_data.summary
    
    async def _plan_searches(self, research_id: str, query: str) -> WebSearchPlan:
        """Plant die Suchen für die Anfrage."""
        try:
            self._update_status(research_id, "planning", 10, "Planning searches...")
            
            result = await Runner.run(
                planner_agent,
                f"Query: {query}",
            )
            
            if result is None or not hasattr(result, 'final_output'):
                # Erstelle einen Fallback-Plan, wenn der Agent keine Ergebnisse liefert
                fallback_plan = WebSearchPlan(searches=[
                    WebSearchItem(query=query, reason="Direct search for the query")
                ])
                self._update_status(research_id, "planning_completed", 20, "Created fallback plan")
                return fallback_plan
            
            self._update_status(
                research_id, 
                "planning_completed", 
                20, 
                f"Will perform {len(result.final_output.searches)} searches"
            )
            
            return result.final_output_as(WebSearchPlan)
        except Exception as e:
            # Fehlerbehandlung für die Planung
            error_message = f"Error in planning: {str(e)}"
            print(error_message)
            self._update_status(research_id, "planning_error", 15, error_message)
            
            # Erstelle einen Fallback-Plan
            return WebSearchPlan(searches=[
                WebSearchItem(query=query, reason="Fallback search due to planning error")
            ])
    
    async def _perform_searches(self, research_id: str, search_plan: WebSearchPlan) -> list[str]:
        """Führt die geplanten Suchen durch."""
        with custom_span("Search the web"):
            self._update_status(research_id, "searching", 25, "Starting web searches...")
            
            num_completed = 0
            total_searches = len(search_plan.searches)
            
            if total_searches == 0:
                self._update_status(research_id, "searching_completed", 60, "No searches to perform")
                return []
            
            tasks = [asyncio.create_task(self._search(item)) for item in search_plan.searches]
            results = []
            
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    print(f"Error in search task: {str(e)}")
                
                num_completed += 1
                progress = 25 + (num_completed / total_searches) * 35  # Fortschritt von 25% auf 60%
                
                self._update_status(
                    research_id, 
                    "searching", 
                    int(progress), 
                    f"Searching... {num_completed}/{total_searches} completed"
                )
            
            self._update_status(research_id, "searching_completed", 60, "All searches completed")
            
            # Wenn keine Ergebnisse gefunden wurden, füge eine Standardnachricht hinzu
            if not results:
                results.append("No search results found. Please try a different query or check your internet connection.")
            
            return results
    
    async def _search(self, item: WebSearchItem) -> str | None:
        """Führt eine einzelne Suche durch."""
        input = f"Search term: {item.query}\nReason for searching: {item.reason}"
        try:
            result = await Runner.run(
                search_agent,
                input,
            )
            return str(result.final_output) if result and hasattr(result, 'final_output') else None
        except Exception as e:
            print(f"Error in search: {str(e)}")
            return f"Error during search for '{item.query}': {str(e)}"
    
    async def _write_report(self, research_id: str, query: str, search_results: list[str]) -> ReportData:
        """Erstellt einen Bericht aus den Suchergebnissen."""
        try:
            self._update_status(research_id, "writing", 65, "Thinking about report...")
            
            # Bereite die Eingabe vor und begrenze sie bei Bedarf
            combined_results = "\n\n".join(search_results)
            if len(combined_results) > 50000:  # Begrenze die Länge, um Tokenprobleme zu vermeiden
                combined_results = combined_results[:50000] + "... (truncated due to length)"
            
            input = f"Original query: {query}\nSummarized search results: {combined_results}"
            
            result = Runner.run_streamed(
                writer_agent,
                input,
            )
            
            # Überwache den Fortschritt
            current_progress = 70
            for step in result:
                if current_progress < 95:
                    current_progress += 1
                    if current_progress % 5 == 0:
                        self._update_status(research_id, "writing", current_progress, "Writing report...")
            
            if not hasattr(result, 'final_output'):
                # Fallback für den Fall, dass der Agent keinen Bericht erstellt
                fallback_report = ReportData(
                    short_summary=f"Brief summary of research on '{query}'",
                    markdown_report=f"# Research on {query}\n\nUnable to generate a full report. Please try again later.",
                    follow_up_questions=["What specific aspect of this topic interests you the most?"]
                )
                self._update_status(research_id, "writing_completed", 95, "Created fallback report")
                return fallback_report
            
            self._update_status(research_id, "report_completed", 95, "Report completed")
            
            return result.final_output_as(ReportData)
        except Exception as e:
            # Fehlerbehandlung für den Schreibprozess
            error_message = f"Error writing report: {str(e)}"
            print(error_message)
            self._update_status(research_id, "writing_error", 80, error_message)
            
            # Erstelle einen Fallback-Bericht
            return ReportData(
                short_summary=f"Error while researching '{query}'",
                markdown_report=f"# Error in Research Process\n\nWe encountered an error while generating your report on '{query}'. Please try again later.\n\nError details: {str(e)}",
                follow_up_questions=["Would you like to try a different query?", "Would you like to try again later?"]
            )
    
    async def _analyze_trends(self, research_id: str, query: str, search_results: list[str]) -> TrendAnalysisData:
        """Analysiert Trends aus den Suchergebnissen."""
        try:
            self._update_status(research_id, "analyzing", 65, "Analyzing trends...")
            
            # Bereite die Eingabe vor und begrenze sie bei Bedarf
            combined_results = "\n\n".join(search_results)
            if len(combined_results) > 50000:  # Begrenze die Länge, um Tokenprobleme zu vermeiden
                combined_results = combined_results[:50000] + "... (truncated due to length)"
            
            input = f"Topic for trend analysis: {query}\nSearch results: {combined_results}"
            
            result = Runner.run_streamed(
                trends_writer_agent,
                input,
            )
            
            # Überwache den Fortschritt
            current_progress = 70
            for step in result:
                if current_progress < 95:
                    current_progress += 1
                    if current_progress % 5 == 0:
                        self._update_status(research_id, "analyzing", current_progress, "Analyzing trends...")
            
            if not hasattr(result, 'final_output'):
                # Fallback für den Fall, dass der Agent keine Trends erstellt
                fallback_trends = [
                    Trend(title=f"Trend {i} for {query}", description="Unable to generate detailed trend information. Please try again later.")
                    for i in range(1, 11)
                ]
                fallback_analysis = TrendAnalysisData(
                    topic=query,
                    trends=fallback_trends,
                    summary=f"Analysis of trends related to {query}. Please try again for more detailed results."
                )
                self._update_status(research_id, "analyzing_completed", 95, "Created fallback trend analysis")
                return fallback_analysis
            
            self._update_status(research_id, "analysis_completed", 95, "Trend analysis completed")
            
            return result.final_output_as(TrendAnalysisData)
        except Exception as e:
            # Fehlerbehandlung für den Analyseprozess
            error_message = f"Error analyzing trends: {str(e)}"
            print(error_message)
            self._update_status(research_id, "analyzing_error", 80, error_message)
            
            # Erstelle eine Fallback-Analyse
            fallback_trends = [
                Trend(title=f"Error in trend analysis", description=f"We encountered an error while analyzing trends for '{query}'. Please try again later.")
                for _ in range(10)
            ]
            return TrendAnalysisData(
                topic=query,
                trends=fallback_trends,
                summary=f"Error analyzing trends for '{query}': {str(e)}"
            ) 