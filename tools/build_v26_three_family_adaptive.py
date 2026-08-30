"""Build V26: improved deterministic heuristics for all three GLEE families."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "notebooks"
    / "Glee_competition_25"
    / "GLEE_Competition_agent_v25_bargaining_v23_negotiation.ipynb"
)
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v26_three_family_adaptive.ipynb"


BOB_POLICY = r'''

# ---------------------------------------------------------------------------
# V26 Bob repair: use the successful Alice architecture with Bob calibration
# ---------------------------------------------------------------------------

def v26_bob_bargaining_strategy(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) != 2:
        return v26_alice_bargaining_strategy(game)
    opponent = other_player(me)
    assign_v26(game, me)
    money = finite_float(state["money_to_divide"])
    t = round_progress(state)
    my_delta = player_delta(state, me)
    model = update_bargaining_memory(game, me, opponent, money)
    base_floor = estimate_bargaining_floor(game, state, me, opponent, model)
    demands = model["opponent_demands"][-7:]
    trend = robust_median_step(demands)
    volatility = robust_mad(demands)
    stalls = bargaining_stall_count(state, money)

    if demands:
        predicted_demand = clamp(demands[-1] + trend, 0.0, 1.0)
        behavioral_floor = predicted_demand - (0.035 + 0.020 * t)
        floor = max(model["rejected_floor"],
                    0.78 * base_floor + 0.22 * behavioral_floor)
    else:
        predicted_demand = None
        floor = base_floor
    floor = clamp(floor, 0.18, 0.90)

    if game["valid_actions"]["type"] == "offer":
        if stalls >= 3 and demands:
            cap = 0.94 if final_round(state) else 0.82
            responder_share = clamp(demands[-1], 0.20, cap)
            reason = "bob_bounded_cycle_match"
        else:
            search_floor = clamp(floor - 0.006, 0.18, 0.88)
            width = clamp(0.016 + 0.60 * volatility, 0.014, 0.044)
            failure_cost = 0.045 + 0.24 * t + 0.50 * (1.0 - my_delta)
            best = None
            for step in range(20, 189):
                responder_share = step / 200.0
                accept_probability = logistic(
                    (responder_share - search_floor + 0.007) / width
                )
                own_share = 1.0 - responder_share
                value = (accept_probability * own_share**1.16 -
                         (1.0 - accept_probability) * failure_cost)
                candidate = (value, own_share, responder_share)
                if best is None or candidate > best:
                    best = candidate
            responder_share = best[2]
            reason = "bob_surplus_protected_offer"
        responder_gain = round(money * responder_share, 8)
        own_gain = money - responder_gain
        action = {"alice_gain": responder_gain, "bob_gain": own_gain}
        if state.get("messages_allowed"):
            action["message"] = action_message(
                "This split reflects the observed demands and remaining delay cost."
            )
        return trace_v26(game, me, {
            "reason": reason, "base_floor": round(base_floor, 5),
            "floor": round(floor, 5), "trend": round(trend, 5),
            "volatility": round(volatility, 5), "stalls": stalls,
            "predicted_demand": predicted_demand,
        }, action)

    current_gain = allocation(state.get("last_offer") or {}, me)
    if current_gain is None:
        return trace_v26(game, me, {"reason": "missing_offer"}, {"decision": "reject"})
    current_share = current_gain / max(money, 1e-12)
    if final_round(state):
        decision = "accept" if current_gain > 0 else "reject"
        return trace_v26(game, me, {
            "reason": "terminal_ir", "current_share": current_share,
        }, {"decision": decision})
    if stalls >= 3 and current_share >= 0.18:
        return trace_v26(game, me, {
            "reason": "bob_bounded_cycle_accept", "current_share": current_share,
        }, {"decision": "accept"})

    favorable_concession = -trend if demands else 0.0
    wait_bonus = clamp(0.25 * favorable_concession, -0.02, 0.02)
    continuation_share = my_delta * (1.0 - floor) * clamp(
        0.80 + wait_bonus + 0.10 * t - 0.06 * stalls, 0.48, 0.92
    )
    risk_floor = max(0.18, 0.35 - 0.08 * t - 0.055 * stalls)
    required_share = max(risk_floor, continuation_share)
    decision = "accept" if current_share + 1e-12 >= required_share else "reject"
    return trace_v26(game, me, {
        "reason": "bob_surplus_protected_accept",
        "current_share": current_share, "required_share": required_share,
        "continuation_share": continuation_share, "stalls": stalls,
    }, {"decision": decision})


def v26_all_role_bargaining(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) == 1:
        return v26_alice_bargaining_strategy(game)
    return v26_bob_bargaining_strategy(game)


STRATEGIES["bargaining"] = v26_all_role_bargaining
STRATEGIES["negotiation"] = v26_negotiation_strategy
STRATEGIES["persuasion"] = v26_persuasion_strategy
print("V26 portfolio: repaired Alice + repaired Bob + drift-aware negotiation + terminal-only persuasion.")
'''


V26_TESTS = r'''
def run_v26_adaptive_tests():
    for player in ("player_1", "player_2"):
        offer = base_game("bargaining", "offer", {
            "current_player": player, "money_to_divide": 100.0,
            "delta_1": 0.92, "delta_2": 0.95,
            "complete_information": True, "round": 1,
            "max_rounds": 8, "horizon_known": True,
            "history": [], "messages_allowed": False,
        }, player, f"v26-repaired-{player}")
        action = v26_all_role_bargaining(offer)
        validate_action(offer, action)
        own_key = "alice_gain" if player == "player_1" else "bob_gain"
        assert action[own_key] >= 6.0

    # Message-enabled hidden negotiation receives the drift-relief calibration
    # while remaining inside the acting player's reservation value.
    hidden = base_game("negotiation", "respond", {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "player_1_value": 40.0,
        "complete_information": False, "round": 2,
        "max_rounds": 8, "horizon_known": True,
        "last_offer": {"price": 42.0, "message": "Consider this."},
        "history": [], "messages_allowed": True,
    }, "player_1", "v26-drift-negotiation")
    action = v26_negotiation_strategy(hidden)
    validate_action(hidden, action)
    if action["decision"] == "RejectOffer":
        assert action["product_price"] >= 40.0

    # Preserve the successful terminal-only persuasion behavior.
    low_early = base_game("persuasion", "seller_recommendation", {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "product_price": 100.0,
        "p": 0.5, "v": 180.0, "u": 20.0, "round": 2,
        "total_rounds": 10, "current_quality": "low", "history": [],
    }, "player_1", "v26-persuasion-early")
    assert v26_persuasion_strategy(low_early)["decision"] == "no"
    low_early["game_id"] = "v26-persuasion-terminal"
    low_early["game_state"]["round"] = 10
    assert v26_persuasion_strategy(low_early)["decision"] == "yes"
    print("All V26 adaptive three-family tests passed.")

run_v26_adaptive_tests()
'''


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V25", "V26").replace("v25", "v26")
        cell.source = cell.source.replace(
            'print("V26 portfolio: repaired Alice + frozen V23 negotiation + terminal-only persuasion seller.")\n',
            "",
        )
        cell.source = cell.source.replace(
            'print("V26 portfolio: deterministic bargaining + exact V23 negotiation decisions.")\n',
            "",
        )
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V26 — adaptive heuristics for all three families

V26 is fully deterministic and targets 50 games in bargaining, negotiation, and
persuasion. Alice retains the repeatedly positive V24 repair. Bob receives the
same surplus-protection architecture with role-specific calibration. Negotiation
retains V23 reservation safety but concedes slightly faster in the message-enabled
and known-horizon contexts that reversed during V25. Persuasion retains V24's
positive buyer and terminal-only seller policy.

The runner uses one queue assignment at a time, authoritative rating checks,
family-specific baseline stop-losses, and trailing drawdown limits after five
games. `GLEE_API_KEY` is loaded at runtime from the environment, Kaggle Secrets,
or a hidden prompt. No language model is used.
"""

    policy_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and "def v26_negotiation_strategy" in cell.source
    )

    # Soften only the contexts that reversed in V25; retain reservation safety.
    policy_cell.source = policy_cell.source.replace(
        'base_capture = ((0.72 - 0.12 * t) if role == "seller" else\n'
        '                        (0.66 - 0.10 * t))',
        'base_capture = ((0.72 - 0.12 * t) if role == "seller" else\n'
        '                        (0.66 - 0.10 * t))\n'
        '        if state.get("messages_allowed"):\n'
        '            base_capture -= 0.04\n'
        '        if state.get("horizon_known") and role == "seller":\n'
        '            base_capture -= 0.02',
    )
    policy_cell.source = policy_cell.source.replace(
        'claim = ((0.70 - 0.11 * t) if role == "seller" else\n'
        '                 (0.64 - 0.09 * t))',
        'claim = ((0.70 - 0.11 * t) if role == "seller" else\n'
        '                 (0.64 - 0.09 * t))\n'
        '        if state.get("messages_allowed"):\n'
        '            claim -= 0.04',
    )
    policy_cell.source = policy_cell.source.replace(
        'if profitable and stalls >= 3:',
        'if profitable and stalls >= 2:',
    )
    policy_cell.source = policy_cell.source.replace(
        'continuation_factor = clamp(\n'
        '        (0.80 if role == "seller" else 0.76) - 0.13 * t - 0.08 * min(stalls, 2),',
        'message_relief = 0.06 if state.get("messages_allowed") else 0.0\n'
        '    continuation_factor = clamp(\n'
        '        (0.80 if role == "seller" else 0.76) - message_relief - 0.13 * t - 0.08 * min(stalls, 2),',
    )
    policy_cell.source = policy_cell.source.replace(
        'minimum_capture = 0.52 + 0.06 * (1.0 - t)',
        'minimum_capture = (0.48 if state.get("messages_allowed") else 0.52) + 0.06 * (1.0 - t)',
    )
    policy_cell.source = policy_cell.source.replace(
        'blend = clamp(0.22 + 0.38 * t + 0.08 * min(stalls, 2), 0.0, 0.70)',
        'blend = clamp(0.22 + 0.38 * t + 0.08 * min(stalls, 2) +\n'
        '                  (0.10 if state.get("messages_allowed") else 0.0), 0.0, 0.80)',
    )

    policy_cell.source += BOB_POLICY

    repair_test_index = next(
        index for index, cell in enumerate(notebook.cells)
        if cell.cell_type == "code" and "run_v26_repair_tests()" in cell.source
    )
    notebook.cells.insert(repair_test_index + 1, nbformat.v4.new_code_cell(V26_TESTS))

    live_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and 'LIVE_BUILD_ID = "v26-heuristic-bargaining-v23-negotiation-2026-08-28"' in cell.source
    )
    live_cell.source = live_cell.source.replace(
        'LIVE_BUILD_ID = "v26-heuristic-bargaining-v23-negotiation-2026-08-28"',
        'LIVE_BUILD_ID = "v26-three-family-adaptive-2026-08-28"',
    )
    live_cell.source = live_cell.source.replace(
        'TARGET_COMPLETIONS = {\n    "bargaining": 50,\n    "negotiation": 50,\n}',
        'TARGET_COMPLETIONS = {\n    "bargaining": 50,\n    "negotiation": 50,\n    "persuasion": 50,\n}',
    )
    live_cell.source = live_cell.source.replace(
        'FAMILY_STOP_LOSS = {\n    "bargaining": 12.0,\n    "negotiation": 20.0,\n}',
        'FAMILY_STOP_LOSS = {\n    "bargaining": 12.0,\n    "negotiation": 20.0,\n    "persuasion": 12.0,\n}',
    )
    live_cell.source = live_cell.source.replace(
        'FAMILY_MAX_DRAWDOWN = {"bargaining": 10.0, "negotiation": 15.0}',
        'FAMILY_MAX_DRAWDOWN = {\n'
        '    "bargaining": 10.0, "negotiation": 15.0, "persuasion": 10.0\n'
        '}',
    )

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
