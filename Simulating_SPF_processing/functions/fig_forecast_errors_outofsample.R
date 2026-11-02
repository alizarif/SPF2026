
fig_forecast_errors_outofsample <- function() {
  
  data_ts_0 <- data_ts
  load(file = "data/outofsample_data.rda")
  data_ts_1 <- data_ts
  
  data_ts <- data_ts_0 |> 
    dplyr::bind_rows(data_ts_1)
  
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
                                           variable %in% jj,
                                           date_q>"2020-12-31"),
                           ggplot2::aes(x=date_q, y=forecast_error)) +
        ggplot2::geom_hline(yintercept=0, linetype="dotted", color = "black", size=0.5) +
        ggplot2::geom_vline(xintercept=as.numeric(as.Date("2023-10-31")), linetype="dashed", color = "black", size=1) +
        ggplot2::geom_line(ggplot2::aes(color=type_ordered, 
                                        size=type_ordered)) +
        ggplot2::scale_color_manual(values=c("darkgray", "black")) +
        ggplot2::scale_y_continuous(labels = label_func) +
        ggplot2::scale_size_manual(values=c(1.4,0.5)) +
        ggplot2::stat_summary(
          geom = "rect",
          ggplot2::aes(group = data.table::rleid(nber_rec),
                       xmin = ggplot2::after_stat(xmin)-50,
                       xmax = ggplot2::after_stat(xmax)+50,
                       alpha = I((nber_rec) * 0.15),
                       y = ggplot2::resolution(forecast_error)),
          fun.min = min, fun.max = max,
          orientation = "y", 
          ymin = -Inf, ymax = Inf
        ) +
        ggplot2::theme_light(base_size = 10) +
        ggplot2::theme(axis.title = ggplot2::element_blank(),
                       panel.grid.major = ggplot2::element_blank(), 
                       panel.grid.minor = ggplot2::element_blank(),
                       legend.title = ggplot2::element_blank(),
                       legend.position = "none")
      
      pdf(paste0("figures/forecast_error_oos_",jj,'_',horizons[ii,"id"],".pdf"), 
          width=w/2, height=h*0.6)
      print(p)
      dev.off()
    }
  }
}