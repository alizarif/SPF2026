
tab_forecast_accuracy_recall <- function(filename = "tables/forecast_accuracy_recall.txt") {
  
  err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
  mae <- function(x) {mean(abs(x |> na.omit()), na.rm=TRUE)}
  
  # Baseline results
  accuracy_baseline <- data_ts |>
    dplyr::filter(id %in% horizons$id,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    dplyr::mutate(forecast_error = 100*forecast_error/realized,
                  forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","forecast_error") 
  
  accuracy_baseline <- accuracy_baseline[match(variables$variable_longname,accuracy_baseline$variable_longname),]
  
  horizons0 <- horizons
  
  
  # Recall results 
  load(file = "data/recall_data.rda")
  accuracy <- data_ts |>
    dplyr::filter(id %in% horizons0$id,
                  type %in% "AI") |>
    dplyr::group_by(id,variable) |>
    dplyr::mutate(forecast_error = 100*forecast_error/realized,
                  forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("variable_longname","forecast_error") 
  
  accuracy <- accuracy[match(variables$variable_longname,accuracy$variable_longname),]
  
  # Merge results
  accuracy <- accuracy |>
    dplyr::rename("Recall"="forecast_error") |>
    dplyr::left_join(accuracy_baseline |>
                       dplyr::rename("Nowcast"="forecast_error"))
  
  # Create table with designated filename
  writeLines(knitr::kable(accuracy, "latex", 
                          digits=2, 
                          align = c(rep(c('l',rep('d{3.2}',2)),length(horizons$id))), 
                          booktabs=T),
             filename)

  tbl <- readLines(filename)
  tbl <- c(tbl[1:2],
           "& \\multicolumn{1}{c}{Recall} & \\multicolumn{1}{c}{Nowcast}\\\\",
           tbl[4:length(tbl)])
  tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  tbl <- boldface_table(tbl,compare_columns=list(c(2,3)))
  writeLines(tbl,filename)
  
}