
tab_regress_ai_spf <- function() {
  
  filename = 'tables/regress_ai_spf.txt'
  
  mdl_list <- list()
  wald_list <- list()
  
  for (ii in 1:dim(horizons)[1]) {
    
    mdl_list[[ii]] <- lm(
      formula = get(survey_names[2]) ~ get(survey_names[1]),
      data = data_all_individuals_match)
    
    wald_list[[ii]] <- car::linearHypothesis(mdl_list[[ii]], 
                                             c("(Intercept) = 0",
                                               'get(survey_names[1]) = 1'),
                                             test="Chisq")
    
  }
  
  modelsummary::msummary(mdl_list,
                         stars=TRUE,
                         gof_map = gof_map,
                         coef_map = c('(Intercept)' = 'Intercept',
                                      'get(horizons[ii, "id_ai"])' = 'Coefficient'),
                         output = gsub('txt','tex',filename),
                         fmt = 2)
  
  # Format table
  tbl <- read.delim(gsub('txt','tex',filename))
  tbl <- tbl[3:dim(tbl)[1]-1,1]
  idx <- which(grepl("\\toprule",tbl,fixed=T))
  num_col <- stringr::str_count(tbl[length(tbl)-3],"&")+1
  tbl <- tbl[idx:(length(tbl)-1)]
  tbl <- c(tbl[1:2], 
           paste('&',paste(paste0('\\multicolumn{1}{c}{',horizons$label,'}'), collapse=' & '),'\\\\ \\midrule'), 
           tbl[3:length(tbl)])
  tbl <- gsub("*** ","^{***} ",tbl,fixed=T)
  tbl <- gsub("** ","^{**} ",tbl,fixed=T)
  tbl <- gsub("* ","^{*} ",tbl,fixed=T)
  tbl <- gsub("+ ","^{+} ",tbl,fixed=T)
  tbl <- c(paste0("\\begin{tabular}{l",paste(replicate(num_col-1, "d{1.2}"), collapse = ""),"}"),
           tbl,
           paste0("\\multicolumn{",num_col,"}{r}{\\rule{0pt}{1em}+ p < 0.1, * p < 0.05, ** p < 0.01, *** p < 0.001}"),
           "\\end{tabular}")
  
  idx.NumObs <- which(grepl("Num.Obs.",tbl,fixed=T))
  row.NumObs <- strsplit(tbl[idx.NumObs]," ") |> unlist()
  NumObs <- strtoi(row.NumObs) 
  row.NumObs[!(is.na(NumObs))] <- paste0('\\multicolumn{1}{c}{',NumObs |> na.omit(),'}')
  tbl[idx.NumObs] <- paste(row.NumObs, collapse=' ')
  tbl <- c(tbl[1:idx.NumObs-1],"\\midrule",tbl[idx.NumObs:length(tbl)])
  
  idx.R2 <- which(grepl("R2",tbl,fixed=T))
  row.R2 <- strsplit(tbl[idx.R2]," ") |> unlist()
  R2 <- R2 <- as.double(row.R2)
  row.R2[!(is.na(R2))] <- paste0(round(na.omit(R2),2))
  tbl[idx.R2] <- paste(row.R2, collapse=' ')
  
  # Appendix test coefficients?
  #wald_list
  
  # Save table and remove temp tex file
  write(tbl,file=filename)
  file.remove(gsub('txt','tex',filename))
  
}