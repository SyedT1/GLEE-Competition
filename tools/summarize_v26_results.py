"""Create paper-ready, live-only V26 result tables from saved artifacts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "notebooks" / "Glee_competition_26"
REPORT_PATH = ARTIFACT_DIR / "glee_v26_session_report.json"
EVIDENCE_PATH = ARTIFACT_DIR / "glee_v26_evidence.jsonl"
DATA_DIR = ROOT / "paper" / "data"


def family_summaries() -> list[dict]:
    rows = []
    with EVIDENCE_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if event.get("event") == "v26_family_summary":
                rows.append(event["payload"])
    if {row["family"] for row in rows} != {
        "bargaining", "negotiation", "persuasion"
    }:
        raise RuntimeError("Expected all three V26 family summaries")
    return rows


def main() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    live_ids = {
        game_id for game_id, row in report["assignments"].items()
        if not row.get("synthetic", False)
    }
    outcomes = [
        row for row in report["rating_outcomes"] if row["game_id"] in live_ids
    ]
    if len(outcomes) != 73:
        raise RuntimeError(f"Expected 73 live outcomes, found {len(outcomes)}")
    if report["action_fallbacks"] or report["telemetry"]:
        raise RuntimeError("V26 contains a fallback or telemetry diagnostic")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    games_path = DATA_DIR / "v26_live_rating_games.csv"
    with games_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["game_id", "family", "role", "arm", "context",
                  "rating_delta", "rating_reward"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in outcomes:
            writer.writerow({
                "game_id": row["game_id"],
                "family": row["family"],
                "role": row["role"],
                "arm": row["arm"],
                "context": json.dumps(row.get("context", []), separators=(",", ":")),
                "rating_delta": f'{row["rating_delta"]:.2f}',
                "rating_reward": f'{row["rating_reward"]:.6f}',
            })

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in outcomes:
        groups[(row["family"], "all")].append(row)
        groups[(row["family"], row["role"])].append(row)

    aggregate_path = DATA_DIR / "v26_live_rating_aggregate.csv"
    with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["family", "role", "games", "positive", "negative", "zero",
                  "rating_change", "mean_rating_delta"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for family in ("bargaining", "negotiation", "persuasion"):
            roles = ["all"] + sorted(
                role for fam, role in groups if fam == family and role != "all"
            )
            for role in roles:
                rows = groups[(family, role)]
                total = sum(row["rating_delta"] for row in rows)
                writer.writerow({
                    "family": family,
                    "role": role,
                    "games": len(rows),
                    "positive": sum(row["rating_delta"] > 0 for row in rows),
                    "negative": sum(row["rating_delta"] < 0 for row in rows),
                    "zero": sum(row["rating_delta"] == 0 for row in rows),
                    "rating_change": f"{total:.2f}",
                    "mean_rating_delta": f"{total / len(rows):.3f}",
                })

    summaries_path = DATA_DIR / "v26_family_summaries.csv"
    with summaries_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["family", "initial_rating", "initial_games", "final_rating",
                  "final_games", "completed", "rating_change", "peak_rating",
                  "peak_drawdown", "stop_reason"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in family_summaries():
            writer.writerow({
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
            })

    expected = {
        ("bargaining", "all"): (11, 10.10),
        ("negotiation", "all"): (46, 47.41),
        ("persuasion", "all"): (16, 14.56),
    }
    for key, (count, total) in expected.items():
        rows = groups[key]
        if len(rows) != count or round(sum(r["rating_delta"] for r in rows), 2) != total:
            raise RuntimeError(f"Unexpected V26 aggregate for {key}")

    print(f"Wrote {games_path.relative_to(ROOT)} ({len(outcomes)} live games)")
    print(f"Wrote {aggregate_path.relative_to(ROOT)}")
    print(f"Wrote {summaries_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
