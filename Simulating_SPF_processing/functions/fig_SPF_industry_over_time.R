
fig_SPF_industry_over_time <- function() {
  
  colors <- RColorBrewer::brewer.pal(8, 'Set2')
  colors <- colors[1:length(SPFmicrodata_long$SPF_industry_id |> unique())]
  colors[length(SPFmicrodata_long$SPF_industry_id |> unique())] <- "#BEBEBE"
  
  p <- ggplot2::ggplot(data = SPFmicrodata_long |> 
                         dplyr::select(date_q,SPF_human_id,SPF_industry_id) |>
                         unique() |>
                         dplyr::group_by(date_q,SPF_industry_id) |>
                         dplyr::summarise(n = dplyr::n()) |>
                         dplyr::ungroup(), 
                       mapping = ggplot2::aes(date_q, n, fill=SPF_industry_id)) +
    ggstream::geom_stream(type="proportional") +
    ggplot2::labs(x = "",
                  y = "",
                  fill = "") +
    ggplot2::scale_fill_manual(values = colors) +
    ggplot2::theme_minimal(base_size = 10) +
    ggplot2::theme(legend.position = "bottom",
                   legend.justification = "center",
                   legend.text = ggplot2::element_text(size=6),
                   legend.key.height = ggplot2::unit(2, 'mm'),
                   legend.key.width = ggplot2::unit(2, 'mm'))
  
  pdf(paste0("figures/SPF_industry_over_time.pdf"), 
      width=w, height=h)
  print(p)
  dev.off()
  
}