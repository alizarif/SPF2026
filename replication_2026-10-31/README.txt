PREDICTABLE FORECASTERS — REPLICATION AUDIT
31 October 2026

START HERE
output/pdf/original_vs_replicated.pdf
  60-page report: comparison summary, methods, then each original screenshot
  immediately followed by the independently rebuilt result. All 8 numbered
  figures and 15 numbered tables are included, including continuation pages.

../outputs/replication/replication_comparison.xlsx
  Searchable 23-item summary and 2,305 cell comparisons, including significance
  stars. Original values, recomputed values, differences and tolerances are
  available. All comparison formulas have verified cached results.

replication_comparison.json / .csv
cell_comparison.json / .csv
  Machine-readable summary and detailed audit. Stars are encoded as counts
  (0, 1, 2 or 3), not as p-values. Table cells and figure-series comparisons are
  separate checks; no single aggregate percentage measures scientific validity.

CONCLUSION
Replication is partial. Many point estimates reproduce, but current files mix
multiple data versions, some printed descriptions differ from the computations,
and several results remain unresolved. Table 11's regression estimates are not
reproduced. Table B.14 and some significance tests remain only partly matched.
The report explicitly preserves every mismatch; target numbers never replace
newly calculated results.

WHAT WAS RUN
The supplied R calculations were ported to Python because R was unavailable.
Missing scripts were reconstructed from the paper and supplied numerical data.
This is not a claim that the original R project executes end to end unchanged.
Existing AI responses were analyzed; no paid model calls or new forecasts were
requested. Raw numeric AI forecasts were reconciled to the saved R data objects.
Baseline medians and clipped errors were independently rebuilt and verified.

The OOS archive includes 2023-2024, although B.13 says 2024. Its last column is
horizon 4, although labeled 2. Its saved horizon-4 errors are unclipped where the
current prepare_data.R rule would clip them. The table's saved-data calculation
matches, but that raw preprocessing pipeline is not fully reproduced. See
 oos_error_reconciliation.json and accompanying CSVs.

KEY METHOD QUALIFICATIONS
- Table 3 uses repeated forecaster-panel realizations, N=5,308; its ACF depends
  on stored row order, not on a single chronological quarterly series.
- Tables 4 and 6 include panel-size weights through duplicate joins.
- The supplied randomization code uses signed errors, despite MAE wording.
- Table 6 compares best AI personas with human medians, not best human IDs.
- Table 7 matches only with human horizons 0/3 versus AI horizons 1/4.
- Table 8 ratios match, but the supplied significance procedure swaps AI/Human
  within ablations rather than baseline/ablation MAEs; many star patterns differ.
- Table 9 event dates and deadline offsets are documentary manuscript inputs;
  event Z-scores are independently calculated with the reported caveats.
- Table 10 includes duplicate 2023 quarters: 108 observations, 104 unique dates.
- Table 12 uses all 5,388 raw responses, including placeholder-name rows.
- Table D.15 was reconstructed; DM tests use absolute loss and test horizon 1
  at all three forecast horizons. All displayed values and stars match.
- Figure 4's recovered histograms contain 121 retained forecasters, not the
  caption's 194. Figures 2 and A.2 reflect metadata-version differences.
- Figure 1 and Tables 1/2 are documentary source reproductions, not estimates.

REPRODUCIBILITY
Scripts are in scripts/. Run from this directory or its parent with Python3.11+
and dependencies in requirements.txt. Numerical caches are included, so the
statistical calculations can be rerun without decoding the large original R
workspaces. Keep this folder beside Simulating_SPF_processing and latest draft;
source paths currently reference that supplied directory structure and the PDF
at /Users/alizarif/Downloads/predictable_forecasters.pdf.

  python3 scripts/run_replication.py

To rebuild numerical caches from the supplied R objects and raw workbooks first:

  python3 scripts/run_replication.py --rebuild-cache

The cache reader additionally requires pyreadr and narwhals. It can use an
installed reader or PYREADR_EXTRA_PATH; no reader binary is bundled here.

To also rebuild the XLSX, pass --with-workbook. Its builder uses the installed
Codex @oai/artifact-tool runtime, with a node_modules symlink to the bundled
runtime libraries. See scripts/build_comparison_workbook.mjs. The output is
../outputs/replication/replication_comparison.xlsx.

The source-PDF crop inventory is already included in originals/. If the source
PDF changes, regenerate it using scripts/inventory_final_pdf.py before rerunning
calculations. Do not use a different PDF without updating its target inventory.

CHECKS AND CONTENTS
- data_cache/: numerical inputs and detailed provenance/source reconciliation.
- reproduced/: regenerated figures, tables, series, regression inputs and outputs.
- originals/: high-resolution original screenshots, source text and source map.
- scripts/: data extraction, computations, comparisons and deliverable builders.
- *_results.json: detailed figure/table method and validation records.
- report_page_index.json: maps every source page to its paired report pages.
- source_integrity_check.json: all 998 pre-existing project files verified
  byte-for-byte unchanged against the inventory taken before this work.
- final_validation.json: final PDF coverage, numeric-file and artifact checks.

RANDOMIZATION
10,000 simulations, seed 20261031. The original seed is not supplied. Exact
rounded p-value agreement and Monte Carlo compatibility are shown separately.
Compatibility uses max(0.015, 0.005 + 3*sqrt(2*p*(1-p)/10000)). This diagnostic
allowance is not evidence of identical simulations. Invalid simulated statistics
are omitted, matching R's na.rm=TRUE. Star comparisons remain exact and separate.
