"""Balance smoke-test — runs a handful of topics through the real graph and
checks for gross imbalance, guardrail failures, or missing sourcing.

This is NOT a bias benchmark (that would need human-labeled ground truth).
It's a cheap, repeatable check that catches regressions like "the right
agent's rebuttal collapsed to one sentence" or "the guardrail is failing
on every run" before a demo. Costs real API calls — run deliberately, not
in CI on every commit.

Usage:
    python -m scripts.eval_topics
    python -m scripts.eval_topics --out eval_report.json
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from agents.graph import build_graph

EVAL_TOPICS = [
    "India's Uniform Civil Code debate",
    "Agnipath military recruitment scheme",
    "Delimitation of Lok Sabha constituencies",
    "India's new Digital Personal Data Protection Act",
    "Farm laws and MSP guarantee demands",
]

# A wildly lopsided word-count ratio between sides usually means one agent's
# prompt/response degenerated (empty rebuttal, refusal, truncation) rather
# than a genuine rhetorical difference.
BALANCE_RATIO_FLOOR = 0.4
BALANCE_RATIO_CEILING = 2.5


@dataclass
class TopicEval:
    topic: str
    ok: bool
    error: Optional[str] = None
    right_word_count: int = 0
    left_word_count: int = 0
    balance_ratio: Optional[float] = None
    balance_flagged: bool = False
    guardrail_passed: Optional[bool] = None
    guardrail_notes: Optional[str] = None
    num_sources: int = 0
    case_points_by_side: Optional[Dict[str, int]] = None


def _word_count(*texts: str) -> int:
    return sum(len(t.split()) for t in texts if t)


def evaluate_topic(graph, topic: str) -> TopicEval:
    try:
        result = graph.invoke({"topic": topic, "news_context": []})
    except Exception as exc:  # noqa: BLE001 - report, don't crash the run
        return TopicEval(topic=topic, ok=False, error=str(exc))

    right_words = _word_count(result.get("right_opening", ""), result.get("right_rebuttal", ""))
    left_words = _word_count(result.get("left_opening", ""), result.get("left_rebuttal", ""))
    ratio = (right_words / left_words) if left_words else None
    flagged = ratio is not None and not (BALANCE_RATIO_FLOOR <= ratio <= BALANCE_RATIO_CEILING)

    summary = result.get("moderator_summary") or {}
    by_side: Dict[str, int] = {}
    for point in summary.get("case_for", []) + summary.get("case_against", []):
        side = point.get("raised_by", "Unknown")
        by_side[side] = by_side.get(side, 0) + 1

    return TopicEval(
        topic=topic,
        ok=True,
        right_word_count=right_words,
        left_word_count=left_words,
        balance_ratio=round(ratio, 2) if ratio is not None else None,
        balance_flagged=flagged,
        guardrail_passed=result.get("guardrail_passed"),
        guardrail_notes=result.get("guardrail_notes"),
        num_sources=len(summary.get("sources", [])),
        case_points_by_side=by_side,
    )


def run(topics: List[str]) -> List[TopicEval]:
    graph = build_graph()
    return [evaluate_topic(graph, topic) for topic in topics]


def print_report(evals: List[TopicEval]) -> None:
    print(f"{'topic':<50} {'ratio':>6} {'guardrail':>10} {'sources':>8} {'flag':>6}")
    print("-" * 84)
    for e in evals:
        if not e.ok:
            print(f"{e.topic[:50]:<50} {'ERROR':>6} {'-':>10} {'-':>8} {'!!':>6}  ({e.error})")
            continue
        flag = "FLAG" if e.balance_flagged or e.guardrail_passed is False else ""
        print(
            f"{e.topic[:50]:<50} {str(e.balance_ratio):>6} "
            f"{str(e.guardrail_passed):>10} {e.num_sources:>8} {flag:>6}"
        )

    n = len(evals)
    ok = [e for e in evals if e.ok]
    errored = n - len(ok)
    flagged = sum(1 for e in ok if e.balance_flagged)
    guardrail_failures = sum(1 for e in ok if e.guardrail_passed is False)
    print("-" * 84)
    print(
        f"{n} topics | {errored} errored | {flagged} balance-flagged | "
        f"{guardrail_failures} guardrail failures"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=str, default=None, help="Optional path to write a JSON report to."
    )
    parser.add_argument(
        "--topics", nargs="*", default=None, help="Override the built-in topic list."
    )
    args = parser.parse_args()

    topics = args.topics or EVAL_TOPICS
    evals = run(topics)
    print_report(evals)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in evals], f, indent=2)
        print(f"\nWrote {args.out}")

    any_flagged = any(e.balance_flagged or e.guardrail_passed is False or not e.ok for e in evals)
    return 1 if any_flagged else 0


if __name__ == "__main__":
    sys.exit(main())
