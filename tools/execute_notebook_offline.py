"""Execute a notebook's Python cells without Jupyter or live matchmaking."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import nbformat


class OfflineGleeClient:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Live GleeClient construction is disabled offline")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: execute_notebook_offline.py NOTEBOOK.ipynb")

    notebook_path = Path(sys.argv[1]).resolve()
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)

    sdk = types.ModuleType("glee_sdk")
    sdk.GleeClient = OfflineGleeClient
    sys.modules["glee_sdk"] = sdk

    namespace = {
        "__name__": "__notebook__",
        "display": lambda *items, **kwargs: None,
    }
    work_dir = Path.cwd() / "tmp"
    work_dir.mkdir(parents=True, exist_ok=True)
    os.environ["GLEE_V31_WORK_DIR"] = str(work_dir)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        source = "\n".join(
            line for line in cell.source.splitlines()
            if not line.lstrip().startswith(("%", "!"))
        )
        if not source.strip():
            continue
        try:
            exec(compile(source, f"{notebook_path.name}:cell-{index}", "exec"), namespace)
        except Exception as exc:
            raise RuntimeError(
                f"offline execution failed in cell {index}: {exc}"
            ) from exc

    print(f"Offline execution passed: {notebook_path.name}")


if __name__ == "__main__":
    main()
