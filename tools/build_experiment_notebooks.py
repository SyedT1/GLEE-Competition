"""Build the controlled post-V13 GLEE experiment notebooks.

The notebooks deliberately reuse the audited V13 policy cells.  This script only
adds experiment-specific arm assignment, telemetry, analysis, and offline tests.
Live matchmaking remains disabled in every generated notebook.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"
BASE_PATH = NOTEBOOK_DIR / "GLEE_Competition_agent_v13.ipynb"


def md(text: str):
    return nbformat.v4.new_markdown_cell(text.strip() + "\n")


def code(text: str):
    return nbformat.v4.new_code_cell(text.strip() + "\n")


def clean_base(version: str, title: str, summary: str):
    notebook = nbformat.read(BASE_PATH, as_version=4)
    notebook = copy.deepcopy(notebook)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        else:
            cell.pop("outputs", None)
            cell.pop("execution_count", None)

    notebook.cells[0].source = f"""# {title}

{summary}

This notebook inherits the deterministic V4 bargaining, V5 negotiation, and V3
persuasion policies plus V13's strict action validation. It contains no Qwen or
other language-model component. **Live matchmaking is disabled by default.**
Run all offline tests before deliberately enabling one controlled assignment.
"""

    config = notebook.cells[3].source
    config = config.replace("GLEE_V13_MODE", f"GLEE_{version.upper()}_MODE")
    config = config.replace("GLEE_V13_WORK_DIR", f"GLEE_{version.upper()}_WORK_DIR")
    config = config.replace("GLEE_V13_STATE_PATH", f"GLEE_{version.upper()}_STATE_PATH")
    config = config.replace("GLEE_V13_EVIDENCE_PATH", f"GLEE_{version.upper()}_EVIDENCE_PATH")
    config = config.replace("glee_v13_policy_state.json", f"glee_{version}_policy_state.json")
    config = config.replace("glee_v13_evidence.jsonl", f"glee_{version}_evidence.jsonl")
    config += r'''

def configure_glee_api_key():
    """Load the key at runtime without storing its value in the notebook."""
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

    # Keep the inherited version-13 state schema internally; each experiment has
    # isolated paths, so no state can contaminate another experiment.
    return notebook


def live_cell(notebook, family: str, strategy_name: str, report_name: str):
    source = notebook.cells[17].source
    marker = 'EVALUATION_FAMILY = "bargaining"'
    source = source[: source.index(marker)] + f'''EVALUATION_FAMILY = "{family}"
RUN_LIVE = False

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    {report_name} = run_one_queue_assignment(
        client, {strategy_name}, EVALUATION_FAMILY
    )
    display({report_name})
else:
    print("Live matchmaking is disabled. Review tests and set RUN_LIVE=True for one assignment only.")
'''
    notebook.cells[17].source = source


def insert_before_runner(notebook, *cells):
    notebook.cells[16:16] = list(cells)
    # Original runner/test/inspection cells move right by len(cells).
    return 17 + len(cells)


def set_runner_cell(notebook, original_runner_index: int, family: str,
                    strategy_name: str, report_name: str):
    source = notebook.cells[original_runner_index].source
    marker = 'EVALUATION_FAMILY = "bargaining"'
    source = source[: source.index(marker)] + f'''EVALUATION_FAMILY = "{family}"
RUN_LIVE = False

if RUN_LIVE:
    api_key = configure_glee_api_key()
    client = GleeClient(api_key=api_key)
    {report_name} = run_one_queue_assignment(client, {strategy_name}, EVALUATION_FAMILY)
    display({report_name})
else:
    print("Live matchmaking is disabled. Review tests and set RUN_LIVE=True for one assignment only.")
'''
    notebook.cells[original_runner_index].source = source


def write(notebook, filename: str):
    path = NOTEBOOK_DIR / filename
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    print(path.relative_to(ROOT))


def build_negotiation_drift():
    nb = clean_base(
        "v14",
        "GLEE V14 — frozen-policy negotiation drift audit",
        "Diagnose why the unchanged V5 negotiation core was positive in V5/V8 but negative in V11. No challenger policy is active.",
    )
    experiment = code(r'''
# Pre-registered observational audit. The economic action is still the exact V5 policy.
EXPERIMENT_ID = "v14_negotiation_drift"
DRIFT_DECISIONS = deque(maxlen=4000)

def visible_negotiation_snapshot(game):
    state = game["game_state"]
    me = canonical_player(game.get("your_player", state.get("current_player", "player_1")))
    role = state.get(f"{me}_role", "unknown")
    own_value = state.get(f"{me}_value")
    opponent = other_player(me)
    opponent_value = state.get(f"{opponent}_value")
    values = [finite_float(value) for value in (own_value, opponent_value) if value is not None]
    return {
        "experiment_id": EXPERIMENT_ID,
        "game_id": str(game.get("game_id")),
        "role": role,
        "round": state.get("round"),
        "max_rounds": state.get("max_rounds"),
        "horizon_known": bool(state.get("horizon_known")),
        "complete_information": bool(state.get("complete_information")),
        "own_value": own_value,
        "visible_opponent_value": opponent_value,
        "visible_value_span": max(values) - min(values) if len(values) == 2 else None,
        "last_offer": state.get("last_offer"),
        "history": state.get("history", []),
        "opponent": game.get("opponent"),
    }

def negotiation_drift_strategy(game):
    if game.get("game_family") != "negotiation":
        raise ValueError("V14 is negotiation-only")
    before = visible_negotiation_snapshot(game)
    started = time.perf_counter()
    action = strategy(game)
    elapsed_ms = 1000.0 * (time.perf_counter() - started)
    record = {**before, "action": action, "decision_latency_ms": round(elapsed_ms, 3)}
    DRIFT_DECISIONS.append(record)
    append_jsonl("negotiation_drift_decision", record)
    return action

def drift_rows():
    rows = []
    for record in DRIFT_DECISIONS:
        row = {key: value for key, value in record.items() if key not in {"history", "last_offer", "opponent", "action"}}
        row["action"] = json.dumps(record["action"], sort_keys=True)
        row["opponent_type"] = (record.get("opponent") or {}).get("type")
        row["opponent_name"] = (record.get("opponent") or {}).get("name")
        rows.append(row)
    return rows

probe = base_game("negotiation", "offer", {
    "current_player": "player_1", "player_1_role": "seller", "player_2_role": "buyer",
    "player_1_value": 20.0, "player_2_value": 100.0, "complete_information": True,
    "round": 1, "max_rounds": 6, "horizon_known": True, "history": [],
}, "player_1", "v14-drift-probe")
assert validate_action(probe, negotiation_drift_strategy(probe))
assert DRIFT_DECISIONS[-1]["role"] == "seller"
print("V14 drift-audit wrapper test passed.")
''')
    analysis = code(r'''
# After each deliberately triggered assignment, inspect these rows before continuing.
display(drift_rows()[-50:])
print("Action fallbacks:", len(ACTION_FALLBACK_LOG))
print("Telemetry diagnostics:", len(TELEMETRY_LOG))
print("Evidence path:", EVIDENCE_PATH.resolve())
''')
    runner_index = insert_before_runner(nb, md("## V14 drift-audit instrumentation"), experiment, analysis)
    set_runner_cell(nb, runner_index, "negotiation", "negotiation_drift_strategy", "v14_live_report")
    write(nb, "GLEE_Competition_experiment_v14_negotiation_drift.ipynb")


def build_alice_ablation():
    nb = clean_base(
        "v15",
        "GLEE V15 — randomized Alice bargaining ablation",
        "Compare V4 against symmetric Alice-only responder-floor perturbations while keeping cycle insurance fixed.",
    )
    experiment = code(r'''
EXPERIMENT_ID = "v15_alice_ablation"
ALICE_ARMS = ("v4_safe", "alice_claim_006", "alice_deal_006")
ALICE_ASSIGNMENT_LOG = deque(maxlen=1000)

def preassigned_alice_arm(game_id):
    token = hashlib.sha256(f"{EXPERIMENT_ID}:{game_id}".encode()).digest()
    return ALICE_ARMS[int.from_bytes(token[:8], "big") % len(ALICE_ARMS)]

_base_select_policy_arm = select_policy_arm

def select_policy_arm(game, role):
    """Equal-probability, immutable whole-game assignment for Alice; V4 for Bob."""
    if game.get("game_family") != "bargaining":
        return _base_select_policy_arm(game, role)
    game_id = str(game.get("game_id", "unknown"))
    with LOCK:
        existing = POLICY_ASSIGNMENTS.get(game_id)
        if existing:
            return existing["arm"]
        arm = preassigned_alice_arm(game_id) if player_index(role) == 1 else "v4_safe"
        assignment = {
            "family": "bargaining", "role": canonical_player(role),
            "context": policy_context(game, canonical_player(role)), "arm": arm,
            "player": canonical_player(game.get("your_player", role)),
            "state": dict(game["game_state"]), "synthetic": is_synthetic_game_id(game_id),
            "experiment_id": EXPERIMENT_ID,
        }
        POLICY_ASSIGNMENTS[game_id] = assignment
        ALICE_ASSIGNMENT_LOG.append({"game_id": game_id, "role": assignment["role"], "arm": arm})
        append_jsonl("alice_arm_assignment", ALICE_ASSIGNMENT_LOG[-1])
        return arm

def alice_experiment_strategy(game):
    if game.get("game_family") != "bargaining":
        raise ValueError("V15 is bargaining-only")
    action = strategy(game)
    assignment = POLICY_ASSIGNMENTS[str(game["game_id"])]
    append_jsonl("alice_ablation_decision", {
        "experiment_id": EXPERIMENT_ID, "game_id": str(game["game_id"]),
        "role": assignment["role"], "arm": assignment["arm"],
        "round": game["game_state"].get("round"), "action": action,
        "stall_count": bargaining_stall_count(game["game_state"], finite_float(game["game_state"]["money_to_divide"])),
    })
    return action

def make_alice_probe(game_id):
    return base_game("bargaining", "offer", {
        "current_player": "player_1", "money_to_divide": 100.0,
        "complete_information": False, "round": 1, "max_rounds": 8,
        "horizon_known": True, "history": [],
    }, "player_1", game_id)

probe_ids = [f"live-like-alice-{i}" for i in range(60)]
assigned = [preassigned_alice_arm(game_id) for game_id in probe_ids]
assert set(assigned) == set(ALICE_ARMS)
probe = make_alice_probe("live-like-alice-contract")
assert validate_action(probe, alice_experiment_strategy(probe))
assert select_policy_arm(probe, "player_1") == select_policy_arm(probe, "player_1")
print("V15 immutable randomized-arm tests passed.")
''')
    analysis = code(r'''
def alice_assignment_counts():
    counts = defaultdict(int)
    for assignment in POLICY_ASSIGNMENTS.values():
        if assignment.get("experiment_id") == EXPERIMENT_ID:
            counts[(assignment["role"], assignment["arm"])] += 1
    return [{"role": role, "arm": arm, "n": n} for (role, arm), n in sorted(counts.items())]

display(alice_assignment_counts())
print("Primary outcome: unambiguous per-game rating delta, stratified by Alice/Bob and arm.")
print("Secondary outcomes: rounds, agreement, own share, zero payoff, and cycle-detector activation.")
''')
    runner_index = insert_before_runner(nb, md("## V15 pre-registered Alice-only arm assignment"), experiment, analysis)
    set_runner_cell(nb, runner_index, "bargaining", "alice_experiment_strategy", "v15_live_report")
    write(nb, "GLEE_Competition_experiment_v15_alice_ablation.ipynb")


def build_cycle_ablation():
    nb = clean_base(
        "v16",
        "GLEE V16 — offline bargaining cycle-repair ablation",
        "Replay the extreme-discount failure under V3, cap-only, detector-only, and full V4 mechanisms. This notebook never enters matchmaking.",
    )
    experiment = code(r'''
EXPERIMENT_ID = "v16_cycle_ablation"

def ablation_offer(state, arm):
    money = finite_float(state["money_to_divide"])
    me = canonical_player(state.get("current_player", "player_1"))
    opponent = other_player(me)
    own_delta = player_delta(state, me)
    opponent_delta = player_delta(state, opponent)
    visible_floor = rubinstein_responder_share(own_delta, opponent_delta)
    remove_cap = arm in {"cap_only", "v4_full"}
    detector = arm in {"detector_only", "v4_full"}
    responder_share = visible_floor if remove_cap else min(0.50, visible_floor)
    series = bargaining_offer_series(state, money)
    stalls = min(tail_repeat_count(series["player_1"], 0.003), tail_repeat_count(series["player_2"], 0.003))
    if detector and stalls >= 3 and series[opponent]:
        responder_share = clamp(series[opponent][-1], 0.20, 0.9999)
    responder_gain = round(money * responder_share, 8)
    own_gain = money - responder_gain
    return ({"alice_gain": own_gain, "bob_gain": responder_gain} if player_index(me) == 1
            else {"alice_gain": responder_gain, "bob_gain": own_gain})

def ablation_response(state, arm):
    money = finite_float(state["money_to_divide"])
    me = canonical_player(state.get("current_player", "player_1"))
    gain = allocation(state.get("last_offer") or {}, me)
    stalls = bargaining_stall_count(state, money)
    detector = arm in {"detector_only", "v4_full"}
    if detector and stalls >= 3 and gain is not None and gain > 0:
        return {"decision": "accept"}
    return {"decision": "reject"}

def extreme_history(repeats=3, money=1_000_000.0):
    history = []
    for round_number in range(1, repeats + 1):
        history.extend([
            {"round": round_number, "proposer": "player_1", "offer": {"player_1_gain": 350000.0, "player_2_gain": 650000.0}, "decision": "reject"},
            {"round": round_number, "proposer": "player_2", "offer": {"player_1_gain": 0.01, "player_2_gain": money - 0.01}, "decision": "reject"},
        ])
    return history

def cycle_ablation_rows():
    rows = []
    for arm in ("v3", "cap_only", "detector_only", "v4_full"):
        state = {
            "current_player": "player_1", "money_to_divide": 1_000_000.0,
            "complete_information": True, "delta_1": 0.10, "delta_2": 0.9999,
            "horizon_known": False, "round": 7, "history": extreme_history(),
        }
        offer = ablation_offer(state, arm)
        response_state = dict(state)
        response_state["current_player"] = "player_1"
        response_state["last_offer"] = {"player_1_gain": 0.01, "player_2_gain": 999999.99}
        rows.append({
            "arm": arm,
            "alice_offer": offer["alice_gain"], "bob_offer": offer["bob_gain"],
            "response_to_positive_cent": ablation_response(response_state, arm)["decision"],
            "stall_count": bargaining_stall_count(state, state["money_to_divide"]),
        })
    return rows

CYCLE_ABLATION = cycle_ablation_rows()
by_arm = {row["arm"]: row for row in CYCLE_ABLATION}
assert by_arm["v3"]["bob_offer"] <= 500000.0 + 1e-6
assert by_arm["cap_only"]["bob_offer"] > 990000.0
assert by_arm["detector_only"]["response_to_positive_cent"] == "accept"
assert by_arm["v4_full"]["response_to_positive_cent"] == "accept"
display(CYCLE_ABLATION)
print("V16 cycle mechanism ablation passed.")
''')
    sensitivity = code(r'''
# Neighboring sensitivity grid: vary extreme discounts and cycle length.
SENSITIVITY_ROWS = []
for own_delta in (0.05, 0.10, 0.20, 0.50):
    for opponent_delta in (0.95, 0.99, 0.9999):
        for repeats in (0, 1, 2, 3, 4):
            state = {
                "current_player": "player_1", "money_to_divide": 1_000_000.0,
                "complete_information": True, "delta_1": own_delta, "delta_2": opponent_delta,
                "horizon_known": False, "round": 2 * repeats + 1,
                "history": extreme_history(repeats),
            }
            for arm in ("v3", "cap_only", "detector_only", "v4_full"):
                offer = ablation_offer(state, arm)
                SENSITIVITY_ROWS.append({
                    "own_delta": own_delta, "opponent_delta": opponent_delta,
                    "repeats": repeats, "arm": arm,
                    "opponent_share": offer["bob_gain"] / state["money_to_divide"],
                })
display(SENSITIVITY_ROWS[:20])
print("Sensitivity rows:", len(SENSITIVITY_ROWS))
''')
    insert_before_runner(nb, md("## V16 two-factor cycle-repair ablation"), experiment, sensitivity)
    # Disable and label the inherited live cell even if a user executes all cells.
    runner_index = 20
    source = nb.cells[runner_index].source
    marker = 'EVALUATION_FAMILY = "bargaining"'
    nb.cells[runner_index].source = source[: source.index(marker)] + '''RUN_LIVE = False
print("V16 is offline-only; live matchmaking is intentionally unavailable.")
'''
    write(nb, "GLEE_Competition_experiment_v16_cycle_ablation.ipynb")


def build_persuasion_seller():
    nb = clean_base(
        "v17",
        "GLEE V17 — randomized persuasion-seller policy experiment",
        "Compare V3 pooling, full truthfulness, and terminal-only pooling while locking every buyer to V3.",
    )
    experiment = code(r'''
EXPERIMENT_ID = "v17_persuasion_seller"
SELLER_ARMS = ("v3_safe", "seller_truthful", "seller_terminal_pool")
SELLER_ASSIGNMENT_LOG = deque(maxlen=1000)

def preassigned_seller_arm(game_id):
    token = hashlib.sha256(f"{EXPERIMENT_ID}:{game_id}".encode()).digest()
    return SELLER_ARMS[int.from_bytes(token[:8], "big") % len(SELLER_ARMS)]

_base_select_policy_arm = select_policy_arm

def select_policy_arm(game, role):
    if game.get("game_family") != "persuasion":
        return _base_select_policy_arm(game, role)
    game_id = str(game.get("game_id", "unknown"))
    with LOCK:
        existing = POLICY_ASSIGNMENTS.get(game_id)
        if existing:
            return existing["arm"]
        arm = preassigned_seller_arm(game_id) if role == "seller" else "v3_safe"
        assignment = {
            "family": "persuasion", "role": role, "context": policy_context(game, role),
            "arm": arm, "player": canonical_player(game.get("your_player", game["game_state"].get("current_player", "player_1"))),
            "state": dict(game["game_state"]), "synthetic": is_synthetic_game_id(game_id),
            "experiment_id": EXPERIMENT_ID,
        }
        POLICY_ASSIGNMENTS[game_id] = assignment
        SELLER_ASSIGNMENT_LOG.append({"game_id": game_id, "role": role, "arm": arm})
        append_jsonl("persuasion_seller_arm_assignment", SELLER_ASSIGNMENT_LOG[-1])
        return arm

def persuasion_experiment_strategy(game):
    if game.get("game_family") != "persuasion":
        raise ValueError("V17 is persuasion-only")
    action = strategy(game)
    assignment = POLICY_ASSIGNMENTS[str(game["game_id"])]
    state = game["game_state"]
    append_jsonl("persuasion_experiment_decision", {
        "experiment_id": EXPERIMENT_ID, "game_id": str(game["game_id"]),
        "role": assignment["role"], "arm": assignment["arm"],
        "round": state.get("round"), "max_rounds": state.get("max_rounds"),
        "quality": state.get("quality"), "product_price": state.get("product_price"),
        "history": state.get("history", []), "action": action,
    })
    return action

probe_ids = [f"live-like-seller-{i}" for i in range(60)]
assert set(preassigned_seller_arm(game_id) for game_id in probe_ids) == set(SELLER_ARMS)
seller_probe = base_game("persuasion", "seller_recommendation", {
    "current_player": "player_1", "player_1_role": "seller", "player_2_role": "buyer",
    "quality": "high", "p": 0.5, "v": 100.0, "u": 0.0, "product_price": 50.0,
    "round": 1, "max_rounds": 6, "horizon_known": True, "history": [],
}, "player_1", "live-like-seller-contract")
assert validate_action(seller_probe, persuasion_experiment_strategy(seller_probe))
print("V17 seller-arm randomization and contract tests passed.")
''')
    analysis = code(r'''
def persuasion_assignment_counts():
    counts = defaultdict(int)
    for assignment in POLICY_ASSIGNMENTS.values():
        if assignment.get("experiment_id") == EXPERIMENT_ID:
            counts[(assignment["role"], assignment["arm"])] += 1
    return [{"role": role, "arm": arm, "n": n} for (role, arm), n in sorted(counts.items())]

display(persuasion_assignment_counts())
print("Buyer policy is locked to v3_safe. Analyze sellers by arm and never pool buyer and seller outcomes.")
print("Primary outcome: rating delta. Secondary: seller payoff, purchase response, precision, and credibility path.")
''')
    runner_index = insert_before_runner(nb, md("## V17 whole-game seller-arm assignment"), experiment, analysis)
    set_runner_cell(nb, runner_index, "persuasion", "persuasion_experiment_strategy", "v17_live_report")
    write(nb, "GLEE_Competition_experiment_v17_persuasion_seller.ipynb")


def build_runner_faults():
    nb = clean_base(
        "v18",
        "GLEE V18 — controlled-runner fault-injection laboratory",
        "Test queue races, duplicate pending turns, server rejection, and cleanup without contacting GLEE.",
    )
    faults = code(r'''
EXPERIMENT_ID = "v18_runner_fault_injection"

def runner_probe_game(game_id="fault-game-1", round_number=1):
    return base_game("bargaining", "offer", {
        "current_player": "player_1", "money_to_divide": 100.0,
        "complete_information": False, "round": round_number, "max_rounds": 4,
        "horizon_known": True, "history": [],
    }, "player_1", game_id)

class ScriptedRunnerClient:
    def __init__(self, pending_frames, reject_moves=False, leave_error=False):
        self.pending_frames = list(pending_frames)
        self.reject_moves = reject_moves
        self.leave_error = leave_error
        self.frame = 0
        self.queue_calls = []
        self.leave_calls = []
        self.moves = []
        self.assigned = {str(game["game_id"]) for frame in pending_frames for game in frame}

    def stats(self):
        active = 1 if self.frame < len(self.pending_frames) else 0
        return {"active_games": active if self.queue_calls else 0,
                "scores": {"bargaining": {"rating": 1000.0, "games_played": 0}}}

    def queue(self, family):
        self.queue_calls.append(family)
        return {"status": "queued"}

    def leave_queue(self, family=None):
        self.leave_calls.append(family)
        if self.leave_error:
            raise RuntimeError("injected leave failure")
        return {"status": "left"}

    def pending_games(self):
        if self.frame >= len(self.pending_frames):
            return []
        frame = self.pending_frames[self.frame]
        self.frame += 1
        return frame

    def move(self, game_id, action):
        self.moves.append((str(game_id), dict(action)))
        if self.reject_moves:
            return {"valid": False, "game_over": False}
        return {"valid": True, "game_over": True}

FAULT_RESULTS = []

single = ScriptedRunnerClient([[runner_probe_game()]])
report = run_one_queue_assignment(single, strategy, "bargaining", poll_interval=0, stats_interval=0)
assert report["assignment_overshoot"] == 0 and len(single.moves) == 1
assert single.queue_calls == ["bargaining"] and single.leave_calls
FAULT_RESULTS.append({"scenario": "single_assignment", "status": "pass", **report})

overshoot = ScriptedRunnerClient([[
    runner_probe_game("fault-game-a"), runner_probe_game("fault-game-b")
]])
report = run_one_queue_assignment(overshoot, strategy, "bargaining", poll_interval=0, stats_interval=0)
assert report["assignment_overshoot"] == 1 and len(overshoot.moves) == 2
FAULT_RESULTS.append({"scenario": "assignment_overshoot", "status": "pass", **report})

rejected = ScriptedRunnerClient([[runner_probe_game("fault-rejected")]], reject_moves=True)
try:
    run_one_queue_assignment(rejected, strategy, "bargaining", poll_interval=0, stats_interval=0)
    raise AssertionError("injected server rejection was not raised")
except RuntimeError as exc:
    assert "server rejected move" in str(exc)
    assert rejected.leave_calls
FAULT_RESULTS.append({"scenario": "server_rejection_cleanup", "status": "pass"})

leave_failure = ScriptedRunnerClient([[runner_probe_game("fault-leave")]], leave_error=True)
try:
    run_one_queue_assignment(leave_failure, strategy, "bargaining", poll_interval=0, stats_interval=0)
except RuntimeError:
    pass
assert any(item.get("event") == "leave_queue" for item in TELEMETRY_LOG)
FAULT_RESULTS.append({"scenario": "leave_failure_telemetry", "status": "pass"})

display(FAULT_RESULTS)
print("V18 runner fault-injection suite passed without network access.")
''')
    # Fault tests need the runner definition before their cell, so append after it.
    nb.cells[16].source = nb.cells[16].source.replace(
        "## Controlled live runner", "## Runner under test"
    )
    runner_source = nb.cells[17].source
    marker = 'EVALUATION_FAMILY = "bargaining"'
    nb.cells[17].source = runner_source[: runner_source.index(marker)] + '''RUN_LIVE = False
print("V18 is offline-only; no live client is created.")
'''
    nb.cells[18:18] = [md("## V18 deterministic fault injection"), faults]
    write(nb, "GLEE_Competition_experiment_v18_runner_fault_injection.ipynb")


def main():
    build_negotiation_drift()
    build_alice_ablation()
    build_cycle_ablation()
    build_persuasion_seller()
    build_runner_faults()


if __name__ == "__main__":
    main()
