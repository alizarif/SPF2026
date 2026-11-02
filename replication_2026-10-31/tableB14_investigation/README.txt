TABLE B.14 INVESTIGATION

Defensible caption-accurate current-data results verified; original published pipeline only partly recovered

Final PDF-ready table: verified_table.json
Numerical results: verified_results.json / .csv
Quarter-level winners, source forecasts, actuals and errors: verified_quarter_results.json / .csv
Raw reconciliation: raw_validation.json
Historical reconstruction: historical_code_results.json, historical_quarter_results.json, historical_fit.json
Source hashes: source_provenance.json
Rebuild: python3 replication_2026-10-31/tableB14_investigation/investigate_table_b14.py
Document evidence: python3 replication_2026-10-31/tableB14_investigation/write_evidence.py

F1. The published caption defines a per-quarter minimum individual absolute error in BOTH surveys. The archived R best-OOS function instead selects one AI name across time and compares it with HUMAN MEDIANS.
Evidence: Simulating_SPF_processing/functions/tab_forecast_accuracy_best_outofsample.R:20-47, Simulating_SPF_processing/functions/tab_forecast_accuracy_best_outofsample.R:62-89, replication_2026-10-31/originals/page_065.txt
Status: direct source contradiction

F2. The archived function reports MAEs for data_ts2, but computes p-values using data_ts. Its statistic is difference in signed mean errors, not difference in MAEs. Thus the test uses median survey forecasts rather than the selected best forecasts reported in the table.
Evidence: Simulating_SPF_processing/functions/tab_forecast_accuracy_best_outofsample.R:93-126, historical_code_results.json
Status: direct code evidence

F3. The best-OOS file and ordinary OOS file define the same function name, tab_forecast_accuracy_outofsample. Alphabetical sourcing in the driver loads the ordinary function later, and the driver has no separate best-OOS call. A fresh current driver does not generate the archived B.14 output.
Evidence: Simulating_SPF_processing/tables_figures_all.R:1-4, Simulating_SPF_processing/tables_figures_all.R:104-107, Simulating_SPF_processing/functions/tab_forecast_accuracy_best_outofsample.R:2, Simulating_SPF_processing/functions/tab_forecast_accuracy_outofsample.R:1
Status: direct code evidence

F4. Current preparation branches on the literal substring outofsample. The old workbook matches it (2024-only sample, horizons 0/1/2); the currently selected _oos.xlsx filename does not (includes 2023 and horizons 0/1/4). The old filename also skips local construction of SPFmicrodata_long even though it is subsequently referenced. These source versions are not a self-contained reproduction of the old table.
Evidence: Simulating_SPF_processing/functions/prepare_data.R:21-26, Simulating_SPF_processing/functions/prepare_data.R:73-76, Simulating_SPF_processing/functions/prepare_data.R:437-499, Simulating_SPF_processing/tables_figures_all.R:34-35
Status: direct code evidence

F5. The historical AI workbook has 492 raw rows, 260 in 2024 (65 per quarter). The current workbook has 1574 raw rows and 1561 after supplied cleaning, with 798 named rows in 2024 (199,199,199,201). Neither raw workbook has duplicate Name-quarter rows. The final calculation uses the current driver-selected workbook and reconstructs its GDP-price scale and named-row rules.
Evidence: raw_validation.json
Status: raw-file verified

F6. Archived h2 plot paths independently stop at origin 2024Q1 (target 2024Q3) for CPI, Core CPI, PCE and Core PCE. Other variables stop at origin 2024Q2 (target 2024Q4). This supports an older variable-specific availability cutoff; it was not chosen by minimizing table discrepancies.
Evidence: archived_figure_cutoff_evidence.json
Status: direct vector-path evidence, historical sample inference

F7. Using the old AI workbook, one best name across time, and the archived-figure-supported cutoff recovers 63/66 published AI MAEs within half a displayed unit. The three remaining AI discrepancies are all AAA bond yield. Raw human medians recover 62/66 human MAEs. Applying current median clipping also recovers 62/66 but changes which four miss, so the current clipping code cannot explain all historical human entries consistently.
Evidence: historical_fit.json, historical_code_results.json
Status: computed provenance evidence; complete original pipeline unresolved

F8. A selected name may have missing forecasts. For example, NGDP h1 selects Sacha Gelfer, whose mean uses two forecasts, while the source path keeps three human-median quarters. This explains published AI MAEs below the per-quarter-minimum average over all eligible quarters; it is an unequal-sample, across-time selection effect.
Evidence: historical_quarter_results.json, historical_code_results.json
Status: raw-source and code verified

F9. The historical median signed-error test is compatible with 64/66 published p-values after allowing two-decimal display rounding and three standard errors of a 10000-draw Monte Carlo estimator. Remaining failures are Housing h1 and AAA bond h2. This supports the wrong-test-input provenance but does not prove an exact historical seed or data snapshot.
Evidence: historical_p_provenance.json
Status: statistical diagnostic, not exact reproduction

F10. The verified table implements the caption on current supplied data: forecast origins 2024Q1-Q4; horizons 0,1,2; target date origin+h; minimum individual absolute error per survey and quarter; matched quarterly samples; exact two-sided sign-flip test on MAE differences. Future target quarters in 2025 are used when supplied actuals exist. Only CPROF has missing 2025Q1/Q2 actuals, giving one N=3 and one N=2 test; the other 64 tests have N=4.
Evidence: verified_table.json, verified_results.json, verified_quarter_results.json, raw_validation.json
Status: independently raw-validated recalculation; explicit forecast-origin sample interpretation

F11. Exact tests enumerate all 2^N assignments, eliminating Monte Carlo noise. With at most four paired quarters, the minimum two-sided exact p-value here is 0.125; none meets the paper significance-star thresholds. This is a method-faithful exact version of a paired randomization test of MAE differences, not recovery of the paper seed.
Evidence: verified_results.json
Status: exact finite enumeration

F12. Final display uses decimal arithmetic on source forecast and actual values for minima and means, then ROUND_HALF_EVEN at two decimals. Float estimates are retained separately. UNEMP h0 AI is exactly 0.075 and displays 0.08; p=0.125 displays 0.12. Differences from a published Monte Carlo p-value of 0.13 are not merely formatting differences.
Evidence: rounding_boundaries.json, verified_results.json
Status: deterministic arithmetic and display policy

The verified table is a new, coherent calculation of the stated statistic using the current source inputs. It must not be described as a full numerical recovery of the published historical run. The supplied actuals are used as supplied; this local investigation does not replace them with newly downloaded vintages. No original research file or PDF builder was modified.
