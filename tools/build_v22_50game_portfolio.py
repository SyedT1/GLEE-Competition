"""Build V22: V4 bargaining plus V21 negotiation/persuasion, 50 games each."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "GLEE_Competition_agent_v21_controlled_microbatches.ipynb"
OUTPUT = ROOT / "notebooks" / "GLEE_Competition_agent_v22_improved_50_each.ipynb"


def main():
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V21", "V22").replace("v21", "v22")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = """# GLEE Competition agent V22 — improved portfolio, 50 games per family

V22 applies the live V21 evidence family by family. The V21 bargaining challenger
is rejected after triggering its rating stop-loss in three games, so bargaining
returns to the live-tested V4 champion with cycle insurance. Negotiation and
persuasion retain the V21 heuristics that produced strong positive 20-game runs.

The controlled runner targets 50 authoritative completions in each family. It
enters one queue at a time, leaves after assignment, drains all assigned games,
and inspects rating, count, fallback, telemetry, and overshoot state before every
re-entry. Rating stop-losses can end a family before 50 games; overshoot, action
fallback, or telemetry failure aborts the complete session. No language model is
used.
"""

    # Replace the experimental bargaining core in the active strategy map with
    # the inherited, live-tested V4 implementation. Keep V22 negotiation and
    # persuasion unchanged from their successful V21 run.
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'STRATEGIES = {' in cell.source and 'v22_bargaining_strategy' in cell.source:
            cell.source += r'''

# Evidence-backed family portfolio after the V21 live run.
V22_REJECTED_BARGAINING_CHALLENGER = v22_bargaining_strategy
STRATEGIES["bargaining"] = bargaining_strategy       # exact V4 champion
STRATEGIES["negotiation"] = v22_negotiation_strategy
STRATEGIES["persuasion"] = v22_persuasion_strategy
print("V22 portfolio: V4 bargaining + V22 negotiation + V22 persuasion.")
'''
            break
    else:
        raise RuntimeError("V22 strategy cell not found")

    # V4 bargaining is expected to retain its v4_safe arm label while the two
    # V22 heuristic families use v22_heuristic.
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'all(item["arm"] == V22_ARM' in cell.source:
            cell.source = cell.source.replace(
                'all(item["arm"] == V22_ARM for game_id, item in POLICY_ASSIGNMENTS.items()',
                'all(item["arm"] in {V22_ARM, "v4_safe"} for game_id, item in POLICY_ASSIGNMENTS.items()',
            )
            cell.source += r'''

# Property-test identifiers must never enter live reward harvesting or telemetry.
for _game_id, _assignment in POLICY_ASSIGNMENTS.items():
    if str(_game_id).startswith("v22-"):
        _assignment["synthetic"] = True
print("V22 synthetic property assignments isolated from live evidence.")
'''
            break
    else:
        raise RuntimeError("V22 arm assertion not found")

    # Configure the larger experiment and make the build unmistakable in Kaggle.
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'LIVE_BUILD_ID = "v22-controlled-microbatches-2026-08-28"' in cell.source:
            cell.source = cell.source.replace(
                'LIVE_BUILD_ID = "v22-controlled-microbatches-2026-08-28"',
                'LIVE_BUILD_ID = "v22-improved-50-each-2026-08-28"',
            )
            cell.source = cell.source.replace('"bargaining": 20', '"bargaining": 50')
            cell.source = cell.source.replace('"negotiation": 20', '"negotiation": 50')
            cell.source = cell.source.replace('"persuasion": 20', '"persuasion": 50')
            cell.source = cell.source.replace(
                '"bargaining": 12.0,\n    "negotiation": 12.0,\n    "persuasion": 12.0,',
                '"bargaining": 20.0,\n    "negotiation": 20.0,\n    "persuasion": 20.0,',
            )
            cell.source = cell.source.replace(
                "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 30",
                "MAX_QUEUE_ATTEMPTS_PER_FAMILY = 70",
            )
            break
    else:
        raise RuntimeError("V22 live configuration cell not found")

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
