# Predictable Forecasters: replication and verification

Code, analysis, and reproduced results for **“Simulating the Survey of Professional Forecasters”** by Anne Lundgaard Hansen, John J. Horton, Sophia Kazinnik, Daniela Puzzello, and Ali Zarifhonarvar. The reference is the supplied **June 2026 draft**, [predictable_forecasters.pdf](paper/predictable_forecasters.pdf).

This public research repository, [alizarif/SPF2026](https://github.com/alizarif/SPF2026), includes the underlying research inputs used by the packaged workflows, supplied research code, and replication outputs. Authorship and source attribution remain with the paper and original data providers; this packaging does not add a new software or data license.

The audit covers all **8 numbered figures and 15 numbered tables**, including appendices. Replication is **partial**: many estimates match, but supplied data versions, implemented methods, and printed descriptions do not always agree. Matching a printed value does not establish that its method is appropriate. The repository preserves discrepancies and distinguishes recovery of published results from new calculations using the stated definitions.

Existing AI responses were analyzed; no new model forecasts, paid API calls, or replacement macroeconomic data were requested. The original research calculations were ported from R to Python, with missing procedures reconstructed and identified as such. This is not a claim that the original R project runs unchanged from beginning to end.

## Start here

| Artifact | Purpose |
| --- | --- |
| [Verified tables-only PDF](replication_2026-10-31/output/pdf/tables_verified_results.pdf) | All 15 tables. Published entries are black; differing recalculations appear beside them in red brackets. Tables 11 and B.14 use the later verified methods described below. |
| [Verification findings](replication_2026-10-31/tables_review/verification_findings.txt) | Methods, limitations, rounding policy, and validation of the updated tables. Read alongside the clean PDF, which contains no explanatory notes. |
| [Full-paper comparison report](replication_2026-10-31/output/pdf/original_vs_replicated.pdf) | Earlier 60-page audit: each original figure/table image is followed by its reproduction, with a summary and method notes. It predates the later Table 11/B.14 investigations. |
| [Comparison workbook](outputs/replication/replication_comparison.xlsx) | Earlier 23-item summary and 2,305 cell comparisons. Its Table 11/B.14 entries retain the initial audit; use the investigation outputs for the updated results. |
| [Latest machine-readable tables](replication_2026-10-31/tables_review/table_data_verified.json) | Published and recalculated cells, display precision, significance markers, and comparison metadata. |

`replication_comparison.json/.csv`, `cell_comparison.json/.csv`, and `audit_summary.json` inside `replication_2026-10-31/` also describe the **earlier audit**, not a combined score for the updated tables.

The additional [tables_replicated.pdf](replication_2026-10-31/output/pdf/tables_replicated.pdf) is a 13-page user derivative retained for reference. The verification claims below apply to the canonical 15-page `tables_verified_results.pdf`, not automatically to that derivative.

## What the later investigations established

**Table 11.** All 32 published AI numeric cells and eight significance markers were recovered numerically. The matching calculation uses one-quarter-ahead AI forecasts, compares them with human nowcast medians, and treats the current human median as the “error” benchmark; it does not use the stated realized forecast error. It also retains duplicate-quarter observations, gaps, and placeholder-name responses. No original generating script was found, so this is numerical recovery, not documentary proof of the original implementation. The published human panel remains unresolved.

The updated Table 11 instead uses one consistent, declared specification for both surveys: nowcasts exactly one quarter apart, the prior-quarter historical value available in the current SPF survey, the prior human nowcast median, OLS with an intercept, and HC1 robust standard errors. Conflicting AI forecasts within a named person-quarter are averaged, an explicit choice with sensitivity results retained. All 16 regressions were independently checked. See [findings](replication_2026-10-31/table11_investigation/findings.txt), [full estimates](replication_2026-10-31/table11_investigation/verified_estimates.json), and [method evidence](replication_2026-10-31/table11_investigation/verified_evidence.json).

**Table B.14.** Archived code selects one AI name across time and compares it with human medians, while its test uses median signed errors. This differs from the caption's best individual forecast in each survey and quarter. Historical reconstruction recovers 63/66 AI MAEs and 62/66 human MAEs, but the complete published pipeline remains unresolved.

The updated B.14 uses current supplied data, 2024 forecast origins, horizons 0/1/2, each survey's minimum individual absolute error per quarter, matched samples, and exact paired sign-flip tests of MAE differences. There are only two to four usable quarters per comparison; the smallest exact two-sided p-value is 0.125. All 261 usable quarter-level comparisons and 66 tests were independently verified. See [investigation findings](replication_2026-10-31/tableB14_investigation/README.txt) and [full results](replication_2026-10-31/tableB14_investigation/verified_results.json).

These two updated tables are **verified recalculations under documented choices**, not claims that every published original has been recovered. Other important limitations include differing horizon labels in Table 7 and B.13, signed-error randomization tests accompanying MAE tables, source-version differences in some figures, and unresolved significance discrepancies. GDP values retain changes in base-year dollars across survey vintages. Consult the item-level evidence before interpreting a result.

## Repository structure

```text
reproduce.py                 Verification, updated tables, earlier audit, cache rebuild
paper/                       Reference manuscript PDF
Simulating_SPF_processing/   Required supplied source code and selected input files
latest draft/                Required manuscript/table/figure references
replication_2026-10-31/
  scripts/                   Python computations, comparisons, PDF/workbook builders
  data_cache/                Parquet inputs, source mappings, reconciliation evidence
  originals/                 Reference crops, captions, inventory, source map
  reproduced/                Rebuilt figures/tables and their numerical outputs
  table11_investigation/     Published AI recovery and consistent nowcast recalculation
  tableB14_investigation/    Historical diagnostics and stated-method recalculation
  tables_review/             Canonical table cells, independent checks, rounding audit
  output/pdf/                Review PDFs
outputs/replication/          Comparison workbook
```

The package preserves the input hierarchy and includes numerical caches, the six R archives used to rebuild them, their raw-workbook/CSV reconciliation inputs, and the selected sources needed by the investigations. The packaged `individual_forecasters.csv` is a documented two-column derivative containing only `Name` and `date_q`, as required by the figure calculation. The rounding audit uses two extracted `archived_generic_*.parquet` objects, with a [source manifest](replication_2026-10-31/data_cache/archived_generic_objects.json) and [extraction script](replication_2026-10-31/scripts/extract_archived_generic_objects.py); the original credential-bearing `generic_output.RData` archive is omitted. These included inputs support the packaged workflows; they do not establish that the original research project runs unchanged from every raw source.

## Reproduction

Use Python 3.11 or later and a separate environment. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r replication_2026-10-31/requirements.txt
```

Check the saved numerical results and the canonical PDF without rerunning the research estimates:

```sh
python reproduce.py --verify
```

Recompute the Table 11/B.14 investigations from their included source inputs, then build and check the updated tables:

```sh
python reproduce.py --tables
```

Rebuild the earlier full-paper audit using the included numerical caches:

```sh
python reproduce.py --legacy
```

Rebuild and validate the numerical caches from the included R archives and source reconciliation inputs:

```sh
python reproduce.py --rebuild-cache
```

Expected outputs are the updated investigation JSON/CSV/Parquet files and `replication_2026-10-31/output/pdf/tables_verified_results.pdf` for `--tables`; rebuilt figures/tables, comparison JSON/CSV files, and `original_vs_replicated.pdf` for `--legacy`; and refreshed `data_cache/` files and provenance checks for `--rebuild-cache`. The modes are mutually exclusive; no flag defaults to verification. Cache rebuilding extracts saved R objects and reconciles source inputs, rather than rerunning every original R transformation.

**Dependencies.** The full cache rebuild requires `pyreadr` and `narwhals`; the rounding audit reads the included Parquet extracts and does not require an R reader. Rebuilding the comparison XLSX additionally requires Node.js and Codex's `@oai/artifact-tool` runtime, which is not bundled. The saved XLSX is readable without it. Historical evidence files may retain original machine paths; use `reproduce.py` for the packaged workflows.

## Validation and interpretation

The latest PDF was checked against **1,709 numeric cells**, with all 15 pages visually reviewed. Independent calculations verified all Table 11 regressions and B.14 minima/tests. Source hashes and reconciliation files document the inputs; the original 998-file research tree was verified unchanged during the initial audit.

The earlier randomization calculations use 10,000 draws and seed `20261031`; the original seed is unknown. Exact printed agreement and Monte Carlo compatibility are separate diagnostics. Simulation variation is not a display-rounding error. The final table review contains 421 red numeric annotations and one red horizon-label annotation; no remaining change was demonstrated to be rounding alone. Detailed checks are in [final validation](replication_2026-10-31/tables_review/final_verified_tables_validation.json) and the adjoining audit files.

Before publication, all four packaged workflows completed under Python 3.11. The 31 comparable Parquet caches matched the reviewed originals exactly, and the rebuilt 15-page tables PDF and 60-page comparison report rendered identically to the reviewed versions. [Publication validation](PACKAGE_VALIDATION.json) records these checks; [the package manifest](PACKAGE_MANIFEST.json) records the current file hashes. The older manifest inside `replication_2026-10-31/` remains historical evidence.
