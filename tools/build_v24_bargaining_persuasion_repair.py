"""Build the V24 bargaining/persuasion repair notebook from rendered V23."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "notebooks"
    / "Glee_competition_23"
    / "GLEE_Competition_agent_v23_adaptive_defender.ipynb"
)
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v24_bp_repair.ipynb"


V24_POLICY_FOOTER = r'''

# ---------------------------------------------------------------------------
# V24: repair only the roles rejected by the V23 live evidence
# ---------------------------------------------------------------------------

def v24_alice_bargaining_strategy(game):
    """Alice repair: protect own surplus, concede gradually, retain cycle escape."""
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) != 1:
        return bargaining_strategy(game)
    opponent = other_player(me)
    assign_v24(game, me)
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
        # V23 overweighted the opponent path. V24 anchors mainly on the
        # configuration model and permits only a bounded behavioral correction.
        floor = 0.75 * base_floor + 0.25 * behavioral_floor
        floor = max(floor, model["rejected_floor"])
    else:
        predicted_demand = None
        floor = base_floor
    floor = clamp(floor, 0.18, 0.90)

    if game["valid_actions"]["type"] == "offer":
        if stalls >= 3 and demands:
            # Preserve agreement recovery without surrendering nearly the pot.
            cap = 0.94 if final_round(state) else 0.82
            responder_share = clamp(demands[-1], 0.20, cap)
            reason = "bounded_cycle_match"
        else:
            # Claim slightly more than V4 as Alice. V23 moved in the opposite
            # direction and lost 15.13 points in five Alice assignments.
            search_floor = clamp(floor - 0.010, 0.18, 0.88)
            width = clamp(0.016 + 0.65 * volatility, 0.014, 0.045)
            failure_cost = 0.045 + 0.25 * t + 0.50 * (1.0 - my_delta)
            best = None
            for step in range(20, 189):
                responder_share = step / 200.0
                accept_probability = logistic(
                    (responder_share - search_floor + 0.007) / width
                )
                own_share = 1.0 - responder_share
                value = (accept_probability * own_share**1.18 -
                         (1.0 - accept_probability) * failure_cost)
                candidate = (value, own_share, responder_share)
                if best is None or candidate > best:
                    best = candidate
            responder_share = best[2]
            reason = "alice_surplus_protected_offer"
        responder_gain = round(money * responder_share, 8)
        own_gain = money - responder_gain
        action = {"alice_gain": own_gain, "bob_gain": responder_gain}
        if state.get("messages_allowed"):
            action["message"] = action_message(
                "This split reflects the observed demands and the remaining delay cost."
            )
        return trace_v24(game, me, {
            "reason": reason,
            "base_floor": round(base_floor, 5),
            "floor": round(floor, 5),
            "trend": round(trend, 5),
            "volatility": round(volatility, 5),
            "stalls": stalls,
            "predicted_demand": predicted_demand,
        }, action)

    current_gain = allocation(state.get("last_offer") or {}, me)
    if current_gain is None:
        return trace_v24(game, me, {"reason": "missing_offer"}, {"decision": "reject"})
    current_share = current_gain / max(money, 1e-12)
    if final_round(state):
        decision = "accept" if current_gain > 0 else "reject"
        return trace_v24(game, me, {
            "reason": "terminal_ir", "current_share": current_share,
        }, {"decision": decision})
    if stalls >= 3 and current_share >= 0.18:
        return trace_v24(game, me, {
            "reason": "bounded_cycle_accept", "current_share": current_share,
        }, {"decision": "accept"})

    favorable_concession = -trend if demands else 0.0
    wait_bonus = clamp(0.25 * favorable_concession, -0.02, 0.02)
    continuation_share = my_delta * (1.0 - floor) * clamp(
        0.80 + wait_bonus + 0.10 * t - 0.06 * stalls, 0.48, 0.92
    )
    # V23 used 0.26 for Alice. Restore surplus protection early while still
    # allowing agreements near the deadline or after repeated states.
    risk_floor = max(0.18, 0.36 - 0.08 * t - 0.055 * stalls)
    required_share = max(risk_floor, continuation_share)
    decision = "accept" if current_share + 1e-12 >= required_share else "reject"
    return trace_v24(game, me, {
        "reason": "alice_surplus_protected_accept",
        "current_share": current_share,
        "required_share": required_share,
        "continuation_share": continuation_share,
        "stalls": stalls,
    }, {"decision": decision})


def v24_role_aware_bargaining(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) == 2:
        return bargaining_strategy(game)  # exact V4 Bob; positive in V23
    return v24_alice_bargaining_strategy(game)


def v24_persuasion_strategy(game):
    """Freeze the positive V23 buyer and use terminal-only seller pooling."""
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    price = finite_float(state["product_price"])
    p = clamp(finite_float(state.get("p"), 0.5), 0.0, 1.0)
    round_no = max(1, int(state.get("round", 1)))
    total_raw = state.get("total_rounds", state.get("max_rounds"))
    horizon_known = total_raw is not None
    total_rounds = max(round_no, int(total_raw or round_no))
    seller_view = action_type in {"seller_message", "seller_recommendation"}
    role = "seller" if seller_view else "buyer"
    assign_v24(game, role)
    model = update_persuasion_memory(game, seller_view)

    if seller_view:
        quality = state.get("current_quality", state.get("quality"))
        terminal = horizon_known and round_no >= total_rounds
        # Selling a low-quality unit before the terminal round damages future
        # credibility. At the terminal round that continuation cost is zero.
        recommend = quality == "high" or (quality == "low" and terminal)
        if action_type == "seller_recommendation":
            action = {"decision": "yes" if recommend else "no"}
        else:
            action = {"message": action_message(
                "My recommendation: BUY this product." if recommend else
                "My recommendation: PASS on this product this round."
            )}
        return trace_v24(game, role, {
            "reason": "high_quality" if quality == "high" else
                      ("terminal_pool" if terminal else "truthful_reputation"),
            "quality": quality,
            "terminal": terminal,
            "positive_response_trials": model["positive_decisions"],
        }, action)

    # Preserve the positive V23 buyer rule exactly.
    v, u = finite_float(state["v"]), finite_float(state["u"])
    if price <= u:
        return trace_v24(game, role, {"reason": "price_below_low_value"}, {"decision": "yes"})
    if price > v:
        return trace_v24(game, role, {"reason": "price_above_high_value"}, {"decision": "no"})
    signal = signal_polarity(state.get("seller_message"))
    posterior = p if signal is None else precision_lower_bound(model, signal, p)
    expected_value = posterior * v + (1.0 - posterior) * u
    observations = (model["pos_high"] + model["pos_low"] if signal is True else
                    model["neg_high"] + model["neg_low"] if signal is False else 0.0)
    remaining_fraction = (total_rounds - round_no) / max(1, total_rounds)
    near_cutoff = abs(expected_value - price) <= 0.08 * max(1.0, v - u)
    information_bonus = (0.010 * max(0.0, v - u) * remaining_fraction /
                         math.sqrt(1.0 + observations)
                         if signal is True and near_cutoff and observations < 4 else 0.0)
    decision = "yes" if expected_value + information_bonus >= price else "no"
    return trace_v24(game, role, {
        "reason": "v23_buyer_frozen",
        "signal": signal,
        "posterior_lcb": posterior,
        "expected_value": expected_value,
        "information_bonus": information_bonus,
    }, {"decision": decision})


STRATEGIES["bargaining"] = v24_role_aware_bargaining
STRATEGIES["negotiation"] = v24_negotiation_strategy  # exact successful V23 rule
STRATEGIES["persuasion"] = v24_persuasion_strategy
print("V24 portfolio: repaired Alice + frozen V23 negotiation + terminal-only persuasion seller.")
'''


V24_TESTS = r'''

import copy

def run_v24_repair_tests():
    alice_offer = base_game("bargaining", "offer", {
        "current_player": "player_1", "money_to_divide": 100.0,
        "delta_1": 0.92, "delta_2": 0.95, "complete_information": True,
        "round": 1, "max_rounds": 8, "horizon_known": True,
        "history": [], "messages_allowed": False,
    }, "player_1", "v24-alice-offer")
    action = v24_role_aware_bargaining(alice_offer)
    validate_action(alice_offer, action)
    assert action["alice_gain"] >= 6.0

    low_nonterminal = base_game("persuasion", "seller_message", {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "product_price": 100.0,
        "p": 0.5, "v": 180.0, "u": 20.0, "round": 2,
        "total_rounds": 10, "current_quality": "low", "history": [],
    }, "player_1", "v24-low-nonterminal")
    action = v24_persuasion_strategy(low_nonterminal)
    validate_action(low_nonterminal, action)
    assert "PASS" in action["message"]

    low_terminal = copy.deepcopy(low_nonterminal)
    low_terminal["game_id"] = "v24-low-terminal"
    low_terminal["game_state"]["round"] = 10
    action = v24_persuasion_strategy(low_terminal)
    validate_action(low_terminal, action)
    assert "BUY" in action["message"]

    high_product = copy.deepcopy(low_nonterminal)
    high_product["game_id"] = "v24-high"
    high_product["game_state"]["current_quality"] = "high"
    action = v24_persuasion_strategy(high_product)
    validate_action(high_product, action)
    assert "BUY" in action["message"]
    print("All V24 bargaining and persuasion repair tests passed.")

run_v24_repair_tests()
'''


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V23", "V24").replace("v23", "v24")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V24 — bargaining and persuasion repair

V24 changes only the roles rejected by the V23 live evidence. Bob retains the
V4 bargaining policy, and both negotiation roles retain the successful V23
defensive heuristic. Alice now protects her own surplus, limits opponent-demand
adaptation, and keeps bounded cycle escape. The persuasion buyer is frozen from
V23; the seller is truthful before the final round and pools low quality only
when no future reputation remains.

The live experiment targets 50 bargaining and 50 persuasion completions. It does
not expose negotiation again. Each family uses concurrency one, a 12-point
baseline stop-loss, and a 10-point trailing drawdown after five games. Economic
actions are deterministic heuristics; no language model is used.
"""

    policy_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and "def v24_bargaining_strategy" in cell.source
    )
    footer_at = policy_cell.source.index("\ndef v24_role_aware_bargaining")
    policy_cell.source = policy_cell.source[:footer_at] + V24_POLICY_FOOTER

    test_index = next(
        index for index, cell in enumerate(notebook.cells)
        if cell.cell_type == "code" and "V24 synthetic property assignments isolated" in cell.source
    )
    inherited_tests = notebook.cells[test_index]
    inherited_tests.source = inherited_tests.source.replace(
        "# The cycle detector accepts a strictly positive allocation after three stalls.",
        "# The cycle detector rejects a near-zero allocation but accepts a bounded positive share.",
    )
    inherited_tests.source = inherited_tests.source.replace(
        'assert strategy(cycle_game)["decision"] == "accept"',
        'assert strategy(cycle_game)["decision"] == "reject"\n'
        '    cycle_state["last_offer"] = {"player_1_gain": 20.0, "player_2_gain": 80.0}\n'
        '    bounded_cycle = base_game("bargaining", "respond", cycle_state,\n'
        '                              "player_1", "v24-cycle-bounded")\n'
        '    assert strategy(bounded_cycle)["decision"] == "accept"',
    )
    notebook.cells.insert(test_index + 1, nbformat.v4.new_code_cell(V24_TESTS))

    live_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and 'LIVE_BUILD_ID = "v24-adaptive-defender-2026-08-28"' in cell.source
    )
    live_cell.source = live_cell.source.replace(
        'LIVE_BUILD_ID = "v24-adaptive-defender-2026-08-28"',
        'LIVE_BUILD_ID = "v24-bargaining-persuasion-repair-2026-08-28"',
    )
    live_cell.source = live_cell.source.replace(
        'TARGET_COMPLETIONS = {\n    "bargaining": 50,\n    "negotiation": 50,\n    "persuasion": 50,\n}',
        'TARGET_COMPLETIONS = {\n    "bargaining": 50,\n    "persuasion": 50,\n}',
    )
    live_cell.source = live_cell.source.replace(
        'FAMILY_STOP_LOSS = {\n    "bargaining": 20.0,\n    "negotiation": 20.0,\n    "persuasion": 20.0,\n}',
        'FAMILY_STOP_LOSS = {\n    "bargaining": 12.0,\n    "persuasion": 12.0,\n}',
    )
    live_cell.source = live_cell.source.replace(
        "FAMILY_MAX_DRAWDOWN = 15.0",
        "FAMILY_MAX_DRAWDOWN = 10.0\nMIN_GAMES_BEFORE_TRAILING_STOP = 5",
    )
    live_cell.source = live_cell.source.replace(
        "if peak_drawdown >= FAMILY_MAX_DRAWDOWN:",
        "if cumulative_count >= MIN_GAMES_BEFORE_TRAILING_STOP and peak_drawdown >= FAMILY_MAX_DRAWDOWN:",
    )

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
