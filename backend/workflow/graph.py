from langgraph.graph import StateGraph, END
from backend.workflow.state import GraphState
from backend.workflow.nodes.planner import planner_node
from backend.workflow.nodes.researcher import researcher_node
from backend.workflow.nodes.analyst import analyst_node
from backend.workflow.nodes.qa_check import qa_check_node
from backend.workflow.nodes.reporter import reporter_node
from backend.config import settings

def route_after_qa(state: GraphState) -> str:
    """Conditional routing function based on quality score and retry limit."""
    quality_score = state.get("quality_score", 1.0)
    retry_count = state.get("retry_count", 0)
    
    # Check if there is an error in state; if so, shortcut to END
    if state.get("error"):
        return "reporter" 
        
    if quality_score >= settings.QA_QUALITY_THRESHOLD:
        return "reporter"
        
    if retry_count < settings.MAX_RETRY_COUNT:
        return "researcher"
        
    return "reporter"

# Define workflow graph
workflow = StateGraph(GraphState)

# Add all nodes
workflow.add_node("planner", planner_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("qa_check", qa_check_node)
workflow.add_node("reporter", reporter_node)

# Set entry point and static edges
workflow.set_entry_point("planner")
workflow.add_edge("planner", "researcher")
workflow.add_edge("researcher", "analyst")
workflow.add_edge("analyst", "qa_check")

# Add conditional routing after QA Check
workflow.add_conditional_edges(
    "qa_check",
    route_after_qa,
    {
        "researcher": "researcher",
        "reporter": "reporter"
    }
)

# Connect reporter to END
workflow.add_edge("reporter", END)

# Compile graph
graph = workflow.compile()
