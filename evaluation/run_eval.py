"""
FILE PURPOSE: Offline Retrieval Quality Evaluation

This file measures whether the retriever ranks the expected source document
first for a set of labelled questions. It is the retrieval regression gate
used in CI.

Metrics:
- hit@1: share of questions whose top result comes from the expected source.
- MRR (mean reciprocal rank): average of 1/rank of the first correct source
  among the retrieved chunks, using top_k results. 0 when it is not retrieved.

The sample corpus is small, so top-k hit rates are not informative. Hit@1 and
MRR are used because they reject retrievers that merely return everything.

Usage:

    python -m rag.ingest
    python -m evaluation.run_eval --min-hit-rate 0.75

The process exits with status 1 when hit@1 falls below the threshold.
"""

# Import argparse for command-line options.
import argparse

# Import json to read the golden set and print the report.
import json

# Import sys to return a non-zero exit code when the gate fails.
import sys

# Import Path for locating the default golden set beside this file.
from pathlib import Path

# Import the retriever used by the Researcher Agent.
from rag.retriever import retrieve_context


# Default labelled question file stored beside this module.
DEFAULT_GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.jsonl"


def load_golden_set(path: Path) -> list[dict]:
    """
    Load labelled questions from a JSON Lines file.

    Args:
        path:
            File where each line holds a question and its expected source.

    Returns:
        A list of dictionaries with `question` and `expected_source` keys.
    """

    # Parse every non-empty line as one JSON object.
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evaluate_retrieval(examples: list[dict], top_k: int) -> dict:
    """
    Score the retriever against labelled examples.

    Args:
        examples:
            Labelled questions with the expected source document.

        top_k:
            Number of chunks retrieved per question.

    Returns:
        Aggregate metrics and one result row per question.
    """

    # Collect a row per question and the running totals.
    rows: list[dict] = []
    reciprocal_ranks: list[float] = []
    hits_at_1 = 0

    for example in examples:

        # Retrieve the top chunks for this question.
        retrieved = retrieve_context(example["question"], top_k=top_k)
        sources = [item["source"] for item in retrieved]

        # Find the rank of the first chunk from the expected source (1-based).
        rank = next(
            (position for position, source in enumerate(sources, start=1)
             if source == example["expected_source"]),
            None,
        )

        # Credit a top-1 hit and accumulate the reciprocal rank.
        if rank == 1:
            hits_at_1 += 1
        reciprocal_ranks.append(1 / rank if rank else 0.0)

        rows.append({
            "question": example["question"],
            "expected_source": example["expected_source"],
            "top_source": sources[0] if sources else None,
            "rank": rank,
        })

    # Report the aggregate metrics alongside the per-question rows.
    total = len(examples)
    return {
        "questions": total,
        "hit_at_1": round(hits_at_1 / total, 4) if total else 0.0,
        "mrr": round(sum(reciprocal_ranks) / total, 4) if total else 0.0,
        "rows": rows,
    }


def main() -> int:
    """Run the retrieval evaluation and return a process exit code."""

    # Define the command-line options.
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality.")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--min-hit-rate", type=float, default=0.75)
    args = parser.parse_args()

    # Score the retriever and print the full report.
    report = evaluate_retrieval(load_golden_set(args.golden), top_k=args.top_k)
    print(json.dumps(report, indent=2))

    # Fail the gate when top-1 accuracy drops below the threshold.
    if report["hit_at_1"] < args.min_hit_rate:
        print(
            f"FAIL: hit@1 {report['hit_at_1']} is below {args.min_hit_rate}",
            file=sys.stderr,
        )
        return 1

    print(f"PASS: hit@1 {report['hit_at_1']} meets {args.min_hit_rate}")
    return 0


# Run the evaluation only when this file is executed directly.
if __name__ == "__main__":
    sys.exit(main())
