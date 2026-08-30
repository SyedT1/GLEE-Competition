"""Build V33: a guarded heuristic portfolio targeting 150 games per family."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "GLEE_Competition_agent_v31_contextual_60_each.ipynb"
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v33_heuristic_150_each.ipynb"


POLICY = r'''
# ---------------------------------------------------------------------------
# V33 evidence-locked portfolio
# ---------------------------------------------------------------------------
V33_ARM = "v33_evidence_locked_heuristic"


def trace_v33(game, role, metrics, action):
    record = {
        "game_id": str(game.get("game_id")),
        "family": game["game_family"],
        "role": role,
        "round": game["game_state"].get("round"),
        "metrics": metrics,
        "action": dict(action),
    }
    HEURISTIC_TRACE.append(record)
    append_jsonl("v33_heuristic_decision", record)
    return action


def assign_v33(game, role, branch):
    game_id = str(game.get("game_id", "unknown"))
    with LOCK:
        existing = POLICY_ASSIGNMENTS.get(game_id, {})
        existing.update({
            "family": game["game_family"],
            "role": role,
            "context": policy_context(game, role),
            "arm": f"{V33_ARM}:{branch}",
            "player": canonical_player(game.get(
                "your_player", game["game_state"].get("current_player", "player_1")
            )),
            "state": dict(game["game_state"]),
            "synthetic": is_synthetic_game_id(game_id) or game_id.startswith("v33-"),
        })
        POLICY_ASSIGNMENTS[game_id] = existing


def v33_bargaining_strategy(game):
    """Keep positive V27 Alice and V29 delay-aware Bob without blanket softening."""
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    branch = "alice_v27_champion" if player_index(me) == 1 else "bob_v29_delay_recovery"
    assign_v33(game, me, branch)
    action = v29_bargaining_strategy(game)
    return trace_v33(game, me, {
        "branch": branch,
        "progress": round_progress(state),
        "own_delta": player_delta(state, me),
        "stalls": bargaining_stall_count(state, finite_float(state["money_to_divide"])),
    }, action)


def v33_negotiation_strategy(game):
    """Use the V23 buyer rollback and the later positive seller branch."""
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state["current_player"]))
    role = state[f"{me}_role"]
    branch = "buyer_v23_rollback" if role == "buyer" else "seller_v27_champion"
    assign_v33(game, role, branch)
    action = v28_negotiation_strategy(game)
    return trace_v33(game, role, {
        "branch": branch,
        "progress": round_progress(state),
        "complete_information": bool(state.get("complete_information")),
        "messages_allowed": bool(state.get("messages_allowed")),
    }, action)


def v33_quality_signal_counts(state):
    counts = {"high_positive": 0, "low_positive": 0, "low_seen": 0}
    for record in state.get("history", []):
        if not isinstance(record, dict):
            continue
        quality = record.get("quality", record.get("current_quality"))
        if quality == "low":
            counts["low_seen"] += 1
        positive = signal_polarity(record.get(
            "seller_message", record.get("seller_recommendation")
        ))
        if positive is True and quality == "high":
            counts["high_positive"] += 1
        elif positive is True and quality == "low":
            counts["low_positive"] += 1
    return counts


def v33_pool_probability(state, p, price, round_no, total_rounds):
    """A near-optimal Bayesian pool bounded strictly inside buyer obedience."""
    cutoff = persuasion_cutoff(state, price)
    terminal = round_no >= total_rounds
    if cutoff is None:
        # Hidden receiver values: monetize cautiously, but do not return to the
        # terminal-only policy that repeatedly lost seller rating.
        return clamp(0.12 + 0.28 * p + (0.05 if terminal else 0.0), 0.0, 0.40)
    if cutoff <= 0.0:
        return 1.0
    if cutoff >= 1.0:
        return 0.0
    bound = static_pool_bound(p, cutoff)
    # Preserve a finite-sample obedience margin. Terminal play receives only a
    # small relaxation; it never becomes unconditional deception.
    utilization = 0.94 if terminal else 0.88
    return clamp(utilization * bound, 0.0, min(0.92, bound))


def v33_paced_pool(probability, low_seen):
    """Spread low-quality recommendations evenly instead of bursty hashing."""
    before = math.floor(low_seen * probability + 1e-12)
    after = math.floor((low_seen + 1) * probability + 1e-12)
    return after > before


def v33_persuasion_strategy(game):
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    seller_view = action_type in {"seller_message", "seller_recommendation"}
    if not seller_view:
        # V23/V27 buyer behavior was positive in every large role-level audit.
        assign_v33(game, "buyer", "buyer_v23_champion")
        action = v27_persuasion_100_strategy(game)
        return trace_v33(game, "buyer", {"branch": "buyer_v23_champion"}, action)

    assign_v33(game, "seller", "seller_obedience_paced_pool")
    quality = state.get("current_quality", state.get("quality"))
    price = finite_float(state["product_price"])
    p = clamp(finite_float(state.get("p"), 0.5), 0.0, 1.0)
    round_no = max(1, int(state.get("round", 1)))
    total_rounds = max(
        round_no,
        int(state.get("total_rounds", state.get("max_rounds", round_no)) or round_no),
    )
    counts = v33_quality_signal_counts(state)
    probability = 0.0
    recommend = quality == "high"
    if quality == "low":
        probability = v33_pool_probability(state, p, price, round_no, total_rounds)
        recommend = v33_paced_pool(probability, counts["low_seen"])

    if action_type == "seller_recommendation":
        action = {"decision": "yes" if recommend else "no"}
    else:
        action = {"message": action_message(
            "My recommendation: BUY this product." if recommend else
            "My recommendation: PASS on this product this round."
        )}
    return trace_v33(game, "seller", {
        "branch": "seller_obedience_paced_pool",
        "quality": quality,
        "pool_probability": probability,
        "low_seen": counts["low_seen"],
        "positive_high": counts["high_positive"],
        "positive_low": counts["low_positive"],
        "cutoff": persuasion_cutoff(state, price),
    }, action)


STRATEGIES["bargaining"] = v33_bargaining_strategy
STRATEGIES["negotiation"] = v33_negotiation_strategy
STRATEGIES["persuasion"] = v33_persuasion_strategy
print("V33 portfolio activated: role-locked bargaining/negotiation + obedience-paced persuasion.")
'''


TESTS = r'''
def run_v33_policy_tests():
    checked = 0
    for player in ("player_1", "player_2"):
        for action_type in ("offer", "respond"):
            state = {
                "current_player": player, "money_to_divide": 100.0,
                "delta_1": 0.90, "delta_2": 0.96,
                "complete_information": True, "round": 3,
                "max_rounds": 9, "horizon_known": True,
                "history": [], "messages_allowed": False,
            }
            if action_type == "respond":
                state["last_offer"] = {"alice_gain": 48.0, "bob_gain": 52.0}
            game = base_game("bargaining", action_type, state, player,
                             f"v33-bargaining-{player}-{action_type}")
            validate_action(game, v33_bargaining_strategy(game))
            checked += 1

    for role in ("buyer", "seller"):
        opponent_role = "seller" if role == "buyer" else "buyer"
        for action_type in ("offer", "respond"):
            state = {
                "current_player": "player_1", "player_1_role": role,
                "player_2_role": opponent_role,
                "player_1_value": 80.0 if role == "buyer" else 40.0,
                "player_2_value": 40.0 if role == "buyer" else 80.0,
                "complete_information": True, "round": 2,
                "max_rounds": 8, "horizon_known": True,
                "history": [], "messages_allowed": False,
            }
            if action_type == "respond":
                state["last_offer"] = {"price": 58.0}
            game = base_game("negotiation", action_type, state, "player_1",
                             f"v33-negotiation-{role}-{action_type}")
            validate_action(game, v33_negotiation_strategy(game))
            checked += 1

    seller_state = {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "product_price": 100.0,
        "p": 0.50, "v": 180.0, "u": 20.0, "round": 3,
        "total_rounds": 10, "current_quality": "low", "history": [],
    }
    for mode in ("seller_recommendation", "seller_message"):
        game = base_game("persuasion", mode, dict(seller_state), "player_1",
                         f"v33-persuasion-{mode}")
        validate_action(game, v33_persuasion_strategy(game))
        checked += 1

    # Pacing realizes the requested probability to within one low-quality draw.
    for probability in (0.0, 0.13, 0.50, 0.88, 1.0):
        realized = sum(v33_paced_pool(probability, i) for i in range(100))
        assert abs(realized - 100 * probability) <= 1.0

    # The known-value policy never exceeds its Bayesian obedience bound.
    for p in (0.20, 0.50, 0.80):
        for price in (40.0, 100.0, 170.0):
            state = dict(seller_state, p=p, product_price=price)
            probability = v33_pool_probability(state, p, price, 3, 10)
            cutoff = persuasion_cutoff(state, price)
            if cutoff is not None and 0.0 < cutoff < 1.0:
                assert probability <= static_pool_bound(p, cutoff) + 1e-12
            assert 0.0 <= probability <= 1.0

    assert checked == 10
    assert not ACTION_FALLBACK_LOG
    assert not TELEMETRY_LOG
    print("All V33 family, role, contract, pacing, and obedience tests passed.")


run_v33_policy_tests()
'''


RUNNER = r'''
LIVE_BUILD_ID = "v33-heuristic-150-each-2026-08-30"
print("Live build:", LIVE_BUILD_ID)

FAMILY_ORDER = ("bargaining", "persuasion", "negotiation")
TARGET_COMPLETIONS = {family: 150 for family in FAMILY_ORDER}
MAX_QUEUE_ATTEMPTS_PER_FAMILY = 190
MATCH_TIMEOUT_SECONDS = 300.0
MAX_CONSECUTIVE_TIMEOUTS = 3

# These are emergency exposure limits, not optimization claims. They are wide
# enough for rating noise but stop a repeat of the V11-style uncontrolled loss.
FAMILY_STOP_LOSS = {"bargaining": 30.0, "negotiation": 40.0, "persuasion": 28.0}
FAMILY_MAX_DRAWDOWN = {"bargaining": 24.0, "negotiation": 30.0, "persuasion": 22.0}
MIN_GAMES_BEFORE_TRAILING_STOP = 20
ROLE_STOP_LOSS = {"bargaining": 24.0, "negotiation": 28.0, "persuasion": 20.0}
ROLE_MAX_DRAWDOWN = {"bargaining": 18.0, "negotiation": 22.0, "persuasion": 16.0}
MIN_ROLE_GAMES_BEFORE_STOP = 10

# Upload-and-run default. Set GLEE_V33_RUN_LIVE=0 for a dry run.
RUN_LIVE = os.environ.get("GLEE_V33_RUN_LIVE", "1").strip() == "1"

assert TARGET_COMPLETIONS == {
    "bargaining": 150, "persuasion": 150, "negotiation": 150
}
assert MAX_QUEUE_ATTEMPTS_PER_FAMILY >= 150
print("V33 live configuration verified: 150 targets per family (450 maximum).")
print("RUN_LIVE:", RUN_LIVE)


def family_score_snapshot(stats, family):
    scores = stats.get("scores") or {}
    item = scores.get(family) or {}
    rating = item.get("rating")
    count = item.get("games_played", item.get("games", item.get("game_count", 0)))
    if rating is None:
        raise KeyError(f"stats missing {family} rating: {stats}")
    return {"rating": finite_float(rating), "games_played": int(count or 0)}


def role_guard_reason(family, role_deltas):
    for role, deltas in role_deltas.items():
        if len(deltas) < MIN_ROLE_GAMES_BEFORE_STOP:
            continue
        cumulative = sum(deltas)
        running = 0.0
        peak = 0.0
        for delta in deltas:
            running += delta
            peak = max(peak, running)
        if cumulative <= -ROLE_STOP_LOSS[family]:
            return f"role baseline stop-loss: {role}"
        if peak - cumulative >= ROLE_MAX_DRAWDOWN[family]:
            return f"role trailing drawdown: {role}"
    return None


def run_v33_family(client, family, target):
    initial = family_score_snapshot(client.stats(), family)
    peak_rating = initial["rating"]
    checkpoints = []
    role_deltas = defaultdict(list)
    stop_reason = None
    global_abort = False
    consecutive_timeouts = 0

    for attempt in range(1, MAX_QUEUE_ATTEMPTS_PER_FAMILY + 1):
        current = family_score_snapshot(client.stats(), family)
        completed = current["games_played"] - initial["games_played"]
        if completed >= target:
            stop_reason = "target reached"
            break
        if completed % 10 == 0:
            print(
                f"{family}: mini-batch checkpoint {completed}/{target}; "
                f"rating {current['rating'] - initial['rating']:+.2f}; "
                f"roles {dict((k, round(sum(v), 2)) for k, v in role_deltas.items())}"
            )

        fallback_before = len(ACTION_FALLBACK_LOG)
        telemetry_before = len(TELEMETRY_LOG)
        report = run_one_queue_assignment(
            client, strategy, family, match_timeout=MATCH_TIMEOUT_SECONDS
        )
        before = family_score_snapshot(report["before"], family)
        after = family_score_snapshot(report["after"], family)
        count_delta = after["games_played"] - before["games_played"]
        rating_delta = after["rating"] - before["rating"]
        completed = after["games_played"] - initial["games_played"]
        cumulative = after["rating"] - initial["rating"]
        peak_rating = max(peak_rating, after["rating"])
        drawdown = peak_rating - after["rating"]
        new_fallbacks = len(ACTION_FALLBACK_LOG) - fallback_before
        new_telemetry = len(TELEMETRY_LOG) - telemetry_before

        harvested = harvest_completed_games(client)
        credited = credit_rating_delta(
            report["assigned_ids"], family,
            before["rating"], after["rating"], count_delta,
        )
        role = None
        if count_delta == 1 and len(report["assigned_ids"]) == 1:
            assignment = POLICY_ASSIGNMENTS.get(report["assigned_ids"][0], {})
            role = str(assignment.get("role", "unknown"))
            role_deltas[role].append(rating_delta)

        checkpoint = {
            "family": family, "attempt": attempt, "target": target,
            "count_delta": count_delta, "rating_delta": round(rating_delta, 6),
            "cumulative_count": completed, "cumulative_rating": round(cumulative, 6),
            "peak_rating": round(peak_rating, 6), "peak_drawdown": round(drawdown, 6),
            "role": role,
            "role_cumulative": (round(sum(role_deltas[role]), 6) if role else None),
            "assignment_overshoot": report["assignment_overshoot"],
            "assigned_ids": report["assigned_ids"],
            "harvested_count": len(harvested), "rating_credit": credited,
            "new_action_fallbacks": new_fallbacks, "new_telemetry": new_telemetry,
        }
        checkpoints.append(checkpoint)
        append_jsonl("v33_microbatch_checkpoint", checkpoint)

        if report["assignment_overshoot"] > 0 or count_delta < 0 or count_delta > 1:
            stop_reason, global_abort = "unsafe assignment/count overshoot", True
            break
        if new_fallbacks or new_telemetry:
            stop_reason = "live action fallback" if new_fallbacks else "new telemetry diagnostic"
            global_abort = True
            break
        if count_delta == 0:
            consecutive_timeouts += 1
            if consecutive_timeouts >= MAX_CONSECUTIVE_TIMEOUTS:
                stop_reason = "repeated matchmaking timeout"
                break
            continue
        consecutive_timeouts = 0

        role_stop = role_guard_reason(family, role_deltas)
        if role_stop:
            stop_reason = role_stop
            break
        if completed >= MIN_GAMES_BEFORE_TRAILING_STOP:
            if cumulative <= -FAMILY_STOP_LOSS[family]:
                stop_reason = "family baseline stop-loss"
                break
            if drawdown >= FAMILY_MAX_DRAWDOWN[family]:
                stop_reason = "family trailing drawdown"
                break
        if completed >= target:
            stop_reason = "target reached"
            break
    else:
        stop_reason = "maximum queue attempts reached"

    final = family_score_snapshot(client.stats(), family)
    summary = {
        "family": family, "initial": initial, "final": final,
        "completed": final["games_played"] - initial["games_played"],
        "rating_change": round(final["rating"] - initial["rating"], 6),
        "peak_rating": round(peak_rating, 6),
        "peak_drawdown": round(peak_rating - final["rating"], 6),
        "role_deltas": {key: list(values) for key, values in role_deltas.items()},
        "stop_reason": stop_reason, "global_abort": global_abort,
        "checkpoints": checkpoints,
    }
    append_jsonl("v33_family_summary", summary)
    return summary


def run_v33_controller_tests():
    old_min = MIN_ROLE_GAMES_BEFORE_STOP
    globals()["MIN_ROLE_GAMES_BEFORE_STOP"] = 3
    try:
        assert role_guard_reason("persuasion", {"seller": [-8.0, -7.0, -6.0]}) == \
            "role baseline stop-loss: seller"
        assert role_guard_reason("negotiation", {"buyer": [3.0, -2.0, 1.0]}) is None
    finally:
        globals()["MIN_ROLE_GAMES_BEFORE_STOP"] = old_min
    assert FAMILY_ORDER == ("bargaining", "persuasion", "negotiation")
    assert all(TARGET_COMPLETIONS[family] == 150 for family in FAMILY_ORDER)
    print("All V33 target, ordering, role-guard, and exposure tests passed.")


run_v33_controller_tests()

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    v33_family_summaries = []
    for family in FAMILY_ORDER:
        print(f"Starting V33 {family}: target={TARGET_COMPLETIONS[family]}")
        summary = run_v33_family(client, family, TARGET_COMPLETIONS[family])
        v33_family_summaries.append(summary)
        display(summary)
        if summary["global_abort"]:
            print("Aborting remaining families:", summary["stop_reason"])
            break
    report_paths = export_session_report(
        "glee_v33_session_report.json", "glee_v33_rating_outcomes.csv"
    )
    print("Family summaries completed:", len(v33_family_summaries))
    print("Session reports:", report_paths)
else:
    print("Live matchmaking disabled by GLEE_V33_RUN_LIVE=0.")
'''


INTRO = """# GLEE Competition agent V33 — heuristic 150 games per family

