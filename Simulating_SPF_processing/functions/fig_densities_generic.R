
fig_densities_generic <- function() {
  
  data_long_baseline <- data_long
  
  load(file = "data/generic_N_forecaster_data.rda")
  
  for (ii in 1:nrow(horizons)) {
    
    for (jj in variables$variable) {
      
      dates_selected <- c("1999-01-01","2008-07-01","2020-04-01","2023-01-01")
    
      tmp <- data_long |>
        dplyr::mutate(type="AI (generic)") |>
        dplyr::select(id,value,variable,type,date_q) |>
        dplyr::filter(id %in% horizons[ii,"id"],
                      variable %in% jj,
                      date_q %in% dates_selected)
      
      data_ <-  data_long_baseline |> 
        dplyr::filter(id %in% horizons[ii,"id"],
                      variable %in% jj,
                      type %in% "AI",
                      date_q %in% dates_selected) |>
        dplyr::select(id,value,variable,type,date_q) |>
        dplyr::bind_rows(tmp) |>
        dplyr::bind_rows(SPFmicrodata_long |>
                           dplyr::mutate(type="Human") |>
                           dplyr::select(id,value,variable,type,date_q) |>
                           dplyr::filter(id %in% horizons[ii,"id"],
                                         variable %in% jj,
                                         date_q %in% dates_selected)) |>
        dplyr::mutate(yearqtr = as.factor(paste0(lubridate::year(date_q)," Q",lubridate::quarter(date_q)))) |>
        dplyr::left_join(data_long_baseline |> 
                           dplyr::filter(id %in% horizons[ii,"id"],
                                         variable %in% jj,
                                         type %in% "Realized",
                                         date_q %in% dates_selected) |>
                           dplyr::select(date_q,value) |>
                           dplyr::rename("Realized" = "value") |>
                           unique(), 
                         by="date_q") |>
        dplyr::mutate(value = value-Realized,
                      type = factor(type, levels=c(survey_names[2],
                                                   survey_names[1],
                                                   "AI (generic)"))) |>
        dplyr::select(value,type,yearqtr)
      
      p <- ggplot2::ggplot(data = data_ |> dplyr::filter(type %in% c(survey_names,"AI (generic)")),
                      ggplot2::aes(x = value, y = yearqtr, 
                                   group = interaction(yearqtr,type),
                                   fill = type)) +
        ggridges::geom_density_ridges(#jittered_points = TRUE, position = "raincloud", point_alpha=1,  point_shape=21,
                                      alpha = 0.7, linewidth=0
                                      ) +
        ggridges::scale_fill_cyclical(values=c("darkgray","black","red")) +
        #ggplot2::geom_point(data = data_ |> dplyr::filter(type %in% "AI (generic)"), fill="white",color="black", shape=21) +
        # ggplot2::geom_point(data=data_long |> 
        #                      dplyr::filter(id %in% horizons[ii,"id"],
        #                                    variable %in% jj,
        #                                    type %in% "Realized",
        #                                    date_q %in% dates_selected) |>
        #                      dplyr::select(date_q,value) |>
        #                      dplyr::rename("Realized" = "value") |>
        #                      dplyr::mutate(yearqtr = as.factor(paste0(lubridate::year(date_q)," Q",lubridate::quarter(date_q)))) |>
        #                      unique(), 
        #                     ggplot2::aes(x=Realized,y=yearqtr),
        #                     shape=21, color = "Black", fill = "White",size=2.5,
        #                     inherit.aes = F) +
        # ggplot2::geom_vline(xintercept = 0, linetype="solid", 
        #                     color = "black", linewidth=0.5) +
        ggplot2::scale_shape_identity() +
        ggplot2::theme_light(base_size = 10) +
        ggplot2::theme(axis.title = ggplot2::element_blank(),
                       panel.grid.major = ggplot2::element_blank(), 
                       panel.grid.minor = ggplot2::element_blank(),
                       legend.position="none") 
      
      
      pdf(paste0("figures/density_w_generic_",jj,'_',horizons[ii,"id"],".pdf"), 
          width=w/2, height=h*0.6)
      print(p)
      dev.off()
      
      
      # p <- ggplot2::ggplot(data = data_long |> 
      #                        dplyr::filter(id %in% horizons[ii,"id"],
      #                                      variable %in% jj,
      #                                      type %in% "AI") |>
      #                        dplyr::select(id,value,variable,type) |>
      #                        dplyr::bind_rows(SPFmicrodata_long |>
      #                                           dplyr::mutate(type="Human") |>
      #                                           dplyr::select(id,value,variable,type) |>
      #                                           dplyr::filter(id %in% horizons[ii,"id"],
      #                                                         variable %in% jj))) +
      #   ggplot2::geom_density(ggplot2::aes(x = value,
      #                                      color=type, 
      #                                      size=type)) +
      #   ggplot2::scale_color_manual(values=c("darkgray", "black")) +
      #   ggplot2::scale_size_manual(values=c(1.4,0.5)) +
      #   ggplot2::theme_light(base_size = 10) +
      #   ggplot2::theme(axis.title = ggplot2::element_blank(),
      #                  panel.grid.major = ggplot2::element_blank(), 
      #                  panel.grid.minor = ggplot2::element_blank(),
      #                  legend.position="none")
      # 
      # pdf(paste0("figures/density_",jj,'_',horizons[ii,"id"],".pdf"), 
      #     width=w/2, height=h*0.6)
      # print(p)
      # dev.off()
      
    }
  }
  
  
  p <- ggplot2::ggplot(data = data.frame(
    type = factor(survey_names, levels=c(survey_names[2],
                                 survey_names[1])),
    value = c(1,2))) +
    ggplot2::geom_density(ggplot2::aes(y=value,fill=type),alpha=0.7,size=0.1) +
    ggplot2::scale_fill_manual(values=c("darkgray", "black")) +
    ggplot2::theme_light(base_size = 10) +
    ggplot2::theme(axis.title = ggplot2::element_blank(),
                   panel.grid.major = ggplot2::element_blank(), 
                   panel.grid.minor = ggplot2::element_blank(),
                   legend.title = ggplot2::element_blank(),
                   legend.position = "bottom")
  

  pdf(paste0("figures/density_lgd.pdf"), 
      width=w/2, height=h*0.6)
  print(p)
  dev.off()
  
}

