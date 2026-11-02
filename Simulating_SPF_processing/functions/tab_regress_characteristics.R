
tab_regress_characteristics <- function() {
  
  variables_select = c("CPI","TBILL","RGDP","UNEMP")
  
  for (ii in horizons$id) {
  
    for (kk in c(characteristics,"all_characteristics")) {
      
      filename = paste0('tables/regress_',kk,'_',ii,'.txt')
    
      if (kk %in% "all_characteristics") {
        kk <- characteristics  
      }
      
      mdl_list <- list()
      
      for (jj in variables_select) {  
        
        tmp <- data_long |>
          dplyr::filter(variable %in% jj,
                        id %in% ii,
                        type %in% "AI") |>
          dplyr::select(date_q,Name,value,all_of(kk)) |>
          dplyr::left_join(data_long |> 
                             dplyr::filter(id %in% ii,
                                           variable %in% jj,
                                           type %in% "Realized") |>
                             dplyr::select(date_q,value) |>
                             dplyr::rename("Realized" = "value") |>
                             unique(),
                           by="date_q") |>
          dplyr::mutate(forecast_error = abs((value-Realized)/Realized),
                        forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
          na.omit() |>
          unique()

          
          fml <- paste0("forecast_error ~ ",paste0("factor(",kk,")",collapse=" + "))
          
          mdl_list[[variables$variable_longname[variables$variable==jj]]] <- plm::plm(
            formula = fml,
            effect = "time",
            model = "pooling",
            data = tmp,
            cluster = "time")
      }
      
      modelsummary::msummary(mdl_list,
                             stars=TRUE,
                             gof_map = gof_map,
                             output = gsub('txt','tex',filename),
                             fmt = 2)
      
      # Format table
      tbl <- read.delim(gsub('txt','tex',filename))
      tbl <- tbl[3:dim(tbl)[1]-1,1]
      idx <- which(grepl("\\toprule",tbl,fixed=TRUE))
      num_col <- stringr::str_count(tbl[length(tbl)-3],"&")+1
      tbl <- tbl[idx:(length(tbl)-1)]
      tbl <- gsub("*** ","^{***} ",tbl,fixed=TRUE)
      tbl <- gsub("** ","^{**} ",tbl,fixed=TRUE)
      tbl <- gsub("* ","^{*} ",tbl,fixed=TRUE)
      tbl <- gsub(" + "," plus ",tbl,fixed=TRUE)
      tbl <- gsub("+ ","^{+} ",tbl,fixed=TRUE)
      tbl <- gsub(" plus "," + ",tbl,fixed=TRUE)
      tbl <- gsub('(Intercept)','Intercept',tbl,fixed=TRUE)
      for (ll in 1:length(kk)) {
        tbl <- gsub(paste0("factor(",gsub("_","\\_",kk[ll],fixed=TRUE),")"),"",tbl,fixed=TRUE)  
      }
      
      tbl <- c(paste0("\\begin{tabular}{l",paste(replicate(num_col-1, "d{1.2}"), collapse = ""),"}"),
               tbl,
               paste0("\\multicolumn{",num_col,"}{r}{\\rule{0pt}{1em}+ p < 0.1, * p < 0.05, ** p < 0.01, *** p < 0.001}"),
               "\\end{tabular}")
      
      idx.NumObs <- which(grepl("Num.Obs.",tbl,fixed=TRUE))
      row.NumObs <- strsplit(tbl[idx.NumObs]," ") |> unlist()
      NumObs <- strtoi(row.NumObs) 
      row.NumObs[!(is.na(NumObs))] <- paste0('\\multicolumn{1}{c}{',NumObs |> na.omit(),'}')
      tbl[idx.NumObs] <- paste(row.NumObs, collapse=' ')
      tbl <- c(tbl[1:idx.NumObs-1],"\\midrule",tbl[idx.NumObs:length(tbl)])
      
      idx.R2 <- which(grepl("R2",tbl,fixed=T))
      row.R2 <- strsplit(tbl[idx.R2]," ") |> unlist()
      R2 <- as.double(row.R2)
      row.R2[!(is.na(R2))] <- paste0(sprintf("%.2f",na.omit(R2)))
      tbl[idx.R2] <- paste(row.R2, collapse=' ')
      
      idx.NumObs <- which(grepl("Num.Obs.",tbl,fixed=TRUE))
      tbl <- c(tbl[1:idx.NumObs-1],
               paste('Time FE &',paste(rep("\\multicolumn{1}{c}{Y}",num_col-1),collapse="&"),"\\\\"),
               tbl[idx.NumObs:length(tbl)])
      
      tbl[3] <- paste('&',
                      paste(paste0('\\multicolumn{1}{c}{',
                                   gsub("\\\\ \\midrule %% TinyTableHeader","",
                                        sapply(stringr::str_split(tbl[3]," & "),
                                               function(x) {gsub("& ","",x)}),
                                        fixed=TRUE),'}'), 
                            collapse=' & '),'\\\\ \\midrule')
      
      
      # Save table and remove temp tex file
      write(tbl,file=filename)
      file.remove(gsub('txt','tex',filename))
      

    }
  }
}
