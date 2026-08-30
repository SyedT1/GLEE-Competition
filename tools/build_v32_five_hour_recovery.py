"""Build V32: guarded five-hour Bargaining/Negotiation score recovery."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "GLEE_Competition_agent_v31_contextual_60_each.ipynb"
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v32_five_hour_recovery.ipynb"


CONTROLLER = r'''
LIVE_BUILD_ID = "v32-five-hour-recovery-2026-08-30"

# Authoritative dashboard snapshot supplied immediately before this build.
CURRENT_SNAPSHOT = {
    "bargaining": {"rating": 1327.2, "games_played": 324, "today": 35},
    "negotiation": {"rating": 1690.7, "games_played": 551, "today": 60},
    "persuasion": {"rating": 1770.2, "games_played": 561, "today": 11},
}
DOCUMENTED_PRE_V31 = {
    "bargaining": {"rating": 1316.73, "games_played": 289},
    "negotiation": {"rating": 1650.24, "games_played": 490},
    "persuasion": {"rating": 1790.16, "games_played": 550},
}

RECOVERY_FAMILIES = ("bargaining", "negotiation")
TARGET_ADDITIONAL = {"bargaining": 100, "negotiation": 100}
ALLOCATION_WEIGHT = {"bargaining": 0.62, "negotiation": 0.38}
MAX_TOTAL_COMPLETIONS = 150
SESSION_BUDGET_SECONDS = 4.5 * 60 * 60  # preserves a 30-minute submission buffer
MATCH_TIMEOUT_SECONDS = 240.0

# A new session is allowed little downside. All checks use authoritative ratings.
FAMILY_STOP_LOSS = {"bargaining": 12.0, "negotiation": 18.0}
FAMILY_MAX_DRAWDOWN = {"bargaining": 9.0, "negotiation": 13.0}
MIN_GAMES_BEFORE_TRAILING_STOP = 8
ROLLING_WINDOW = 6
ROLLING_STOP = {"bargaining": -7.0, "negotiation": -9.0}
MAX_NEGATIVE_STREAK = 4
ROLE_WINDOW = 5
ROLE_STOP = {"bargaining": -8.0, "negotiation": -10.0}
PORTFOLIO_STOP_LOSS = 18.0
MAX_CONSECUTIVE_TIMEOUTS = 2
RUN_LIVE = os.environ.get("GLEE_V32_RUN_LIVE", "0").strip() == "1"


def supplied_snapshot_analysis():
    rows = []
    for family in ("bargaining", "negotiation", "persuasion"):
        now = CURRENT_SNAPSHOT[family]
        before = DOCUMENTED_PRE_V31[family]
        games = now["games_played"] - before["games_played"]
        gain = now["rating"] - before["rating"]
        rows.append({
            "family": family,
            "games_since_documented_endpoint": games,
            "rating_change": round(gain, 2),
            "change_per_game": round(gain / games, 3) if games else None,
        })
    return rows


print("Live build:", LIVE_BUILD_ID)
print("Snapshot diagnosis:")
for _row in supplied_snapshot_analysis():
    print(_row)
print("RUN_LIVE:", RUN_LIVE)


def family_score_snapshot(stats, family):
    scores = stats.get("scores") or {}
    item = scores.get(family) or {}
    rating = item.get("rating")
    count = item.get("games_played", item.get("games", item.get("game_count", 0)))
    if rating is None:
        raise KeyError(f"stats missing {family} rating: {stats}")
    return {"rating": finite_float(rating), "games_played": int(count or 0)}


def negative_streak(deltas):
    streak = 0
    for value in reversed(deltas):
        if value < 0:
            streak += 1
        else:
            break
    return streak


def family_guard_reason(family, state):
    deltas = state["deltas"]
    count = len(deltas)
    cumulative = state["current_rating"] - state["initial_rating"]
    drawdown = state["peak_rating"] - state["current_rating"]
    if cumulative <= -FAMILY_STOP_LOSS[family]:
        return "family baseline stop-loss"
    if count >= MIN_GAMES_BEFORE_TRAILING_STOP and drawdown >= FAMILY_MAX_DRAWDOWN[family]:
        return "family trailing drawdown"
    if len(deltas) >= ROLLING_WINDOW and sum(deltas[-ROLLING_WINDOW:]) <= ROLLING_STOP[family]:
        return "negative rolling window"
    if negative_streak(deltas) >= MAX_NEGATIVE_STREAK:
        return "negative streak"
    for role, role_deltas in state["role_deltas"].items():
        if len(role_deltas) >= ROLE_WINDOW and sum(role_deltas[-ROLE_WINDOW:]) <= ROLE_STOP[family]:
            return f"role-local loss: {role}"
    if state["timeouts"] >= MAX_CONSECUTIVE_TIMEOUTS:
        return "repeated matchmaking timeout"
    if count >= TARGET_ADDITIONAL[family]:
        return "family target reached"
    return None


def choose_recovery_family(states):
    """Weighted-fair allocation: 62% bargaining, 38% negotiation."""
    eligible = [
        family for family in RECOVERY_FAMILIES
        if not states[family].get("stop_reason")
        and len(states[family]["deltas"]) < TARGET_ADDITIONAL[family]
    ]
    if not eligible:
        return None
    # Seed both families before momentum can influence the schedule.
    for family in RECOVERY_FAMILIES:
        if family in eligible and len(states[family]["deltas"]) < 2:
            return family
    return min(
        eligible,
        key=lambda family: (
            len(states[family]["deltas"]) / ALLOCATION_WEIGHT[family],
            RECOVERY_FAMILIES.index(family),
        ),
    )


def run_five_hour_recovery(client):
    started = time.monotonic()
    initial_stats = client.stats()
    states = {}
    for family in RECOVERY_FAMILIES:
        snap = family_score_snapshot(initial_stats, family)
        states[family] = {
            "initial_rating": snap["rating"],
            "initial_games": snap["games_played"],
            "current_rating": snap["rating"],
            "current_games": snap["games_played"],
            "peak_rating": snap["rating"],
            "deltas": [],
            "role_deltas": defaultdict(list),
            "timeouts": 0,
            "stop_reason": None,
            "checkpoints": [],
        }
    portfolio_initial = sum(states[f]["initial_rating"] for f in RECOVERY_FAMILIES)
    global_stop = None

    while True:
        elapsed = time.monotonic() - started
        completed_total = sum(len(states[f]["deltas"]) for f in RECOVERY_FAMILIES)
        portfolio_now = sum(states[f]["current_rating"] for f in RECOVERY_FAMILIES)
        if elapsed >= SESSION_BUDGET_SECONDS:
            global_stop = "time budget reached"
            break
        if completed_total >= MAX_TOTAL_COMPLETIONS:
            global_stop = "portfolio completion ceiling reached"
            break
        if portfolio_now - portfolio_initial <= -PORTFOLIO_STOP_LOSS:
            global_stop = "portfolio stop-loss"
            break

        for family in RECOVERY_FAMILIES:
            if not states[family]["stop_reason"]:
                states[family]["stop_reason"] = family_guard_reason(family, states[family])
        family = choose_recovery_family(states)
        if family is None:
            global_stop = "all family guards closed"
            break

        fallback_before = len(ACTION_FALLBACK_LOG)
        telemetry_before = len(TELEMETRY_LOG)
        state = states[family]
        print(
            f"{family}: recovery game {len(state['deltas']) + 1}; "
            f"session total {completed_total}; elapsed {elapsed / 60:.1f} min"
        )
        report = run_one_queue_assignment(
            client, strategy, family, match_timeout=MATCH_TIMEOUT_SECONDS
        )
        before = family_score_snapshot(report["before"], family)
        after = family_score_snapshot(report["after"], family)
        count_delta = after["games_played"] - before["games_played"]
        rating_delta = after["rating"] - before["rating"]
        new_fallbacks = len(ACTION_FALLBACK_LOG) - fallback_before
        new_telemetry = len(TELEMETRY_LOG) - telemetry_before

        harvested = harvest_completed_games(client)
        credited = credit_rating_delta(
            report["assigned_ids"], family,
            before["rating"], after["rating"], count_delta,
        )
        checkpoint = {
            "family": family,
            "count_delta": count_delta,
            "rating_delta": round(rating_delta, 6),
            "assigned_ids": report["assigned_ids"],
            "assignment_overshoot": report["assignment_overshoot"],
            "harvested_count": len(harvested),
            "rating_credit": credited,
            "new_action_fallbacks": new_fallbacks,
            "new_telemetry": new_telemetry,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        state["checkpoints"].append(checkpoint)
        append_jsonl("v32_recovery_checkpoint", checkpoint)
        display(checkpoint)

        if report["assignment_overshoot"] > 0 or new_fallbacks or new_telemetry:
            global_stop = (
                "assignment overshoot" if report["assignment_overshoot"] > 0 else
                "live action fallback" if new_fallbacks else "new telemetry diagnostic"
            )
            break
        if count_delta < 0 or count_delta > 1:
            global_stop = f"unsafe authoritative count delta: {count_delta}"
            break
        if count_delta == 0:
            state["timeouts"] += 1
            state["stop_reason"] = family_guard_reason(family, state)
            continue

        state["timeouts"] = 0
        state["current_rating"] = after["rating"]
        state["current_games"] = after["games_played"]
        state["peak_rating"] = max(state["peak_rating"], after["rating"])
        state["deltas"].append(rating_delta)
        if len(report["assigned_ids"]) == 1:
            assignment = POLICY_ASSIGNMENTS.get(report["assigned_ids"][0], {})
            role = str(assignment.get("role", "unknown"))
            state["role_deltas"][role].append(rating_delta)
        state["stop_reason"] = family_guard_reason(family, state)

    final_stats = client.stats()
    summary = {
        "build_id": LIVE_BUILD_ID,
        "global_stop": global_stop,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "families": {},
    }
    for family in RECOVERY_FAMILIES:
        final = family_score_snapshot(final_stats, family)
        state = states[family]
        summary["families"][family] = {
            "initial_rating": state["initial_rating"],
            "final_rating": final["rating"],
            "rating_change": round(final["rating"] - state["initial_rating"], 6),
            "completed": final["games_played"] - state["initial_games"],
            "peak_rating": state["peak_rating"],
            "peak_drawdown": round(state["peak_rating"] - final["rating"], 6),
            "stop_reason": state["stop_reason"],
            "role_rating_changes": {
                role: round(sum(values), 6)
                for role, values in state["role_deltas"].items()
            },
            "checkpoints": state["checkpoints"],
        }
    append_jsonl("v32_recovery_summary", summary)
    return summary


def run_v32_controller_tests():
    def mock_state(rating=1000.0):
        return {
            "initial_rating": rating, "current_rating": rating,
            "peak_rating": rating, "deltas": [],
            "role_deltas": defaultdict(list), "timeouts": 0,
            "stop_reason": None,
        }

    states = {family: mock_state() for family in RECOVERY_FAMILIES}
    assert choose_recovery_family(states) == "bargaining"
    states["bargaining"]["deltas"] = [1.0, 1.0]
    assert choose_recovery_family(states) == "negotiation"

    losing = mock_state()
    losing["deltas"] = [-2.0, -2.0, -2.0, -2.0]
    losing["current_rating"] = 992.0
    assert family_guard_reason("bargaining", losing) == "negative streak"

    role_loss = mock_state()
    role_loss["deltas"] = [1.0, -2.0, 1.0, -2.0, -2.0]
    role_loss["current_rating"] = 996.0
    role_loss["role_deltas"]["player_2"] = [-2.0] * 5
    assert family_guard_reason("bargaining", role_loss) == "role-local loss: player_2"
    assert "persuasion" not in RECOVERY_FAMILIES
    assert abs(sum(ALLOCATION_WEIGHT.values()) - 1.0) < 1e-12
    print("All V32 allocation, loss-guard, role-guard, and scope tests passed.")


run_v32_controller_tests()

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    v32_recovery_summary = run_five_hour_recovery(client)
    display(v32_recovery_summary)
    report_paths = export_session_report(
        "glee_v32_session_report.json", "glee_v32_rating_outcomes.csv"
    )
    print("Session reports:", report_paths)
else:
    print("Live matchmaking disabled. Set GLEE_V32_RUN_LIVE=1 only for the live run.")
'''


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            cell.source = cell.source.replace("glee_v31_", "glee_v32_")
            cell.source = cell.source.replace("GLEE_V31_", "GLEE_V32_")

    notebook.cells[0].source = """# GLEE V32 — guarded five-hour score recovery

