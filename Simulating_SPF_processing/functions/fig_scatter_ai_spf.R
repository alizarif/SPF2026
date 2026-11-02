
fig_scatter_ai_spf <- function() {
  
  # Match individual forecasts by lowest forecast error
  data_long_all_individual$forecast_error <- err(data_long_all_individual |> 
                                                   dplyr::select(forecast,realized))
  
  data_all_individuals_match <- data_long_all_individual |>
    dplyr::left_join(number_forecasters |> 
                       dplyr::select(-type_ordered) |>
                       tidyr::pivot_wider(names_from=type,
                                          values_from=n) |>
                       dplyr::rename_with(~c("n_AI","n_Human"),survey_names), 
                     by=c("date_q","id")) |>
    dplyr::mutate(n = pmin(n_AI,n_Human)) |>
    dplyr::group_by(date_q,type,id) |>
    dplyr::arrange(abs(forecast_error)) |>
    dplyr::slice(1:n) |>
    dplyr::mutate(idx = 1:n) |>
    dplyr::ungroup() |>
    dplyr::select(-c(id_forecast,n,n_AI,n_Human,id_realized,forecast_error)) |>
    tidyr::pivot_wider(names_from = type, values_from = forecast)
  
  ii=3
  p <- ggplot2::ggplot(data_all_individuals_match) +
    ggplot2::geom_point(ggplot2::aes(x=get(survey_names[2]),
                                     y=get(survey_names[1]))) +
    ggplot2::geom_abline(intercept = 0, slope = 1)
  
  pdf(paste0("figures/scatter_ai_spf_",horizons[ii,"id"],".pdf"), width=w, height=h)
  print(p)
  dev.off()
  
}