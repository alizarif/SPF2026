FIGURE REPLICATION

Run from the project directory after scripts/build_data_cache.py:
  MPLCONFIGDIR=/tmp/spf_matplotlib python3 replication_2026-10-31/scripts/replicate_figures.py

All statistical figures are recomputed from supplied datasets using a documented Python port. Existing plot PDFs/images are read only for validation. Figure 1 is an explicitly labeled documentary screenshot reuse.

Deliverables: eleven page PDFs and PNGs for eight unique figures; combined PDFs for Figures2,3,5; numerical CSVs; detailed audit in replication_2026-10-31/figures_results.json. All eleven pages visually reviewed; label/legend overlap repaired.

Validation:
Figure1: original acknowledgments screenshot, documentary reuse.
Figure2: exact current participant counts/shares exported, but available metadata differ from published composition. Example: current average unknown gender share1.36%, original polygon area2.82%. Public-appearance category sets differ. Gaussian smoothing approximates ggstream. Partial replication, not exact.
Figure3: all16 AI/human curves match original vector paths and labeled ordinate scales to PDF coordinate rounding. All32200 baseline medians independently rebuilt from individual long data exactly match cache; clipped forecast errors differ only by4.55e-13 floating precision.
Figure4: independently recovered raw NOWCAST calculation, including No Name Provided. Restrict to>=10validobservations BEFORE quarterly demeaning. All61nonzero bars across80bins match original image heights within0.55pixels; RGDPmean11.481789,NGDPmean-0.819080. Actual plotted sample121, not caption194 (pre-restriction count). Four means, ranges, SDs and alternative horizon/order checks exported. Generated values never taken from image pixels.
Figure5: all64KDE curves compared at512gridpoints each to original vector shapes. Correct Rnrd0 constant-sample fallback implemented. Direct Gaussian evaluation differs slightly from R FFT density: worstpeak-relative error1.5943%, worstRMS0.1090%. Error samples and bandwidths exported.
Figure6: all8curves match original vector paths and labeled ordinate scales. The final PDF uses the OOS run for ALL2023–2024quarters, including2023overlap withbaseline. Rebuilt medians/errors for the64plottedobservations equal cache exactly.
FigureA.1: both100-quarter count paths match. Original AIcounts come from older multivariable_SPF6.xlsx (5188rows afterNoNameProvided exclusion), not later5308-row baseline.
FigureA.2: current participation metadata restricted to original193names. Original vector contains5232tile records; metadata5236. Both5208unique membershiptiles. 189of193original per-row membershippatterns match metadata; four patterns differ. Partial historical replication with tie-order/gradient differences.

Separate OOS preprocessing caveat: oos_error_reconciliation.json/csv and scripts/check_oos_forecast_errors.py show current3SD rule differs from saved prepared errors outsideFigure6. Most differences occur id4; these do not affect the replicated Figure6 one-quarter series. Published historical prepared-data results should not be described as completely recovered by current raw preprocessing.
