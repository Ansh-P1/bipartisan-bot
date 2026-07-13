# Bipartisan Bot

A two-agent (+ moderator) LangGraph system that debates a current Indian policy
topic from right-of-center and left-of-center perspectives, grounded in live
news retrieval, and gives the user a fact-checked pros/cons synthesis.

Built as a Value Labs FDE interview demo. See `CLAUDE.md` for the full spec
and `docs/INTERVIEW_NOTES.md` for talking points.

## Architecture

```
START --> research (fetch news via Tavily/DuckDuckGo)
research --> right_opening, left_opening (parallel)
right_opening, left_opening --> right_rebuttal
right_opening, left_opening --> left_rebuttal
right_rebuttal, left_rebuttal --> moderator (structured JSON synthesis)
moderator --> guardrail (safety check)
guardrail --> END
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY (and optionally OPENAI_API_KEY, TAVILY_API_KEY)
```

At minimum you need one LLM key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).
`TAVILY_API_KEY` is optional — without it, news search falls back to
DuckDuckGo (no key required).

## Running

Headless graph run (no UI):

```bash
python -m agents.graph
```

Streamlit app:

```bash
streamlit run app.py
```

## Tests

```bash
pytest
```

Tests mock the LLM and search boundary, so they run without API keys or
network access.

## Evaluation harness (smoke test)

```bash
python -m scripts.eval_topics
python -m scripts.eval_topics --out eval_report.json
```

Runs the real graph (real API calls, real cost) across five preset topics
and flags gross regressions: a lopsided word-count ratio between sides
(one agent's response collapsing or refusing), a failed guardrail, or a
topic with zero cited sources. This is a **smoke test, not a bias
benchmark** — it catches "something broke," not "the debate is politically
fair." See `docs/INTERVIEW_NOTES.md` for why that distinction matters.

## File structure

```
bipartisan-bot/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── app.py
├── agents/
│   ├── state.py       # DebateState TypedDict schema
│   ├── prompts.py      # All debate/moderator/guardrail prompts
│   ├── tools.py         # search_news() — Tavily primary, DDG fallback
│   ├── llm.py            # get_llm(role) factory — Anthropic default, OpenAI fallback
│   └── graph.py            # LangGraph StateGraph wiring
├── docs/
│   └── INTERVIEW_NOTES.md
├── scripts/
│   └── eval_topics.py     # Balance/regression smoke test across preset topics
└── tests/
    └── test_graph.py
```

## Known limitations

- No true bias audit — `scripts/eval_topics.py` is a regression smoke test
  (word-count balance, guardrail pass rate, source count), not a measured
  bias benchmark against human-labeled ground truth.
- No caching or rate-limiting on the news tool — repeated demo runs will
  re-fetch and re-spend tokens.
- Single-turn only — no follow-up Q&A within a debate once it's rendered.
- Guardrail is a single LLM call, not a dedicated classifier — fine for a
  demo, not for production scale.
