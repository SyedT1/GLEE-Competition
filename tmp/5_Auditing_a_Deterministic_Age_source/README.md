# Camera-ready IAB 2026 paper

This is an editable camera-ready revision of the supplied review PDF,
`../5_Auditing_a_Deterministic_Age.pdf`. The original LaTeX source for that PDF
was unavailable; this project was reconstructed from the closest paper package
and the PDF text, then revised to add the author details and a three-panel
decision figure explaining Equations 1--3 in response to review.

## Compile

Open `main.tex` as the main document in Overleaf and use pdfLaTeX, or run:

```text
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The NeurIPS 2026 `neurips_2026.sty` file is included unmodified. The paper
uses the `dblblindworkshop,final` options and includes the completed
`checklist.tex`. Figure 1 is drawn with TikZ in `figures/decision_flow.tex`.
The appendix ratings figure uses PGFPlots and the three
`figures/ratings_*.dat` files derived from the ordered rating CSV. The older
Matplotlib PDF remains in the full source folder as an archived output.

The project compiles locally with Tectonic. The decision diagram remains beside
Section 3, the detailed method-lineage table is in Appendix B, and the main
text ends on page 4; references, appendices, and checklist follow. Inspect the
compiled PDF in Overleaf before submission, because its pdfLaTeX engine may
place floats differently from Tectonic.

## Evidence and scope

The full local folder contains the executed V33 notebook, evidence, development
notebooks, and hash manifests. The compact Overleaf ZIP contains the LaTeX
source, style file, bibliography, checklist, and figure needed to compile.
The repository did not contain the complete 1,704-game dashboard export or
`analysis/analyze_game_history.py`; the dashboard-history aggregates in the
paper cannot be regenerated from this folder alone.

The observed competition trace is post-selection and adaptively stopped. The
reported ratings do not identify causal effects of the policy branches.
