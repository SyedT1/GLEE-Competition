"""Build three isolated post-V27 recovery notebooks."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parent
V27 = ROOT / "Glee_competition_27" / "GLEE_Competition_agent_v27_100_each.ipynb"
V23 = ROOT / "Glee_competition_23" / "GLEE_Competition_agent_v23_adaptive_defender.ipynb"


def extract_v23_buyer() -> str:
    notebook = nbformat.read(V23, as_version=4)
    source = next(
        cell.source for cell in notebook.cells
        if cell.cell_type == "code" and "def v23_negotiation_strategy" in cell.source
    )
    start = source.index("def v23_negotiation_strategy")
    end = source.index(
        "# ---------------------------------------------------------------------------\n# Persuasion",
        start,
    )
    function = source[start:end].rstrip()
    return (
        function.replace("def v23_negotiation_strategy", "def v28_v23_buyer_strategy")
        .replace("assign_v23(game, role)", "assign_recovery(game, role, V28_BUYER_ARM)")
        .replace("trace_v23(game, role", "trace_recovery(game, role")
    )


COMMON_ASSIGN = r'''
def assign_recovery(game, role, arm):
    game_id = str(game.get("game_id", "unknown"))
    with LOCK:
        if game_id not in POLICY_ASSIGNMENTS:
            POLICY_ASSIGNMENTS[game_id] = {
                "family": game["game_family"], "role": role,
                "context": policy_context(game, role), "arm": arm,
                "player": canonical_player(game.get(
                    "your_player", game["game_state"].get("current_player", "player_1"))),
                "state": dict(game["game_state"]),
                "synthetic": is_synthetic_game_id(game_id) or game_id.startswith(
                    ("v28-", "v29-", "v30-")
                ),
            }
        return POLICY_ASSIGNMENTS[game_id]["arm"]


def trace_recovery(game, role, metrics, action):
    record = {
        "game_id": str(game.get("game_id")), "family": game["game_family"],
        "role": role, "round": game["game_state"].get("round"),
        "metrics": metrics, "action": dict(action),
    }
    HEURISTIC_TRACE.append(record)
    append_jsonl("role_isolated_recovery_decision", record)
    return action
'''


V28_POLICY = COMMON_ASSIGN + r'''
V28_BUYER_ARM = "v28_exact_v23_buyer"
V28_SELLER_ARM = "v27_frozen_seller"

__V23_BUYER_FUNCTION__


def v28_negotiation_strategy(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    role = state[f"{me}_role"]
    if role == "buyer":
        return v28_v23_buyer_strategy(game)
    return v27_negotiation_100_strategy(game)


STRATEGIES["negotiation"] = v28_negotiation_strategy
print("V28: exact V23 buyer rollback + frozen V27 seller.")
'''


V28_TESTS = r'''
def run_v28_tests():
    checked = 0
    for complete in (False, True):
        for horizon in (5, 8, 20):
            for action_type in ("offer", "respond"):
                state = {
                    "current_player": "player_1", "player_1_role": "buyer",
                    "player_2_role": "seller", "player_1_value": 80.0,
                    "player_2_value": 40.0, "complete_information": complete,
                    "round": 2, "max_rounds": horizon, "horizon_known": True,
                    "history": [], "messages_allowed": False,
                }
                if action_type == "respond":
                    state["last_offer"] = {"price": 58.0}
                game = base_game("negotiation", action_type, state, "player_1",
                                 f"v28-buyer-{checked}")
                action = v28_negotiation_strategy(game)
                validate_action(game, action)
                if action_type == "offer":
                    assert action["product_price"] <= state["player_1_value"]
                elif action.get("decision") == "RejectOffer":
                    assert action["product_price"] <= state["player_1_value"]
                checked += 1

    seller = base_game("negotiation", "offer", {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "player_1_value": 40.0,
        "player_2_value": 80.0, "complete_information": True,
        "round": 1, "max_rounds": 8, "horizon_known": True,
        "history": [], "messages_allowed": False,
    }, "player_1", "v28-frozen-seller")
    action = v28_negotiation_strategy(seller)
    validate_action(seller, action)
    assert action["product_price"] >= 40.0
    assert checked == 12
    assert not ACTION_FALLBACK_LOG
    print("All V28 buyer rollback, frozen-seller, safety, and contract tests passed.")

run_v28_tests()
'''


V29_POLICY = COMMON_ASSIGN + r'''
V29_BOB_ARM = "v29_bob_agreement_recovery"


def v29_bob_strategy(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) != 2:
        return v27_bargaining_100_strategy(game)
    assign_recovery(game, me, V29_BOB_ARM)
    action = dict(v27_bob_bargaining_strategy(game))
    money = finite_float(state["money_to_divide"])
    t = round_progress(state)
    delta = player_delta(state, me)
    stalls = bargaining_stall_count(state, money)

    if game["valid_actions"]["type"] == "offer":
        # Remove V27's full-information blanket correction. Apply a smaller,
        # Bob-only agreement adjustment, strongest when delay is expensive.
        own = finite_float(action["bob_gain"])
        relief_share = (0.018 if delta < 0.95 else 0.008) + 0.008 * t
        transfer = min(money * relief_share, max(0.0, own - 0.24 * money))
        action["bob_gain"] = round(own - transfer, 8)
        action["alice_gain"] = money - action["bob_gain"]
        return trace_recovery(game, me, {
            "reason": "bob_delay_aware_offer", "delta": delta,
            "transfer": transfer, "progress": t,
        }, action)

    if action.get("decision") == "reject":
        current_gain = allocation(state.get("last_offer") or {}, me)
        if current_gain is not None and current_gain > 0:
            current_share = current_gain / max(money, 1e-12)
            recovery_floor = max(
                0.16,
                (0.30 if delta < 0.95 else 0.33) - 0.09 * t - 0.055 * stalls,
            )
            if current_share + 1e-12 >= recovery_floor:
                return trace_recovery(game, me, {
                    "reason": "bob_delay_aware_accept", "delta": delta,
                    "current_share": current_share, "floor": recovery_floor,
                }, {"decision": "accept"})
    return action


def v29_bargaining_strategy(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    if player_index(me) == 1:
        return v27_bargaining_100_strategy(game)
    return v29_bob_strategy(game)


STRATEGIES["bargaining"] = v29_bargaining_strategy
print("V29: frozen V27 Alice + Bob delay-aware agreement recovery.")
'''


V29_TESTS = r'''
def run_v29_tests():
    checked = 0
    for complete in (False, True):
        for delta in (0.75, 0.90, 0.97, 1.0):
            offer = base_game("bargaining", "offer", {
                "current_player": "player_2", "money_to_divide": 100.0,
                "delta_1": 0.95, "delta_2": delta,
                "complete_information": complete, "round": 2,
                "max_rounds": 8, "horizon_known": True,
                "history": [], "messages_allowed": False,
            }, "player_2", f"v29-bob-offer-{checked}")
            action = v29_bargaining_strategy(offer)
            validate_action(offer, action)
            assert abs(action["alice_gain"] + action["bob_gain"] - 100.0) < 1e-7
            assert action["bob_gain"] >= 0.0

            respond = copy.deepcopy(offer)
            respond["game_id"] = f"v29-bob-respond-{checked}"
            respond["valid_actions"] = {"type": "respond"}
            respond["game_state"]["last_offer"] = {
                "alice_gain": 72.0, "bob_gain": 28.0
            }
            validate_action(respond, v29_bargaining_strategy(respond))
            checked += 1

    alice = base_game("bargaining", "offer", {
        "current_player": "player_1", "money_to_divide": 100.0,
        "delta_1": 0.92, "delta_2": 0.95,
        "complete_information": True, "round": 1,
        "max_rounds": 8, "horizon_known": True,
        "history": [], "messages_allowed": False,
    }, "player_1", "v29-frozen-alice")
    validate_action(alice, v29_bargaining_strategy(alice))
    assert checked == 8
    assert not ACTION_FALLBACK_LOG
    print("All V29 Bob recovery, frozen-Alice, safety, and contract tests passed.")

run_v29_tests()
'''


V30_POLICY = COMMON_ASSIGN + r'''
V30_BINARY_SELLER_ARM = "v30_calibrated_binary_pool"


def v30_binary_pool_probability(state, model, p, price, round_no, total_rounds):
    t = (round_no - 1) / max(1, total_rounds - 1)
    cutoff = persuasion_cutoff(state, price)
    if cutoff is None:
        base = 0.10 + 0.25 * p + 0.15 * t
    elif cutoff <= 0.0:
        return 1.0
    elif cutoff >= 1.0:
        return 0.0
    else:
        # Stay strictly inside the Bayes-feasible pooling bound so a positive
        # recommendation remains favorable to a threshold buyer.
        base = 0.55 * static_pool_bound(p, cutoff)
    response_lcb = beta_lower_mean(
        model["positive_buys"], model["positive_decisions"], 1.0, 1.0
    )
    response_gate = 0.65 + 0.35 * response_lcb
    cap = 0.65 if round_no >= total_rounds else 0.40
    return clamp(base * response_gate, 0.0, cap)


def v30_persuasion_strategy(game):
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    if action_type != "seller_recommendation":
        return v27_persuasion_100_strategy(game)

    role = "seller"
    assign_recovery(game, role, V30_BINARY_SELLER_ARM)
    model = update_persuasion_memory(game, True)
    quality = state.get("current_quality", state.get("quality"))
    p = clamp(finite_float(state.get("p"), 0.5), 0.0, 1.0)
    price = finite_float(state["product_price"])
    round_no = max(1, int(state.get("round", 1)))
    total_rounds = max(
        round_no,
        int(state.get("total_rounds", state.get("max_rounds", round_no)) or round_no),
    )
    probability = 0.0
    recommend = quality == "high"
    if quality == "low":
        probability = v30_binary_pool_probability(
            state, model, p, price, round_no, total_rounds
        )
        recommend = stable_unit(game, "v30-binary-pool") < probability
    return trace_recovery(game, role, {
        "reason": "binary_high_quality" if quality == "high" else "binary_calibrated_pool",
        "quality": quality, "pool_probability": probability,
        "positive_response_trials": model["positive_decisions"],
    }, {"decision": "yes" if recommend else "no"})


STRATEGIES["persuasion"] = v30_persuasion_strategy
print("V30: frozen V27 buyer/text seller + calibrated binary seller pooling.")
'''


V30_TESTS = r'''
def run_v30_tests():
    checked = 0
    for p in (0.25, 0.50, 0.75):
        for cutoff_case, price in (("low", 40.0), ("middle", 100.0), ("high", 170.0)):
            state = {
                "current_player": "player_1", "player_1_role": "seller",
                "player_2_role": "buyer", "product_price": price,
                "p": p, "v": 180.0, "u": 20.0, "round": 3,
                "total_rounds": 10, "current_quality": "low", "history": [],
            }
            game = base_game("persuasion", "seller_recommendation", state,
                             "player_1", f"v30-binary-{checked}")
            action = v30_persuasion_strategy(game)
            validate_action(game, action)
            probability = HEURISTIC_TRACE[-1]["metrics"]["pool_probability"]
            assert 0.0 <= probability <= 0.40 + 1e-12
            cutoff = persuasion_cutoff(state, price)
            if cutoff is not None and 0.0 < cutoff < 1.0:
                assert probability <= static_pool_bound(p, cutoff) + 1e-12
            checked += 1

    high = base_game("persuasion", "seller_recommendation", {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "product_price": 100.0,
        "p": 0.5, "v": 180.0, "u": 20.0, "round": 1,
        "total_rounds": 10, "current_quality": "high", "history": [],
    }, "player_1", "v30-binary-high")
    assert v30_persuasion_strategy(high)["decision"] == "yes"

    text = copy.deepcopy(high)
    text["game_id"] = "v30-frozen-text"
    text["valid_actions"] = {"type": "seller_message"}
    validate_action(text, v30_persuasion_strategy(text))
    assert checked == 9
    assert not ACTION_FALLBACK_LOG
    print("All V30 calibrated-pooling, frozen-branch, safety, and contract tests passed.")

run_v30_tests()
'''


RUNNER_TEMPLATE = r'''
from glee_sdk import GleeClient

__RUN_ONE_QUEUE__

LIVE_BUILD_ID = "__BUILD_ID__"
LIVE_FAMILY = "__FAMILY__"
FOCAL_ROLE = "__ROLE__"
FOCAL_MODE = __MODE__
TARGET_FOCAL_COMPLETIONS = __TARGET__
MAX_TOTAL_COMPLETIONS = __MAX_TOTAL__
MAX_QUEUE_ATTEMPTS = __MAX_ATTEMPTS__
FOCAL_STOP_LOSS = 8.0
FOCAL_MAX_DRAWDOWN = 6.0
COMPANION_STOP_LOSS = 10.0
MIN_ROLE_GAMES_BEFORE_DRAWDOWN = 5
MATCH_TIMEOUT_SECONDS = 300.0
RUN_LIVE = False

print("Live build:", LIVE_BUILD_ID)
print("Role-isolated live configuration:", {
    "family": LIVE_FAMILY, "focal_role": FOCAL_ROLE, "focal_mode": FOCAL_MODE,
    "target": TARGET_FOCAL_COMPLETIONS, "max_total": MAX_TOTAL_COMPLETIONS,
})


def family_score_snapshot(stats, family):
    scores = stats.get("scores") or {}
    item = scores.get(family) or {}
    rating = item.get("rating")
    count = item.get("games_played", item.get("games", item.get("game_count", 0)))
    if rating is None:
        raise KeyError(f"stats missing {family} rating: {stats}")
    return {"rating": finite_float(rating), "games_played": int(count or 0)}


def focal_record(record):
    if not record or record.get("role") != FOCAL_ROLE:
        return False
    if FOCAL_MODE is None:
        return True
    context = record.get("context") or []
    return len(context) > 1 and context[1] == FOCAL_MODE


def role_guard(count, cumulative, peak, focal):
    loss_limit = FOCAL_STOP_LOSS if focal else COMPANION_STOP_LOSS
    if cumulative <= -abs(loss_limit):
        return "focal role stop-loss" if focal else "companion role stop-loss"
    if (focal and count >= MIN_ROLE_GAMES_BEFORE_DRAWDOWN and
            peak - cumulative >= FOCAL_MAX_DRAWDOWN):
        return "focal role trailing drawdown"
    return None


def run_role_isolated_microbatch(client):
    initial = family_score_snapshot(client.stats(), LIVE_FAMILY)
    role_stats = {}
    focal_count = 0
    checkpoints = []
    stop_reason = None
    global_abort = False

    for attempt in range(1, MAX_QUEUE_ATTEMPTS + 1):
        current = family_score_snapshot(client.stats(), LIVE_FAMILY)
        total = current["games_played"] - initial["games_played"]
        if focal_count >= TARGET_FOCAL_COMPLETIONS:
            stop_reason = "focal target reached"
            break
        if total >= MAX_TOTAL_COMPLETIONS:
            stop_reason = "maximum total completions reached"
            break

        fallback_before = len(ACTION_FALLBACK_LOG)
        telemetry_before = len(TELEMETRY_LOG)
        print(
            f"{LIVE_FAMILY}: attempt {attempt}; focal {focal_count}/"
            f"{TARGET_FOCAL_COMPLETIONS}; total {total}/{MAX_TOTAL_COMPLETIONS}"
        )
        report = run_one_queue_assignment(
            client, strategy, LIVE_FAMILY, match_timeout=MATCH_TIMEOUT_SECONDS
        )
        before = family_score_snapshot(report["before"], LIVE_FAMILY)
        after = family_score_snapshot(report["after"], LIVE_FAMILY)
        count_delta = after["games_played"] - before["games_played"]
        harvested = harvest_completed_games(client)
        credited = credit_rating_delta(
            report["assigned_ids"], LIVE_FAMILY,
            before["rating"], after["rating"], count_delta,
        )
        new_fallbacks = len(ACTION_FALLBACK_LOG) - fallback_before
        new_telemetry = len(TELEMETRY_LOG) - telemetry_before
        checkpoint = {
            "attempt": attempt, "family": LIVE_FAMILY,
            "count_delta": count_delta, "rating_credit": credited,
            "assigned_ids": report["assigned_ids"],
            "assignment_overshoot": report["assignment_overshoot"],
            "harvested_count": len(harvested),
            "new_action_fallbacks": new_fallbacks,
            "new_telemetry": new_telemetry,
        }
        checkpoints.append(checkpoint)
        append_jsonl("role_isolated_checkpoint", checkpoint)
        display(checkpoint)

        if report["assignment_overshoot"] > 0 or new_fallbacks or new_telemetry:
            stop_reason = "global safety abort"
            global_abort = True
            break
        if count_delta != 1 or credited is None:
            stop_reason = "ambiguous authoritative completion"
            global_abort = True
            break

        key = credited["role"]
        if LIVE_FAMILY == "persuasion":
            context = credited.get("context") or []
            key = f"{key}:{context[1] if len(context) > 1 else 'unknown'}"
        item = role_stats.setdefault(key, {"count": 0, "sum": 0.0, "peak": 0.0})
        item["count"] += 1
        item["sum"] += finite_float(credited["rating_delta"])
        item["peak"] = max(item["peak"], item["sum"])

        is_focal = focal_record(credited)
        if is_focal:
            focal_count += 1
        reason = role_guard(item["count"], item["sum"], item["peak"], is_focal)
        if reason:
            stop_reason = reason
            break
        if focal_count >= TARGET_FOCAL_COMPLETIONS:
            stop_reason = "focal target reached"
            break
    else:
        stop_reason = "maximum queue attempts reached"

    final = family_score_snapshot(client.stats(), LIVE_FAMILY)
    summary = {
        "family": LIVE_FAMILY, "focal_role": FOCAL_ROLE,
        "focal_mode": FOCAL_MODE, "focal_completed": focal_count,
        "initial": initial, "final": final,
        "total_completed": final["games_played"] - initial["games_played"],
        "rating_change": round(final["rating"] - initial["rating"], 6),
        "role_stats": role_stats, "stop_reason": stop_reason,
        "global_abort": global_abort, "checkpoints": checkpoints,
    }
    append_jsonl("role_isolated_summary", summary)
    return summary


def run_role_guard_tests():
    assert role_guard(1, -8.1, 0.0, True) == "focal role stop-loss"
    assert role_guard(5, 1.0, 7.1, True) == "focal role trailing drawdown"
    assert role_guard(4, -9.9, 0.0, False) is None
    assert role_guard(4, -10.1, 0.0, False) == "companion role stop-loss"
    print("Role-local stop-loss and drawdown tests passed.")


run_role_guard_tests()

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    focused_summary = run_role_isolated_microbatch(client)
    display(focused_summary)
    report_paths = export_session_report("__REPORT__", "__CSV__")
    print("Session reports:", report_paths)
else:
    print("Live matchmaking is disabled by RUN_LIVE=False.")
'''


def run_one_queue_source(notebook) -> str:
    source = next(
        cell.source for cell in notebook.cells
        if cell.cell_type == "code" and "def run_one_queue_assignment" in cell.source
    )
    start = source.index("def run_one_queue_assignment")
    end = source.index("LIVE_BUILD_ID", start)
    return source[start:end].rstrip()


def build(spec: dict, v23_buyer: str) -> Path:
    base = nbformat.read(V27, as_version=4)
    live_index = next(
        i for i, cell in enumerate(base.cells)
        if cell.cell_type == "markdown" and "Controlled live runner" in cell.source
    )
    runner_function = run_one_queue_source(base)
    notebook = copy.deepcopy(base)
    notebook.cells = notebook.cells[:live_index]
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            cell.source = cell.source.replace("glee_v27_", f"glee_v{spec['version']}_")
            cell.source = cell.source.replace("GLEE_V27_", f"GLEE_V{spec['version']}_")

    notebook.cells[0].source = spec["intro"]
    policy = spec["policy"].replace("__V23_BUYER_FUNCTION__", v23_buyer)
    runner = (
        RUNNER_TEMPLATE.replace("__RUN_ONE_QUEUE__", runner_function)
        .replace("__BUILD_ID__", spec["build_id"])
        .replace("__FAMILY__", spec["family"])
        .replace("__ROLE__", spec["role"])
        .replace("__MODE__", repr(spec["mode"]))
        .replace("__TARGET__", str(spec["target"]))
        .replace("__MAX_TOTAL__", str(spec["max_total"]))
        .replace("__MAX_ATTEMPTS__", str(spec["max_attempts"]))
        .replace("__REPORT__", f"glee_v{spec['version']}_session_report.json")
        .replace("__CSV__", f"glee_v{spec['version']}_rating_outcomes.csv")
    )
    notebook.cells.extend([
        nbformat.v4.new_markdown_cell(spec["policy_heading"]),
        nbformat.v4.new_code_cell(policy),
        nbformat.v4.new_markdown_cell("## Focused offline regression and contract tests"),
        nbformat.v4.new_code_cell(spec["tests"]),
        nbformat.v4.new_markdown_cell(
            "## Role-isolated live runner\n\n"
            "The live cell defaults to `RUN_LIVE = False`. It admits one assignment, "
            "leaves the queue immediately, and stops from assignment-linked role evidence."
        ),
        nbformat.v4.new_code_cell(runner),
        nbformat.v4.new_markdown_cell("## Inspect exact evidence"),
        nbformat.v4.new_code_cell(
            "print('Run mode:', RUN_MODE)\n"
            "print('Live action fallback count:', len(ACTION_FALLBACK_LOG))\n"
            "print('Telemetry diagnostic count:', len(TELEMETRY_LOG))\n"
            "print('Persistent state:', POLICY_STATE_PATH)\n"
            "print('Append-only evidence:', EVIDENCE_PATH)\n"
        ),
    ])
    nbformat.validate(notebook)
    output = ROOT / spec["filename"]
    nbformat.write(notebook, output)
    return output


def main() -> None:
    v23_buyer = extract_v23_buyer()
    specs = [
        {
            "version": 28,
            "filename": "GLEE_Competition_agent_v28_negotiation_buyer_rollback.ipynb",
            "build_id": "v28-negotiation-buyer-rollback-2026-08-29",
            "family": "negotiation", "role": "buyer", "mode": None,
            "target": 20, "max_total": 45, "max_attempts": 55,
            "policy": V28_POLICY, "tests": V28_TESTS,
            "policy_heading": "## V28 policy — exact V23 buyer rollback",
            "intro": """# GLEE Competition agent V28 — negotiation-buyer rollback

