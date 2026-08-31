"""Build V21: controlled repeated micro-batches for all three GLEE families."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "20_live_three_family_robust_projection_credibility_safe_pooling.ipynb"
OUTPUT = ROOT / "notebooks" / "21_controlled_microbatches_family_stop_loss_authoritative_accounting.ipynb"


def main():
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V20", "V21").replace("v20", "v21")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V21 — controlled larger experiments

V21 runs the tested non-LLM V19/V20 heuristic policy in repeated, interruptible
micro-batches. It targets 20 authoritative completions in each family, but enters
only one queue at a time, leaves after observing an assignment, drains all assigned
games, and checks rating, game count, fallbacks, telemetry, and assignment overshoot
before re-entering matchmaking.

The purpose is to collect a larger role- and configuration-stratified sample without
returning to V11's blocking high-concurrency runner. A family-level rating stop-loss
is enforced from the initial snapshot. Overshoot, action fallback, or telemetry
failure aborts the complete session. No Qwen or other language model is used.
"""

    live_cell = None
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'LIVE_BUILD_ID = "v21-live-three-family-2026-08-28"' in cell.source:
            live_cell = cell
            break
    if live_cell is None:
        raise RuntimeError("V21 live runner cell not found")

    prefix = live_cell.source[: live_cell.source.index("LIVE_BUILD_ID =")]
    live_cell.source = prefix + r'''
LIVE_BUILD_ID = "v21-controlled-microbatches-2026-08-28"
print("Live build:", LIVE_BUILD_ID)

TARGET_COMPLETIONS = {
    "bargaining": 20,
    "negotiation": 20,
    "persuasion": 20,
}
FAMILY_STOP_LOSS = {
    "bargaining": 12.0,
    "negotiation": 12.0,
    "persuasion": 12.0,
}
MAX_QUEUE_ATTEMPTS_PER_FAMILY = 30
MATCH_TIMEOUT_SECONDS = 300.0
RUN_LIVE = True

def family_score_snapshot(stats, family):
    scores = stats.get("scores") or {}
    item = scores.get(family) or {}
    rating = item.get("rating")
    count = item.get("games_played", item.get("games", item.get("game_count", 0)))
    if rating is None:
        raise KeyError(f"stats missing {family} rating: {stats}")
    return {"rating": finite_float(rating), "games_played": int(count or 0)}

def run_controlled_family_microbatch(client, family, target, stop_loss):
    initial_stats = client.stats()
    initial = family_score_snapshot(initial_stats, family)
    checkpoints = []
    stop_reason = None
    global_abort = False

    for attempt in range(1, MAX_QUEUE_ATTEMPTS_PER_FAMILY + 1):
        current_stats = client.stats()
        current = family_score_snapshot(current_stats, family)
        completed = current["games_played"] - initial["games_played"]
        if completed >= target:
            stop_reason = "target reached"
            break

        fallback_before = len(ACTION_FALLBACK_LOG)
        telemetry_before = len(TELEMETRY_LOG)
        print(
            f"{family}: attempt {attempt}; authoritative completions "
            f"{completed}/{target}; rating change "
            f"{current['rating'] - initial['rating']:+.2f}"
        )
        report = run_one_queue_assignment(
            client, strategy, family, match_timeout=MATCH_TIMEOUT_SECONDS
        )
        after = family_score_snapshot(report["after"], family)
        before = family_score_snapshot(report["before"], family)
        count_delta = after["games_played"] - before["games_played"]
        rating_delta = after["rating"] - before["rating"]
        cumulative_count = after["games_played"] - initial["games_played"]
        cumulative_rating = after["rating"] - initial["rating"]
        new_fallbacks = len(ACTION_FALLBACK_LOG) - fallback_before
        new_telemetry = len(TELEMETRY_LOG) - telemetry_before

        harvested = harvest_completed_games(client)
        credited = credit_rating_delta(
            report["assigned_ids"], family,
            before["rating"], after["rating"], count_delta,
        )
        checkpoint = {
            "family": family, "attempt": attempt,
            "target": target, "count_delta": count_delta,
            "rating_delta": round(rating_delta, 6),
            "cumulative_count": cumulative_count,
            "cumulative_rating": round(cumulative_rating, 6),
            "assignment_overshoot": report["assignment_overshoot"],
            "assigned_ids": report["assigned_ids"],
            "harvested_count": len(harvested),
            "rating_credit": credited,
            "new_action_fallbacks": new_fallbacks,
            "new_telemetry": new_telemetry,
        }
        checkpoints.append(checkpoint)
        append_jsonl("v21_microbatch_checkpoint", checkpoint)
        display(checkpoint)

        if report["assignment_overshoot"] > 0:
            stop_reason = "assignment overshoot"
            global_abort = True
            break
        if new_fallbacks > 0:
            stop_reason = "live action fallback"
            global_abort = True
            break
        if new_telemetry > 0:
            stop_reason = "new telemetry diagnostic"
            global_abort = True
            break
        if count_delta <= 0:
            stop_reason = "no authoritative completion before timeout"
            break
        if cumulative_rating <= -abs(stop_loss):
            stop_reason = "family rating stop-loss"
            break
        if cumulative_count >= target:
            stop_reason = "target reached"
            break
    else:
        stop_reason = "maximum queue attempts reached"

    final_stats = client.stats()
    final = family_score_snapshot(final_stats, family)
    summary = {
        "family": family,
        "initial": initial,
        "final": final,
        "completed": final["games_played"] - initial["games_played"],
        "rating_change": round(final["rating"] - initial["rating"], 6),
        "stop_reason": stop_reason,
        "global_abort": global_abort,
        "checkpoints": checkpoints,
    }
    append_jsonl("v21_family_summary", summary)
    return summary

def run_v21_microbatch_tests():
    class MicroBatchClient:
        def __init__(self, rating_deltas):
            self.rating_deltas = list(rating_deltas)
            self.finished = 0
            self.rating = 1000.0
            self.queued = False
            self.delivered = False

        def stats(self):
            return {
                "active_games": 0,
                "scores": {
                    "bargaining": {
                        "rating": self.rating,
                        "games_played": self.finished,
                    }
                },
            }

        def queue(self, family):
            assert family == "bargaining"
            self.queued = True
            self.delivered = False
            return {"status": "queued"}

        def leave_queue(self, family=None):
            self.queued = False
            return {"status": "left"}

        def pending_games(self):
            if not self.queued or self.delivered:
                return []
            self.delivered = True
            return [base_game("bargaining", "offer", {
                "current_player": "player_1", "money_to_divide": 100.0,
                "delta_1": 0.90, "delta_2": 0.95,
                "complete_information": True, "round": 1,
                "max_rounds": 5, "horizon_known": True,
                "history": [], "messages_allowed": False,
            }, "player_1", f"test-micro-{self.finished + 1}")]

        def move(self, game_id, action):
            validate_action(self.pending_game_template(game_id), action)
            delta = self.rating_deltas[min(self.finished, len(self.rating_deltas) - 1)]
            self.finished += 1
            self.rating += delta
            return {"valid": True, "game_over": True}

        def pending_game_template(self, game_id):
            return base_game("bargaining", "offer", {
                "current_player": "player_1", "money_to_divide": 100.0,
                "delta_1": 0.90, "delta_2": 0.95,
                "complete_information": True, "round": 1,
                "max_rounds": 5, "horizon_known": True,
                "history": [], "messages_allowed": False,
            }, "player_1", game_id)

        def game_state(self, game_id):
            return {"player_1_payoff": 50.0}

    clean = MicroBatchClient([1.0, 1.5, -0.5])
    summary = run_controlled_family_microbatch(clean, "bargaining", 3, 12.0)
    assert summary["completed"] == 3
    assert summary["stop_reason"] == "target reached"
    assert not summary["global_abort"]

    losing = MicroBatchClient([-13.0, 5.0])
    summary = run_controlled_family_microbatch(losing, "bargaining", 5, 12.0)
    assert summary["completed"] == 1
    assert summary["stop_reason"] == "family rating stop-loss"
    assert not summary["global_abort"]
    print("V21 repeated micro-batch target and stop-loss tests passed.")

if not RUN_LIVE:
    run_v21_microbatch_tests()

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    v21_family_summaries = []
    for family, target in TARGET_COMPLETIONS.items():
        print(f"Starting controlled {family} micro-batch: target={target}")
        summary = run_controlled_family_microbatch(
            client, family, target, FAMILY_STOP_LOSS[family]
        )
        v21_family_summaries.append(summary)
        display(summary)
        if summary["global_abort"]:
            print("Aborting remaining families:", summary["stop_reason"])
            break
    report_paths = export_session_report(
        "glee_v21_session_report.json", "glee_v21_rating_outcomes.csv"
    )
    print("Family summaries completed:", len(v21_family_summaries))
    print("Session reports:", report_paths)
else:
    print("Live matchmaking is disabled by RUN_LIVE=False.")
'''

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
