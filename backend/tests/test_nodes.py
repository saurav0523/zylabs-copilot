import pytest
from unittest.mock import AsyncMock, patch
from backend.workflow.state import GraphState
from backend.workflow.nodes.planner import planner_node
from backend.workflow.nodes.researcher import researcher_node
from backend.workflow.nodes.analyst import analyst_node
from backend.workflow.nodes.qa_check import qa_check_node
from backend.workflow.nodes.reporter import reporter_node

@pytest.fixture
def base_state() -> GraphState:
    return {
        "session_id": "test-session-id",
        "company_name": "Test Company",
        "website": "https://test.com",
        "objective": "Test objective",
        "scrape_targets": [],
        "scraped_pages": [],
        "research_notes": "",
        "analysis": {},
        "quality_score": 0.0,
        "retry_count": 0,
        "report": None,
        "error": None
    }

@pytest.mark.asyncio
@patch("backend.workflow.nodes.planner.llm_service")
@patch("backend.workflow.nodes.planner.ws_manager")
async def test_planner_node_success(mock_ws, mock_llm, base_state):
    mock_llm.generate_json = AsyncMock(return_value={"targets": ["https://test.com/about"]})
    mock_ws.broadcast = AsyncMock()

    result = await planner_node(base_state)
    
    assert result["error"] is None
    assert "https://test.com/about" in result["scrape_targets"]
    assert "https://test.com" in result["scrape_targets"]
    mock_ws.broadcast.assert_called()

@pytest.mark.asyncio
@patch("backend.workflow.nodes.planner.llm_service")
@patch("backend.workflow.nodes.planner.ws_manager")
async def test_planner_node_exception(mock_ws, mock_llm, base_state):
    mock_llm.generate_json = AsyncMock(side_effect=Exception("LLM failure"))
    mock_ws.broadcast = AsyncMock()

    result = await planner_node(base_state)
    
    assert "Planner failed" in result["error"]
    mock_ws.broadcast.assert_called()

@pytest.mark.asyncio
@patch("backend.workflow.nodes.researcher.tavily_service")
@patch("backend.workflow.nodes.researcher.settings")
@patch("backend.workflow.nodes.researcher.ws_manager")
async def test_researcher_node_tavily_path(mock_ws, mock_settings, mock_tavily, base_state):
    base_state["company_name"] = "Test Company"
    mock_settings.TAVILY_API_KEY = "tvly-test"
    mock_settings.FIRECRAWL_API_KEY = ""
    mock_tavily.search = AsyncMock(return_value=[{
        "title": "Tavily Title",
        "url": "https://test.com/tavily",
        "content": "tavily content"
    }])
    mock_ws.broadcast = AsyncMock()

    result = await researcher_node(base_state)
    
    assert result["error"] is None
    assert len(result["scraped_pages"]) == 1
    assert "tavily content" in result["research_notes"]
    mock_tavily.search.assert_called()

@pytest.mark.asyncio
@patch("backend.workflow.nodes.researcher.firecrawl_service")
@patch("backend.workflow.nodes.researcher.settings")
@patch("backend.workflow.nodes.researcher.ws_manager")
async def test_researcher_node_firecrawl_path(mock_ws, mock_settings, mock_firecrawl, base_state):
    base_state["scrape_targets"] = ["https://test.com"]
    mock_settings.TAVILY_API_KEY = None
    mock_settings.FIRECRAWL_API_KEY = "fc-test"
    mock_firecrawl.scrape_url = AsyncMock(return_value={
        "markdown": "scraped content", 
        "metadata": {"title": "Test Title", "sourceURL": "https://test.com"}
    })
    mock_ws.broadcast = AsyncMock()

    result = await researcher_node(base_state)
    
    assert result["error"] is None
    assert len(result["scraped_pages"]) == 1
    assert "scraped content" in result["research_notes"]
    mock_firecrawl.scrape_url.assert_called_with("https://test.com")

