
fig_ts_median_wRealized <- function() {

  for (ii in 1:nrow(horizons)) {
    
    for (jj in variables$variable) {
      
      if (variables[variables$variable %in% jj,"Units"] %in% "Percentage Points") {
        label_func <- function(x) paste0(x, "%")  
      } else if (variables[variables$variable %in% jj,"Units"] %in% "Billions USD") {
        label_func <- function(x) paste0("$",x,"B")  
      } else if (variables[variables$variable %in% jj,"Units"] %in% "Thousands") {
        label_func <- function(x) paste0(x, "(x1000)")  
      } else if (variables[variables$variable %in% jj,"Units"] %in% "Millions") {
        label_func <- function(x) paste0(x, "M")  
      } else {
        label_func <- function(x) paste0(x)
      }
      
      p <- ggplot2::ggplot(data = data_ts |> 
                             dplyr::filter(id %in% horizons[ii,"id"],
                                           variable %in% jj) |>
                             dplyr::rename('Realized'='realized') |>
                             dplyr::select(date_q,nber_rec,median,Realized,type) |>
                             tidyr::pivot_wider(names_from='type',values_from='median') |>
                             tidyr::pivot_longer(-c(date_q,nber_rec),values_to = 'value', names_to = 'type') |>
                             dplyr::mutate(type_ordered = factor(type, levels=c(survey_names[2],
                                                                                survey_names[1],
                                                                                "Realized"))),
                           ggplot2::aes(x=date_q, y=value)) +
        #ggplot2::geom_ribbon(ggplot2::aes(ymin = p10, ymax = p90, fill = type_ordered), 
        #                     alpha = 0.6) +
        ggplot2::geom_line(ggplot2::aes(color=type_ordered, 
                                        size=type_ordered,
                                        linetype=type_ordered)) +
        ggplot2::scale_color_manual(values=c("darkgray", "black","black")) +
        ggplot2::scale_y_continuous(labels = label_func) +
        ggplot2::scale_size_manual(values=c(1.4,0.5,0.5)) +
        ggplot2::scale_linetype_manual(values = c(1,1,3)) +
        ggplot2::stat_summary(
          geom = "rect",
          ggplot2::aes(group = data.table::rleid(nber_rec),
                       xmin = ggplot2::after_stat(xmin)-50,
                       xmax = ggplot2::after_stat(xmax)+50,
                       alpha = I((nber_rec) * 0.15),
                       y = ggplot2::resolution(value)),
          fun.min = min, fun.max = max,
          orientation = "y", 
          ymin = -Inf, ymax = Inf
        ) +
        ggplot2::theme_light(base_size = 10) +
        ggplot2::theme(axis.title = ggplot2::element_blank(),
                       panel.grid.major = ggplot2::element_blank(), 
                       panel.grid.minor = ggplot2::element_blank(),
                       legend.position="none")
  
      pdf(paste0("figures/ts_median_",jj,'_',horizons[ii,"id"],"_realized.pdf"), 
          width=w/2, height=h*0.6)
      print(p)
      dev.off()
      
    }
  }
  
}