This notebook is a no-LLM, family-specific recovery portfolio targeting exactly
150 authoritative completions in each family (450 maximum). It starts with
bargaining because that is the largest rating deficit, then runs persuasion and
negotiation. Matchmaking is always concurrency one and is re-evaluated after
every authoritative completion; a printed mini-batch checkpoint appears every
10 completions.

The design follows the complete V23–V32 evidence rather than aggregate ratings:

- **Bargaining:** retain the strongly positive V27 Alice branch and the V29
  delay/stall-aware Bob recovery. Do not repeat V27's blanket Bob concession.
- **Negotiation:** use the exact V23 buyer rollback and retain the later seller
  champion, because aggregate negotiation gains previously hid buyer losses.
- **Persuasion:** retain the repeatedly positive buyer. Replace terminal-only
  and under-pooling seller rules with deterministic Bayesian pooling kept inside
  the receiver-obedience bound in both binary and text modes.

Role-local and family-local emergency guards prevent one strong role from hiding
a material regression. These controls can stop a family before 150 if continued
play is demonstrably unsafe; no notebook can honestly guarantee a rating gain
against changing opponents. Live play defaults on. Set `GLEE_V33_RUN_LIVE=0`
before execution for an offline dry run.
"""


AUDIT = """## Failure audit and design decisions

