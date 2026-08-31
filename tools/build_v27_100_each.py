"""Build V27: evidence-guided heuristics with 100-game targets per family."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "notebooks" / "Glee_competition_26"
    / "26_three_family_adaptive_role_calibration_contextual_concession.ipynb"
)
OUTPUT = ROOT / "notebooks" / "27_evidence_guided_context_repair_configuration_gated_pooling.ipynb"


V27_POLICY = r'''
# ---------------------------------------------------------------------------
# V27 evidence-guided overrides
# ---------------------------------------------------------------------------

V27_ARM = "v27_context_repair"

def trace_v27(game, role, metrics, action):
    record = {
        "game_id": str(game.get("game_id")), "family": game["game_family"],
        "role": role, "round": game["game_state"].get("round"),
        "metrics": metrics, "action": dict(action),
    }
    HEURISTIC_TRACE.append(record)
    append_jsonl("v27_context_repair_decision", record)
    return action


def v27_bargaining_100_strategy(game):
    """Preserve V26 except for a bounded full-information deal correction."""
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    action = dict(v27_all_role_bargaining(game))
    if not state.get("complete_information"):
        return action

    money = finite_float(state["money_to_divide"])
    t = round_progress(state)
    if game["valid_actions"]["type"] == "offer":
        own_key = "alice_gain" if player_index(me) == 1 else "bob_gain"
        other_key = "bob_gain" if player_index(me) == 1 else "alice_gain"
        own_gain = finite_float(action[own_key])
        # V26's full-information Alice and long-horizon Bob contexts were weak.
        # A small, bounded transfer raises agreement probability while retaining
        # at least 22% of the pot for the proposer.
        relief_share = (0.012 if player_index(me) == 2 else 0.018) + 0.012 * t
        transfer = min(money * relief_share, max(0.0, own_gain - 0.22 * money))
        action[own_key] = round(own_gain - transfer, 8)
        action[other_key] = money - action[own_key]
        return trace_v27(game, me, {
            "reason": "full_information_deal_correction",
            "transfer": transfer, "progress": t,
        }, action)

    if action.get("decision") == "reject":
        current_gain = allocation(state.get("last_offer") or {}, me)
        if current_gain is not None and current_gain > 0:
            current_share = current_gain / max(money, 1e-12)
            deal_floor = max(0.20, 0.33 - 0.10 * t)
            if current_share + 1e-12 >= deal_floor:
                return trace_v27(game, me, {
                    "reason": "full_information_positive_deal",
                    "current_share": current_share, "deal_floor": deal_floor,
                }, {"decision": "accept"})
    return action


def v27_negotiation_100_strategy(game):
    """Repair only V26's losing full-information horizon buckets."""
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    opponent = other_player(me)
    role = state[f"{me}_role"]
    action = dict(v27_negotiation_strategy(game))
    if not state.get("complete_information"):
        return action

    horizon = int(state.get("max_rounds", state.get("total_rounds", 0)) or 0)
    horizon_bucket = coarse_bucket(horizon, (5, 12, 30))
    weak_bucket = ((role == "seller" and horizon_bucket == 0) or
                   (role == "buyer" and horizon_bucket == 1))
    if not weak_bucket:
        return action

    my_value = finite_float(state[f"{me}_value"])
    opponent_value = finite_float(state[f"{opponent}_value"])
    seller_value = my_value if role == "seller" else opponent_value
    buyer_value = my_value if role == "buyer" else opponent_value
    surplus = buyer_value - seller_value
    if surplus <= 1e-12:
        return action

    midpoint = seller_value + 0.50 * surplus
    if game["valid_actions"]["type"] == "offer":
        price = finite_float(action["product_price"], midpoint)
        repaired = 0.85 * price + 0.15 * midpoint
        repaired = max(my_value, repaired) if role == "seller" else min(my_value, repaired)
        action["product_price"] = round(max(0.0, repaired), 8)
        return trace_v27(game, role, {
            "reason": "weak_context_midpoint_offer", "horizon_bucket": horizon_bucket,
            "base_price": price, "repaired_price": repaired,
        }, action)

    offer = state.get("last_offer") or {}
    price = finite_float(offer.get("price"), my_value)
    offered_utility = price - my_value if role == "seller" else my_value - price
    capture = offered_utility / surplus
    t = round_progress(state)
    acceptance_capture = 0.40 + 0.08 * (1.0 - t)
    if offered_utility >= -1e-9 and capture + 1e-12 >= acceptance_capture:
        return trace_v27(game, role, {
            "reason": "weak_context_profitable_accept", "capture": capture,
            "acceptance_capture": acceptance_capture,
        }, {"decision": "AcceptOffer"})

    if action.get("decision") == "RejectOffer" and "product_price" in action:
        counter = finite_float(action["product_price"], midpoint)
        counter = 0.82 * counter + 0.18 * price
        counter = max(my_value, counter) if role == "seller" else min(my_value, counter)
        action["product_price"] = round(max(0.0, counter), 8)
        return trace_v27(game, role, {
            "reason": "weak_context_faster_counter", "capture": capture,
            "counter": counter,
        }, action)
    return action