V28 changes only the rejected V27 negotiation buyer. It restores the exact V23
buyer decision function, which was positive in both V23 and V25, and freezes the
positive V27 seller. Bargaining and persuasion receive no live traffic.

The live target is 20 buyer-role completions, subject to an eight-point focal
loss limit, six-point focal trailing drawdown after five buyer games, a
companion-seller loss limit, and a 45-game family ceiling. `RUN_LIVE` defaults
to `False`. Offline tests establish safety and contract validity, not rating
superiority.
""",
        },
        {
            "version": 29,
            "filename": "GLEE_Competition_agent_v29_bob_recovery.ipynb",
            "build_id": "v29-bob-recovery-2026-08-29",
            "family": "bargaining", "role": "player_2", "mode": None,
            "target": 16, "max_total": 40, "max_attempts": 50,
            "policy": V29_POLICY, "tests": V29_TESTS,
            "policy_heading": "## V29 policy — Bob delay-aware recovery",
            "intro": """# GLEE Competition agent V29 — Bob recovery

V29 freezes the strongly positive V27 Alice branch and changes only Bob. The
Bob policy removes the blanket full-information correction, makes a small
delay-aware agreement adjustment, and lowers acceptance floors only when delay
or repeated states make waiting expensive. Negotiation and persuasion receive
no live traffic.

