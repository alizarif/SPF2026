
tab_descriptive_stats <- function() {
  
  filename = 'tables/descriptive_stats.txt'
  
  sum_stat <- data_long |>
    dplyr::filter(type %in% "Realized",
                  id %in% 0) |>
    dplyr::select(date_q,value,variable_name) |>
    dplyr::group_by(variable_name) |>
    dplyr::mutate(scale = any(value>=1000),
                  value = ifelse(scale,value/1000,value),
                  variable_name = ifelse(scale,paste0(variable_name," (x1000)"),variable_name)) |>
    dplyr::summarize(n = dplyr::n(),
                     mean = mean(value),
                     sd = sd(value),
                     skew = e1071::skewness(value),
                     kurt = e1071::kurtosis(value),
                     median = median(value),
                     min = min(value),
                     max = max(value),
                     rho = acf(value,1,plot=F)[[1]][2]
                     ) |>
    dplyr::ungroup()
  
  sum_stat <- sum_stat[match(variables$variable_longname,gsub(" \\(x1000\\)","",sum_stat$variable_name)),]
  
  # Create table with designated filename
  writeLines(knitr::kable(sum_stat, "latex", 
                          digits=2, 
                          align = c('l',rep('d{2.2}',(dim(sum_stat)[2]-1))), 
                          booktabs=T),
             filename)
  
  tbl <- readLines(filename)
  tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
  tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
  tbl[3] <- "& \\multicolumn{1}{c}{N} & \\multicolumn{1}{c}{Mean} & \\multicolumn{1}{c}{SD}
             & \\multicolumn{1}{c}{Skewness} & \\multicolumn{1}{c}{Kurtosis} & \\multicolumn{1}{c}{Median}
             & \\multicolumn{1}{c}{Min} & \\multicolumn{1}{c}{Max} & \\multicolumn{1}{c}{ACF(1)}\\\\"
  tbl <- insert_sections(tbl)
  
  writeLines(tbl,filename)
}