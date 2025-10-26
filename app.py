# app.py

import streamlit as st
import os
from dotenv import load_dotenv
from graph import app
import time

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Multi-Agent Research Assistant 🤖",
    page_icon="🧠",
    layout="wide"
)

# --- Check for API Keys ---
def check_api_keys():
    """Check if required API keys are present."""
    together_key = os.environ.get("TOGETHER_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    
    if not together_key or not tavily_key:
        st.error("🚨 API keys not found! Please set TOGETHER_API_KEY and TAVILY_API_KEY in your .env file.")
        return False
    
    st.success("✅ API keys loaded successfully.")
    return True

# --- Header ---
st.title("Multi-Agent Research Assistant 🤖🧠")
st.markdown("""
Welcome to your intelligent research assistant! 
Enter a research topic, and a team of AI agents will collaborate to produce a comprehensive report.

**Agent Team:**
- 🎯 **Supervisor**: Manages the workflow and coordinates tasks
- 🔍 **Researcher**: Gathers information using web search
- ✍️ **Writer**: Creates and revises the research report
- 🔎 **Critiquer**: Reviews drafts and provides feedback
""")

st.divider()

# --- Show Graph Image ---
graph_path = "assets/research_graph.png"
mermaid_path = "assets/research_graph.mmd"

if os.path.exists(graph_path):
    st.image(graph_path, caption="Multi-Agent Workflow", use_column_width=True)
elif os.path.exists(mermaid_path):
    with open(mermaid_path, "r") as f:
        mermaid_code = f.read()
    st.code(mermaid_code, language="mermaid")
    st.info("💡 View this diagram at: https://mermaid.live/")
else:
    st.info("💡 Run `python visualize_graph.py` to generate workflow visualization.")

st.divider()

# --- Check API Keys ---
if not check_api_keys():
    st.stop()

# --- Main Application ---
st.header("🚀 Start Your Research")

# User input
topic = st.text_input(
    "Enter your research topic:",
    placeholder="e.g., Impact of quantum computing on cybersecurity",
    key="topic_input"
)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    max_iterations = st.slider(
        "Max Workflow Iterations",
        min_value=5,
        max_value=25,
        value=15,
        help="Maximum number of agent interactions"
    )
    
    st.divider()
    st.subheader("📋 How it works")
    st.markdown("""
    1. **Supervisor** analyzes the task
    2. **Researcher** gathers information
    3. **Writer** creates a draft
    4. **Critiquer** reviews quality
    5. Loop continues until approved
    """)

# Start button
if st.button("🚀 Start Research", type="primary", use_container_width=True):
    if not topic:
        st.error("⚠️ Please enter a research topic.")
    else:
        # Define the initial state
        initial_state = {
            "main_task": topic,
            "research_findings": [],
            "draft": "",
            "critique_notes": "",
            "revision_number": 0,
            "next_step": "",
            "current_sub_task": ""
        }
        
        # Configuration
        config = {"recursion_limit": max_iterations}
        
        st.info("🤖 Agents are starting their work...")
        
        # Create containers for live updates
        status_container = st.container()
        progress_bar = st.progress(0)
        
        # Use st.status to show progress
        with status_container:
            with st.status("🔄 Agents are collaborating...", expanded=True) as status:
                final_state = None
                step_count = 0
                
                try:
                    # Stream the graph execution
                    for step in app.stream(initial_state, config=config):
                        step_count += 1
                        progress_bar.progress(min(step_count / max_iterations, 1.0))
                        
                        # Get node name and output
                        node_name = list(step.keys())[0]
                        node_output = step[node_name]
                        final_state = node_output
                        
                        # Display node output
                        st.markdown(f"### 🤖 Agent: `{node_name.upper()}`")
                        
                        if node_name == "supervisor":
                            next_step = node_output.get('next_step', 'N/A')
                            task = node_output.get('current_sub_task', 'N/A')
                            st.markdown(f"**Decision:** {next_step}")
                            st.markdown(f"**Task:** {task}")
                        
                        elif node_name == "researcher":
                            findings = node_output.get('research_findings', [])
                            if findings:
                                latest = findings[-1]
                                st.success("✓ Research completed")
                                with st.expander("View findings"):
                                    st.write(latest)
                        
                        elif node_name == "writer":
                            draft = node_output.get('draft', '')
                            revision = node_output.get('revision_number', 0)
                            st.success(f"✓ Draft {revision} generated")
                            with st.expander("Preview draft"):
                                st.write(draft[:500] + "..." if len(draft) > 500 else draft)
                        
                        elif node_name == "critiquer":
                            critique = node_output.get('critique_notes', '')
                            if "APPROVED" in critique.upper():
                                st.success("✅ Draft APPROVED!")
                            else:
                                st.warning("📝 Revisions requested")
                                with st.expander("View critique"):
                                    st.write(critique)
                        
                        st.divider()
                        time.sleep(0.5)
                    
                    # Update status when done
                    status.update(label="✅ Work Complete!", state="complete")
                    
                except Exception as e:
                    status.update(label="❌ Error occurred", state="error")
                    st.error(f"An error occurred: {str(e)}")
                    st.exception(e)
        
        # Display final report
        if final_state and final_state.get("draft"):
            st.divider()
            st.header("📄 Final Research Report")
            
            # Display report
            st.markdown(final_state["draft"])
            
            # Display metadata
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Report Statistics")
                st.metric("Revisions", final_state.get("revision_number", 0))
                st.metric("Research Sources", len(final_state.get("research_findings", [])))
                st.metric("Word Count", len(final_state["draft"].split()))
            
            with col2:
                st.subheader("🔍 Research Findings")
                with st.expander("View all research data"):
                    for idx, finding in enumerate(final_state.get("research_findings", []), 1):
                        st.markdown(f"**Finding {idx}:**")
                        st.write(finding)
                        st.divider()
            
            # Download button
            st.download_button(
                label="📥 Download Report",
                data=final_state["draft"],
                file_name=f"research_report_{topic.replace(' ', '_')}.txt",
                mime="text/plain"
            )
        else:
            st.error("❌ No report was generated. Please try again.")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Powered by LangChain, LangGraph, Together AI & Tavily</p>
</div>
""", unsafe_allow_html=True)