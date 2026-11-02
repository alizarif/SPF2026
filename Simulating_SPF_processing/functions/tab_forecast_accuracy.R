
tab_forecast_accuracy <- function(filename = 'tables/forecast_accuracy', data_file = NULL) {
  
  if (!(is.null(data))) {
    load(file = data_file)
  }
  
  # File names
  filename1 = paste0(filename,'_ai_spf.txt')
  # filename2 = paste0(filename,'_ai_spf_vix_above_quartile.txt') 
  # filename3 = paste0(filename,'_ai_spf_vix_below_quartile.txt') 
  # filename4 = paste0(filename,'_ai_spf_nber_rec.txt') 
  
  # Define functions
  err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
  mae <- function(x) {mean(abs(x |> na.omit()), na.rm=TRUE)}
  
  # Define splitting indicators and variables
  data_ts <- data_ts |> dplyr::mutate(vix_ind = ifelse(vix<(quantile(data_ts$vix |> na.omit(),0.75)), ifelse(vix<=(quantile(data_ts$vix |> na.omit(),0.25)),-1,0),1),
                                      epu_ind = ifelse(epu<(quantile(data_ts$epu |> na.omit(),0.75)),0,1))
            
  times_w_human_forecasts <- data_long |>
    dplyr::filter(id %in% horizons$id,
                  type %in% survey_names[2]) |>
    dplyr::mutate(date_q_ = !(is.na(value))) |>
    dplyr::select(id,variable,date_q,date_q_)
    
  # Accuracy: Full sample and sub-sample
  accuracy <- data_ts |>
    dplyr::left_join(times_w_human_forecasts, by=c("id","variable","date_q")) |>
    dplyr::filter(date_q_==TRUE) |> 
    dplyr::select(-date_q_) |>
    dplyr::filter(id %in% horizons$id) |>
    dplyr::group_by(id,type,variable) |>
    #dplyr::mutate(forecast_error = (forecast_error-mean(realized,na.rm=T))/sd(realized,na.rm=T),
    #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::left_join(
      data_ts |> dplyr::filter(vix_ind==1) |>
        dplyr::group_by(id,type,variable) |>
        #dplyr::mutate(forecast_error = (forecast_error-mean(realized,na.rm=T))/sd(realized,na.rm=T),
        #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
        dplyr::summarise_at("forecast_error",mae) |>
        #dplyr::mutate(forecast_error = (forecast_error-mean(data_ts$realized|>unique(),na.rm=T))/sd(data_ts$realized|>unique(),na.rm=T)) |>
        dplyr::rename("forecast_error_vix"="forecast_error"),
      by=c("id","type","variable")) |>
    dplyr::left_join(
      data_ts |> dplyr::filter(vix_ind==-1) |>
        dplyr::group_by(id,type,variable) |>
        #dplyr::mutate(forecast_error = (forecast_error-mean(realized,na.rm=T))/sd(realized,na.rm=T),
        #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
        dplyr::summarise_at("forecast_error",mae) |>
        #dplyr::mutate(forecast_error = (forecast_error-mean(data_ts$realized|>unique(),na.rm=T))/sd(data_ts$realized|>unique(),na.rm=T)) |>
        dplyr::rename("forecast_error_epu"="forecast_error"),
      by=c("id","type","variable")) |>
    dplyr::left_join(
      data_ts |> dplyr::filter(nber_rec==0,
                               vix_ind==1) |>
        dplyr::group_by(id,type,variable) |>
        #dplyr::mutate(forecast_error = (forecast_error-mean(realized,na.rm=T))/sd(realized,na.rm=T),
        #              forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
        dplyr::summarise_at("forecast_error",mae) |>
        #dplyr::mutate(forecast_error = (forecast_error-mean(data_ts$realized|>unique(),na.rm=T))/sd(data_ts$realized|>unique(),na.rm=T)) |>
        dplyr::rename("forecast_error_nber"="forecast_error"),
      by=c("id","type","variable")) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("id","type","variable_longname","forecast_error","forecast_error_vix","forecast_error_epu","forecast_error_nber") 
  
  # # t-tests 
  # ttest <- data_ts |>
  #   dplyr::filter(split==0,
  #                 id %in% horizons$id) |>
  #   tidyr::pivot_wider(names_from=type,
  #                      values_from=c(forecast_error)) |>
  #   dplyr::group_by(id,variable) |>
  #   dplyr::mutate(tstat = t.test(AI, Human, 
  #                                alternative = "two.sided", 
  #                                mu = 0, 
  #                                paired = FALSE, 
  #                                var.equal = FALSE, 
  #                                conf.level = 0.95)[[1]],
  #                 tpval = t.test(AI, Human, 
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
  #   unique() |>
  #   dplyr::left_join(
  #     data_ts |> 
  #       dplyr::filter(split==1,
  #                     id %in% horizons$id) |>
  #       tidyr::pivot_wider(names_from=type,
  #                          values_from=c(forecast_error)) |>
  #       dplyr::group_by(id,variable) |>
  #       dplyr::mutate(tstat_rec = t.test(AI, Human, 
  #                                        alternative = "two.sided", 
  #                                        mu = 0, 
  #                                        paired = FALSE, 
  #                                        var.equal = FALSE, 
  #                                        conf.level = 0.95)[[1]],
  #                     tpval_rec = t.test(AI, Human, 
  #                                        alternative = "two.sided", 
  #                                        mu = 0, 
  #                                        paired = FALSE, 
  #                                        var.equal = FALSE, 
  #                                        conf.level = 0.95)[[3]]) |>
  #       dplyr::ungroup() |>
  #       dplyr::mutate(tpval_10 = ifelse(tpval_rec<=0.1,1,0),
  #                     tpval_5 = ifelse(tpval_rec<=0.05,1,0),
  #                     tpval_1 = ifelse(tpval_rec<=0.01,1,0),
  #                     stars_rec = tpval_10 + tpval_5 + tpval_1) |>
  #       dplyr::select(id,variable,tstat_rec,tpval_rec,stars_rec) |>
  #       unique()
  #   )
  
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
  
  # tests2 <- randomization_test(data_ts |>
  #                               dplyr::filter(id %in% horizons$id,
  #                                             vix_ind==1),
  #                             null_hypothesis,num_sim=10000)
  # names(tests2)[3] ="Significance"
  # 
  # tests3 <- randomization_test(data_ts |>
  #                                dplyr::filter(id %in% horizons$id,
  #                                              vix_ind==-1),
  #                              null_hypothesis,num_sim=10000)
  # names(tests3)[3] ="Significance"
  # 
  # tests4 <- randomization_test(data_ts |>
  #                                dplyr::filter(id %in% horizons$id,
  #                                              nber_rec==0,
  #                                              vix_ind==1),
  #                              null_hypothesis,num_sim=10)
  # names(tests4)[3] ="Significance"
  
  # Full Sample
  table1 <- accuracy |>
    dplyr::select("id","type","variable_longname","forecast_error") |>
    tidyr::pivot_wider(names_from="type",
                       values_from=c("forecast_error")) |>
    dplyr::left_join(tests1) |>
    tidyr::pivot_wider(names_from=id,
                       values_from=all_of(c(survey_names,"Significance"))) |>
    #dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
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
           "Horizon (quarters) & \\multicolumn{3}{c}{0} && \\multicolumn{3}{c}{1} && \\multicolumn{3}{c}{4}  \\\\",
           " \\cmidrule{2-4} \\cmidrule{6-8} \\cmidrule{10-12}",
           paste(paste(rep("& \\multicolumn{1}{c}{AI} & \\multicolumn{1}{c}{Human} & \\multicolumn{1}{c}{P-val}",length(horizons$id)),collapse="&"),"\\\\"),
           tbl[4:length(tbl)])
  tbl <- boldface_table(tbl,compare_columns = list(c(2,3),c(6,7),c(10,11)))
  tbl <- insert_sections(tbl)
  tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  tbl <- gsub("star1","^{\\\\star}",tbl)
  tbl <- gsub("star0","",tbl)
  writeLines(tbl,filename1)
  
  # # Sample: VIX>average
  # table2 <- accuracy |>
  #   dplyr::select("id","type","variable_longname","forecast_error_vix") |>
  #   dplyr::rename("forecast_error"="forecast_error_vix") |>
  #   tidyr::pivot_wider(names_from="type",
  #                      values_from=c("forecast_error")) |>
  #   dplyr::left_join(tests2) |>
  #   tidyr::pivot_wider(names_from=id,
  #                      values_from=all_of(c(survey_names,"Significance"))) |>
  #   dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
  #   dplyr::mutate(!!!setNames(rep(NA, length(horizons$id)), paste0("empty_",horizons$id))) |>
  #   dplyr::select("variable_longname",
  #                 lapply(horizons$id,function(x) paste0(c(survey_names,"Significance","empty"),"_",x)) |> unlist()
  #   )
  # table2 <- table2[match(variables$variable_longname,table2$variable_longname),]
  # if (grepl('empty',names(table2)[dim(table2)[2]])) {
  #   table2 <- table2[,1:(dim(table2)[2]-1)]  
  # }
  # 
  # writeLines(knitr::kable(table2, "latex", 
  #                         digits=2, 
  #                         align = c(rep(c('l',rep('d{3.2}',2),'d{1.2}'),length(horizons$id))), 
  #                         booktabs=T),
  #            filename2)
  # 
  # tbl <- readLines(filename2)
  # tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  # tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  # tbl <- c(tbl[1:2],
  #          "Horizon (quarters) & \\multicolumn{3}{c}{0} && \\multicolumn{3}{c}{1} && \\multicolumn{3}{c}{4}  \\\\",
  #          " \\cmidrule{2-4} \\cmidrule{6-8} \\cmidrule{10-12}",
  #          paste(paste(rep("& \\multicolumn{1}{c}{AI} & \\multicolumn{1}{c}{Human} & \\multicolumn{1}{c}{P-val}",length(horizons$id)),collapse="&"),"\\\\"),
  #          tbl[4:length(tbl)])
  # tbl <- boldface_table(tbl,compare_columns = list(c(2,3),c(6,7),c(10,11)))
  # tbl <- insert_sections(tbl)
  # tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  # tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  # tbl <- gsub("star1","\\\\star",tbl)
  # tbl <- gsub("star0","",tbl)
  # writeLines(tbl,filename2)
  # 
  # # Sample: EPU>average
  # table3 <- accuracy |>
  #   dplyr::select("id","type","variable_longname","forecast_error_epu") |>
  #   dplyr::rename("forecast_error"="forecast_error_epu") |>
  #   tidyr::pivot_wider(names_from="type",
  #                      values_from=c("forecast_error")) |>
  #   dplyr::left_join(tests3) |>
  #   tidyr::pivot_wider(names_from=id,
  #                      values_from=all_of(c(survey_names,"Significance"))) |>
  #   dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
  #   dplyr::mutate(!!!setNames(rep(NA, length(horizons$id)), paste0("empty_",horizons$id))) |>
  #   dplyr::select("variable_longname",
  #                 lapply(horizons$id,function(x) paste0(c(survey_names,"Significance","empty"),"_",x)) |> unlist()
  #   )
  # table3 <- table3[match(variables$variable_longname,table3$variable_longname),]
  # if (grepl('empty',names(table3)[dim(table3)[2]])) {
  #   table3 <- table3[,1:(dim(table3)[2]-1)]  
  # }
  # 
  # writeLines(knitr::kable(table3, "latex", 
  #                         digits=2, 
  #                         align = c(rep(c('l',rep('d{3.2}',2),'d{1.2}'),length(horizons$id))), 
  #                         booktabs=T),
  #            filename3)
  # 
  # tbl <- readLines(filename3)
  # tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  # tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  # tbl <- c(tbl[1:2],
  #          "Horizon (quarters) & \\multicolumn{3}{c}{0} && \\multicolumn{3}{c}{1} && \\multicolumn{3}{c}{4}  \\\\",
  #          " \\cmidrule{2-4} \\cmidrule{6-8} \\cmidrule{10-12}",
  #          paste(paste(rep("& \\multicolumn{1}{c}{AI} & \\multicolumn{1}{c}{Human} & \\multicolumn{1}{c}{P-val}",length(horizons$id)),collapse="&"),"\\\\"),
  #          tbl[4:length(tbl)])
  # tbl <- boldface_table(tbl,compare_columns = list(c(2,3),c(6,7),c(10,11)))
  # tbl <- insert_sections(tbl)
  # tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  # tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  # tbl <- gsub("star1","\\\\star",tbl)
  # tbl <- gsub("star0","",tbl)
  # writeLines(tbl,filename3)
  # 
  # # Sample: NBER recessions
  # table4 <- accuracy |>
  #   dplyr::select("id","type","variable_longname","forecast_error_nber") |>
  #   dplyr::rename("forecast_error"="forecast_error_nber") |>
  #   tidyr::pivot_wider(names_from="type",
  #                      values_from=c("forecast_error")) |>
  #   dplyr::left_join(tests4) |>
  #   tidyr::pivot_wider(names_from=id,
  #                      values_from=all_of(c(survey_names,"Significance"))) |>
  #   dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
  #   dplyr::mutate(!!!setNames(rep(NA, length(horizons$id)), paste0("empty_",horizons$id))) |>
  #   dplyr::select("variable_longname",
  #                 lapply(horizons$id,function(x) paste0(c(survey_names,"Significance","empty"),"_",x)) |> unlist()
  #   )
  # table4 <- table4[match(variables$variable_longname,table4$variable_longname),]
  # if (grepl('empty',names(table4)[dim(table4)[2]])) {
  #   table4 <- table4[,1:(dim(table4)[2]-1)]  
  # }
  # 
  # writeLines(knitr::kable(table4, "latex", 
  #                         digits=2, 
  #                         align = c(rep(c('l',rep('d{3.2}',2),'d{1.2}'),length(horizons$id))), 
  #                         booktabs=T),
  #            filename4)
  # 
  # tbl <- readLines(filename4)
  # tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  # tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  # tbl <- c(tbl[1:2],
  #          "Horizon (quarters) & \\multicolumn{3}{c}{0} && \\multicolumn{3}{c}{1} && \\multicolumn{3}{c}{4}  \\\\",
  #          " \\cmidrule{2-4} \\cmidrule{6-8} \\cmidrule{10-12}",
  #          paste(paste(rep("& \\multicolumn{1}{c}{AI} & \\multicolumn{1}{c}{Human} & \\multicolumn{1}{c}{P-val}",length(horizons$id)),collapse="&"),"\\\\"),
  #          tbl[4:length(tbl)])
  # tbl <- boldface_table(tbl,compare_columns = list(c(2,3),c(6,7),c(10,11)))
  # tbl <- insert_sections(tbl)
  # tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  # tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  # tbl <- gsub("star1","\\\\star",tbl)
  # tbl <- gsub("star0","",tbl)
  # writeLines(tbl,filename4)
  
}