"""Build V23 from the completed V22 live evidence."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "GLEE_Competition_agent_v22_improved_50_each.ipynb"
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v23_adaptive_defender.ipynb"


def main():
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V22", "V23").replace("v22", "v23")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V23 — adaptive high-rating defender

V23 responds to the completed V22 run. V22 persuasion was strongly positive over
50 games, so that policy is frozen. Bargaining crossed its stop-loss in six games;
V23 keeps historically stronger Bob on V4 and gives Alice a more deal-oriented,
lower-continuation-risk rule. Negotiation crossed its stop-loss after a mid-run
reversal; V23 raises surplus-protection thresholds, slows counteroffer concession,
and exits repeated infeasible unknown-horizon paths earlier.

The runner still targets 50 completions per family, but now protects both the
initial rating and the best rating reached during the session. A 20-point loss
from baseline stops a family, while a 15-point peak-to-current drawdown preserves
gains after a strong start. No language model is used.
"""

    policy_cell = None
    for cell in notebook.cells:
        if cell.cell_type == "code" and "def v23_bargaining_strategy" in cell.source:
            policy_cell = cell
            break
    if policy_cell is None:
        raise RuntimeError("V23 policy cell not found")

    # Alice: make agreement failure more expensive and stop shaving the inferred
    # responder floor. Bob remains on the established V4 implementation below.
    policy_cell.source = policy_cell.source.replace(
        "payoff_power = 1.12 if alice else 1.16",
        "payoff_power = 1.06 if alice else 1.16",
    )
    policy_cell.source = policy_cell.source.replace(
        "failure_multiplier = 1.12 if alice else 1.00",
        "failure_multiplier = 1.35 if alice else 1.00",
    )
    policy_cell.source = policy_cell.source.replace(
        "search_floor = clamp(floor - (0.006 if alice else 0.0), 0.16, 0.999)",
        "search_floor = clamp(floor + (0.015 if alice else 0.0), 0.16, 0.999)",
    )
    policy_cell.source = policy_cell.source.replace(
        "role_floor = 0.30 if player_index(me) == 1 else 0.33",
        "role_floor = 0.26 if player_index(me) == 1 else 0.33",
    )

    # Negotiation: protect a larger configuration-relative surplus share and
    # concede more slowly. Final-round individual rationality is unchanged.
    policy_cell.source = policy_cell.source.replace(
        "(0.70 - 0.14 * t) if role == \"seller\" else\n                        (0.63 - 0.12 * t)",
        "(0.72 - 0.12 * t) if role == \"seller\" else\n                        (0.66 - 0.10 * t)",
    )
    policy_cell.source = policy_cell.source.replace(
        "own_capture = clamp(base_capture, 0.50, 0.76)",
        "own_capture = clamp(base_capture, 0.54, 0.80)",
    )
    policy_cell.source = policy_cell.source.replace(
        "(0.66 - 0.13 * t) if role == \"seller\" else\n                 (0.59 - 0.11 * t)",
        "(0.70 - 0.11 * t) if role == \"seller\" else\n                 (0.64 - 0.09 * t)",
    )
    policy_cell.source = policy_cell.source.replace(
        "if profitable and stalls >= 2:",
        "if profitable and stalls >= 3:",
    )
    policy_cell.source = policy_cell.source.replace(
        "if not profitable and stalls >= 3 and not state.get(\"horizon_known\"):",
        "if not profitable and stalls >= 2 and not state.get(\"horizon_known\"):",
    )
    policy_cell.source = policy_cell.source.replace(
        "(0.76 if role == \"seller\" else 0.71) - 0.16 * t - 0.10 * min(stalls, 2)",
        "(0.80 if role == \"seller\" else 0.76) - 0.13 * t - 0.08 * min(stalls, 2)",
    )
    policy_cell.source = policy_cell.source.replace(
        "minimum_capture = 0.47 + 0.06 * (1.0 - t)",
        "minimum_capture = 0.52 + 0.06 * (1.0 - t)",
    )
    policy_cell.source = policy_cell.source.replace(
        "blend = clamp(0.28 + 0.44 * t + 0.10 * min(stalls, 2), 0.0, 0.82)",
        "blend = clamp(0.22 + 0.38 * t + 0.08 * min(stalls, 2), 0.0, 0.70)",
    )

    # Replace the inherited V23 portfolio footer with the new role-aware map.
    footer = r'''

def v23_role_aware_bargaining(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) == 2:
        return bargaining_strategy(game)       # Bob: exact V4 champion
    return v23_bargaining_strategy(game)       # Alice: deal-oriented repair

STRATEGIES["bargaining"] = v23_role_aware_bargaining
STRATEGIES["negotiation"] = v23_negotiation_strategy
STRATEGIES["persuasion"] = v23_persuasion_strategy  # frozen V22 winner
print("V23 portfolio: role-aware bargaining + defensive negotiation + frozen persuasion.")
'''
    marker = "# Evidence-backed family portfolio after the V21 live run."
    # The comment was version-neutral in V22 and remains present after replacement.
    if marker not in policy_cell.source:
        marker = "# Evidence-backed family portfolio after the V23 live run."
    if marker in policy_cell.source:
        policy_cell.source = policy_cell.source[: policy_cell.source.index(marker)] + footer
    else:
        raise RuntimeError("V23 portfolio footer not found")

    # The V23 bargaining property test may use either V4 (Bob) or V23 (Alice).
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'V23 synthetic property assignments isolated' in cell.source:
            # Existing allowed-arm assertion already permits V23_ARM and v4_safe.
            break
    else:
        raise RuntimeError("V23 test cell not found")

    live_cell = None
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'LIVE_BUILD_ID = "v23-improved-50-each-2026-08-28"' in cell.source:
            live_cell = cell
            break
    if live_cell is None:
        raise RuntimeError("V23 live cell not found")

    live_cell.source = live_cell.source.replace(
        'LIVE_BUILD_ID = "v23-improved-50-each-2026-08-28"',
        'LIVE_BUILD_ID = "v23-adaptive-defender-2026-08-28"',
    )
    live_cell.source = live_cell.source.replace(
        "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 70",
        "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 70\nFAMILY_MAX_DRAWDOWN = 15.0",
    )
    live_cell.source = live_cell.source.replace(
        "checkpoints = []\n    stop_reason = None",
        "checkpoints = []\n    peak_rating = initial[\"rating\"]\n    stop_reason = None",
    )
    live_cell.source = live_cell.source.replace(
        "cumulative_rating = after[\"rating\"] - initial[\"rating\"]\n        new_fallbacks",
        "cumulative_rating = after[\"rating\"] - initial[\"rating\"]\n"
        "        peak_rating = max(peak_rating, after[\"rating\"])\n"
        "        peak_drawdown = peak_rating - after[\"rating\"]\n"
        "        new_fallbacks",
    )
    live_cell.source = live_cell.source.replace(
        '"cumulative_rating": round(cumulative_rating, 6),\n            "assignment_overshoot"',
        '"cumulative_rating": round(cumulative_rating, 6),\n'
        '            "peak_rating": round(peak_rating, 6),\n'
        '            "peak_drawdown": round(peak_drawdown, 6),\n'
        '            "assignment_overshoot"',
    )
    live_cell.source = live_cell.source.replace(
        'if cumulative_rating <= -abs(stop_loss):\n            stop_reason = "family rating stop-loss"\n            break',
        'if cumulative_rating <= -abs(stop_loss):\n'
        '            stop_reason = "family rating stop-loss"\n'
        '            break\n'
        '        if peak_drawdown >= FAMILY_MAX_DRAWDOWN:\n'
        '            stop_reason = "trailing rating drawdown"\n'
        '            break',
    )
    live_cell.source = live_cell.source.replace(
        '"rating_change": round(final["rating"] - initial["rating"], 6),\n        "stop_reason"',
        '"rating_change": round(final["rating"] - initial["rating"], 6),\n'
        '        "peak_rating": round(peak_rating, 6),\n'
        '        "peak_drawdown": round(peak_rating - final["rating"], 6),\n'
        '        "stop_reason"',
    )

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
