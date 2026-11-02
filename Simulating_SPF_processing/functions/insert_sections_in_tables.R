
insert_sections <- function(tbl) {
 
  idx_1 <- which(grepl("Nominal GDP",tbl))
  
  num_col <- length(strsplit(tbl[idx_1],'&')[[1]])-1
  
  tbl <- c(tbl[1:(idx_1-1)], 
           paste0("\\multicolumn{",num_col,"}{l}{Section 1: US Business Indicators}\\\\"), 
           "\\midrule",
           tbl[idx_1:length(tbl)])
  
  idx_2 <- which(grepl("Real GDP",tbl))
  
  tbl <- c(tbl[1:(idx_2-1)],
           "\\midrule",
           paste0("\\multicolumn{",num_col,"}{l}{Section 2: Real GDP and Its Components}\\\\"), 
           "\\midrule",
           tbl[idx_2:length(tbl)])
  
  idx_3 <- min(which(grepl("CPI Inflation Rate",tbl)))
  
  tbl <- c(tbl[1:(idx_3-1)],
           "\\midrule",
           paste0("\\multicolumn{",num_col,"}{l}{Section 3: CPI and PCE Inflation}\\\\"), 
           "\\midrule",
           tbl[idx_3:length(tbl)])
  
  idx_4 <- min(which(grepl("Average",tbl)))
  
  if (idx_4<Inf) { # If the 'average' row exists
    tbl <- c(tbl[1:(idx_4-1)],
             "\\midrule",
             tbl[idx_4:length(tbl)])
    
  }
  
  
  tbl
    
}
