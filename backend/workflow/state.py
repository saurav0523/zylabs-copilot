from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    session_id: str
    company_name: str
    website: str
    objective: str
    scrape_targets: List[str]       # URLs to scrape, Planner → Researcher
    scraped_pages: List[Dict[str, Any]]  # Raw scrape outputs, Researcher → Analyst
    research_notes: str             # Researcher → Analyst (supplementary markdown/text summaries)
    analysis: Dict[str, Any]        # Structured extracted signals, Analyst → Reporter
    quality_score: float            # Quality evaluation score (0.0 - 1.0)
    retry_count: int                # Tracks routing iterations
    report: Optional[Dict[str, Any]] # Final 8-section briefing
    error: Optional[str]            # Holds errors if any node fails
