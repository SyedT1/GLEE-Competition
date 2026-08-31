# GLEE competition paper

Submission-ready LaTeX scaffold for the IAB Competition Paper Track at NeurIPS 2026.

## Build

From this directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Alternatively:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The official `neurips_2026.sty` and `checklist.tex` are included from the NeurIPS 2026 author kit. Do not edit the style file.

## Final manual checks before submission

- Verify the author name, Center for Computational and Data Sciences Lab affiliation, email, Agent ID, and agent name.
- Confirm from the compiled PDF that the approximately 1,860-word main body is at most four pages. References and the checklist may use additional pages; the supplementary reproducibility file is not compiled into the paper.
- Confirm the latest single-blind instructions on OpenReview before submission.
- Ensure the PDF uses US Letter, contains embedded fonts, and includes the checklist after references and optional appendices.
- Provide the GLEE Agent ID in the OpenReview submission form.
- Choose archival proceedings or workshop-only presentation in the OpenReview form.
- Verify every citation and URL manually; authors remain responsible for the paper's content.

The manuscript treats all V3--V33 batches as sequential and descriptive, uses
only verified V33 results in its principal table, and contains all 16 official
checklist answers with the instruction block removed.

Deadline: September 5, 2026, midnight Anywhere on Earth.

## Files

- `main.tex`: compilation entry point and section order.
- `metadata.tex`: author and agent metadata.
- `abstract.tex`: current one-paragraph abstract.
- `sections/`: four-page main-paper draft.
- `tables/results.tex`: compact verified V33 live-results table.
- `data/game_history.txt`: raw dashboard text copied after the V3 batch.
- `data/v3_batch_aggregate.csv`: aggregate outcomes and rating changes derived from that history.
- `data/v4_bargaining_games.csv`: the 25 reported V4 bargaining outcomes, roles, times, and rounded rating changes.
- `data/v4_bargaining_aggregate.csv`: overall and role-stratified V4 bargaining statistics.
- `data/v5_negotiation_visible_games.csv`: all 55 V5 negotiation rows supplied from the dashboard, in newest-to-oldest order.
- `data/v5_negotiation_aggregate.csv`: exact V5 before/after snapshot plus complete overall and role-stratified statistics.
- `data/v6_persuasion_games.csv`: all 35 V6 persuasion role outcomes and rounded rating changes.
- `data/v6_persuasion_aggregate.csv`: exact V6 persuasion snapshot plus complete role-stratified statistics.
- `data/v7_bargaining_games.csv`: all 40 V7 bargaining agreements, roles, times, and rounded rating changes.
- `data/v7_bargaining_aggregate.csv`: exact V7 before/after snapshot, terminal-reward count, and role-stratified statistics.
- `data/v8_negotiation_games.csv`: all 44 V8 negotiation roles, opponents, outcomes, times, and rounded rating changes.
- `data/v8_negotiation_aggregate.csv`: exact V8 snapshot plus role/outcome summaries and clean terminal instrumentation counts.
- `data/v10_negotiation_games.csv`: both supplied V10 buyer walkaways and rounded rating changes.
- `data/v10_negotiation_aggregate.csv`: exact V10 snapshot, overshoot, attribution, and instrumentation summary.
- `data/v11_negotiation_games.csv`: all 53 supplied V11 negotiation rows.
- `data/v11_negotiation_aggregate.csv`: exact V11 loss, role/outcome splits, overshoot, and instrumentation summary.
- `data/v23_live_rating_games.csv`: all 71 live V23 assignment-linked rating outcomes; the synthetic unit-test row is excluded.
- `data/v23_live_rating_aggregate.csv`: V23 family and role counts, signs, sums, and means.
- `data/v23_family_summaries.csv`: exact V23 snapshots, peaks, drawdowns, and stop reasons.
- `data/v24_live_rating_games.csv`: all 20 live V24 assignment-linked outcomes; the synthetic test row is excluded.
- `data/v24_live_rating_aggregate.csv`: V24 bargaining and persuasion role summaries.
- `data/v24_family_summaries.csv`: exact V24 snapshots, peaks, drawdowns, and stop reasons.
- `data/v25_live_rating_games.csv`: all 51 live V25 assignment-linked outcomes; the synthetic test row is excluded.
- `data/v25_live_rating_aggregate.csv`: V25 bargaining and negotiation role summaries.
- `data/v25_family_summaries.csv`: exact V25 snapshots, peaks, drawdowns, and stop reasons.
- `data/v26_live_rating_games.csv`: all 73 live V26 assignment-linked outcomes; the synthetic test row is excluded.
- `data/v26_live_rating_aggregate.csv`: V26 three-family role summaries.
- `data/v26_family_summaries.csv`: exact V26 snapshots, peaks, drawdowns, and stop reasons.
- `data/v27_live_rating_games.csv`: all 139 live V27 assignment-linked outcomes; the synthetic test row is excluded.
- `data/v27_live_rating_aggregate.csv`: V27 three-family role summaries.
- `data/v27_family_summaries.csv`: exact V27 snapshots, peaks, drawdowns, and stop reasons.
- `../notebooks/glee_competition_33/`: V33 notebook plus the exact session report, 248-row live rating extract (after excluding one synthetic row), policy state, and append-only evidence.
- `appendices/reproducibility.tex`: execution and hyperparameter details.
- `appendices/statistical_analysis.tex`: distributional, sequential, behavioral,
  configuration, and stop-sensitivity audit.
- `analysis/analyze_v33_transcripts.py`: reproducible parser and statistics/figure generator.
- `data/all_game_transcripts_v33.txt`: raw transcript export (220 recoverable games;
  28 rated assignments are absent from the export).
- `data/v33_rating_outcomes.csv`: 249-row V33 rating extract, including the one
  synthetic contract-test row that the analysis excludes.
- `data/v33_*.csv` and `data/v33_analysis_summary.json`: generated family, role,
  context, transcript, and stopping-sensitivity audit outputs.
- `figures/v33_sequential_ratings.pdf`: cumulative rating paths and stop boundaries.
- `references.bib`: verified core references.
- `checklist.tex`: mandatory official NeurIPS checklist; must be completed.
- `neurips_2026.sty`: unmodified official style.
- `SUBMISSION_CHECKLIST.md`: final packaging and policy checks.
