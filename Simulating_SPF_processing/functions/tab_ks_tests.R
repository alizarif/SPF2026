
tab_ks_tests <- function() {
  
  for (ii in horizons$id) {
    
    data_long_ii <- data_long_all_individual |> dplyr::filter(id %in% ii)
    
    stats::ks.test(data_long_ii |> 
                     dplyr::filter(type %in% survey_names[1]) |>
                     dplyr::pull(forecast),
                   data_long_ii |> 
                     dplyr::filter(type %in% survey_names[2]) |>
                     dplyr::pull(forecast))  
  }
  
}