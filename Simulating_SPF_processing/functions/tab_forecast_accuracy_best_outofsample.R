
tab_forecast_accuracy_outofsample <- function(filename = 'tables/forecast_accuracy_best_forecasters_oos.txt') {
  
  filename1 <- filename
  
  # Load data
  load(file = "data/outofsample_data.rda")
  
  # Define functions
  err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
  mae <- function(x) {mean(abs(x |> na.omit()), na.rm=TRUE)}
  
  # ggplot2::ggplot(data_ts |>
  #                   dplyr::filter(id %in% "0",
  #                                 variable %in% "HOUSING"),
  #                 ggplot2::aes(x=date_q,y=median,color=type)) +
  #   ggplot2::geom_line() +
  #   ggplot2::geom_line(ggplot2::aes(x=date_q,y=realized),color='Black')
  
  # Define time series: Best forecaster across time (per id, variable) (against Human median)
  times_w_human_forecasts <- data_long |>
    dplyr::filter(id %in% horizons$id,
                  type %in% survey_names[2]) |>
    dplyr::mutate(date_q_ = !(is.na(value))) |>
    dplyr::select(id,variable,date_q,date_q_)
  
  best_forecaster <- data_long |>
    dplyr::filter(type %in% survey_names,
                  id %in% horizons$id,
                  type %in% survey_names[1]) |>
    dplyr::select(date_q,id,variable,value,type,Name) |>
    dplyr::left_join(times_w_human_forecasts, by=c("id","variable","date_q")) |>
    dplyr::filter(date_q_==T) |> 
    dplyr::select(-date_q_) |>
    dplyr::left_join(data_ts |> 
                       dplyr::select(date_q,id,variable,type,realized), 
                     by=c('id','variable','type','date_q')) |>
    dplyr::mutate(forecast_error = value - realized) |>
    dplyr::group_by(id,variable,Name) |>
    dplyr::mutate(forecast_error = mae(forecast_error)) |>
    dplyr::ungroup() |>
    dplyr::group_by(id,variable) |>
    dplyr::arrange(forecast_error) |>
    dplyr::summarise(best_name = dplyr::first(na.omit(Name))) |>
    dplyr::ungroup() 
  
  times_w_best_forecasts <- data_long |>
    dplyr::filter(id %in% horizons$id,
                  type %in% survey_names[1]) |>
    dplyr::left_join(best_forecaster,by=c("id","variable")) |>
    dplyr::mutate(best_forecast = best_name==Name) |>
    dplyr::filter(best_forecast == T) |>
    dplyr::select(date_q,id,variable) |>
    dplyr::mutate(date_q_ = T)
  
  data_ts2 <- data_long |>
    dplyr::filter(id %in% horizons$id,
                  type %in% survey_names[1]) |>
    dplyr::left_join(best_forecaster,by=c("id","variable")) |>
    dplyr::mutate(best_forecast = best_name==Name) |>
    dplyr::filter(best_forecast == T) |>
    dplyr::select(date_q,id,variable,value,type) |>
    dplyr::left_join(data_ts |> 
                       dplyr::select(date_q,id,variable,type,realized), 
                     by=c('id','variable','type','date_q')) |>
    dplyr::mutate(forecast_error = value - realized) |>
    dplyr::select(date_q,id,variable,forecast_error,type) |>
    dplyr::bind_rows(data_ts |> 
                       dplyr::filter(id %in% horizons$id,
                                     type %in% survey_names[2]) |>
                       dplyr::left_join(times_w_best_forecasts, by=c("id","variable","date_q")) |>
                       dplyr::filter(date_q_==T) |>
                       dplyr::select(date_q,id,variable,forecast_error,type))
  
  # Accuracy
  accuracy <- data_ts2 |>
    dplyr::filter(id %in% horizons$id) |>
    dplyr::group_by(id,type,variable) |>
    #dplyr::mutate(forecast_error = (forecast_error-mean(realized,na.rm=T))/sd(realized,na.rm=T),
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("id","type","variable_longname","forecast_error") 
  
  # Randomization tests
  null_hypothesis <- function(df) {
    df |>
      dplyr::select(date_q,type,id,variable,forecast_error) |>
      dplyr::group_by(id,variable,type) |>
      dplyr::summarize(Mean = mean(forecast_error, na.rm=TRUE)) |>
      dplyr::ungroup() |>
      tidyr::pivot_wider(names_from = type, values_from = c(Mean)) |> 
      dplyr::mutate(Mean = AI-Human) |>
      dplyr::select(id,variable,Mean)
  }
  
  tests1 <- randomization_test(data_ts |>
                              dplyr::filter(id %in% horizons$id),
                            null_hypothesis,num_sim=10000)
  names(tests1)[3] ="Significance"
  
  # Full Sample
  table1 <- accuracy |>
    dplyr::select("id","type","variable_longname","forecast_error") |>
    tidyr::pivot_wider(names_from="type",
                       values_from=c("forecast_error")) |>
    dplyr::left_join(tests1) |>
    tidyr::pivot_wider(names_from=id,
                       values_from=all_of(c(survey_names,"Significance"))) |>
    dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
    dplyr::mutate(!!!setNames(rep(NA, length(horizons$id)), paste0("empty_",horizons$id))) |>
    dplyr::select("variable_longname",
                  lapply(horizons$id,function(x) paste0(c(survey_names,"Significance","empty"),"_",x)) |> unlist()
    )
  table1 <- table1[match(variables$variable_longname,table1$variable_longname),]
  if (grepl('empty',names(table1)[dim(table1)[2]])) {
    table1 <- table1[,1:(dim(table1)[2]-1)]  
  }
  
  writeLines(knitr::kable(table1, "latex", 
                          digits=2, 
                          align = c(rep(c('l',rep('d{3.2}',2),'d{1.2}'),length(horizons$id))), 
                          booktabs=T),
             filename1)
  
  tbl <- readLines(filename1)
  tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  tbl <- c(tbl[1:2],
           "Horizon (quarters) & \\multicolumn{3}{c}{0} && \\multicolumn{3}{c}{1} && \\multicolumn{3}{c}{2}  \\\\",
           " \\cmidrule{2-4} \\cmidrule{6-8} \\cmidrule{10-12}",
           paste(paste(rep("& \\multicolumn{1}{c}{AI} & \\multicolumn{1}{c}{Human} & \\multicolumn{1}{c}{P-val}",length(horizons$id)),collapse="&"),"\\\\"),
           tbl[4:length(tbl)])
  tbl <- boldface_table(tbl,compare_columns = list(c(2,3),c(6,7),c(10,11)))
  tbl <- insert_sections(tbl)
  tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  tbl <- gsub("star1","\\\\star",tbl)
  tbl <- gsub("star0","",tbl)
  writeLines(tbl,filename1)
  
  
}