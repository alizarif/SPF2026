
tab_rand_test_moments_generic <- function() {
  
  load(file = "data/generic_N_forecaster_data.rda")
  
  filename_raw = 'tables/test_moments_ai_against_spf_generic.txt'
  
  times_w_human_forecasts <- data_long |>
    dplyr::filter(id %in% horizons$id,
                  type %in% survey_names[2]) |>
    dplyr::mutate(date_q_ = !(is.na(value))) |>
    dplyr::select(id,variable,date_q,date_q_)
    
  # Pooling across time
  data_all <- data_long |> 
    dplyr::filter(id %in% horizons$id, type %in% survey_names[1]) |>
    dplyr::select(id,variable,value,type,date_q) |>
    dplyr::left_join(times_w_human_forecasts, by=c("id","variable","date_q"), relationship = "many-to-many") |>
    dplyr::filter(date_q_==T) |> 
    dplyr::select(-c(date_q_,date_q)) |>
    dplyr::bind_rows(SPFmicrodata_long |> 
                       dplyr::filter(id %in% horizons$id) |>
                       dplyr::select(id,variable,value) |>
                       dplyr::mutate(type = "Human")) 
  
  compute_moment_diff <- function(data_all) {
    data_all |> 
      dplyr::group_by(id,variable,type) |>
      dplyr::summarize(Skewness = e1071::skewness(value, na.rm=TRUE),
                       Kurtosis = e1071::kurtosis(value, na.rm=TRUE),
                       Median = median(value, na.rm=TRUE),
                       P25 = quantile(value, 0.25, na.rm=TRUE),
                       P75 = quantile(value, 0.75, na.rm=TRUE),
                       SD = sd(value, na.rm=TRUE),
                       Mean = mean(value, na.rm=TRUE)) |>
      dplyr::ungroup() |>
      tidyr::pivot_wider(names_from = type, values_from = c(Skewness,Kurtosis,Median,P25,P75,SD,Mean)) |> 
      dplyr::mutate(Skewness = Skewness_AI-Skewness_Human,
                    Kurtosis = Kurtosis_AI-Kurtosis_Human,
                    Median = Median_AI-Median_Human,
                    P25 = P25_AI-P25_Human,
                    P75 = P75_AI-P75_Human,
                    SD = SD_AI-SD_Human,
                    Mean = Mean_AI-Mean_Human) |>
      dplyr::select(id,variable,Median,P25,P75,Mean,SD,Skewness,Kurtosis)
  }
  
  diff_obs <- compute_moment_diff(data_all)
  
  diff_sim = replicate(n = 10000, 
                       expr = {
                         data_sim <- data_all |>
                           dplyr::mutate(type = sample(c("AI","Human"),
                                                       dim(data_all)[1],
                                                       replace=TRUE))
                         
                          skew_diff_obs <- compute_moment_diff(data_sim)})
  

  # Compute p-values
  # H0: Skewness are the same for AI and Human (skew_diff = 0)
  
  moments <- c("Median","P25","P75","Mean","SD","Skewness","Kurtosis")
  
  pval <- lapply(moments, function(x) {
    rowMeans(abs(do.call(cbind.data.frame, diff_sim[x,]))>=abs(diff_obs |> dplyr::pull(x)),na.rm=TRUE)})
  pval <- do.call(cbind.data.frame,pval)
  
  pval <- cbind(diff_obs$id,diff_obs$variable,pval)
  names(pval) = c("id","variable",moments)
  
  stars <- pval |>
    unique() |>
    tidyr::pivot_longer(cols=all_of(moments),names_to="moment",values_to="pval") |>
    dplyr::left_join(diff_obs |> 
                       tidyr::pivot_longer(moments,
                                           names_to = 'moment', 
                                           values_to = 'diff'), 
                     by=c('id','variable','moment')) |>
    dplyr::mutate(
      pval_10 = ifelse(pval<=0.1,1,0),
      pval_5 = ifelse(pval<=0.05,1,0),
      pval_1 = ifelse(pval<=0.01,1,0),
      stars = pval_10 + pval_5 + pval_1,
      stars = gsub("1","star1",stars),
      stars = gsub("2","star2",stars),
      stars = gsub("3","star3",stars),
      stars = gsub("0","star0",stars),
      diff = paste0(sprintf("%.2f", diff),stars)
    ) |>
    dplyr::select(id,variable,diff,moment) |>
    tidyr::pivot_wider(names_from="moment", values_from="diff") |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select(id,variable_longname,moments) #|>
    #dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield"))
  
  # Create table with designated filename
  for (ii in horizons$id) {
    
    filename = paste0(gsub('.txt','',filename_raw),'_',ii,'.txt')
    
    tmp <- stars |> dplyr::filter(id %in% ii) |> dplyr::select(-id)
    tmp <- tmp[match(variables$variable_longname,tmp$variable_longname),]
    
    writeLines(knitr::kable(tmp, "latex", 
                            digits=2, 
                            align = c('l','l',rep('d{3.5}',length(moments))), 
                            booktabs=T),
               filename)
    
    tbl <- readLines(filename)
    tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
    tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
    
    tmp <- stringr::str_split(stringr::str_split(tbl[3],'&')[[1]],'\\\\') |> unlist()
    tbl[3] <- paste('&',paste(paste0('\\multicolumn{1}{c}{',tmp[3:(length(tmp)-2)],'}'),collapse = " & "),'\\\\')
    tbl <- insert_sections(tbl)
    tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
    tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
    tbl <- gsub("star1","^{\\\\star}",tbl)
    tbl <- gsub("star0","",tbl)
    
    writeLines(tbl,filename)
    
  }
  
  
  
  
}