def v27_persuasion_100_strategy(game):
    """Keep the positive buyer; make low-quality seller pooling configuration-safe."""
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    seller_view = action_type in {"seller_message", "seller_recommendation"}
    if not seller_view:
        return v27_persuasion_strategy(game)

    role = "seller"
    assign_v27(game, role)
    model = update_persuasion_memory(game, True)
    quality = state.get("current_quality", state.get("quality"))
    round_no = max(1, int(state.get("round", 1)))
    total_raw = state.get("total_rounds", state.get("max_rounds"))
    terminal = total_raw is not None and round_no >= int(total_raw)
    p = clamp(finite_float(state.get("p"), 0.5), 0.0, 1.0)

    recommend = quality == "high"
    gate = "truthful"
    if quality == "low" and terminal and action_type == "seller_message" and p >= 0.60:
        if "v" in state and "u" in state:
            cutoff = persuasion_cutoff(state, finite_float(state["product_price"]))
            recommend = cutoff is not None and 0.60 <= cutoff < 1.0
            gate = "terminal_text_high_prior_known"
        else:
            recommend = True
            gate = "terminal_text_high_prior_hidden"
    elif quality == "low" and action_type == "seller_recommendation":
        # V26 binary seller contexts lost 11.60 points in three games.
        recommend = False
        gate = "binary_truthful"

    if action_type == "seller_recommendation":
        action = {"decision": "yes" if recommend else "no"}
    else:
        action = {"message": action_message(
            "My recommendation: BUY this product." if recommend else
            "My recommendation: PASS on this product this round."
        )}
    return trace_v27(game, role, {
        "reason": gate, "quality": quality, "terminal": terminal, "p": p,
        "positive_response_trials": model["positive_decisions"],
    }, action)


STRATEGIES["bargaining"] = v27_bargaining_100_strategy
STRATEGIES["negotiation"] = v27_negotiation_100_strategy
STRATEGIES["persuasion"] = v27_persuasion_100_strategy
print("V27 portfolio: bounded bargaining repair + weak-context negotiation repair + gated persuasion seller.")
'''


V27_TESTS = r'''
def run_v27_100_each_tests():
    # Exercise both bargaining roles, both action types, and budget preservation.
    for player in ("player_1", "player_2"):
        offer = base_game("bargaining", "offer", {
            "current_player": player, "money_to_divide": 100.0,
            "delta_1": 0.92, "delta_2": 0.95,
            "complete_information": True, "round": 2,
            "max_rounds": 8, "horizon_known": True,
            "history": [], "messages_allowed": True,
        }, player, f"v27-bargaining-offer-{player}")
        action = v27_bargaining_100_strategy(offer)
        validate_action(offer, action)
        assert abs(action["alice_gain"] + action["bob_gain"] - 100.0) < 1e-7
        assert action["alice_gain"] >= 0 and action["bob_gain"] >= 0

        respond = copy.deepcopy(offer)
        respond["game_id"] = f"v27-bargaining-respond-{player}"
        respond["valid_actions"] = {"type": "respond"}
        respond["game_state"]["last_offer"] = {"alice_gain": 50.0, "bob_gain": 50.0}
        validate_action(respond, v27_bargaining_100_strategy(respond))

    # Test the two V26 negotiation contexts repaired by V27.
    cases = (("seller", 5, 40.0, 80.0, 62.0),
             ("buyer", 8, 80.0, 40.0, 58.0))
    for role, horizon, own_value, other_value, price in cases:
        opponent_role = "buyer" if role == "seller" else "seller"
        game = base_game("negotiation", "respond", {
            "current_player": "player_1", "player_1_role": role,
            "player_2_role": opponent_role, "player_1_value": own_value,
            "player_2_value": other_value, "complete_information": True,
            "round": 2, "max_rounds": horizon, "horizon_known": True,
            "last_offer": {"price": price}, "history": [],
            "messages_allowed": False,
        }, "player_1", f"v27-negotiation-{role}")
        action = v27_negotiation_100_strategy(game)
        validate_action(game, action)
        if action["decision"] == "RejectOffer":
            assert action["product_price"] >= own_value if role == "seller" else action["product_price"] <= own_value

    # Seller gates: binary low quality is truthful, terminal text pooling is
    # gated by prior/configuration, and high quality is always recommended.
    base_state = {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "product_price": 132.0,
        "p": 0.70, "v": 180.0, "u": 20.0, "round": 10,
        "total_rounds": 10, "current_quality": "low", "history": [],
    }
    binary = base_game("persuasion", "seller_recommendation", dict(base_state),
                       "player_1", "v27-persuasion-binary-low")
    assert v27_persuasion_100_strategy(binary)["decision"] == "no"
    text = base_game("persuasion", "seller_message", dict(base_state),
                     "player_1", "v27-persuasion-text-low")
    assert "BUY" in v27_persuasion_100_strategy(text)["message"]
    text["game_id"] = "v27-persuasion-text-early"
    text["game_state"]["round"] = 2
    assert "PASS" in v27_persuasion_100_strategy(text)["message"]
    text["game_id"] = "v27-persuasion-text-high"
    text["game_state"]["current_quality"] = "high"
    assert "BUY" in v27_persuasion_100_strategy(text)["message"]

    # Grid smoke test across information, horizon, role, and messaging modes.
    checked = 0
    for complete_information in (False, True):
        for messages_allowed in (False, True):
            for player, role in (("player_1", "seller"), ("player_2", "buyer")):
                opponent = other_player(player)
                opponent_role = "buyer" if role == "seller" else "seller"
                game = base_game("negotiation", "offer", {
                    "current_player": player, f"{player}_role": role,
                    f"{opponent}_role": opponent_role, f"{player}_value": 60.0,
                    f"{opponent}_value": 75.0 if role == "seller" else 45.0,
                    "complete_information": complete_information,
                    "round": 1, "max_rounds": 8, "horizon_known": True,
                    "history": [], "messages_allowed": messages_allowed,
                }, player, f"v27-grid-{checked}")
                validate_action(game, v27_negotiation_100_strategy(game))
                checked += 1
    assert checked == 8
    assert not ACTION_FALLBACK_LOG
    print("All V27 100-each policy, safety, and contract tests passed.")

