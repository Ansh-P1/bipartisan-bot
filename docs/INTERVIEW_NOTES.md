# Interview Notes — Bipartisan Bot

Talking points for walking through this project in an FDE interview.

## Why this is an "agentic AI" system, not a chatbot

The graph has two workers (Right, Left) and a moderator/guardrail supervisor
stage, wired through LangGraph's `StateGraph`. That's the actual pattern
interviewers are screening for — orchestration and shared mutable state, not
a single system prompt wrapped in a chat loop.

Worth screen-sharing `agents/graph.py` and narrating:

- **Parallel fan-out / fan-in**: `research` fans out to both openings
  concurrently; both openings fan back in before either rebuttal starts
  (each rebuttal needs the opponent's opening in shared state); both
  rebuttals fan in again before the moderator runs. This is a genuinely
  branching graph, not a linear chain — walk through why that shape is the
  right tool here (rebuttals structurally need both openings to exist first).
- **Shared mutable state**: `DebateState` is a single TypedDict that every
  node reads from and writes into. No node re-derives context another node
  already produced.
- **Terminal safety gate**: guardrail runs after the moderator, before
  anything reaches the user — a dedicated node, not a prompt instruction
  hoping the model behaves.

## Tool use / grounding

The debate is grounded in retrieved news (`agents/tools.py:search_news`),
not hallucinated. This is the RAG-for-agents story: two agents get the same
news context, so disagreements are about interpretation and values, not
different facts.

## Graceful degradation — say this out loud

Two deliberate reliability choices, both narratable in the interview as
"anticipating what breaks in production":

1. **LLM backend fallback** (`agents/llm.py`): `get_llm()` prefers Anthropic,
   falls back to OpenAI if only `OPENAI_API_KEY` is set. Not locked to one
   vendor.
2. **Search fallback** (`agents/tools.py`): Tavily is the primary search
   backend (purpose-built for agent retrieval, ranked/structured results,
   date filtering). If it fails or no `TAVILY_API_KEY` is set, it silently
   falls back to DuckDuckGo — zero API keys beyond the LLM key needed for a
   live demo to work at all. The `try/except` around Tavily is deliberate,
   not an oversight.

## Moderator output contract

The moderator returns structured JSON via `with_structured_output` +
Pydantic (`ModeratorOutput` in `agents/graph.py`), not hand-parsed text.
Note in the interview: `case_for` / `case_against` is *not* forced into
"right = pro, left = anti" — each point is tagged with who raised it
(`raised_by: Right|Left|Both`), because real Indian policy debates don't
split cleanly along that axis.

## Governance instinct

The guardrail node is a single LLM call reviewing both sides' full text for
dehumanizing language, fabricated quotes, and unsupported inflammatory
claims — deliberately lenient on ordinary political disagreement, only
flagging genuine violations. This is the "anticipate what breaks in
production" mindset: a debate app about political topics needs a safety net
before anything reaches the user, even in a demo.

## Evaluation harness — `scripts/eval_topics.py`

CLAUDE.md §13 names "no persistent eval set or automated bias audit" as a
known gap. `scripts/eval_topics.py` closes *part* of that gap, and the
honest framing of what it does and doesn't do is itself the interview
point:

- **What it checks**: runs the real graph across five preset topics and
  flags (a) a lopsided word-count ratio between Right and Left output
  (catches a degenerate/refused/truncated response — not a rhetorical
  judgment call), (b) any guardrail failure, (c) any topic with zero cited
  sources in the moderator summary.
- **What it does NOT check**: whether the content is *actually* politically
  balanced, factually accurate, or well-argued. That needs human-labeled
  ground truth and a rubric, which this project doesn't have.
- **Why build the cheap version first**: a regression smoke test that runs
  in minutes catches the failure mode that actually happens in practice
  (one agent's call errors out, refuses, or degenerates) without pretending
  to solve the much harder problem (measuring political fairness). Say this
  distinction out loud unprompted — it's the difference between "I built an
  eval" and "I understand what my eval doesn't cover."
- It deliberately lives outside `tests/` and isn't wired into CI — it costs
  real API calls, so `tests/test_graph.py` stays mocked and free while this
  stays an opt-in, deliberate run (`python -m scripts.eval_topics`).

## If asked "what would you build next"

- A real bias benchmark: human-labeled topics with a balance rubric, scored
  by a separate LLM-as-judge call — the harder version of what
  `eval_topics.py` currently fakes with word counts.
- Cache `search_news` results per topic for the demo session to avoid
  re-spending tokens on repeated runs.
- A follow-up Q&A turn that re-enters the graph with the existing debate
  state as context instead of starting over.
