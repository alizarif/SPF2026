
tab_forecast_accuracy_generic <- function(filename = "tables/forecast_accuracy_generic.txt") {
  
  id_select <- c("0","4")
  
  err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
  mae <- function(x) {mean(abs(x |> na.omit()), na.rm=TRUE)}
  
  # Baseline results
  accuracy_baseline <- data_ts |>
    dplyr::filter(id %in% id_select,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    #dplyr::mutate(forecast_error = 100*forecast_error,
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","id","forecast_error") |>
    tidyr::pivot_wider(names_from = id,
                       values_from = forecast_error)
  
  accuracy_baseline <- accuracy_baseline[match(variables$variable_longname,accuracy_baseline$variable_longname),]
  data_ts_baseline <- data_ts
  
  # Generic results WITH real-time data 
  #load(file = "data/generic_N_forecaster_data.rda")
  load(file = "data/generic_forecaster_data.rda")
  accuracy_generic <- data_ts |>
    dplyr::filter(id %in% id_select,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    #dplyr::mutate(forecast_error = 100*forecast_error,
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","id","forecast_error") |>
    tidyr::pivot_wider(names_from = id,
                       values_from = forecast_error)
  
  accuracy_generic <- accuracy_generic[match(variables$variable_longname,accuracy_generic$variable_longname),]
  
  # Randomization tests
  null_hypothesis <- function(df) {
    df |>
      dplyr::filter(type %in% "AI") |>
      dplyr::select(date_q,id,variable,forecast_error) |>
      dplyr::group_by(id,variable) |>
      dplyr::summarize(Mean = mean(forecast_error, na.rm=TRUE)) |>
      dplyr::ungroup() |>
      dplyr::left_join(
        data_ts_baseline |>
          dplyr::filter(type %in% "AI") |>
          dplyr::select(date_q,id,variable,forecast_error) |>
          dplyr::group_by(id,variable) |>
          dplyr::summarize(Mean_baseline = mean(forecast_error, na.rm=TRUE)) |>
          dplyr::ungroup() 
      ) |>
      dplyr::mutate(Mean = Mean-Mean_baseline) |>
      dplyr::select(id,variable,Mean)
  }
  
  tests_generic <- suppressMessages(randomization_test(data_ts |>
                                         dplyr::filter(id %in% id_select),
                                       null_hypothesis,num_sim=10000))
  names(tests_generic)[3] ="Significance_generic"
  
  # ttest <- data_ts |>
  #   dplyr::filter(id %in% horizons$id,
  #                 type %in% "AI") |>
  #   dplyr::select(date_q,id,variable,variable_name,forecast_error) |>
  #   dplyr::rename("forecast_error_generic"="forecast_error") |>
  #   unique() |>
  #   dplyr::left_join(data_ts_baseline |>
  #                      dplyr::filter(id %in% horizons$id,
  #                                    type %in% "AI") |>
  #                      dplyr::select(date_q,id,variable,forecast_error) |>
  #                      dplyr::rename("forecast_error_baseline"="forecast_error") |>unique(),
  #                    by = c("date_q","id","variable")) |>
  #   dplyr::group_by(id,variable) |>
  #   dplyr::mutate(tstat = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[1]],
  #                 tpval = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[3]]) |>
  #   dplyr::ungroup() |>
  #   dplyr::mutate(tpval_10 = ifelse(tpval<=0.1,1,0),
  #                 tpval_5 = ifelse(tpval<=0.05,1,0),
  #                 tpval_1 = ifelse(tpval<=0.01,1,0),
  #                 stars = tpval_10 + tpval_5 + tpval_1) |>
  #   dplyr::select(id,variable,tstat,tpval,stars) |>
  #   unique() 
  # 
  # ttest_average <- data_ts |>
  #   dplyr::filter(id %in% horizons$id,
  #                 type %in% "AI") |>
  #   dplyr::select(date_q,id,variable,forecast_error) |>
  #   dplyr::group_by(date_q,id) |>
  #   dplyr::summarize(forecast_error = mean(forecast_error, na.rm=TRUE)) |>
  #   dplyr::ungroup() |> 
  #   dplyr::rename("forecast_error_generic"="forecast_error") |>
  #   unique() |>
  #   dplyr::left_join(data_ts_baseline |>
  #                      dplyr::filter(id %in% horizons$id,
  #                                    type %in% "AI") |>
  #                      dplyr::select(date_q,id,variable,forecast_error) |>
  #                      dplyr::group_by(date_q,id) |>
  #                      dplyr::summarize(forecast_error = mean(forecast_error, na.rm=TRUE)) |>
  #                      dplyr::ungroup() |> 
  #                      dplyr::rename("forecast_error_baseline"="forecast_error") |>unique(),
  #                    by = c("date_q","id")) |>
  #   dplyr::group_by(id) |>
  #   dplyr::mutate(tstat = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[1]],
  #                 tpval = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[3]]) |>
  #   dplyr::ungroup() |>
  #   dplyr::mutate(tpval_10 = ifelse(tpval<=0.1,1,0),
  #                 tpval_5 = ifelse(tpval<=0.05,1,0),
  #                 tpval_1 = ifelse(tpval<=0.01,1,0),
  #                 stars = tpval_10 + tpval_5 + tpval_1) |>
  #   dplyr::select(id,tstat,tpval,stars) |>
  #   unique() 
  
  # Generic results WITHOUT real-time data 
  load(file = "data/generic_forecaster_no_realtime_data.rda")
  accuracy_generic_no_realtime <- data_ts |>
    dplyr::filter(id %in% id_select,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    #dplyr::mutate(forecast_error = 100*forecast_error,
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","id","forecast_error") |>
    tidyr::pivot_wider(names_from = id,
                       values_from = forecast_error)
  accuracy_generic_no_realtime <- accuracy_generic_no_realtime[match(variables$variable_longname,accuracy_generic_no_realtime$variable_longname),]
  
  tests_generic_no_realtime <- suppressMessages(randomization_test(data_ts |>
                                        dplyr::filter(id %in% id_select),
                                      null_hypothesis,num_sim=10000))
  names(tests_generic_no_realtime)[3] ="Significance_generic_no_realtime"
  
  # Generic results WITHOUT ANY data 
  load(file = "data/generic_forecaster_no_data.rda")
  accuracy_generic_no_data <- data_ts |>
    dplyr::filter(id %in% id_select,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    #dplyr::mutate(forecast_error = 100*forecast_error,
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","id","forecast_error") |>
    tidyr::pivot_wider(names_from = id,
                       values_from = forecast_error)
  accuracy_generic_no_data <- accuracy_generic_no_data[match(variables$variable_longname,accuracy_generic_no_data$variable_longname),]
  
  tests_generic_no_data <- suppressMessages(randomization_test(data_ts |>
                                                dplyr::filter(id %in% id_select),
                                              null_hypothesis,num_sim=10000))
  names(tests_generic_no_data)[3] ="Significance_generic_no_data"
  
  # ttest <- data_ts |>
  #   dplyr::filter(id %in% horizons$id,
  #                 type %in% "AI") |>
  #   dplyr::select(date_q,id,variable,variable_name,forecast_error) |>
  #   dplyr::rename("forecast_error_generic"="forecast_error") |>
  #   unique() |>
  #   dplyr::left_join(data_ts_baseline |>
  #                      dplyr::filter(id %in% horizons$id,
  #                                    type %in% "AI") |>
  #                      dplyr::select(date_q,id,variable,forecast_error) |>
  #                      dplyr::rename("forecast_error_baseline"="forecast_error") |>unique(),
  #                    by = c("date_q","id","variable")) |>
  #   dplyr::group_by(id,variable) |>
  #   dplyr::mutate(tstat = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[1]],
  #                 tpval = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[3]]) |>
  #   dplyr::ungroup() |>
  #   dplyr::mutate(tpval_10 = ifelse(tpval<=0.1,1,0),
  #                 tpval_5 = ifelse(tpval<=0.05,1,0),
  #                 tpval_1 = ifelse(tpval<=0.01,1,0),
  #                 stars = tpval_10 + tpval_5 + tpval_1) |>
  #   dplyr::select(id,variable,tstat,tpval,stars) |>
  #   unique() 
  # 
  # ttest_average <- data_ts |>
  #   dplyr::filter(id %in% horizons$id,
  #                 type %in% "AI") |>
  #   dplyr::select(date_q,id,variable,forecast_error) |>
  #   dplyr::group_by(date_q,id) |>
  #   dplyr::summarize(forecast_error = mean(forecast_error, na.rm=TRUE)) |>
  #   dplyr::ungroup() |> 
  #   dplyr::rename("forecast_error_generic"="forecast_error") |>
  #   unique() |>
  #   dplyr::left_join(data_ts_baseline |>
  #                      dplyr::filter(id %in% horizons$id,
  #                                    type %in% "AI") |>
  #                      dplyr::select(date_q,id,variable,forecast_error) |>
  #                      dplyr::group_by(date_q,id) |>
  #                      dplyr::summarize(forecast_error = mean(forecast_error, na.rm=TRUE)) |>
  #                      dplyr::ungroup() |> 
  #                      dplyr::rename("forecast_error_baseline"="forecast_error") |>unique(),
  #                    by = c("date_q","id")) |>
  #   dplyr::group_by(id) |>
  #   dplyr::mutate(tstat = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[1]],
  #                 tpval = t.test(forecast_error_generic, forecast_error_baseline, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[3]]) |>
  #   dplyr::ungroup() |>
  #   dplyr::mutate(tpval_10 = ifelse(tpval<=0.1,1,0),
  #                 tpval_5 = ifelse(tpval<=0.05,1,0),
  #                 tpval_1 = ifelse(tpval<=0.01,1,0),
  #                 stars = tpval_10 + tpval_5 + tpval_1) |>
  #   dplyr::select(id,tstat,tpval,stars) |>
  #   unique() 
  
  # Recall
  load(file = "data/recall_data.rda")
  accuracy_recall <- data_ts |>
    dplyr::filter(id %in% id_select,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    #dplyr::mutate(forecast_error = 100*forecast_error,
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","id","forecast_error") |>
    tidyr::pivot_wider(names_from = id,
                       values_from = forecast_error)
  accuracy_recall <- accuracy_recall[match(variables$variable_longname,accuracy_recall$variable_longname),]
  
  # HERTIL
  tests_recall <- suppressMessages(randomization_test(data_ts |>
                                       dplyr::filter(id %in% 0),
                                       null_hypothesis,num_sim=10000))
  names(tests_recall)[3] ="Significance_recall"
  
  
  # MAEs over baseline MAEs
  accuracy_generic_no_data[,c(2:(length(id_select)+1))] <- accuracy_generic_no_data[,c(2:(length(id_select)+1))]/accuracy_baseline[,c(2:(length(id_select)+1))]
  accuracy_generic_no_realtime[,c(2:(length(id_select)+1))] <- accuracy_generic_no_realtime[,c(2:(length(id_select)+1))]/accuracy_baseline[,c(2:(length(id_select)+1))]
  accuracy_generic[,c(2:(length(id_select)+1))] <- accuracy_generic[,c(2:(length(id_select)+1))]/accuracy_baseline[,c(2:(length(id_select)+1))]
  accuracy_recall[,c(2)] <- accuracy_recall[,c(2)]/accuracy_baseline[,c(2)]
  
  # Merge accuracy results
  accuracy <- accuracy_generic |>
    dplyr::mutate(empty1 = NA) |> 
    dplyr::left_join(accuracy_generic_no_realtime, by = "variable_longname") |>
    dplyr::mutate(empty2 = NA) |>
    dplyr::left_join(accuracy_generic_no_data, by = "variable_longname") |>
    dplyr::mutate(empty3 = NA) |>
    dplyr::left_join(accuracy_recall |> dplyr::select('variable_longname','0'), by = "variable_longname")
    
  # Add row with average
  accuracy <- rbind(accuracy, c('Average',lapply(names(accuracy)[2:dim(accuracy)[2]], 
                                                 function(x) {accuracy |> 
                                                     dplyr::pull(get(x)) |> 
                                                     mean()}) |> unlist()))
  accuracy <- cbind(accuracy$variable_longname, as.data.frame(lapply(accuracy[,2:dim(accuracy)[2]],as.numeric)))
  names(accuracy)[1] <- 'variable_longname'
  
  # Test results
  tests <- tests_generic |>
    dplyr::mutate(id = paste0('generic_',id)) |>
    tidyr::pivot_wider(names_from = id, values_from = 'Significance_generic') |>
    dplyr::mutate(empty1 = NA) |>
    dplyr::left_join(tests_generic_no_realtime |>
                       dplyr::mutate(id = paste0('generic_no_realtime_',id)) |>
                       tidyr::pivot_wider(names_from = id, values_from = 'Significance_generic_no_realtime')) |>
    dplyr::mutate(empty2 = NA) |>
    dplyr::left_join(tests_generic_no_data |>
                       dplyr::mutate(id = paste0('generic_no_data_',id)) |>
                       tidyr::pivot_wider(names_from = id, values_from = 'Significance_generic_no_data')) |>
    dplyr::mutate(empty3 = NA) |>
    dplyr::left_join(tests_recall |>
                       dplyr::mutate(id = paste0('generic_recall_',id)) |>
                       tidyr::pivot_wider(names_from = id, values_from = 'Significance_recall'))
  
  # Create table with designated filename
  writeLines(knitr::kable(accuracy, "latex", 
                          digits=2, 
                          align = c(rep(c('l',rep('d{3.2}',length(id_select))),3),'l','d{5.2}'), 
                          booktabs=T),
             filename)

  tbl <- readLines(filename)
  tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  tbl <- c(tbl[1:2],
           "& \\multicolumn{2}{C{2cm}}{Generic} && \\multicolumn{2}{C{2cm}}{Generic, w/o real-time data} && \\multicolumn{C{3.5cm}}{c}{Generic, w/o real-time data, w/o past SPF data} && \\multicolumn{1}{c}{Recall}\\\\",
           " \\cmidrule{2-3} \\cmidrule{5-6} \\cmidrule{8-9} \\cmidrule{11-11}",
           "Horizon (quarters) & \\multicolumn{1}{c}{0} & \\multicolumn{1}{c}{4} && \\multicolumn{1}{c}{0} & \\multicolumn{1}{c}{4} && \\multicolumn{1}{c}{0} & \\multicolumn{1}{c}{4}  && \\multicolumn{1}{c}{0} \\\\",
           tbl[4:length(tbl)])
  tbl <- boldface_table(tbl, boldface_min = FALSE, boldface_threshold = TRUE, threshold = 1)
  tbl <- add_stars(tbl,tests, 
                   main_matter_end_row = which(grepl("\\bottomrule",tbl,fixed=TRUE))-2)
  tbl <- insert_sections(tbl)
  
  writeLines(tbl,filename)
  
  save.image("generic_output.RData")  
  
  
}