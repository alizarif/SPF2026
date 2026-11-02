rm(list=ls())
setwd(paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/functions"))
sapply(list.files(pattern="[.][rR]$",recursive = TRUE),source,.GlobalEnv)
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Figure settings
w = 6.5
h = 4.5

# Table settings
options(knitr.kable.NA = '') # Ignore NA in tables
gof_map <- modelsummary::gof_map
gof_map$omit[gof_map$clean %in% c("R2","F","AIC","BIC","Log.Lik.","RMSE")] = TRUE
options(modelsummary_format_numeric_latex = "plain")

# ------------------------------------------------------------------------------
# PREPARE DATA FILES

prepare_data(input_filename = "data/merged_results_spf_format_2026_fixed.xlsx",#"data/multivariable_SPF6.xlsx", 
             output_filename = "data/baseline_data.rda")

prepare_data(input_filename = "data/generic_forecaster_results_fixed.xlsx", #data/merged_file_multivariable_generic_cleaned.xlsx", 
             output_filename = "data/generic_forecaster_data.rda")

prepare_data(input_filename = "data/generic_forecaster_no_realtime_fixed.xlsx",#data/merged_file_multivariable_generic_norealtime_cleaned.xlsx", 
             output_filename = "data/generic_forecaster_no_realtime_data.rda")

prepare_data(input_filename = "data/merged_file_multivariable_recall_cleaned2.xlsx", 
             output_filename = "data/recall_data.rda")

prepare_data(input_filename = "data/generic_forecaster_no_data_fixed.xlsx", #"data/merged_file_generic_no_data_at_all_SPF6_multivar_cleaned.xlsx",
             output_filename = "data/generic_forecaster_no_data.rda")

prepare_data(input_filename = "data/merged_results_spf_format_oos.xlsx",# "data/merged_file_outofsample_2024_SPF6_cleaned.xlsx",
             output_filename = "data/outofsample_data.rda")

prepare_data(input_filename = "data/merged_file_llama_70b_cleaned.xlsx",
             output_filename = "data/llama70b.rda")

prepare_data(input_filename = "data/merged_file_deepseek_cleaned.xlsx",
             output_filename = "data/deepseek.rda")

prepare_data(input_filename = "data/merged_file_multi_N_runs_cleaned.xlsx",
             output_filename = "data/generic_N_forecaster_data.rda")

# ------------------------------------------------------------------------------
# TABLES AND FIGURES

# Load baseline data
load(file = "data/baseline_data.rda")

# Human AI legend
fig_human_ai_lgd()

# Figure: Number of forecasters over time
fig_num_forecasters_over_time()

# Figure: Forecaster survival in sample
fig_participation_over_time()

# Figure: Characteristics over time
fig_characteristics_over_time()

# SPF industry classifications
fig_SPF_industry_over_time()

# Figure: Plot time series of median of SPF vs AI
fig_ts_median()
fig_ts_median_wRealized() # with realized values

# Figure: Plot box plots SPF vs AI
#fig_boxplots()

# Figure: Density plots SPF vs AI
fig_densities()
#fig_densities_generic()

# Table: Descriptive statistics
tab_descriptive_stats()

# Table: Accuracy of AI vs SPF median forecasts 
#tab_accuracy_ai_against_spf()

# Table: Test distributions of AI vs SPF forecasts
tab_rand_test_moments()
#tab_rand_test_moments_generic()

# Table: Kolmogorov-Smirnov tests of distributions of AI vs SPF forecasts
#tab_ks_tests()

# Figure: Scatter plot of AI and SPF individual forecasts
#fig_scatter_ai_spf()

# Table: Regress AI vs SPF individual forecasts 
#tab_regress_ai_spf() 

# Figure: Plot time series of forecast errors of SPF and AI
fig_forecast_errors()

# Table: Forecast accuracy of AI and SPF median forecasts 
tab_forecast_accuracy()
tab_forecast_accuracy_best_forecaster()
tab_num_quarters_AI_more_accurate()

# Table: Out-of-sample forecast accuracy of AI and SPF median forecasts 
suppressWarnings(tab_forecast_accuracy_outofsample())
suppressWarnings(fig_forecast_errors_outofsample())

# Table: Regress characteristics on forecast errors and AI-Human differences
tab_regress_characteristics()

# Table: Generic forecaster with and without real-time data forecast accuracy (incl. recall)
tab_forecast_accuracy_generic()

# Table: Recall vs forecast accuracy 
#tab_forecast_accuracy_recall()

# Table: LLAMA forecast accuracy of AI and SPF median forecasts 
tab_forecast_accuracy(filename = 'tables/forecast_accuracy_llama', 
                      data_file="data/llama70b.rda")

# Table: Deepseek forecast accuracy of AI and SPF median forecasts 
tab_forecast_accuracy(filename = 'tables/forecast_accuracy_deepseek', 
                      data_file="data/deepseek.rda")