This notebook addresses the supplied live snapshot of Bargaining 1327.2 after
324 games, Negotiation 1690.7 after 551, and Persuasion 1770.2 after 561.

The key evidence is that the immediately preceding contextual portfolio gained
about 10.47 Bargaining points over 35 games and 40.46 Negotiation points over 61
games, while Persuasion lost about 19.96 over 11. V32 therefore freezes the
currently profitable V31 Bargaining and Negotiation policies, exposes no
Persuasion games, and changes the operational layer only.

The controller admits one assignment at a time for at most 4.5 hours, allocates
62% of opportunities to the lower Bargaining score and 38% to the higher-yield
Negotiation score, and stops on family, rolling-window, streak, role-local,
portfolio, timeout, fallback, telemetry, or overshoot evidence. `RUN_LIVE` is
off unless `GLEE_V32_RUN_LIVE=1` is explicitly set before execution.

This is a risk-managed attempt to improve the two low categories; no heuristic
can guarantee a rating increase against changing opponents and configurations.
"""

    # Keep the proven one-queue primitive and replace V31's sequential runner.
    live_cell = notebook.cells[37]
    marker = 'LIVE_BUILD_ID = "v31-contextual-60-each-2026-08-29"'
    if marker not in live_cell.source:
        raise RuntimeError("V31 live-controller marker not found")
    primitive = live_cell.source.split(marker, 1)[0].rstrip()
    live_cell.source = primitive + "\n\n" + CONTROLLER.strip() + "\n"

    # Update synthetic isolation and inspection labels.
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.source = cell.source.replace(
                '("v28-", "v29-", "v30-", "v31-")',
                '("v28-", "v29-", "v30-", "v31-", "v32-")',
            )
            cell.source = cell.source.replace(
                "V31 and component-test assignments isolated",
                "V32 and component-test assignments isolated",
            )

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
