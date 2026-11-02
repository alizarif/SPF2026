
#' compare_columns is an optional argument containing a list of column numbers
#' that are compared for boldfacing. Each entry in the list indicates a separate
#' set for comparison. If FALSE, the function defined this based on "cmidrule"
#' if it exists in "tbl" and among all columns otherwise.
#' 
#' boldface_min is an optional argument taking value TRUE if minimum values 
#' among compared columns are boldfaced. If FALSE, the function boldfaces max 
#' values.
#' 
#' boldface_threshold is an optional argument taking value TRUE if values 
#' exceeding some threshold specified by the argument ''threshold'' are 
#' boldfaced. boldface_min and boldface_threshold cannot both be true.
#'  
#' main_matter_start_row and main_matter_end_row are optional arguments
#' indicating where the main parts of the table to which boldfacing should be
#' applied starts and ends. If not provided, the function will find the main
#' part based on the locations of "midrule" and "bottomrule".

boldface_table <- function(tbl,
                           compare_columns=FALSE,
                           boldface_min=TRUE,
                           boldface_threshold = FALSE,
                           threshold = NULL,
                           main_matter_start_row=FALSE,
                           main_matter_end_row=FALSE,
                           num_digits=c(2,2)
                           ) {
  
  if (boldface_min == TRUE & boldface_threshold == TRUE) {
    stop("boldface_min and boldface_threshold cannot both be specified as TRUE!")  
  }
  
  if (main_matter_start_row == FALSE) {
    idx <- which(grepl("\\midrule",tbl,fixed=TRUE))
    main_matter_start_row <- idx[length(idx)] + 1
  }
  
  if (main_matter_end_row == FALSE) {
    main_matter_end_row <- which(grepl("\\bottomrule",tbl,fixed=TRUE)) - 1
  }
  
  tbl_main <- tbl[main_matter_start_row:main_matter_end_row]
  tbl_main_split <- stringr::str_split(tbl_main, pattern = " & ") 

  if (any(is.na(compare_columns))) {
    
    idx <- which(grepl("\\cmidrule",tbl,fixed=TRUE)) 
    
    if (any(idx)) {
      
      tmp <- as.numeric(stringr::str_split((gsub("\\D", ",", tbl[idx])),",")[[1]]) |> na.omit()
      compare_columns = list()
      for (ll in 1:(length(tmp)/2)) {
        compare_columns[[ll]] <- c(tmp[(ll*2-1)]:tmp[ll*2])
      }
      
    } else {
      
      # Compare all columns
      compare_columns = list(1:(length(tbl_main_split[[1]])-1))
    }
  }
  
  compare_function <- ifelse(boldface_threshold==TRUE,
                             function(x) (x-threshold),
                             ifelse(boldface_min==TRUE,
                             function(x) min(x), 
                             function(x) max(x)))
  
  tbl_main_bf <- tbl_main
  
  for (ii in 1:length(tbl_main_split)) {
    
    tbl_main_split_row_ii <- tbl_main_split[[ii]]
    tbl_main_split_row_ii[length(tbl_main_split_row_ii)] <- gsub("\\\\","",tbl_main_split_row_ii[length(tbl_main_split_row_ii)])
    
    if (boldface_threshold == TRUE) {
      
      for (jj in which(!is.na(as.numeric(tbl_main_split_row_ii)))) {
        
        if (compare_function(as.numeric(tbl_main_split_row_ii[jj]))>=0) {
          tbl_main_split_row_ii[jj] <- paste0("\\multicolumn{1}{B{.}{.}{",num_digits[1],",",num_digits[2],"}}{",sprintf(paste0("%.",num_digits[2],"f"), as.numeric(tbl_main_split_row_ii[jj])),"}")
        }

      }
      
    } else {
      
      for (jj in compare_columns) {
        
        compared_numbers <- as.numeric(tbl_main_split_row_ii[jj])
        
        if (!(any(is.na(compared_numbers)))) {
          idx_bf <- which(compared_numbers == compare_function(compared_numbers))
          idx_nonbf <- which(!(compared_numbers == compared_numbers[idx_bf]))
          compared_numbers[idx_bf] = paste0("\\multicolumn{1}{B{.}{.}{",num_digits[1],",",num_digits[2],"}}{",sprintf(paste0("%.",num_digits[2],"f"), compared_numbers[idx_bf]),"}")
          compared_numbers[idx_nonbf] = paste0(sprintf(paste0("%.",num_digits[2],"f"), as.numeric(compared_numbers[idx_nonbf])))
          tbl_main_split_row_ii[jj] <- compared_numbers
        }
        
      }
      
    }
    
    tbl_main_bf[ii] <- paste(paste(tbl_main_split_row_ii, collapse = " & "),"\\\\")
    
  }
  
  
  tbl[main_matter_start_row:main_matter_end_row] <- tbl_main_bf
  
  tbl
    
}