The live target is 16 Bob-role completions with role-local loss and drawdown
guards and a 40-game family ceiling. `RUN_LIVE` defaults to `False`. Offline
tests establish safety and contract validity, not rating superiority.
""",
        },
        {
            "version": 30,
            "filename": "GLEE_Competition_agent_v30_binary_seller_ablation.ipynb",
            "build_id": "v30-binary-seller-ablation-2026-08-29",
            "family": "persuasion", "role": "seller", "mode": "binary",
            "target": 12, "max_total": 40, "max_attempts": 50,
            "policy": V30_POLICY, "tests": V30_TESTS,
            "policy_heading": "## V30 policy — calibrated binary seller pooling",
            "intro": """# GLEE Competition agent V30 — binary persuasion-seller ablation

V30 changes only the V27 binary seller, whose deterministic truthfulness lost
36.10 points across 11 games. It retains the positive V27 buyer and text seller,
and introduces deterministic, Bayes-bounded low-quality pooling for binary
recommendations. The probability is capped, response-gated, and reproducible
from game ID and round.

The live target is 12 binary-seller completions with mode-local loss and
drawdown guards and a 40-game persuasion ceiling. `RUN_LIVE` defaults to
`False`. Offline tests establish safety and contract validity, not rating
superiority.
""",
        },
    ]
    for spec in specs:
        output = build(spec, v23_buyer)
        print(output.name)


if __name__ == "__main__":
    main()
