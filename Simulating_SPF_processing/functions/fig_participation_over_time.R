
fig_participation_over_time <- function() {
  
  data_summary <- data_wide |> 
    dplyr::group_by(Name) |>
    dplyr::summarise(duration = dplyr::n(),
                     start = as.numeric(dplyr::first(date_q))) |>
    dplyr::ungroup()
  
  data_summary <- data_summary[order(-data_summary$start,-data_summary$duration),] 
  
  tmp <- data_wide |>
    dplyr::left_join(data_summary,by = "Name") |>
    dplyr::mutate(duration_years = duration/4,
                  Name = factor(Name,levels=data_summary$Name),
                  value = 1) 
  
  p <- ggplot2::ggplot(tmp, 
                       ggplot2::aes(date_q, Name, fill= duration_years)) + 
    ggplot2::geom_tile(color = "white") +
    ggplot2::scale_fill_gradient2(high="darkblue",mid="red",low="white", midpoint=1) +
    ggplot2::theme_light(base_size = 10) +
    ggplot2::theme(axis.text.y = ggplot2::element_blank(),
                   axis.title.x = ggplot2::element_blank(),
                   panel.grid.major = ggplot2::element_blank(), 
                   panel.grid.minor = ggplot2::element_blank(),
                   legend.position="bottom",
                   legend.title = ggplot2::element_blank()) +
    ggplot2::ylab("Individual forecasters")
  
  pdf(paste0("figures/participation_over_time.pdf"), 
      width=w, height=h*1.75)
  print(p)
  dev.off()
  
}