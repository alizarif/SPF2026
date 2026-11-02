
fig_boxplots <- function() {
  
  p <- ggplot2::ggplot(data = data_long_all_individual |> 
                         dplyr::mutate(is_annual = 
                                         ifelse(is.na(as.numeric(data_long_all_individual$id)),
                                                T,F)) |>
                         dplyr::filter(id %in% horizons$id) |>
                         dplyr::mutate(id = paste(id)), 
                       ggplot2::aes(x=id, y=forecast, fill=id)) +
    ggplot2::geom_boxplot(show.legend = F,
                          outliers = F,
                          alpha=0.9)  + 
    ggplot2::scale_y_continuous(labels = function(x) paste0(x, "%")) +
    ggplot2::scale_x_discrete(labels = horizons$label,
                              guide = ggplot2::guide_axis(angle=45)) +
    ggplot2::scale_fill_brewer(palette="Accent") +
    ggplot2::theme(axis.title = ggplot2::element_blank(),
                   panel.grid.major = ggplot2::element_blank(), 
                   panel.grid.minor = ggplot2::element_blank()) +
    ggplot2::facet_wrap(~type) 
  
  pdf(paste0("figures/boxplots.pdf"), width=w, height=h)
  print(p)
  dev.off()
  
}