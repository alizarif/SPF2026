
fig_num_forecasters_over_time <- function(filename = "figures/num_forecasters_over_time.pdf") {
  
  number_forecasters <- data_long |> 
    dplyr::filter(type %in% survey_names[1]) |>
    dplyr::group_by(date_q,variable,id) |>
    dplyr::summarise(n = dplyr::n()) |>
    dplyr::ungroup() |>
    dplyr::group_by(date_q) |>
    dplyr::summarise(n = mean(n)) |>
    dplyr::ungroup() |>
    dplyr::left_join(
      SPFmicrodata_long |> 
        dplyr::group_by(date_q,variable,id) |>
        dplyr::summarise(n_SPF = dplyr::n()) |>
        dplyr::ungroup() |>
        dplyr::group_by(date_q) |>
        dplyr::summarise(n_SPF = mean(n_SPF)) |>
        dplyr::ungroup()
    ) |>
    dplyr::rename_with(~survey_names,c(n,n_SPF)) |>
    tidyr::pivot_longer(all_of(survey_names),
                        names_to = "type", 
                        values_to = "n") |>
    dplyr::mutate(type_ordered = factor(type, 
                                        levels=c(survey_names[2],
                                                 survey_names[1])))
  
  p <- ggplot2::ggplot(data = number_forecasters,
                       mapping = ggplot2::aes(x=date_q, y=n)) +
    ggplot2::geom_line(ggplot2::aes(color=type_ordered, 
                                    size=type_ordered)) +
    ggplot2::scale_color_manual(values=c("darkgray", "black")) +
    ggplot2::scale_size_manual(values=c(1.4,0.5)) +
    ggplot2::scale_y_continuous(breaks = seq(00,70,10), limits = c(0,70)) +
    ggplot2::theme_light(base_size = 10) +
    ggplot2::theme(axis.title = ggplot2::element_blank(),
                   panel.grid.major = ggplot2::element_blank(), 
                   panel.grid.minor = ggplot2::element_blank(),
                   legend.position="none") 
  
  pdf(filename, 
      width=w, height=h)
  print(p)
  dev.off()
  
}
