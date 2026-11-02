
fig_human_ai_lgd <- function() {
   
   p <- ggplot2::ggplot(data = data_ts |> 
                          dplyr::filter(id %in% horizons[1,"id"])) +
     ggplot2::geom_line(ggplot2::aes(x=date_q, y=median, 
                                     color=type_ordered, 
                                     size=type_ordered)) +
     ggplot2::scale_color_manual(values = c("darkgray", "black")) +
     ggplot2::scale_size_manual(values = c(1.4,0.5)) +
     ggplot2::theme_light(base_size = 10) +
     ggplot2::theme(axis.title = ggplot2::element_blank(),
                    panel.grid.major = ggplot2::element_blank(), 
                    panel.grid.minor = ggplot2::element_blank(),
                    legend.title = ggplot2::element_blank(),
                    legend.position = "bottom")
   pdf("figures/human_ai_lgd.pdf", 
       width=w/2, height=h*0.6)
   print(p)
   dev.off()
   
   
   tmp <- data_ts |> 
     dplyr::filter(id %in% horizons[1,"id"])
   tmp[1,'type'] = "Realized"
   tmp <- tmp |>
     dplyr::mutate(type_ordered = factor(type, levels=c(survey_names[2],
                                                        survey_names[1],
                                                        "Realized")))
   p <- ggplot2::ggplot(data = tmp) +
     ggplot2::geom_line(ggplot2::aes(x=date_q, y=median, 
                                     color=type_ordered, 
                                     size=type_ordered,
                                     linetype=type_ordered)) +
     ggplot2::scale_color_manual(values = c("darkgray", "black","black")) +
     ggplot2::scale_size_manual(values = c(1.4,0.5,0.5)) +
     ggplot2::scale_linetype_manual(values = c(1,1,3)) +
     ggplot2::theme_light(base_size = 10) +
     ggplot2::theme(axis.title = ggplot2::element_blank(),
                    panel.grid.major = ggplot2::element_blank(), 
                    panel.grid.minor = ggplot2::element_blank(),
                    legend.title = ggplot2::element_blank(),
                    legend.position = "bottom")
   pdf("figures/human_ai_realized_lgd.pdf", 
       width=w/2, height=h*0.6)
   print(p)
   dev.off()
 }