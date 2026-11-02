
fig_characteristics_over_time <- function() {
  
  for (ii in characteristics) {
    
    data_summary <- data_wide |> 
      tidyr::pivot_longer(all_of(ii)) |>
      dplyr::group_by(date_q, name, value) |>
      dplyr::summarise(n = dplyr::n()) |>
      dplyr::ungroup()
    
    # Set order of legend
    if (ii %in% "cohort") {
      data_summary$value <-  factor(data_summary$value, 
                                    levels=c("-1969", "1970-1989", "1990-2009", 
                                             "2010-","Unknown"))
    }
    if (ii %in% "continent_origin") {
      data_summary$value <-  factor(data_summary$value, 
                                    levels=c("USA", "Americas (excl. USA)", 
                                             "Europe", "Asia", "Unknown"))
    }
    if (ii %in% "education_field") {
      data_summary$value <-  factor(data_summary$value, 
                                    levels=c("Economics/Finance", "Business/Management",  
                                             "Econometrics/Statistics", "Public Administration", 
                                             "Law","Unknown"))
    }
    if (ii %in% "affiliation_type2") {
      data_summary$value <-  factor(data_summary$value, 
                                    levels=c("Consulting", "University",
                                             "Investment Banking", "Commercial Banking",
                                             "Asset Management", "Manufacturing",
                                             "Other", "Unknown"))
    }
    if (ii %in% "title2") {
      data_summary$value <-  factor(data_summary$value, 
                                    levels=c("Chief Economist", "Executive Role",
                                             "Economist","Academic Role",
                                             "Consultant/Analyst", "Unknown"))
    }
    
    colors <- RColorBrewer::brewer.pal(8, 'Set2')
    colors <- colors[1:length(data_summary$value |> unique())]
    colors[length(data_summary$value |> unique())] <- "#BEBEBE"
    
    p <- ggplot2::ggplot(data = data_summary |> dplyr::filter(name==ii), 
                         mapping = ggplot2::aes(date_q, n, fill=value)) +
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
    
    pdf(paste0("figures/",ii,"_over_time_lgd.pdf"), 
        width=w, height=h*0.6)
    print(p)
    dev.off()
    
    p <- ggplot2::ggplot(data = data_summary |> dplyr::filter(name==ii), 
                         mapping = ggplot2::aes(date_q, n, fill=value)) +
      ggstream::geom_stream(type="proportional") +
      ggplot2::labs(x = "",
                    y = "",
                    fill = "") +
      ggplot2::scale_fill_manual(values = colors) +
      ggplot2::theme_minimal(base_size = 10) +
      ggplot2::theme(legend.position = "none")
    
    pdf(paste0("figures/",ii,"_over_time.pdf"), 
        width=w/2, height=h*0.6)
    print(p)
    dev.off()
  }
  
}