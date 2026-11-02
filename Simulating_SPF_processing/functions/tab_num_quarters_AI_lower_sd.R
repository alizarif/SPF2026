
tab_num_quarters_AI_lower_sd <- function(filename = 'tables/forecast_disagreement_num_quarters_ai_spf.txt') {
    
  df <- data_long |> 
    dplyr::filter(id %in% horizons$id, type %in% survey_names[1]) |>
    dplyr::select(id,variable,value,type,date_q) |>
    dplyr::bind_rows(SPFmicrodata_long |> 
                       dplyr::filter(id %in% horizons$id) |>
                       dplyr::select(id,variable,value,date_q) |>
                       dplyr::mutate(type = "Human")) |>
    dplyr::group_by(id,variable,type,date_q) |>
    dplyr::summarize(SD = sd(value, na.rm=TRUE)) |>
    dplyr::ungroup() 
  
  sd <- df |>
    tidyr::pivot_wider(names_from = type, values_from = SD) |>
    dplyr::mutate(SD_smaller_AI = (AI)<=(Human)) |>
    dplyr::group_by(id,variable) |>
    dplyr::summarise_at("SD_smaller_AI",function(x) mean(x,na.rm=T)) |>
    dplyr::ungroup() |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select("id","variable_longname","SD_smaller_AI") 
  
  # Randomization tests
  null_hypothesis <- function(df) {
    df |>
      tidyr::pivot_wider(names_from = type, values_from = SD) |>
      dplyr::mutate(SD_smaller_AI = (AI)<=(Human)) |>
      dplyr::group_by(id,variable) |>
      dplyr::summarise_at("SD_smaller_AI",function(x) mean(x,na.rm=T)) |>
      dplyr::ungroup() |>
      dplyr::mutate(H0 = (SD_smaller_AI-.5)) |>
      dplyr::select(id,variable,H0)
  }
  
  tests <- randomization_test(data_ts |>
                                dplyr::filter(id %in% horizons$id) |>
                                dplyr::select(date_q,id,variable,type) |>
                                dplyr::left_join(df),
                            null_hypothesis,num_sim=10000)
  names(tests)[3] ="Significance"
  
  # Table
  table1 <- sd |>
    dplyr::select("id","variable_longname","SD_smaller_AI") |>
    dplyr::left_join(tests) |>
    tidyr::pivot_wider(names_from=id,
                       values_from=all_of(c("SD_smaller_AI","Significance"))) |>
    dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield")) |>
    dplyr::mutate(!!!setNames(rep(NA, length(horizons$id)), paste0("empty_",horizons$id))) |>
    dplyr::select("variable_longname",
                  lapply(horizons$id,function(x) paste0(c("SD_smaller_AI","Significance","empty"),"_",x)) |> unlist()
    )
  table1 <- table1[match(variables$variable_longname,table1$variable_longname),]
  if (grepl('empty',names(table1)[dim(table1)[2]])) {
    table1 <- table1[,1:(dim(table1)[2]-1)]  
  }
  
  writeLines(knitr::kable(table1, "latex", 
                          digits=2, 
                          align = c(rep(c('l','d{3.2}','d{1.2}'),length(horizons$id))), 
                          booktabs=T),
             filename)
  
  tbl <- readLines(filename)
  tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  tbl <- c(tbl[1:2],
           "Horizon (quarters) & \\multicolumn{2}{c}{0} && \\multicolumn{2}{c}{1} && \\multicolumn{2}{c}{4}  \\\\",
           " \\cmidrule{2-3} \\cmidrule{5-6} \\cmidrule{8-9}",
           paste(paste(rep("& \\multicolumn{1}{c}{Pct} & \\multicolumn{1}{c}{P-val}",length(horizons$id)),collapse="&"),"\\\\"),
           tbl[4:length(tbl)])
  tbl <- boldface_table(tbl, boldface_min = FALSE, boldface_threshold = TRUE, threshold = .5)
  tbl <- insert_sections(tbl)
  tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  tbl <- gsub("star1","^{\\\\star}",tbl)
  tbl <- gsub("star0","",tbl)
  writeLines(tbl,filename)
  
  
}