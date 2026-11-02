
tab_distributions_ai_against_spf <- function() {
  
  filename = 'tables/test_distributions_ai_against_spf.txt'
 
  # Pooling across time
  ks_test <- data_long |> 
    dplyr::filter(id %in% horizons$id, type %in% survey_names[1]) |>
    dplyr::select(id,variable,value,type) |>
    dplyr::bind_rows(SPFmicrodata_long |> 
                       dplyr::select(id,variable,value) |>
                       dplyr::mutate(type = "Human")) |>
    tidyr::pivot_wider(names_from = type, values_from = value, values_fn = list) |> 
    dplyr::group_by(id,variable) |>
    dplyr::mutate(KSstat = tryCatch(stats::ks.test(dplyr::pick(AI) |> unlist(),
                                                   dplyr::pick(Human) |> unlist())[[1]], 
                                    error=function(err) NA),
                  KSpval = tryCatch(stats::ks.test(dplyr::pick(AI) |> unlist(),
                                                   dplyr::pick(Human) |> unlist())[[2]], 
                                    error=function(err) NA)) |>
    dplyr::ungroup() |>
    dplyr::select(-Human,-AI)
  
  ks_test <- ks_test |>
    dplyr::mutate(
      pval_10 = ifelse(KSpval<=0.1,1,0),
      pval_5 = ifelse(KSpval<=0.05,1,0),
      pval_1 = ifelse(KSpval<=0.01,1,0),
      stars = pval_10 + pval_5 + pval_1
    )

  
  # For each quarter
  ks_test <- data_long |> 
    dplyr::filter(id %in% horizons$id, type %in% survey_names[1]) |>
    dplyr::select(date_q,id,variable,value,type) |>
    dplyr::bind_rows(SPFmicrodata_long |> 
                       dplyr::select(date_q,id,variable,value) |>
                       dplyr::mutate(type = "Human")) |>
    tidyr::pivot_wider(names_from = type, values_from = value, values_fn = list) |> 
    dplyr::group_by(id,variable,date_q) |>
    dplyr::mutate(KSstat = tryCatch(stats::ks.test(dplyr::pick(AI) |> unlist(),
                                          dplyr::pick(Human) |> unlist())[[1]], 
                                    error=function(err) NA),
                  KSpval = tryCatch(stats::ks.test(dplyr::pick(AI) |> unlist(),
                                                   dplyr::pick(Human) |> unlist())[[2]], 
                                    error=function(err) NA)) |>
    dplyr::ungroup() |>
    dplyr::select(-Human,-AI)
  
  
  
  pdf("multiple_plots.pdf", width = 8, height = 6)  # Specify filename and dimensions
  
  for (var in variables$variable) {
    plot1 <- ggplot2::ggplot(data = ks_test |> dplyr::filter(variable %in% var, id %in% 0),
                    ggplot2::aes(x=date_q,y=KSpval)) +
      ggplot2::geom_point() +
      ggplot2::ggtitle(var)
  
    print(plot1)  
  }
  
  dev.off()
   
  
  ks_test <- ks_test |>
    dplyr::mutate(
      pval_10 = ifelse(KSpval<=0.1,1,0),
      pval_5 = ifelse(KSpval<=0.05,1,0),
      pval_1 = ifelse(KSpval<=0.01,1,0),
      stars = pval_10 + pval_5 + pval_1
    )
  
  
  
  
  
  var = "TBILL"
  hor = 0
  quar = "1999-01-01"
  x <- data_long |> dplyr::filter(variable %in% var,
                                  id %in% hor,
                                  date_q %in% quar,
                                  type %in% "AI") |>
    dplyr::pull(value)
  
  y <- data_long |> dplyr::filter(variable %in% var,
                                  id %in% hor,
                                  date_q %in% quar,
                                  type %in% "Human") |>
    dplyr::pull(value)
  stats::ks.test(x,
                 y)
  
  ggplot2::ggplot()
  
  
  
    
  
  ttest$stars <- gsub("1","star1",ttest$stars)
  ttest$stars <- gsub("2","star2",ttest$stars)
  ttest$stars <- gsub("3","star3",ttest$stars)
  ttest$stars <- gsub("0"," ",ttest$stars)
  
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
           " & \\multicolumn{4}{c}{Mean absolute percentage error} && \\multicolumn{4}{c}{t-test statistics} \\\\",
           " \\cmidrule{2-5} \\cmidrule{7-10}",
           paste("Horizon (quarter) &", paste(horizons$id,collapse ="&"),"&&",paste(horizons$id,collapse ="&"),"\\\\"),
           tbl[4:length(tbl)])
  #tbl <- boldface_table(tbl, num_digits=c(2,2))
  tbl <- insert_sections(tbl)
  tbl <- gsub("star3","^{\\\\star\\\\star}",tbl)
  tbl <- gsub("star2","^{\\\\star}",tbl)
  tbl <- gsub("star1","",tbl)
  
  writeLines(tbl,filename)
}