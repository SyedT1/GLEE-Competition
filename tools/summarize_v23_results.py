"""Create paper-ready, live-only V23 result tables from saved notebook artifacts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "notebooks" / "Glee_competition_23"
REPORT_PATH = ARTIFACT_DIR / "glee_v23_session_report.json"
EVIDENCE_PATH = ARTIFACT_DIR / "glee_v23_evidence.jsonl"
DATA_DIR = ROOT / "paper" / "data"


def load_family_summaries() -> list[dict]:
    summaries = []
    with EVIDENCE_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if event.get("event") == "v23_family_summary":
                summaries.append(event["payload"])
    if {row["family"] for row in summaries} != {
        "bargaining",
        "negotiation",
        "persuasion",
    }:
        raise RuntimeError("Expected one V23 summary for each family")
    return summaries


def main() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    summaries = load_family_summaries()
    assignments = report["assignments"]
    live_ids = {
        game_id
        for game_id, assignment in assignments.items()
        if not assignment.get("synthetic", False)
    }
    outcomes = [
        row for row in report["rating_outcomes"] if row["game_id"] in live_ids
    ]
    if len(outcomes) != 71:
        raise RuntimeError(f"Expected 71 live outcomes, found {len(outcomes)}")
    if report["action_fallbacks"] or report["telemetry"]:
        raise RuntimeError("V23 report contains a fallback or telemetry diagnostic")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    games_path = DATA_DIR / "v23_live_rating_games.csv"
    with games_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "game_id",
            "family",
            "role",
            "arm",
            "information",
            "context",
            "rating_delta",
            "rating_reward",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in outcomes:
            assignment = assignments[row["game_id"]]
            state = assignment.get("state", {})
            information = (
                "full" if state.get("complete_information") else "hidden"
            )
            writer.writerow(
                {
                    "game_id": row["game_id"],
                    "family": row["family"],
                    "role": row["role"],
                    "arm": row["arm"],
                    "information": information,
                    "context": json.dumps(row.get("context", []), separators=(",", ":")),
                    "rating_delta": f'{row["rating_delta"]:.2f}',
                    "rating_reward": f'{row["rating_reward"]:.6f}',
                }
            )

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in outcomes:
        groups[(row["family"], "all")].append(row)
        groups[(row["family"], row["role"])].append(row)

    aggregate_path = DATA_DIR / "v23_live_rating_aggregate.csv"
    with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "family",
            "role",
            "games",
            "positive",
            "negative",
            "zero",
            "rating_change",
            "mean_rating_delta",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for family in ("bargaining", "negotiation", "persuasion"):
            roles = ["all"] + sorted(
                role for fam, role in groups if fam == family and role != "all"
            )
            for role in roles:
                rows = groups[(family, role)]
                total = sum(row["rating_delta"] for row in rows)
                writer.writerow(
                    {
                        "family": family,
                        "role": role,
                        "games": len(rows),
                        "positive": sum(row["rating_delta"] > 0 for row in rows),
                        "negative": sum(row["rating_delta"] < 0 for row in rows),
                        "zero": sum(row["rating_delta"] == 0 for row in rows),
                        "rating_change": f"{total:.2f}",
                        "mean_rating_delta": f"{total / len(rows):.3f}",
                    }
                )

    summary_path = DATA_DIR / "v23_family_summaries.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "family",
            "initial_rating",
            "initial_games",
            "final_rating",
            "final_games",
            "completed",
            "rating_change",
            "peak_rating",
            "peak_drawdown",
            "stop_reason",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summaries:
            writer.writerow(
                {
                    "family": row["family"],
                    "initial_rating": f'{row["initial"]["rating"]:.2f}',
                    "initial_games": row["initial"]["games_played"],
                    "final_rating": f'{row["final"]["rating"]:.2f}',
                    "final_games": row["final"]["games_played"],
                    "completed": row["completed"],
                    "rating_change": f'{row["rating_change"]:.2f}',
                    "peak_rating": f'{row["peak_rating"]:.2f}',
                    "peak_drawdown": f'{row["peak_drawdown"]:.2f}',
                    "stop_reason": row["stop_reason"],
                }
            )

    expected = {
        ("bargaining", "all"): (11, -12.83),
        ("negotiation", "all"): (50, 177.77),
        ("persuasion", "all"): (10, -13.85),
    }
    for key, (count, total) in expected.items():
        rows = groups[key]
        if len(rows) != count or round(sum(r["rating_delta"] for r in rows), 2) != total:
            raise RuntimeError(f"Unexpected aggregate for {key}")

    print(f"Wrote {games_path.relative_to(ROOT)} ({len(outcomes)} live games)")
    print(f"Wrote {aggregate_path.relative_to(ROOT)}")
    print(f"Wrote {summary_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
