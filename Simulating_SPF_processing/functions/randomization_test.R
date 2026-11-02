
randomization_test <- function(df, null_hypothesis,num_sim=10000) {
  
  if (length(unique(df[1:(dim(df)[1]/2),"type"]))>1) {
    stop("In randomization_test, df must be sorted by type.")  
  }
  
  diff_obs <- null_hypothesis(df)
  
  types <- unique(df$type)
  
  diff_sim = replicate(n = num_sim, 
                       expr = {
                         
                         sampled_types <- sample(types,dim(df)[1]/2,replace=TRUE)
                         sampled_types_inverse <- ifelse(sampled_types=="AI","Human","AI")
                         
                         data_sim <- df |>
                           dplyr::mutate(type = c(sampled_types,sampled_types_inverse))
                           
                         diff <- null_hypothesis(data_sim)})
  
  # Compute p-values
  moments <- names(diff_obs)[dim(diff_obs)[2]]
  
  pval <- lapply(moments, function(x) {
    rowMeans(abs(do.call(cbind.data.frame, diff_sim[x,]))>=abs(diff_obs |> dplyr::pull(x)),na.rm=TRUE)})
  pval <- do.call(cbind.data.frame,pval)
  pval <- cbind(diff_obs |> dplyr::select(-moments) ,pval)
  names(pval) = names(diff_obs)
  
  stars <- pval |>
    unique() |>
    tidyr::pivot_longer(cols=all_of(moments),names_to="moment",values_to="pval") |>
    dplyr::mutate(
      pval_10 = ifelse(pval<=0.1,1,0),
      pval_5 = ifelse(pval<=0.05,1,0),
      pval_1 = ifelse(pval<=0.01,1,0),
      stars = pval_10 + pval_5 + pval_1,
      stars = gsub("1","star1",stars),
      stars = gsub("2","star2",stars),
      stars = gsub("3","star3",stars),
      stars = gsub("0","star0",stars),
      pval = paste0(sprintf("%.2f", pval),stars)
    ) |>
    dplyr::select(names(diff_obs)[1:(dim(diff_obs)[2]-1)],moment,pval) |>
    tidyr::pivot_wider(names_from="moment", values_from="pval") |>
    dplyr::left_join(variables |> dplyr::select(variable,variable_longname), 
                     by=c("variable"="variable")) |>
    dplyr::select(id,variable_longname,moments) #|>
    #dplyr::filter(!(variable_longname %in% "BAA Corp Bond Yield"))
  
  return(stars)
}