@pytest.mark.asyncio
@patch("backend.workflow.nodes.researcher.tavily_service")
@patch("backend.workflow.nodes.researcher.settings")
@patch("backend.workflow.nodes.researcher.ws_manager")
async def test_researcher_node_retry_tavily_fallback(mock_ws, mock_settings, mock_tavily, base_state):
    base_state["retry_count"] = 1
    base_state["website"] = "https://test.com"
    base_state["company_name"] = "Test Company"
    mock_settings.TAVILY_API_KEY = "tvly-test"
    mock_settings.FIRECRAWL_API_KEY = "fc-test"
    mock_tavily.search = AsyncMock(return_value=[{
        "title": "Tavily Fallback Title",
        "url": "https://test.com/fallback",
        "content": "fallback content"
    }])
    mock_ws.broadcast = AsyncMock()

    result = await researcher_node(base_state)
    
    assert result["error"] is None
    assert len(result["scraped_pages"]) == 1
    assert "fallback content" in result["research_notes"]
    mock_tavily.search.assert_called()

@pytest.mark.asyncio
@patch("backend.workflow.nodes.researcher.firecrawl_service")
@patch("backend.workflow.nodes.researcher.settings")
@patch("backend.workflow.nodes.researcher.ws_manager")
async def test_researcher_node_retry_firecrawl_crawl(mock_ws, mock_settings, mock_firecrawl, base_state):
    base_state["retry_count"] = 1
    base_state["website"] = "https://test.com"
    mock_settings.TAVILY_API_KEY = None
    mock_settings.FIRECRAWL_API_KEY = "fc-test"
    mock_firecrawl.crawl_url = AsyncMock(return_value=[{
        "markdown": "crawled content",
        "metadata": {"title": "Crawled Title", "sourceURL": "https://test.com"}
    }])
    mock_ws.broadcast = AsyncMock()

    result = await researcher_node(base_state)
    
    assert result["error"] is None
    assert len(result["scraped_pages"]) == 1
    assert "crawled content" in result["research_notes"]
    mock_firecrawl.crawl_url.assert_called_with("https://test.com", limit=7)

@pytest.mark.asyncio
@patch("backend.workflow.nodes.analyst.llm_service")
@patch("backend.workflow.nodes.analyst.ws_manager")
async def test_analyst_node_success(mock_ws, mock_llm, base_state):
    mock_llm.generate_json = AsyncMock(return_value={"company_overview": "test overview", "business_signals": []})
    mock_ws.broadcast = AsyncMock()

    result = await analyst_node(base_state)
    
    assert result["error"] is None
    assert result["analysis"]["company_overview"] == "test overview"

@pytest.mark.asyncio
@patch("backend.workflow.nodes.qa_check.llm_service")
@patch("backend.workflow.nodes.qa_check.ws_manager")
async def test_qa_check_node_pass(mock_ws, mock_llm, base_state):
    mock_llm.generate_json = AsyncMock(return_value={"quality_score": 0.8, "feedback": "good"})
    mock_ws.broadcast = AsyncMock()

    result = await qa_check_node(base_state)
    
    assert result["error"] is None
    assert result["quality_score"] == 0.8
    assert result["retry_count"] == 0

@pytest.mark.asyncio
@patch("backend.workflow.nodes.qa_check.llm_service")
@patch("backend.workflow.nodes.qa_check.ws_manager")
async def test_qa_check_node_fail_trigger_retry(mock_ws, mock_llm, base_state):
    mock_llm.generate_json = AsyncMock(return_value={"quality_score": 0.5, "feedback": "thin data"})
    mock_ws.broadcast = AsyncMock()

    result = await qa_check_node(base_state)
    
    assert result["error"] is None
    assert result["quality_score"] == 0.5
    assert result["retry_count"] == 1

@pytest.mark.asyncio
@patch("backend.workflow.nodes.reporter.llm_service")
@patch("backend.workflow.nodes.reporter.ws_manager")
async def test_reporter_node_success(mock_ws, mock_llm, base_state):
    mock_llm.generate_json = AsyncMock(return_value={"company_profile": "briefing profile"})
    mock_ws.broadcast = AsyncMock()

    result = await reporter_node(base_state)
    
    assert result["error"] is None
    assert result["report"]["company_profile"] == "briefing profile"
