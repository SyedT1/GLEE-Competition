"""Build fully heuristic V25 bargaining + frozen V23 negotiation notebook."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "notebooks"
    / "Glee_competition_24"
    / "GLEE_Competition_agent_v24_bp_repair.ipynb"
)
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v25_bargaining_v23_negotiation.ipynb"


def main() -> None:
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V24", "V25").replace("v24", "v25")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V25 — heuristic bargaining + V23 negotiation

V25 contains no language model. Bargaining uses the deterministic
V24 role-aware policy: the surplus-protecting Alice repair and the established
Bob policy. Negotiation uses the exact successful V23 defensive decision code.
Persuasion is excluded from live matchmaking.

The runner targets 50 bargaining and 50 negotiation completions with concurrency
one and authoritative inspection after every assignment. Bargaining uses a
12-point baseline stop-loss and 10-point trailing drawdown; negotiation uses a
20-point baseline stop-loss and 15-point trailing drawdown. The API key is loaded
at runtime from `GLEE_API_KEY`, Kaggle Secrets, or a hidden prompt.
"""

    # Keep only the SDK dependency; no model packages or model downloads.
    notebook.cells[1].source = """# Competition SDK dependency.
%pip install -q -U glee-sdk
"""

    policy_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and "def v25_alice_bargaining_strategy" in cell.source
    )
    policy_cell.source += r'''

# Explicit deployment map: deterministic V24-derived bargaining and exact V23 negotiation.
STRATEGIES["bargaining"] = v25_role_aware_bargaining
STRATEGIES["negotiation"] = v25_negotiation_strategy
print("V25 portfolio: deterministic bargaining + exact V23 negotiation decisions.")
'''

    live_cell = next(
        cell for cell in notebook.cells
        if cell.cell_type == "code" and 'LIVE_BUILD_ID = "v25-bargaining-persuasion-repair-2026-08-28"' in cell.source
    )
    live_cell.source = live_cell.source.replace(
        'LIVE_BUILD_ID = "v25-bargaining-persuasion-repair-2026-08-28"',
        'LIVE_BUILD_ID = "v25-heuristic-bargaining-v23-negotiation-2026-08-28"',
    )
    live_cell.source = live_cell.source.replace(
        'TARGET_COMPLETIONS = {\n    "bargaining": 50,\n    "persuasion": 50,\n}',
        'TARGET_COMPLETIONS = {\n    "bargaining": 50,\n    "negotiation": 50,\n}',
    )
    live_cell.source = live_cell.source.replace(
        'FAMILY_STOP_LOSS = {\n    "bargaining": 12.0,\n    "persuasion": 12.0,\n}',
        'FAMILY_STOP_LOSS = {\n    "bargaining": 12.0,\n    "negotiation": 20.0,\n}',
    )
    live_cell.source = live_cell.source.replace(
        "FAMILY_MAX_DRAWDOWN = 10.0\nMIN_GAMES_BEFORE_TRAILING_STOP = 5",
        'FAMILY_MAX_DRAWDOWN = {"bargaining": 10.0, "negotiation": 15.0}\n'
        "MIN_GAMES_BEFORE_TRAILING_STOP = 5",
    )
    live_cell.source = live_cell.source.replace(
        "peak_drawdown >= FAMILY_MAX_DRAWDOWN:",
        "peak_drawdown >= FAMILY_MAX_DRAWDOWN[family]:",
    )

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
