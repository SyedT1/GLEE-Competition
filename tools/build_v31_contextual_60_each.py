"""Build V31: evidence-guided contextual portfolio with 60-game family targets."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
SOURCE = (
    NOTEBOOKS / "Glee_competition_27"
    / "GLEE_Competition_agent_v27_100_each.ipynb"
)
RECOVERY_NOTEBOOKS = {
    28: NOTEBOOKS / "GLEE_Competition_agent_v28_negotiation_buyer_rollback.ipynb",
    29: NOTEBOOKS / "GLEE_Competition_agent_v29_bob_recovery.ipynb",
    30: NOTEBOOKS / "GLEE_Competition_agent_v30_binary_seller_ablation.ipynb",
}
OUTPUT = NOTEBOOKS / "GLEE_Competition_agent_v31_contextual_60_each.ipynb"


def cell_with(notebook, marker: str) -> str:
    return next(
        cell.source for cell in notebook.cells
        if cell.cell_type == "code" and marker in cell.source
    )


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    recovery = {
        version: nbformat.read(path, as_version=4)
        for version, path in RECOVERY_NOTEBOOKS.items()
    }

    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            cell.source = cell.source.replace("glee_v27_", "glee_v31_")
            cell.source = cell.source.replace("GLEE_V27_", "GLEE_V31_")

    notebook.cells[0].source = """# GLEE Competition agent V31 — contextual 60 games per family

V31 is a deterministic, no-LLM portfolio built from the role-level evidence in
V23–V27. It retains the strongest observed branch in each family and changes
only the branches that reversed in V27:

- bargaining keeps V27 Alice and uses delay-aware agreement recovery for Bob;
- negotiation keeps V27 seller and rolls the buyer back to the exact V23 rule;
- persuasion keeps V27 buyer and text seller while using Bayes-bounded,
  response-gated pooling for the binary seller.

The live controller targets 60 authoritative completions in each of bargaining,
negotiation, and persuasion (180 total at most). It admits and drains one queue
assignment at a time. Stop-losses, trailing drawdown, overshoot detection,
strict action validation, and append-only evidence remain active, so a losing
family can stop before 60. `RUN_LIVE` defaults to `False`. Offline tests verify
contracts and safety invariants; they do not prove live rating superiority.
"""

    live_index = next(
        i for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "markdown" and "Controlled live runner" in cell.source
    )

    additions = []
    specs = (
        (28, "V28_BUYER_ARM", "def run_v28_tests", "Negotiation buyer rollback"),
        (29, "V29_BOB_ARM", "def run_v29_tests", "Delay-aware Bob recovery"),
        (30, "V30_BINARY_SELLER_ARM", "def run_v30_tests", "Bayes-bounded binary seller"),
    )
    for version, policy_marker, test_marker, title in specs:
        additions.extend([
            nbformat.v4.new_markdown_cell(f"## V31 component — {title}"),
            nbformat.v4.new_code_cell(cell_with(recovery[version], policy_marker)),
            nbformat.v4.new_code_cell(cell_with(recovery[version], test_marker)),
        ])

    additions.extend([
        nbformat.v4.new_markdown_cell("## V31 combined portfolio tests"),
        nbformat.v4.new_code_cell(r'''
def run_v31_portfolio_tests():
    assert STRATEGIES["bargaining"] is v29_bargaining_strategy
    assert STRATEGIES["negotiation"] is v28_negotiation_strategy
    assert STRATEGIES["persuasion"] is v30_persuasion_strategy

    # All three dispatch paths must remain valid after the component overrides.
    bargaining = base_game("bargaining", "offer", {
        "current_player": "player_2", "money_to_divide": 100.0,
        "delta_1": 0.92, "delta_2": 0.95, "complete_information": True,
        "round": 2, "max_rounds": 8, "horizon_known": True,
        "history": [], "messages_allowed": False,
    }, "player_2", "v31-bargaining")
    validate_action(bargaining, strategy(bargaining))

    negotiation = base_game("negotiation", "offer", {
        "current_player": "player_1", "player_1_role": "buyer",
        "player_2_role": "seller", "player_1_value": 80.0,
        "player_2_value": 40.0, "complete_information": True,
        "round": 2, "max_rounds": 8, "horizon_known": True,
        "history": [], "messages_allowed": False,
    }, "player_1", "v31-negotiation")
    validate_action(negotiation, strategy(negotiation))

    persuasion = base_game("persuasion", "seller_recommendation", {
        "current_player": "player_1", "player_1_role": "seller",
        "player_2_role": "buyer", "product_price": 100.0,
        "p": 0.5, "v": 180.0, "u": 20.0, "round": 3,
        "total_rounds": 10, "current_quality": "low", "history": [],
    }, "player_1", "v31-persuasion")
    validate_action(persuasion, strategy(persuasion))

    assert not ACTION_FALLBACK_LOG
    assert not TELEMETRY_LOG
    print("All V31 contextual portfolio, safety, and contract tests passed.")


run_v31_portfolio_tests()
'''),
    ])
    notebook.cells[live_index:live_index] = additions

    live_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and "TARGET_COMPLETIONS = {" in cell.source
    )
    replacements = {
        'LIVE_BUILD_ID = "v27-evidence-guided-100-each-2026-08-29"':
            'LIVE_BUILD_ID = "v31-contextual-60-each-2026-08-29"',
        '"bargaining": 100,\n    "negotiation": 100,\n    "persuasion": 100,':
            '"bargaining": 60,\n    "negotiation": 60,\n    "persuasion": 60,',
        '"bargaining": 25.0,\n    "negotiation": 35.0,\n    "persuasion": 25.0,':
            '"bargaining": 18.0,\n    "negotiation": 28.0,\n    "persuasion": 18.0,',
        "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 130":
            "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 85",
        '"bargaining": 20.0, "negotiation": 25.0, "persuasion": 20.0':
            '"bargaining": 14.0, "negotiation": 20.0, "persuasion": 14.0',
        "MIN_GAMES_BEFORE_TRAILING_STOP = 20":
            "MIN_GAMES_BEFORE_TRAILING_STOP = 12",
        'assert TARGET_COMPLETIONS == {\n    "bargaining": 100, "negotiation": 100, "persuasion": 100\n}':
            'assert TARGET_COMPLETIONS == {\n    "bargaining": 60, "negotiation": 60, "persuasion": 60\n}',
        "assert MAX_QUEUE_ATTEMPTS_PER_FAMILY >= 100":
            "assert MAX_QUEUE_ATTEMPTS_PER_FAMILY >= 60",
        'print("V27 live configuration verified: 100 targets per family.")':
            'print("V31 live configuration verified: 60 targets per family.")',
    }
    for old, new in replacements.items():
        if old not in live_cell.source:
            raise RuntimeError(f"Expected live-runner text not found: {old!r}")
        live_cell.source = live_cell.source.replace(old, new)

    # Component tests already self-mark V28–V30 IDs. Mark combined V31 tests too.
    inspect_index = next(
        i for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "markdown" and "Inspect exact evidence" in cell.source
    )
    notebook.cells.insert(inspect_index, nbformat.v4.new_code_cell(r'''
for _game_id, _assignment in POLICY_ASSIGNMENTS.items():
    if str(_game_id).startswith(("v28-", "v29-", "v30-", "v31-")):
        _assignment["synthetic"] = True
print("V31 and component-test assignments isolated from live evidence.")
'''))

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
