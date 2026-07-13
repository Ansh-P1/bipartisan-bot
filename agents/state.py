from typing import TypedDict, List, Dict, Optional


class NewsItem(TypedDict):
    title: str
    url: str
    snippet: str
    source: str


class DebateState(TypedDict):
    topic: str
    news_context: List[NewsItem]
    right_opening: Optional[str]
    left_opening: Optional[str]
    right_rebuttal: Optional[str]
    left_rebuttal: Optional[str]
    moderator_summary: Optional[Dict]
    guardrail_passed: Optional[bool]
    guardrail_notes: Optional[str]
