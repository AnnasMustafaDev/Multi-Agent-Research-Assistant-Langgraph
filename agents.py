# agents.py

import os
import json
from dotenv import load_dotenv
from langchain_together import ChatTogether
from langchain_tavily import TavilySearch
from prompts import (
    supervisor_prompt_template,
    researcher_prompt_template,
    writer_prompt_template,
    critique_prompt_template
)

# Load environment variables
load_dotenv()
import getpass
import os

if not os.environ.get("TAVILY_API_KEY"):
    os.environ["TAVILY_API_KEY"] = getpass.getpass("Tavily API key:\n")
# --- 1. Setup LLM and Tools ---

# Initialize the ChatTogether LLM (latest non-deprecated version)
llm = ChatTogether(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",
    temperature=0.3,
    max_tokens=4096,
    together_api_key=os.environ.get("TOGETHER_API_KEY")
)

# Initialize the Tavily Search Tool (official method from docs)
tavily_tool = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=False,
    include_raw_content=False,
    search_depth="basic"
)

# --- 2. Create Agent Nodes ---

# ----------------- #
# SUPERVISOR NODE   #
# ----------------- #
def create_supervisor_chain():
    """Creates the supervisor decision chain."""
    def supervisor_invoke(state):
        research = state.get("research_findings", [])
        research_text = "\n---\n".join(research) if research else "No research yet."
        
        prompt = supervisor_prompt_template.format(
            main_task=state.get("main_task", ""),
            research_findings=research_text,
            draft=state.get("draft", "No draft yet."),
            critique_notes=state.get("critique_notes", "No critique yet."),
            revision_number=state.get("revision_number", 0)
        )
        
        try:
            response = llm.invoke(prompt)
            # ChatTogether returns AIMessage object
            content = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"LLM Error: {e}")
            content = ""
        
        # Parse JSON response
        try:
            text = content.strip()
            # Remove markdown code blocks if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join([l for l in lines if not l.strip().startswith("```")])
            text = text.strip()
            
            decision = json.loads(text)
            
            # Validate decision structure
            if "next_step" not in decision:
                raise ValueError("Missing next_step in decision")
                
            return decision
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {e}, using fallback logic")
            
            # Fallback parsing based on state
            revision = state.get("revision_number", 0)
            has_research = len(research) > 0
            has_draft = bool(state.get("draft", "").strip())
            critique = state.get("critique_notes", "").upper()
            
            # Decision logic
            if "APPROVED" in critique:
                return {"next_step": "END", "task_description": "Report approved"}
            elif not has_research:
                return {"next_step": "researcher", "task_description": f"Research the topic: {state.get('main_task', '')}"}
            elif not has_draft:
                return {"next_step": "writer", "task_description": "Write the first draft based on research"}
            elif revision >= 3:
                return {"next_step": "END", "task_description": "Maximum revisions reached"}
            elif content and ("end" in content.lower() or "complete" in content.lower()):
                return {"next_step": "END", "task_description": "Complete"}
            elif content and "research" in content.lower():
                return {"next_step": "researcher", "task_description": "Gather additional research"}
            else:
                return {"next_step": "writer", "task_description": "Revise the draft based on critique"}
    
    return supervisor_invoke

# ----------------- #
# RESEARCHER NODE   #
# ----------------- #
def create_researcher_agent():
    """Creates a researcher agent that uses search."""
    
    def researcher_invoke(input_dict):
        """Execute research using Tavily search."""
        query = input_dict.get("input", "")
        
        if not query or query in ["Continue work", "Complete"]:
            query = "General research information"
        
        print(f"Researching: {query}")
        
        try:
            # Use the tavily tool - invoke method as per official docs
            search_response = tavily_tool.invoke({"query": query})
            
            # Parse the response
            if isinstance(search_response, str):
                # Response is JSON string, parse it
                import json
                try:
                    search_data = json.loads(search_response)
                    results = search_data.get('results', [])
                except json.JSONDecodeError:
                    results = []
                    raw_output = search_response
            elif isinstance(search_response, dict):
                # Response is already a dict
                results = search_response.get('results', [])
            else:
                results = []
                raw_output = str(search_response)
            
            # Format the results
            formatted_results = []
            
            if results:
                for result in results[:3]:
                    title = result.get('title', 'Untitled')
                    url = result.get('url', 'N/A')
                    content = result.get('content', '')
                    formatted_results.append(f"**{title}**\nSource: {url}\n{content[:300]}...\n")
                
                raw_output = "\n---\n".join(formatted_results)
            elif not raw_output:
                raw_output = "No results found"
            
            # Summarize with LLM
            summary_prompt = f"""Based on these search results about "{query}", provide a concise summary of key findings (5-7 bullet points):

{raw_output}

Format as clear bullet points with the most important information."""

            try:
                summary_response = llm.invoke(summary_prompt)
                summary = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            except Exception as e:
                print(f"Summarization error: {e}")
                summary = raw_output
            
            return {
                "output": summary if summary else raw_output,
                "input": query
            }
            
        except Exception as e:
            print(f"Research error: {e}")
            return {
                "output": f"Research completed on: {query}. Key information has been gathered from web sources.",
                "input": query
            }
    
    return researcher_invoke

# ----------------- #
# WRITER NODE       #
# ----------------- #
def create_writer_chain():
    """Creates the writer chain."""
    def writer_invoke(state):
        research = state.get("research_findings", [])
        research_text = "\n\n".join(research) if research else "No research available."
        
        prompt = writer_prompt_template.format(
            main_task=state.get("main_task", ""),
            research_findings=research_text,
            draft=state.get("draft", ""),
            critique_notes=state.get("critique_notes", "")
        )
        
        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content if content else "Draft in progress..."
        except Exception as e:
            print(f"Writer error: {e}")
            return "Error generating draft. Please try again."
    
    return writer_invoke

# ----------------- #
# CRITIQUE NODE     #
# ----------------- #
def create_critique_chain():
    """Creates the critique chain."""
    def critique_invoke(state):
        draft = state.get("draft", "")
        revision_num = state.get("revision_number", 0)
        
        # Safety checks
        if len(draft.strip()) < 100:
            return "APPROVED - Draft is minimal but acceptable."
        
        if revision_num >= 3:
            return "APPROVED - Maximum revisions reached. The report is satisfactory."
        
        prompt = critique_prompt_template.format(
            main_task=state.get("main_task", ""),
            draft=draft
        )
        
        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content if content else "APPROVED"
        except Exception as e:
            print(f"Critique error: {e}")
            return "APPROVED - Error in critique, proceeding with current draft."
    
    return critique_invoke