"""
Report Agent
=============
The final agent in the pipeline. Takes the analysis output and
transforms it into a polished, structured report that's ready
to be shared with stakeholders.

It applies professional formatting, adds an executive summary,
and ensures the output is actionable.
"""
import time

from app.services.agents.state import AgentState
from app.services.llm.base import BaseLLMService

REPORT_SYSTEM = """You are a professional report writer for an enterprise platform.
You receive an analysis and transform it into a polished, executive-quality report.

Your report MUST include:
1. **Executive Summary** — 2-3 sentence overview of key findings
2. **Key Findings** — bullet points of the most important insights
3. **Detailed Analysis** — the full analysis, well-organized
4. **Recommendations** — actionable next steps based on the findings
5. **Sources Referenced** — list the documents used

Use professional markdown formatting. Be clear, concise, and actionable.
Write as if presenting to a senior executive."""


async def report_node(state: AgentState, llm: BaseLLMService) -> dict:
    """
    LangGraph node: Report Agent
    Reads: state["task"], state["analysis"], state["retrieved_chunks"]
    Writes: state["final_report"], state["step_log"]
    """
    start = time.monotonic()

    # Build list of unique sources
    chunks = state.get("retrieved_chunks", [])
    sources = list({c["document_title"] for c in chunks})

    user_prompt = f"""Original task: {state['task']}

Analysis findings:
{state.get('analysis', 'No analysis available.')}

Documents referenced: {', '.join(sources) if sources else 'None'}

Please generate a professional report based on this analysis."""

    response = await llm.generate(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=REPORT_SYSTEM,
        temperature=0.3,
        max_tokens=3000,
    )

    latency = (time.monotonic() - start) * 1000

    log_entry = {
        "agent": "report",
        "status": "done",
        "message": f"Generated report ({len(response.content)} characters)",
        "output": "Report ready.",
        "latency_ms": round(latency, 1),
        "tokens": response.total_tokens,
    }

    return {
        "final_report": response.content,
        "step_log": [log_entry],
        "total_tokens": state.get("total_tokens", 0) + response.total_tokens,
        "error": None,
    }
