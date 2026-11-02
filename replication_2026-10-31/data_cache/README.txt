Numerical data cache for the final-paper replication

Build: python3 replication_2026-10-31/scripts/build_data_cache.py
Validate inputs: python3 replication_2026-10-31/scripts/validate_data_cache.py
Dependencies: pandas, numpy, pyarrow, openpyxl, pyreadr >=0.5.8, narwhals.
The current run uses temporary reader packages under /tmp/spf_read_data/py311.
Set PYREADR_EXTRA_PATH for another reader installation, or install those
dependencies in the Python environment. No source files or research API calls
are changed or executed. Optional --variants adds llama, deepseek or generic_n.

Primary cached panels

baseline, oos, generic, no_data, no_realtime, recall each have:
  *_wide.parquet: date_q, Name, numeric forecasts and available standardized
    characteristics. VAR_Ah is AI, VAR_Hh human consensus, VAR_Rh realized.
    h = 0/1/2/3/4 for current through four quarters ahead; A/B are annual.
  *_long.parquet: same numeric information in long form, without biographies,
    prompts or other long strings. type is AI/Human/Realized; id is a STRING.
    Name-quarter duplicates and missing forecast values are preserved.
  *_ts.parquet: original R aggregate series, including median, mean, quantiles,
    realized value, clipped median_ and forecast_error. These are not newly
    estimated series. Aggregating AI wide forecasts reproduces every saved
    cross-sectional median exactly for all six datasets.
  *_variables.csv, *_horizons.csv and related metadata preserve source mappings.

baseline_microdata.parquet and oos_microdata.parquet contain anonymous human
forecasts. They must not be matched to named AI forecasters. The supplied source
does not reveal that identity mapping. Human consensus comes from SPF_full_ts;
human mean and quantiles come from these microdata.

Additional sources

baseline_raw_forecasts.parquet preserves all 5388 rows from the updated fixed
workbook, including 80 No Name Provided records; the processed baseline has
5308 rows. Several final-paper analyses use the unfiltered version. There are
28 remaining duplicate Name-quarter records in the processed baseline. Use the
sample specified for the particular reproduction, not a universal deduplication.

old_baseline_raw_forecasts.parquet preserves the earlier multivariable_SPF6
workbook (5268 rows, 5188 after No Name Provided exclusion). Its 22 variables
omit BAA yields. old_baseline_participants.parquet contains its Name/date keys.

baseline_reasoning.parquet preserves all 5388 raw Reasoning Response strings.
The final Table 12 matches this unfiltered sample, including unnamed records.

human_native_core.parquet preserves native SPF columns 1 through 6 for CPI,
UNEMP, RGDP and TBILL, with source human ID and quarter keys. It contains 9033
rows from 1968Q4 through 2024Q4. VAR1 is the prior-quarter estimate at the survey
vintage, VAR2 is the current-quarter nowcast, VAR3 is one quarter ahead, and
VAR6 is four quarters ahead. This native numbering differs from cache id.

source_*.parquet files retain the supplied CSV column names and data. These
include macro outcomes, real-time inputs, SPF consensus, variable mappings,
post-2023 outcomes and the WSJ comparison.

Important scope and timing notes

Units are preserved. Real GDP and similar variables are levels or index values;
they have not been silently converted to growth rates. Inflation inputs are
already annualized percentage points.

The OOS archive includes 2023 and 2024. Restrict the evaluation to 2024 when
interpreting it as a holdout sample; retain 2023 when reproducing transition
plots or an original procedure that explicitly duplicates those observations.

The saved clipped median_ uses realized MEAN +/-3 sample standard deviations,
not the realized MEDIAN stated in the paper. The data include clipped baseline
values as well as recall values. *_clipped_medians.csv identifies every affected
point. Unclipped median is retained separately.

Realizations use a one-quarter shift of the real-time-input file, PGDP vintage
P24Q3, and the manually supplied post-2023 table. Annual realized outcomes are
missing. No current data are downloaded to revise these vintages.

The recall cache is a hybrid: 22 nowcast series match the older recall workbook;
BAA nowcasts match generic_forecaster_recall_fixed.xlsx (96 nonmissing values
over the 100-quarter sample). The current R driver does not fully express this
hybrid. This was verified against both workbooks rather than inferred by name.

Table 7's printed values are exactly reproduced only with human horizons 0/3
and AI horizons 1/4, despite the common h+1/h+4 labels. Quarters with zero SD
at either compared horizon are excluded. The inferred method and a consistent-
horizon diagnostic are saved by scripts/replicate_table7.py.

provenance.json records source hashes, schemas and median reconstruction checks.
raw_reconciliation.json records every raw-to-cache comparison and source hash.
All 161 AI forecast columns match the named workbooks for each full-information
or ablation variant, after the explicit original exclusions and OOS price-index
rescaling. The 22 old recall columns and the additional BAA series also match.
