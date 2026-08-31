"""Create a uniquely named live build from the validated V19 heuristics."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "19_heuristic_challenger_robust_trend_projection_precision_bounded_pooling.ipynb"
OUTPUT = ROOT / "notebooks" / "20_live_three_family_robust_projection_credibility_safe_pooling.ipynb"


def main():
    notebook = copy.deepcopy(nbformat.read(SOURCE, as_version=4))
    for cell in notebook.cells:
        cell.source = cell.source.replace("V19", "V20").replace("v19", "v20")
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    notebook.cells[0].source = notebook.cells[0].source.replace(
        "three-family heuristic challenger",
        "live three-family heuristic build",
    )
    for cell in notebook.cells:
        if cell.cell_type == "code" and 'LIVE_FAMILIES = ("bargaining", "negotiation", "persuasion")' in cell.source:
            cell.source = cell.source.replace(
                'LIVE_FAMILIES = ("bargaining", "negotiation", "persuasion")',
                'LIVE_BUILD_ID = "v20-live-three-family-2026-08-28"\n'
                'print("Live build:", LIVE_BUILD_ID)\n'
                'LIVE_FAMILIES = ("bargaining", "negotiation", "persuasion")',
            )
            break
    else:
        raise RuntimeError("live runner cell not found")

    nbformat.validate(notebook)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
