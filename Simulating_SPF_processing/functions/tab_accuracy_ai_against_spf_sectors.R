
tab_accuracy_ai_against_spf <- function() {
  
  filename = 'tables/accuracy_ai_against_spf.txt'
  
  err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
  mae <- function(x) {mean(abs(x |> na.omit()), na.rm=TRUE)}
  dir_err <- function(x) { sign(dplyr::pull(x,1)) == sign(dplyr::pull(x,2))}
  
  # accuracy <- error_ts |>
  #   dplyr::filter(id %in% horizons$id) |>
  #   dplyr::group_by(id,variable) |>
  #   dplyr::mutate(median_err = 100*median_err/median_Human,
  #                 median_err = ifelse(median_err %in% c(-Inf,Inf),NA,median_err)) |>
  #   dplyr::summarise_at("median_err",mae) |>
  #   dplyr::left_join(
  #     error_ts[data_ts_wide$nber_rec==1,] |>
  #       dplyr::group_by(id,variable) |>
  #       dplyr::mutate(median_err = 100*median_err/median_Human,
  #                     median_err = ifelse(median_err %in% c(-Inf,Inf),NA,median_err)) |>
  #       dplyr::summarise_at(c("median_err_rec"="median_err"),
  #                           mae),
  #     by=c("id","variable")) |>
  #   dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
  #                    by=c("variable"="variable")) |>
  #   dplyr::select("id","variable_longname","median_err","median_err_rec") |>
  #   tidyr::pivot_wider(names_from=id,
  #                      values_from=c(median_err,median_err_rec)) |>
  #   dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
  #   dplyr::mutate(empty=NA) |>
  #   dplyr::select("variable_longname",paste0("median_err_",horizons$id),"empty",
  #                 paste0("median_err_rec_",horizons$id))
  # accuracy <- accuracy[match(variables$variable_longname,accuracy$variable_longname),]
  # 
  # # Create table with designated filename
  # writeLines(knitr::kable(accuracy, "latex", 
  #                         digits=3, 
  #                         align = c('l',rep('d{2.3}',4),'l',rep('d{2.3}',4)), 
  #                         booktabs=T),
  #            filename)
  # 
  # tbl <- readLines(filename)
  # tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  # tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  # tbl <- c(tbl[1:2],
  #          " & \\multicolumn{4}{c}{Median forecasts} && \\multicolumn{4}{c}{Median forecasts in NBER recessions} \\\\",
  #          " \\cmidrule{2-5} \\cmidrule{7-10}",
  #          paste("Horizon (quarter) &", paste(horizons$id,collapse ="&"),"&&",paste(horizons$id,collapse ="&"),"\\\\"),
  #          tbl[4:length(tbl)])
  # tbl <- boldface_table(tbl, num_digits=c(2,3))
  
  # accuracy <- error_ts |>
  #   dplyr::filter(id %in% horizons$id) |>
  #   dplyr::group_by(id,variable) |>
  #   dplyr::mutate(median_err = 100*median_err/median_Human,
  #                 median_err = ifelse(median_err %in% c(-Inf,Inf),NA,median_err)) |>
  #   dplyr::summarise_at("median_err",mae) |>
  #   dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
  #                    by=c("variable"="variable")) |>
  #   dplyr::select("id","variable_longname","median_err") |>
  #   tidyr::pivot_wider(names_from=id,
  #                      values_from=c(median_err)) |>
  #   dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield"))
  # accuracy <- accuracy[match(variables$variable_longname,accuracy$variable_longname),]
  # names(accuracy) <- c("variable_longname",paste0("median_err_",horizons$id))
  
  accuracy <- data_ts |>
    dplyr::filter(id %in% horizons$id) |>
    dplyr::group_by(id,type,variable) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("id","type","variable_longname","forecast_error") |>
    tidyr::pivot_wider(names_from=type, 
                       values_from = forecast_error) |>
    dplyr::mutate(relative_forecast_error = Human/AI) |>
    dplyr::select(-c(AI,Human)) |>
    tidyr::pivot_wider(names_from=id,
                       values_from=c(relative_forecast_error)) |>
    dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield"))
  accuracy <- accuracy[match(variables$variable_longname,accuracy$variable_longname),]
  names(accuracy) <- c("variable_longname",paste0("rel_err_",horizons$id))
  
  ttest <- data_ts |> 
    dplyr::select(c(date_q,id,variable,type,median,nber_rec)) |> 
    tidyr::pivot_wider(names_from = c(type), 
                       values_from = c(median))  |>
    dplyr::filter(id %in% horizons$id) |>
    dplyr::group_by(id,variable) |>
    dplyr::mutate(tstat = t.test(AI, Human, 
                                 alternative = "two.sided", 
                                 mu = 0, 
                                 paired = FALSE, 
                                 var.equal = FALSE, 
                                 conf.level = 0.95)[[1]],
                  tpval = t.test(AI, Human, 
                                 alternative = "two.sided", 
                                 mu = 0, 
                                 paired = FALSE, 
                                 var.equal = FALSE, 
                                 conf.level = 0.95)[[3]]) |>
    dplyr::ungroup() |>
    dplyr::select(id,variable,tstat,tpval) |>
    unique() |>
    dplyr::mutate(
      tpval_10 = ifelse(tpval<=0.1,1,0),
      tpval_5 = ifelse(tpval<=0.05,1,0),
      tpval_1 = ifelse(tpval<=0.01,1,0),
      stars = tpval_10 + tpval_5 + tpval_1
      )
  
  ttest$stars <- gsub("1","star1",ttest$stars)
  ttest$stars <- gsub("2","star2",ttest$stars)
  ttest$stars <- gsub("3","star3",ttest$stars)
  ttest$stars <- gsub("0","star0",ttest$stars)
  
  ttest_wide <- ttest |>
    dplyr::mutate(tstat_ = paste0(sprintf("%.2f", tstat),stars)) |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("id","variable_longname","tstat_") |>
    tidyr::pivot_wider(names_from=id,
                       values_from=c(tstat_)) |>
    dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield"))
  ttest_wide <- ttest_wide[match(variables$variable_longname,ttest_wide$variable_longname),]
  names(ttest_wide) <- c("variable_longname",paste0("tstat_",horizons$id))
  
  table_data <- accuracy |>
  dplyr::mutate(empty=NA) |> 
  dplyr::left_join(ttest_wide)
  
  # Create table with designated filename
  writeLines(knitr::kable(table_data, "latex", 
                          digits=2, 
                          align = c('l',rep('d{2.2}',4),'l',rep('d{4.2}',4)), 
                          booktabs=T),
             filename)
  
  tbl <- readLines(filename)
  tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  tbl <- c(tbl[1:2],
           " & \\multicolumn{4}{c}{Relative MAE (Human/AI)} && \\multicolumn{4}{c}{t-test statistics} \\\\",
           " \\cmidrule{2-5} \\cmidrule{7-10}",
           paste("Horizon (quarter) &", paste(horizons$id,collapse ="&"),"&&",paste(horizons$id,collapse ="&"),"\\\\"),
           tbl[4:length(tbl)])
  tbl <- boldface_table(tbl, boldface_min = FALSE, boldface_threshold = TRUE, threshold = 1)
  tbl <- insert_sections(tbl)
  tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  tbl <- gsub("star1","^{\\\\star}",tbl)
  tbl <- gsub("star0","",tbl)
  
  writeLines(tbl,filename)
}