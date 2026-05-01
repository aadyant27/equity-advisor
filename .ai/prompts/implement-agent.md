# Prompt: Implement an Agent Node

## When to use

When implementing a new LangGraph agent node in the pipeline.

## Template

Implement backend/agents/{agent_name}.py

This is the {agent_name} node for our LangGraph pipeline.

Requirements:
{list requirements specific to this agent}

Rules:

- Import AgentState from backend.agents.state
- Return complete updated AgentState
- Append a log entry to agent_log describing what this agent did
- Load API keys from environment using python-dotenv
- If the agent fails, raise a clear exception with the reason
- Do not create any other files

## Example usage

Used for: ingestion_agent, rag_research_agent, risk_analyst_agent,
strategy_agent, report_agent

## What to review after Claude Code responds

- Are all imports correct and minimal?
- Does it return a complete AgentState not just the changed fields?
- Is there a log entry appended to agent_log?
- Are types matching state.py exactly?
- Is there error handling?
