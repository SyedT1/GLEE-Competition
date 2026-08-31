# GLEE competition paper package

This directory is a self-contained LaTeX and audit package for the IAB 2026
Competition Paper Track. It includes the exact executed V33 notebook and
evidence under `artifacts/v33/`.

## Build the paper

```text
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Equivalent manual sequence:

```text
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The main paper comprises the sections before the bibliography. Policy details,
reproducibility, statistics, and the NeurIPS checklist follow as supplemental
pages. Verify the current four-page main-text rule against the compiled PDF.

## Reproduce tables and figures

From this directory:

```text
python -m pip install -r requirements-analysis.txt
python analysis/analyze_v33_transcripts.py
```

The analysis uses `data/all_game_transcripts_v33.txt` and
`data/v33_rating_outcomes.csv`, then rewrites derived CSVs,
`tables/v33_statistical_analysis.tex`, `figures/v33_sequential_ratings.*`, and
`data/v33_analysis_summary.json`. It can run after extracting the ZIP into a
directory of any name.

`data/leaderboard_snapshot_2026-08-31.csv` separately records the
author-supplied rank-95 dashboard snapshot (overall rating 1674.3); its player
name is anonymized for double-blind review.

## Artifact inventory

- `artifacts/v33/*.ipynb`: exact executed V33 source.
- `artifacts/v33/glee_v33_session_report.json`: complete exported report.
- `artifacts/v33/glee_v33_evidence.jsonl`: ordered append-only evidence with
  only the submitting agent UUID/name replaced by anonymous tokens.
- `artifacts/v33/glee_v33_policy_state.json`: saved policy statistics.
- `artifacts/v33/glee_v33_rating_outcomes.csv`: canonical rating rows.
- `artifacts/v33/ARTIFACT_MANIFEST.sha256`: immutable checksums.
- `PACKAGE_MANIFEST.sha256`: checksums for every bundled source/data file except
  the manifest itself and disposable LaTeX build products.
- `analysis/analyze_v33_transcripts.py`: paper audit generator.
- `requirements-analysis.txt`: pinned audit dependency.
- `requirements-live.txt`: pinned SDK used by the executed notebook.

The bundled files and SHA-256 manifests define the anonymous submission
snapshot. A public repository URL and the corresponding commit are withheld
during double-blind review and can be released afterward.

## Important scope

The V33 data are a fixed-order, post-selection, adaptively stopped competition
trace. They do not identify causal effects of the role branches, support dynamic
receiver-obedience claims, or permit exact leaderboard replay. The transcript
export covers 220/248 rated assignments and has no game IDs, so it is analyzed
separately from rating changes.

## Submission checks

- Confirm the Competition Paper Track and its current double-blind policy.
- Keep review metadata anonymous; enter author metadata and Agent ID only in the
  fields requested by OpenReview.
- Compile and visually inspect every page, reference, table, and URL.
- Confirm US Letter, embedded fonts, main-text page limit, and checklist order.
- Upload the rebuilt ZIP, not an earlier package with the same name.