| Observed problem | Evidence scanned | V33 response |
|---|---|---|
| Unlimited-horizon bargaining can cycle | V3 reached 99 rounds and no deal | Retain repeated-state detection, positive cycle acceptance, and final-round individual rationality |
| Bargaining performance is role-asymmetric | V27 Alice: +38.32/14; Bob: -30.51/27 | Preserve V27 Alice; replace blanket Bob softening with V29 delay/stall-conditioned recovery |
| Agreement rate is not the rating objective | V8 gained on some no-deals; V11's agreements still lost rating | Optimize configuration-relative surplus and reservation safety, not agreement count alone |
| Negotiation aggregate masked a role failure | V27 seller: +77.12/39; buyer: -46.15/29 | Exact V23 buyer rollback plus later seller champion; track rating by role |
| Persuasion buyer is consistently stronger | V23–V27 buyer samples were positive; sellers repeatedly reversed | Freeze the buyer branch; concentrate the new heuristic on seller signaling |
| Terminal-only seller pooling is unstable | V24 seller +3.22/5, then V26 seller -7.27/7 | Remove unconditional terminal deception; remain inside the receiver-obedience bound every round |
| Conservative random pooling underuses persuasion capacity | V30/V31 recovery did not repair the supplied persuasion decline | Use deterministic pacing at 88% of the Bayesian bound (94% terminal), avoiding bursty finite-game randomness |
| Large SDK calls can overshoot badly | V11 requested 24 at concurrency four and received 53 | Admit one assignment, leave the queue, drain it, inspect authoritative stats, then re-enter |
| Policy value is nonstationary | The exact V23 negotiation core ranged from +177.77/50 to +10.30/43 | Keep family and role drawdown guards; do not infer superiority from one batch |
| V32 did not match a three-family 150 request | V32 froze persuasion and capped bargaining+negotiation at 150 total | Target 150 authoritative completions in each of all three families |