run_v27_100_each_tests()

for _game_id, _assignment in POLICY_ASSIGNMENTS.items():
    if str(_game_id).startswith("v27-"):
        _assignment["synthetic"] = True
print("V27 synthetic tests isolated from live evidence.")
'''


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V26", "V27").replace("v26", "v27")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V27 — evidence-guided 100 games per family

V27 is a deterministic, no-LLM successor to the evaluated V26 policy. It targets
100 authoritative completions in each of bargaining, negotiation, and persuasion.
The changes are deliberately local: a bounded full-information bargaining deal
correction, negotiation repair only for the two V26 context buckets with negative
live aggregates, and configuration-gated low-quality persuasion seller behavior.

The notebook defaults to `RUN_LIVE = False`. After all offline tests pass, set it
to `True` for deliberate live execution. One assignment is admitted and drained
at a time. Rating stop-losses, trailing-drawdown guards, assignment-overshoot
checks, schema validation, and append-only evidence remain enabled. Therefore
100 games is the target for each family; safety guards may stop a family early.
Offline tests establish action correctness and safety, not rating superiority.
"""

    policy_index = next(
        i for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "code" and "def v27_bob_bargaining_strategy" in cell.source
    )
    notebook.cells.insert(policy_index + 1, nbformat.v4.new_code_cell(V27_POLICY))

    live_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and "TARGET_COMPLETIONS = {" in cell.source
    )
    live_cell.source = live_cell.source.replace(
        'LIVE_BUILD_ID = "v27-three-family-adaptive-2026-08-28"',
        'LIVE_BUILD_ID = "v27-evidence-guided-100-each-2026-08-29"',
    )
    live_cell.source = live_cell.source.replace(
        '"bargaining": 50,\n    "negotiation": 50,\n    "persuasion": 50,',
        '"bargaining": 100,\n    "negotiation": 100,\n    "persuasion": 100,',
    )
    live_cell.source = live_cell.source.replace(
        '"bargaining": 12.0,\n    "negotiation": 20.0,\n    "persuasion": 12.0,',
        '"bargaining": 25.0,\n    "negotiation": 35.0,\n    "persuasion": 25.0,',
    )
    live_cell.source = live_cell.source.replace(
        "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 70",
        "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 130",
    )
    live_cell.source = live_cell.source.replace(
        '"bargaining": 10.0, "negotiation": 15.0, "persuasion": 10.0',
        '"bargaining": 20.0, "negotiation": 25.0, "persuasion": 20.0',
    )
    live_cell.source = live_cell.source.replace(
        "MIN_GAMES_BEFORE_TRAILING_STOP = 5",
        "MIN_GAMES_BEFORE_TRAILING_STOP = 20",
    )
    live_cell.source = live_cell.source.replace("RUN_LIVE = True", "RUN_LIVE = False")

    live_cell.source = live_cell.source.replace(
        "def family_score_snapshot(stats, family):",
        'assert TARGET_COMPLETIONS == {\n'
        '    "bargaining": 100, "negotiation": 100, "persuasion": 100\n'
        '}\n'
        'assert MAX_QUEUE_ATTEMPTS_PER_FAMILY >= 100\n'
        'print("V27 live configuration verified: 100 targets per family.")\n\n'
        "def family_score_snapshot(stats, family):",
    )

    # Every V27-specific policy test executes before the live-control cell.
    live_markdown_index = next(
        i for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "markdown" and "Controlled live runner" in cell.source
    )
    notebook.cells.insert(live_markdown_index, nbformat.v4.new_code_cell(V27_TESTS))

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
