
#' compare_columns is an optional argument containing a list of column numbers
#' that are compared for boldfacing. Each entry in the list indicates a separate
#' set for comparison. If FALSE, the function defined this based on "cmidrule"
#' if it exists in "tbl" and among all columns otherwise.
#' 
#' 'test' is a data frame with same number of columns and rows as tbl. Its 
#' content has pvalue and 'star0'/'star1'/'star2'/'star3' indicating the 
#' significance of each of the elements of the table

add_stars <- function(tbl,test, 
                      main_matter_start_row = FALSE,
                      main_matter_end_row = FALSE) {
  
  if (main_matter_start_row == FALSE) {
    idx <- which(grepl("\\midrule",tbl,fixed=TRUE))
    main_matter_start_row <- idx[length(idx)] + 1
  }
  
  if (main_matter_end_row == FALSE) {
    main_matter_end_row <- which(grepl("\\bottomrule",tbl,fixed=TRUE)) - 1
  }
  
  tbl_main <- tbl[main_matter_start_row:main_matter_end_row]
  tbl_main_split <- stringr::str_split(tbl_main, pattern = " & ") 
  
  tbl_main_star <- tbl_main
  idx_empty <- which(tbl_main_split[[1]]=='')
  if (length(idx_empty)==1) {
    idx_content <- c(2:(idx_empty-1),(idx_empty+1):length(tbl_main_split[[1]]))  
  } else if (length(idx_empty)==2) {
    idx_content = c(2:(idx_empty[1]-1),(idx_empty[1]+1):(idx_empty[2]-1),(idx_empty[2]+1):length(tbl_main_split[[1]]))
  } else if (length(idx_empty)==3) {
    idx_content = c(2:(idx_empty[1]-1),(idx_empty[1]+1):(idx_empty[2]-1),(idx_empty[2]+1):(idx_empty[3]-1),(idx_empty[3]+1):length(tbl_main_split[[1]]))
  } else {
    stop('add_stars() is only coded for up to 4 sets of columns.')
  }
  
  for (ii in 1:length(tbl_main_split)) {
    
    tbl_main_split_row_ii <- tbl_main_split[[ii]]
    tbl_main_split_row_ii[length(tbl_main_split_row_ii)] <- substr(tbl_main_split_row_ii[length(tbl_main_split_row_ii)],1,nchar(tbl_main_split_row_ii[length(tbl_main_split_row_ii)])-3) 
    
    for (jj in idx_content) {
      
      if (grepl('}',tbl_main_split_row_ii[jj])) {
        
        tbl_main_split_row_ii[jj] <- paste0(substr(tbl_main_split_row_ii[jj],1,nchar(tbl_main_split_row_ii[jj])-1),
                                            substr(tests[ii,jj],nchar(tests[ii,jj])-4,nchar(tests[ii,jj])),
                                            '}')
        
      } else {
        
        tbl_main_split_row_ii[jj] <- paste0(tbl_main_split_row_ii[jj],
                                            substr(tests[ii,jj],nchar(tests[ii,jj])-4,nchar(tests[ii,jj])))
        
      }   
      
    }
    
    tbl_main_star[ii] <- paste(paste(tbl_main_split_row_ii, collapse = " & "),"\\\\")
    
  }
  
  
  tbl[main_matter_start_row:main_matter_end_row] <- tbl_main_star
  
  tbl <- gsub("star3","^{\\\\star\\\\star\\\\star}",tbl)
  tbl <- gsub("star2","^{\\\\star\\\\star}",tbl)
  tbl <- gsub("star1","^{\\\\star}",tbl)
  tbl <- gsub("star0","",tbl)
  
  tbl
  
  
    
}