The evidence is observational rather than randomized: opponent mix, roles,
configuration draws, rating shrinkage, and time all change. V33 therefore locks
the branches with the strongest replicated role evidence, changes only the
unresolved persuasion-seller mechanism, and treats guards as loss containment—not
as proof that a policy is optimal.
"""


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            cell.source = cell.source.replace("glee_v31_", "glee_v33_")
            cell.source = cell.source.replace("GLEE_V31_", "GLEE_V33_")
    notebook.cells[0].source = INTRO
    notebook.cells.insert(1, nbformat.v4.new_markdown_cell(AUDIT))
    for cell in notebook.cells:
        if cell.cell_type == "markdown":
            cell.source = cell.source.replace(
                "Set `RUN_LIVE=True` only after the offline tests pass. "
                "Evaluate one family at a time and start with the dashboard "
                "reporting zero active games.",
                "V33 runs live by default after its offline tests pass. Start "
                "with the dashboard reporting zero active games; set "
                "`GLEE_V33_RUN_LIVE=0` for a dry run.",
            )

    live_index = next(
        i for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "code" and "TARGET_COMPLETIONS = {" in cell.source
    )
    old_live = notebook.cells[live_index].source
    primitive = old_live.split('LIVE_BUILD_ID =', 1)[0]
    notebook.cells[live_index:live_index + 1] = [
        nbformat.v4.new_markdown_cell("## V33 evidence-locked heuristic policy"),
        nbformat.v4.new_code_cell(POLICY),
        nbformat.v4.new_code_cell(TESTS),
        nbformat.v4.new_markdown_cell("## Controlled 150-per-family live runner"),
        nbformat.v4.new_code_cell(primitive + RUNNER),
    ]

    # All generated tests must remain excluded from live evidence harvesting.
    inspect_index = next(
        i for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "markdown" and "Inspect exact evidence" in cell.source
    )
    notebook.cells.insert(inspect_index, nbformat.v4.new_code_cell(r'''
for _game_id, _assignment in POLICY_ASSIGNMENTS.items():
    if str(_game_id).startswith(("v28-", "v29-", "v30-", "v31-", "v33-")):
        _assignment["synthetic"] = True
print("V33 and inherited component-test assignments isolated from live evidence.")
'''))

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
