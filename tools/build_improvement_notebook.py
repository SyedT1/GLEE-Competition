"""Build the non-LLM V19 three-family heuristic challenger notebook."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "notebooks" / "13_controlled_champion_one_queue_append_only_evidence.ipynb"
OUTPUT = ROOT / "notebooks" / "19_heuristic_challenger_robust_trend_projection_precision_bounded_pooling.ipynb"


def md(source: str):
    return nbformat.v4.new_markdown_cell(source.strip() + "\n")


def code(source: str):
    return nbformat.v4.new_code_cell(source.strip() + "\n")


def main():
    notebook = copy.deepcopy(nbformat.read(BASE, as_version=4))
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V19 — three-family heuristic challenger

V19 is a transparent, non-LLM improvement candidate for all three GLEE game
families. It retains V13's strict schema validation, deterministic fallbacks,
append-only evidence, and low-level one-queue runner, then replaces the economic
decision cores with:

- **Bargaining:** robust concession-trend estimation, volatility-aware acceptance
  modeling, Alice-specific risk calibration, and unchanged cycle insurance.
- **Negotiation:** robust opponent-price projection, role-aware surplus targets,
  stall-sensitive continuation value, and strict reservation-value protection.
- **Persuasion:** conservative buyer precision bounds and response-gated,
  credibility-safe seller pooling with a truthful prefix.

These are hypotheses, not established improvements. The final cell is configured
to request one controlled queue exposure sequentially in bargaining, negotiation,
and persuasion, stopping between families on assignment overshoot, fallback, or
telemetry failure. No Qwen, Transformer, or external language model is used.
"""

    config = notebook.cells[3].source
    config = config.replace("GLEE_V13_MODE", "GLEE_V19_MODE")
    config = config.replace("GLEE_V13_WORK_DIR", "GLEE_V19_WORK_DIR")
    config = config.replace("GLEE_V13_STATE_PATH", "GLEE_V19_STATE_PATH")
    config = config.replace("GLEE_V13_EVIDENCE_PATH", "GLEE_V19_EVIDENCE_PATH")
    config = config.replace("glee_v13_policy_state.json", "glee_v19_policy_state.json")
    config = config.replace("glee_v13_evidence.jsonl", "glee_v19_evidence.jsonl")
    config += r'''

def configure_glee_api_key():
    """Load the API key at runtime without storing it in notebook source."""
    if os.environ.get("GLEE_API_KEY"):
        return os.environ["GLEE_API_KEY"]
    try:
        from kaggle_secrets import UserSecretsClient
        secret = UserSecretsClient().get_secret("GLEE_API_KEY")
    except Exception:
        secret = getpass("GLEE API key: ")
    if not secret:
        raise RuntimeError("GLEE_API_KEY was not provided")
    os.environ["GLEE_API_KEY"] = secret
    return os.environ["GLEE_API_KEY"]
'''
    notebook.cells[3].source = config

    heuristics = code(r'''
V19_ARM = "v19_heuristic"
HEURISTIC_TRACE = deque(maxlen=4000)

def robust_median_step(values, window=5):
    recent = [finite_float(value) for value in values[-window:]]
    if len(recent) < 2:
        return 0.0
    return statistics.median([right - left for left, right in zip(recent, recent[1:])])

def robust_mad(values):
    if len(values) < 2:
        return 0.0
    center = statistics.median(values)
    return statistics.median([abs(value - center) for value in values])

def assign_v19(game, role):
    game_id = str(game.get("game_id", "unknown"))
    with LOCK:
        if game_id not in POLICY_ASSIGNMENTS:
            POLICY_ASSIGNMENTS[game_id] = {
                "family": game["game_family"], "role": role,
                "context": policy_context(game, role), "arm": V19_ARM,
                "player": canonical_player(game.get(
                    "your_player", game["game_state"].get("current_player", "player_1"))),
                "state": dict(game["game_state"]),
                "synthetic": is_synthetic_game_id(game_id) or game_id.startswith("v19-"),
            }
        return V19_ARM

def trace_v19(game, role, metrics, action):
    record = {
        "game_id": str(game.get("game_id")), "family": game["game_family"],
        "role": role, "round": game["game_state"].get("round"),
        "metrics": metrics, "action": dict(action),
    }
    HEURISTIC_TRACE.append(record)
    append_jsonl("v19_heuristic_decision", record)
    return action


# ---------------------------------------------------------------------------
# Bargaining: robust trend + volatility-aware offer choice + cycle insurance
# ---------------------------------------------------------------------------
def v19_bargaining_strategy(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    opponent = other_player(me)
    assign_v19(game, me)
    money = finite_float(state["money_to_divide"])
    t = round_progress(state)
    my_delta = player_delta(state, me)
    model = update_bargaining_memory(game, me, opponent, money)
    base_floor = estimate_bargaining_floor(game, state, me, opponent, model)
    demands = model["opponent_demands"][-7:]
    trend = robust_median_step(demands)
    volatility = robust_mad(demands)
    if demands:
        predicted_demand = clamp(demands[-1] + trend, 0.0, 1.0)
        behavioral_floor = predicted_demand - (0.045 + 0.025 * t)
        floor = max(model["rejected_floor"] + (0.004 if model["rejected_floor"] else 0.0),
                    0.58 * base_floor + 0.42 * behavioral_floor)
    else:
        predicted_demand = None
        floor = base_floor
    floor = clamp(floor, 0.18, 0.999)
    stalls = bargaining_stall_count(state, money)

    if game["valid_actions"]["type"] == "offer":
        if stalls >= 3 and demands:
            responder_share = clamp(demands[-1], 0.20, 0.9999)
            reason = "cycle_match"
        else:
            alice = player_index(me) == 1
            # Alice's repeated negative split motivates slightly more deal value;
            # Bob keeps the stronger historical payoff curvature.
            payoff_power = 1.12 if alice else 1.16
            failure_multiplier = 1.12 if alice else 1.00
            search_floor = clamp(floor - (0.006 if alice else 0.0), 0.16, 0.999)
            width = clamp(0.014 + 0.85 * volatility + (0.006 if not demands else 0.0),
                          0.012, 0.055)
            failure_cost = ((0.05 + 0.28 * t + 0.58 * (1.0 - my_delta)) *
                            failure_multiplier)
            best = None
            for step in range(20, 200):
                candidate_share = step / 200.0
                accept_probability = logistic(
                    (candidate_share - search_floor + 0.006) / width
                )
                own_share = 1.0 - candidate_share
                value = (accept_probability * own_share**payoff_power -
                         (1.0 - accept_probability) * failure_cost)
                candidate = (value, own_share, candidate_share)
                if best is None or candidate > best:
                    best = candidate
            responder_share = best[2]
            reason = "expected_payoff"
        responder_gain = round(money * responder_share, 8)
        own_gain = money - responder_gain
        action = ({"alice_gain": own_gain, "bob_gain": responder_gain}
                  if player_index(me) == 1 else
                  {"alice_gain": responder_gain, "bob_gain": own_gain})
        if state.get("messages_allowed"):
            action["message"] = action_message(
                "This offer reflects the observed concession path and remaining delay cost."
            )
        return trace_v19(game, me, {
            "reason": reason, "floor": round(floor, 5), "trend": round(trend, 5),
            "volatility": round(volatility, 5), "stalls": stalls,
            "predicted_demand": predicted_demand,
        }, action)

    current_gain = allocation(state.get("last_offer") or {}, me)
    if current_gain is None:
        action = {"decision": "reject"}
        return trace_v19(game, me, {"reason": "missing_offer"}, action)
    if final_round(state) or (stalls >= 3 and current_gain > 0):
        action = {"decision": "accept" if current_gain >= 0 else "reject"}
        return trace_v19(game, me, {"reason": "terminal_or_cycle", "stalls": stalls}, action)

    favorable_concession = -trend if demands else 0.0
    wait_bonus = clamp(0.30 * favorable_concession, -0.025, 0.025)
    continuation_share = my_delta * (1.0 - floor) * clamp(
        0.77 + wait_bonus + 0.12 * t - 0.07 * stalls, 0.42, 0.92
    )
    role_floor = 0.30 if player_index(me) == 1 else 0.33
    risk_floor = max(0.0, role_floor - 0.09 * t - 0.075 * stalls)
    required = money * max(risk_floor, continuation_share)
    decision = "accept" if current_gain + 1e-9 >= required else "reject"
    return trace_v19(game, me, {
        "reason": "continuation_test", "required": required,
        "current_gain": current_gain, "stalls": stalls,
    }, {"decision": decision})


# ---------------------------------------------------------------------------
# Negotiation: robust projection + drift-resistant surplus protection
# ---------------------------------------------------------------------------
def v19_negotiation_strategy(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    opponent = other_player(me)
    role = state[f"{me}_role"]
    opponent_role = state[f"{opponent}_role"]
    assign_v19(game, role)
    my_value = finite_float(state[f"{me}_value"])
    t = round_progress(state)
    update_negotiation_memory(game, state)
    observed = opponent_prices_in_game(state, opponent)
    stalls = negotiation_stall_count(state, me, opponent)
    raw_step = robust_median_step(observed)
    favorable_step = raw_step if role == "seller" else -raw_step
    opponent_value = state.get(f"{opponent}_value")
    surplus = None

    if state.get("complete_information") and opponent_value is not None:
        opponent_value = finite_float(opponent_value)
        seller_value = my_value if role == "seller" else opponent_value
        buyer_value = my_value if role == "buyer" else opponent_value
        surplus = buyer_value - seller_value
        base_capture = ((0.70 - 0.14 * t) if role == "seller" else
                        (0.63 - 0.12 * t))
        if surplus > 1e-12 and observed:
            concession_rate = clamp(favorable_step / surplus, -0.10, 0.10)
            # Hold somewhat firmer while the opponent is moving toward us;
            # concede when the path is stagnant and the horizon advances.
            base_capture += 0.35 * concession_rate
            base_capture -= 0.025 * min(stalls, 2) * (0.35 + t)
        own_capture = clamp(base_capture, 0.50, 0.76)
        if surplus <= 0:
            target = my_value
        elif role == "seller":
            target = seller_value + own_capture * surplus
        else:
            target = buyer_value - own_capture * surplus
    elif observed:
        latest = observed[-1]
        direction_step = min(0.0, raw_step) if opponent_role == "seller" else max(0.0, raw_step)
        projected = max(0.0, latest + 0.50 * direction_step)
        claim = ((0.66 - 0.13 * t) if role == "seller" else
                 (0.59 - 0.11 * t))
        if role == "seller" and projected >= my_value:
            target = my_value + claim * (projected - my_value)
        elif role == "buyer" and projected <= my_value:
            target = my_value - claim * (my_value - projected)
        else:
            target = my_value
    elif role == "seller":
        target = my_value * (1.32 - 0.14 * t)
    else:
        target = my_value * (0.82 + 0.09 * t)

    target = max(0.0, finite_float(target, my_value))
    metrics = {
        "target": target, "stalls": stalls, "opponent_step": raw_step,
        "observed_prices": observed[-5:], "surplus": surplus,
    }
    if game["valid_actions"]["type"] == "offer":
        action = {"product_price": round(target, 8)}
        if state.get("messages_allowed"):
            action["message"] = action_message(
                "This price remains feasible and reflects the concession path."
            )
        return trace_v19(game, role, {**metrics, "reason": "target_offer"}, action)

    price = finite_float((state.get("last_offer") or {}).get("price"), my_value)
    offered_utility = price - my_value if role == "seller" else my_value - price
    profitable = offered_utility >= -1e-9
    if final_round(state):
        action = {"decision": "AcceptOffer" if profitable else "RejectOffer"}
        return trace_v19(game, role, {**metrics, "reason": "final_round"}, action)
    if profitable and stalls >= 2:
        return trace_v19(game, role, {**metrics, "reason": "profitable_stall"},
                         {"decision": "AcceptOffer"})
    if not profitable and stalls >= 3 and not state.get("horizon_known"):
        return trace_v19(game, role, {**metrics, "reason": "infeasible_cycle"},
                         {"decision": "WalkAway"})

    target_utility = abs(target - my_value)
    continuation_factor = clamp(
        (0.76 if role == "seller" else 0.71) - 0.16 * t - 0.10 * min(stalls, 2),
        0.38, 0.80,
    )
    continuation = target_utility * continuation_factor
    capture = offered_utility / surplus if surplus is not None and surplus > 1e-12 else None
    minimum_capture = 0.47 + 0.06 * (1.0 - t)
    if profitable and (offered_utility + 1e-9 >= continuation or
                       (capture is not None and capture >= minimum_capture)):
        return trace_v19(game, role, {**metrics, "reason": "accept_threshold",
                                      "offered_utility": offered_utility},
                         {"decision": "AcceptOffer"})

    blend = clamp(0.28 + 0.44 * t + 0.10 * min(stalls, 2), 0.0, 0.82)
    counter = (1.0 - blend) * target + blend * price
    counter = max(my_value, counter) if role == "seller" else min(my_value, counter)
    action = {"decision": "RejectOffer", "product_price": round(max(0.0, counter), 8)}
    if state.get("messages_allowed"):
        action["message"] = action_message(
            "I can move toward your offer while preserving non-negative utility."
        )
    return trace_v19(game, role, {**metrics, "reason": "counteroffer",
                                  "offered_utility": offered_utility}, action)


# ---------------------------------------------------------------------------
# Persuasion: conservative buyer + response-gated credibility spending
# ---------------------------------------------------------------------------
def precision_lower_bound(model, positive, p, width=0.55):
    high = model["pos_high"] if positive else model["neg_high"]
    low = model["pos_low"] if positive else model["neg_low"]
    prior = strategic_signal_prior(positive, p)
    alpha = 4.0 * prior + high
    beta = 4.0 * (1.0 - prior) + low
    mean = alpha / (alpha + beta)
    variance = alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1.0))
    return clamp(mean - width * math.sqrt(max(0.0, variance)), 0.0, 1.0)

def v19_seller_pool_probability(state, model, p, price, round_no, total_rounds):
    t = (round_no - 1) / max(1, total_rounds - 1)
    truthful_prefix = max(2, math.ceil(0.25 * total_rounds))
    if round_no <= truthful_prefix:
        return 0.0
    response_lcb = beta_lower_mean(model["positive_buys"],
                                   model["positive_decisions"], 1.0, 1.0)
    if model["positive_decisions"] < 3 or response_lcb < 0.52:
        return 0.0
    cutoff = persuasion_cutoff(state, price)
    terminal = round_no >= total_rounds
    if cutoff is None:
        return clamp((0.10 + 0.30 * t) * response_lcb, 0.0, 0.45 if terminal else 0.20)
    if cutoff <= 0.0:
        return 1.0
    if cutoff >= 1.0:
        return 0.0
    bound = static_pool_bound(p, cutoff)
    trust_after = ((2.5 + model["all_pos_high"]) /
                   (3.3 + model["all_pos_high"] + model["all_pos_low"] + 1.0))
    if not terminal and trust_after < cutoff + 0.04:
        return 0.0
    schedule = 0.10 + 0.90 * t**2
    cap = 1.0 if terminal else 0.55
    return clamp(bound * response_lcb * schedule, 0.0, min(cap, bound))

def v19_persuasion_strategy(game):
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    price = finite_float(state["product_price"])
    p = clamp(finite_float(state.get("p"), 0.5), 0.0, 1.0)
    round_no = max(1, int(state.get("round", 1)))
    total_rounds = max(round_no, int(state.get("total_rounds", state.get("max_rounds", round_no)) or round_no))
    seller_view = action_type in {"seller_message", "seller_recommendation"}
    role = "seller" if seller_view else "buyer"
    assign_v19(game, role)
    model = update_persuasion_memory(game, seller_view)

    if seller_view:
        quality = state.get("current_quality", state.get("quality"))
        probability = 0.0
        recommend = quality == "high"
        if quality == "low":
            probability = v19_seller_pool_probability(
                state, model, p, price, round_no, total_rounds
            )
            recommend = stable_unit(game, "v19-response-gated-pool") < probability
        if action_type == "seller_recommendation":
            action = {"decision": "yes" if recommend else "no"}
        else:
            action = {"message": action_message(
                "My recommendation: BUY this product." if recommend else
                "My recommendation: PASS on this product this round."
            )}
        return trace_v19(game, role, {
            "quality": quality, "pool_probability": probability,
            "positive_response_trials": model["positive_decisions"],
        }, action)

    v, u = finite_float(state["v"]), finite_float(state["u"])
    if price <= u:
        return trace_v19(game, role, {"reason": "price_below_low_value"}, {"decision": "yes"})
    if price > v:
        return trace_v19(game, role, {"reason": "price_above_high_value"}, {"decision": "no"})
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
    return trace_v19(game, role, {
        "signal": signal, "posterior_lcb": posterior,
        "expected_value": expected_value, "information_bonus": information_bonus,
    }, {"decision": decision})


STRATEGIES = {
    "bargaining": v19_bargaining_strategy,
    "negotiation": v19_negotiation_strategy,
    "persuasion": v19_persuasion_strategy,
}
print("Activated V19 heuristic challenger for all three families.")
''')

    tests = code(r'''
def run_v19_tests():
    # Bargaining budget, both roles, broad discount grid.
    for player in ("player_1", "player_2"):
        for d1 in (0.05, 0.50, 0.95, 0.999):
            for d2 in (0.05, 0.50, 0.95, 0.999):
                state = {
                    "current_player": player, "money_to_divide": 137.25,
                    "delta_1": d1, "delta_2": d2, "complete_information": True,
                    "round": 1, "max_rounds": 8, "horizon_known": True,
                    "history": [], "messages_allowed": False,
                }
                game = base_game("bargaining", "offer", state, player,
                                 f"v19-b-{player}-{d1}-{d2}")
                action = strategy(game)
                assert validate_action(game, action) == action
                assert math.isclose(action["alice_gain"] + action["bob_gain"], 137.25,
                                    rel_tol=1e-10, abs_tol=1e-7)

    # The cycle detector accepts a strictly positive allocation after three stalls.
    history = []
    for turn in range(1, 4):
        history.extend([
            {"round": turn, "proposer": "player_1",
             "offer": {"player_1_gain": 35.0, "player_2_gain": 65.0}, "decision": "reject"},
            {"round": turn, "proposer": "player_2",
             "offer": {"player_1_gain": 0.01, "player_2_gain": 99.99}, "decision": "reject"},
        ])
    cycle_state = {
        "current_player": "player_1", "money_to_divide": 100.0,
        "delta_1": 0.10, "delta_2": 0.999, "complete_information": True,
        "round": 7, "horizon_known": False, "history": history,
        "last_offer": {"player_1_gain": 0.01, "player_2_gain": 99.99},
        "messages_allowed": False,
    }
    cycle_game = base_game("bargaining", "respond", cycle_state,
                           "player_1", "v19-cycle")
    assert strategy(cycle_game)["decision"] == "accept"

    # Negotiation never knowingly accepts negative utility and accepts profitable
    # final offers for both roles.
    for role, own_value, good_price, bad_price in (
        ("seller", 40.0, 45.0, 35.0), ("buyer", 100.0, 95.0, 105.0)
    ):
        other_role = "buyer" if role == "seller" else "seller"
        other_value = 100.0 if role == "seller" else 40.0
        template = {
            "current_player": "player_1", "player_1_role": role,
            "player_2_role": other_role, "player_1_value": own_value,
            "player_2_value": other_value, "complete_information": True,
            "round": 5, "max_rounds": 5, "horizon_known": True,
            "history": [], "messages_allowed": False,
        }
        good = base_game("negotiation", "respond",
                         dict(template, last_offer={"price": good_price}),
                         "player_1", f"v19-n-good-{role}")
        bad = base_game("negotiation", "respond",
                        dict(template, last_offer={"price": bad_price}),
                        "player_1", f"v19-n-bad-{role}")
        assert strategy(good)["decision"] == "AcceptOffer"
        assert strategy(bad)["decision"] == "RejectOffer"

    # Persuasion dominance and truthful-prefix behavior.
    buyer_template = {
        "current_player": "player_1", "player_1_role": "buyer",
        "player_2_role": "seller", "p": 0.5, "v": 100.0, "u": 20.0,
        "round": 1, "total_rounds": 8, "history": [],
        "seller_message": "My recommendation: BUY this product.",
    }
    cheap = base_game("persuasion", "buyer_decision",
                      dict(buyer_template, product_price=15.0),
                      "player_1", "v19-p-cheap")
    expensive = base_game("persuasion", "buyer_decision",
                          dict(buyer_template, product_price=110.0),
                          "player_1", "v19-p-expensive")
    assert strategy(cheap)["decision"] == "yes"
    assert strategy(expensive)["decision"] == "no"

    seller_state = {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "p": 0.5, "v": 100.0, "u": 0.0,
        "product_price": 50.0, "current_quality": "low",
        "round": 1, "total_rounds": 8, "history": [],
    }
    early_low = base_game("persuasion", "seller_recommendation", seller_state,
                          "player_1", "v19-p-early-low")
    assert strategy(early_low)["decision"] == "no"

    assert not ACTION_FALLBACK_LOG
    assert all(item["arm"] == V19_ARM for game_id, item in POLICY_ASSIGNMENTS.items()
               if game_id.startswith("v19-"))
    print("All V19 heuristic property, safety, and contract tests passed.")

run_v19_tests()
''')

    analysis = code(r'''
print("V19 heuristic trace rows:", len(HEURISTIC_TRACE))
display(list(HEURISTIC_TRACE)[-30:])
print("Action fallbacks:", len(ACTION_FALLBACK_LOG))
print("Telemetry diagnostics:", len(TELEMETRY_LOG))
print("Important: offline property tests establish safety invariants, not rating superiority.")
''')

    notebook.cells[16:16] = [
        md("## V19 heuristic challenger definitions"), heuristics,
        md("## V19 cross-family property and safety tests"), tests, analysis,
    ]

    runner_index = 22
    runner = notebook.cells[runner_index].source
    marker = 'EVALUATION_FAMILY = "bargaining"'
    runner = runner[: runner.index(marker)] + '''LIVE_FAMILIES = ("bargaining", "negotiation", "persuasion")
RUN_LIVE = True
MATCH_TIMEOUT_SECONDS = 300.0

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    v19_live_reports = []
    for family in LIVE_FAMILIES:
        fallback_before = len(ACTION_FALLBACK_LOG)
        telemetry_before = len(TELEMETRY_LOG)
        print(f"Starting one controlled {family} queue exposure...")
        report = run_one_queue_assignment(
            client, strategy, family, match_timeout=MATCH_TIMEOUT_SECONDS
        )
        v19_live_reports.append(report)
        display(report)
        new_fallbacks = len(ACTION_FALLBACK_LOG) - fallback_before
        new_telemetry = len(TELEMETRY_LOG) - telemetry_before
        if report["assignment_overshoot"] > 0:
            print("Stopping before the next family: assignment overshoot detected.")
            break
        if new_fallbacks > 0:
            print("Stopping before the next family: live action fallback detected.")
            break
        if new_telemetry > 0:
            print("Stopping before the next family: new telemetry diagnostic detected.")
            break
    print("Completed controlled family reports:", len(v19_live_reports))
else:
    print("Live matchmaking is disabled by RUN_LIVE=False.")
'''
    notebook.cells[runner_index].source = runner

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
