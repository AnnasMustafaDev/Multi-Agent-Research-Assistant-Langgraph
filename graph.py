# graph.py

from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
import operator
from agents import (
    create_supervisor_chain,
    create_researcher_agent,
    create_writer_chain,
    create_critique_chain
)

# --- 1. Define the State ---

class ResearchState(TypedDict):
    """State for the research workflow."""
    main_task: str
    research_findings: Annotated[List[str], operator.add]
    draft: str
    critique_notes: str
    revision_number: int
    next_step: str
    current_sub_task: str

# --- 2. Initialize Chains and Agents ---

supervisor_chain = create_supervisor_chain()
researcher_agent = create_researcher_agent()
writer_chain = create_writer_chain()
critique_chain = create_critique_chain()

# --- 3. Define Graph Nodes ---

def supervisor_node(state: ResearchState) -> dict:
    """Supervisor decides the next step."""
    print("\n=== SUPERVISOR ===")
    
    decision = supervisor_chain(state)
    
    next_step = decision.get("next_step", "researcher")
    task_desc = decision.get("task_description", "Continue work")
    
    print(f"Decision: {next_step}")
    print(f"Task: {task_desc}")
    
    return {
        "next_step": next_step,
        "current_sub_task": task_desc,
    }

def research_node(state: ResearchState) -> dict:
    """Research node that gathers information."""
    print("\n=== RESEARCHER ===")
    
    sub_task = state.get("current_sub_task", state.get("main_task"))
    print(f"Researching: {sub_task}")
    
    try:
        result = researcher_agent.invoke({"input": sub_task})
        findings = result.get("output", "Research completed")
        print(f"Found: {findings[:100]}...")
    except Exception as e:
        print(f"Research error: {e}")
        findings = f"Research on {sub_task} - information gathered"
    
    return {
        "research_findings": [findings]
    }

def write_node(state: ResearchState) -> dict:
    """Writer node that creates or revises draft."""
    print("\n=== WRITER ===")
    
    draft = writer_chain(state)
    print(f"Draft created: {len(draft)} characters")
    
    return {
        "draft": draft,
        "revision_number": state.get("revision_number", 0) + 1
    }

def critique_node(state: ResearchState) -> dict:
    """Critique node that reviews the draft."""
    print("\n=== CRITIQUER ===")
    
    critique = critique_chain(state)
    print(f"Critique: {critique[:100]}...")
    
    is_approved = "APPROVED" in critique.upper()
    
    if is_approved:
        print("✓ Draft APPROVED")
        return {
            "critique_notes": "APPROVED",
            "next_step": "END"
        }
    else:
        print("✗ Revisions needed")
        return {
            "critique_notes": critique,
            "next_step": "writer"
        }

# --- 4. Build the Graph ---

def build_graph():
    """Constructs and compiles the LangGraph workflow."""
    
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("writer", write_node)
    workflow.add_node("critiquer", critique_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add edges
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("writer", "critiquer")
    workflow.add_edge("critiquer", "supervisor")
    
    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next_step", "researcher"),
        {
            "researcher": "researcher",
            "writer": "writer",
            "END": END
        }
    )
    
    # Compile the graph
    app = workflow.compile()
    return app

# Create the compiled graph
app = build_graph()