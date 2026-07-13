import json
from typing import Dict, List

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from agents.llm import get_llm
from agents.prompts import (
    GUARDRAIL_PROMPT,
    LEFT_AGENT_PROMPT,
    MODERATOR_PROMPT,
    REBUTTAL_PROMPT,
    RIGHT_AGENT_PROMPT,
)
from agents.state import DebateState, NewsItem
from agents.tools import search_news


def _format_news_context(news_context: List[NewsItem]) -> str:
    if not news_context:
        return "No news context available."
    lines = []
    for item in news_context:
        lines.append(f"- {item['title']} ({item['source']}): {item['snippet']} [{item['url']}]")
    return "\n".join(lines)


class CasePoint(BaseModel):
    point: str
    raised_by: str = Field(description="Right|Left|Both")
    source_url: str = ""


class SourceEntry(BaseModel):
    title: str
    url: str
    source: str


class ModeratorOutput(BaseModel):
    topic_summary: str
    case_for: List[CasePoint]
    case_against: List[CasePoint]
    common_ground: List[str]
    key_facts: List[str]
    sources: List[SourceEntry]


class GuardrailOutput(BaseModel):
    passed: bool
    notes: str


def research_node(state: DebateState) -> Dict:
    news = search_news(state["topic"])
    return {"news_context": news}


def right_opening_node(state: DebateState) -> Dict:
    llm = get_llm("right")
    prompt = RIGHT_AGENT_PROMPT.format(
        topic=state["topic"],
        news_context=_format_news_context(state["news_context"]),
    )
    response = llm.invoke(prompt)
    return {"right_opening": response.content}


def left_opening_node(state: DebateState) -> Dict:
    llm = get_llm("left")
    prompt = LEFT_AGENT_PROMPT.format(
        topic=state["topic"],
        news_context=_format_news_context(state["news_context"]),
    )
    response = llm.invoke(prompt)
    return {"left_opening": response.content}


def right_rebuttal_node(state: DebateState) -> Dict:
    llm = get_llm("right")
    prompt = REBUTTAL_PROMPT.format(
        topic=state["topic"],
        opponent_opening=state["left_opening"],
    )
    response = llm.invoke(prompt)
    return {"right_rebuttal": response.content}


def left_rebuttal_node(state: DebateState) -> Dict:
    llm = get_llm("left")
    prompt = REBUTTAL_PROMPT.format(
        topic=state["topic"],
        opponent_opening=state["right_opening"],
    )
    response = llm.invoke(prompt)
    return {"left_rebuttal": response.content}


def moderator_node(state: DebateState) -> Dict:
    llm = get_llm("moderator").with_structured_output(ModeratorOutput)
    prompt = MODERATOR_PROMPT.format(
        topic=state["topic"],
        right_opening=state["right_opening"],
        left_opening=state["left_opening"],
        right_rebuttal=state["right_rebuttal"],
        left_rebuttal=state["left_rebuttal"],
        news_context=_format_news_context(state["news_context"]),
    )
    result: ModeratorOutput = llm.invoke(prompt)
    return {"moderator_summary": result.model_dump()}


def guardrail_node(state: DebateState) -> Dict:
    llm = get_llm("guardrail").with_structured_output(GuardrailOutput)
    right_text = f"{state['right_opening']}\n\n{state['right_rebuttal']}"
    left_text = f"{state['left_opening']}\n\n{state['left_rebuttal']}"
    prompt = GUARDRAIL_PROMPT.format(right_text=right_text, left_text=left_text)
    result: GuardrailOutput = llm.invoke(prompt)
    return {"guardrail_passed": result.passed, "guardrail_notes": result.notes}


def build_graph():
    graph = StateGraph(DebateState)

    graph.add_node("research", research_node)
    graph.add_node("right_opening", right_opening_node)
    graph.add_node("left_opening", left_opening_node)
    graph.add_node("right_rebuttal", right_rebuttal_node)
    graph.add_node("left_rebuttal", left_rebuttal_node)
    graph.add_node("moderator", moderator_node)
    graph.add_node("guardrail", guardrail_node)

    graph.set_entry_point("research")

    # Parallel fan-out: both openings run off the research node.
    graph.add_edge("research", "right_opening")
    graph.add_edge("research", "left_opening")

    # Fan-in before fan-out: each rebuttal needs both openings in state
    # (own opening to continue from, opponent's opening to respond to).
    graph.add_edge("right_opening", "right_rebuttal")
    graph.add_edge("left_opening", "right_rebuttal")
    graph.add_edge("right_opening", "left_rebuttal")
    graph.add_edge("left_opening", "left_rebuttal")

    # Fan-in: moderator waits for both rebuttals.
    graph.add_edge("right_rebuttal", "moderator")
    graph.add_edge("left_rebuttal", "moderator")

    graph.add_edge("moderator", "guardrail")
    graph.add_edge("guardrail", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({"topic": "India's new data protection bill", "news_context": []})
    print(json.dumps(result["moderator_summary"], indent=2))
    print("Guardrail passed:", result["guardrail_passed"], "-", result["guardrail_notes"])
