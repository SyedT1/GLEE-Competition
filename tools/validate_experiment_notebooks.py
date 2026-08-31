"""Execute every generated experiment notebook with live play disabled."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.argv[1:]:
        files = [ROOT / "notebooks" / name for name in sys.argv[1:]]
    else:
        files = sorted((ROOT / "notebooks").glob("GLEE_Competition_experiment_*.ipynb"))
        files.append(ROOT / "notebooks" / "19_heuristic_challenger_robust_trend_projection_precision_bounded_pooling.ipynb")
        files.append(ROOT / "notebooks" / "20_live_three_family_robust_projection_credibility_safe_pooling.ipynb")
        files.append(ROOT / "notebooks" / "21_controlled_microbatches_family_stop_loss_authoritative_accounting.ipynb")
        files.append(ROOT / "notebooks" / "22_evidence_selected_portfolio_bargaining_rollback_family_stop_loss.ipynb")
        files.append(ROOT / "notebooks" / "23_adaptive_defender_peak_drawdown_reservation_protection.ipynb")
        if len(files) != 10:
            raise RuntimeError("expected five experiment notebooks plus V19 through V23")
    if not files or not all(path.exists() for path in files):
        raise RuntimeError("one or more requested notebooks do not exist")
    for path in files:
        print(f"RUN  {path.name}", flush=True)
        version = re.search(r"(v\d+)", path.name).group(1)
        state_path = ROOT / f".validation_{version}_state.json"
        evidence_path = ROOT / f".validation_{version}_evidence.jsonl"
        if state_path.exists() or evidence_path.exists():
            raise RuntimeError(f"refusing to overwrite existing validation artifacts for {version}")
        state_key = f"GLEE_{version.upper()}_STATE_PATH"
        evidence_key = f"GLEE_{version.upper()}_EVIDENCE_PATH"
        old_state, old_evidence = os.environ.get(state_key), os.environ.get(evidence_key)
        os.environ[state_key] = str(state_path)
        os.environ[evidence_key] = str(evidence_path)
        notebook = nbformat.read(path, as_version=4)
        namespace = {"display": lambda *items, **kwargs: None}
        try:
            for index, cell in enumerate(notebook.cells):
                if cell.cell_type != "code" or "%pip" in cell.source:
                    continue
                source = cell.source.replace("from glee_sdk import GleeClient", "")
                # Validation never contacts the competition, even for notebooks
                # intentionally configured to play when a user executes them.
                source = source.replace("RUN_LIVE = True", "RUN_LIVE = False")
                try:
                    compiled = compile(source, f"{path.name}:cell-{index}", "exec")
                    exec(compiled, namespace)
                except Exception as exc:
                    raise RuntimeError(f"{path.name} failed in code cell {index}") from exc
        finally:
            for artifact in (state_path, evidence_path):
                artifact.unlink(missing_ok=True)
            if old_state is None:
                os.environ.pop(state_key, None)
            else:
                os.environ[state_key] = old_state
            if old_evidence is None:
                os.environ.pop(evidence_key, None)
            else:
                os.environ[evidence_key] = old_evidence
        print(f"PASS {path.name}", flush=True)


if __name__ == "__main__":
    main()
