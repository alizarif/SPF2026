rm(list=ls())
setwd(paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/functions"))
sapply(list.files(pattern="[.][rR]$",recursive = TRUE),source,.GlobalEnv)
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Figure settings
w = 6.5
h = 4.5

# Table settings
options(knitr.kable.NA = '') # Ignore NA in tables
gof_map <- modelsummary::gof_map
gof_map$omit[gof_map$clean %in% c("R2","F","AIC","BIC","Log.Lik.","RMSE")] = TRUE
options(modelsummary_format_numeric_latex = "plain")

# Names of surveys (AI first, then human WSJ)
survey_names <- c("AI","Human")

# ------------------------------------------------------------------------------
# PREPARE DATA

imp <- read.csv("data/merged_UR_LLM_all.csv")
imp <- imp |>
  dplyr::mutate(date_q_1 = lubridate::floor_date(as.Date(imp$Date_Q,format="%m/%d/%y"),'month'),
                date_q_2 = ifelse(is.na(date_q_1),Date_Q,NA),
                date_q_3 = as.Date(date_q_2),
                date_q = as.Date(ifelse(is.na(date_q_1),date_q_3,date_q_1))) |>
  dplyr::select(-c(date_q_1,date_q_2,date_q_3,unique_id,Initial.Response))


horizons <- data.frame(
  label = c("Current quarter","Two quarters ahead","Four quarters ahead"),
  id_wsj = c("_nowcast","_q_2","_q_4"),
  id_spf = c("1","3","5"),
  id_human_spf = c("H0_SPF","H2_SPF","H4_SPF"),
  id_human_wsj = c("H0_WSJ","H2_WSJ","H4_WSJ"),
  id_ai_output = c("_t","_t.2","_t.4"),
  id_ai = c("A0","A2","A4"),
  id = c(0,2,4)
)

variables = data.frame(
  variable = c("UNEMP"),
  variable_WSJ = c("wsj"),
  variable_AI_output = c("Civilian.Unemployment.Rate"),
  Units = c("Percentage Points")
)

# FRED data series
fredr::fredr_set_key(Sys.getenv("FRED_API_KEY")) # unique API key for this script/project
nber_rec <- fredr::fredr(series_id = "USREC",
                         observation_start = min(imp$date_q),
                         observation_end = max(imp$date_q))

data <- list()
data_ts <- list()
for(jj in variables$variable) {
  
  var_WSJ <- paste0(variables$variable_WSJ[which(variables$variable %in% jj)],horizons$id_wsj)
  var_SPF <- paste0(jj,horizons$id_spf)
  var_AI <- paste0(variables$variable_AI_output[which(variables$variable %in% jj)],horizons$id_ai_output)
  
  data_WSJ <- imp |> 
    dplyr::select(date_q,var_WSJ,Name) |>
    tidyr::pivot_longer(cols = -c(date_q,Name),
                        names_to = "id_forecast", 
                        values_to = "value") |>
    dplyr::mutate(id_forecast = gsub(variables$variable_WSJ,"",id_forecast)) |>
    dplyr::left_join(horizons |> dplyr::select(id_wsj,id),
                     by=c("id_forecast" = "id_wsj")) |>
    dplyr::select(-id_forecast) |>
    dplyr::mutate(survey="WSJ",
                  type=survey_names[2])
  
  data_SPF <- imp |> 
    dplyr::select(date_q,var_SPF) |>
    unique() |>
    tidyr::pivot_longer(cols = -c(date_q),
                        names_to = "id_forecast", 
                        values_to = "value") |>
    dplyr::mutate(id_forecast = gsub(jj,"",id_forecast)) |>
    dplyr::left_join(horizons |> dplyr::select(id_spf,id),
                     by=c("id_forecast" = "id_spf")) |>
    dplyr::select(-id_forecast) |>
    dplyr::mutate(survey="SPF",
                  Name=NA,
                  type="SPF")
  
  data_AI <- imp |> 
    dplyr::select(date_q,var_AI,Name) |>
    tidyr::pivot_longer(cols = -c(date_q,Name),
                        names_to = "id_forecast", 
                        values_to = "value") |>
    dplyr::mutate(id_forecast = gsub(variables$variable_AI_output,"",id_forecast)) |>
    dplyr::left_join(horizons |> dplyr::select(id_ai_output,id),
                     by=c("id_forecast" = "id_ai_output")) |>
    dplyr::select(-id_forecast) |>
    dplyr::mutate(survey="AI",
                  type=survey_names[1])
  
  data[[jj]] <- data_WSJ |> 
    dplyr::bind_rows(data_SPF) |>
    dplyr::bind_rows(data_AI) |>
    unique() |>
    dplyr::mutate(type_ordered = factor(type, 
                                        levels=c(survey_names[2],
                                                 survey_names[1],
                                                 "SPF"))) |>
    dplyr::group_by(date_q,Name,id,survey,type,type_ordered) |>
    dplyr::summarise(value=mean(value)) |> # For a few cases, we have multiple AI responses (they are close so just taking the average for now)
    dplyr::ungroup()
  
  data_ts[[jj]] <- data[[jj]] |> 
    dplyr::group_by(date_q,survey,id,type,type_ordered) |>
    dplyr::summarise(median = median(value)) |>
    dplyr::ungroup() |>
    dplyr::left_join(nber_rec |>
                       dplyr::rename("date_q"="date", "nber_rec"="value") |>
                       dplyr::select(date_q,nber_rec),
                     by="date_q")

}

# ------------------------------------------------------------------------------
# TABLES AND FIGURES

# Figure: Plot time series of median of WSJ vs AI
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
    
    p <- ggplot2::ggplot(data = data_ts[[jj]] |> 
                           dplyr::filter(id %in% horizons[ii,"id"],
                                         survey %in% c("AI","WSJ")),
                         ggplot2::aes(x=date_q, y=median)) +
      ggplot2::geom_line(ggplot2::aes(color=type_ordered, 
                                      size=type_ordered)) +
      #ggplot2::scale_fill_manual(values = c("darkgray", "black")) +
      ggplot2::scale_color_manual(values=c("darkgray", "black")) +
      ggplot2::scale_y_continuous(labels = label_func) +
      ggplot2::scale_size_manual(values=c(1.4,0.5)) +
      ggplot2::stat_summary(
        geom = "rect",
        ggplot2::aes(group = data.table::rleid(nber_rec),
                     xmin = ggplot2::after_stat(xmin)-50,
                     xmax = ggplot2::after_stat(xmax)+50,
                     alpha = I((nber_rec) * 0.15),
                     y = ggplot2::resolution(median)),
        fun.min = min, fun.max = max,
        orientation = "y", 
        ymin = -Inf, ymax = Inf
      ) +
      ggplot2::theme_light(base_size = 10) +
      ggplot2::theme(axis.title = ggplot2::element_blank(),
                     panel.grid.major = ggplot2::element_blank(), 
                     panel.grid.minor = ggplot2::element_blank(),
                     legend.position="none")
    
    pdf(paste0("figures/ts_median_",jj,'_',horizons[ii,"id"],"_WSJ.pdf"), 
        width=w, height=h*0.45)
    print(p)
    dev.off()
  }
}
  
# Table: Accuracy of AI vs WSJ median and individual-level forecasts

err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
mae <- function(x) {mean(abs(x |> na.omit()), na.rm=TRUE)}
dir_err <- function(x) { sign(dplyr::pull(x,1)) == sign(dplyr::pull(x,2))}

for (jj in variables$variable) {
  
  data_ts_wide <- data_ts[[jj]] |> 
    dplyr::select(-c(survey,type_ordered)) |>
    tidyr::pivot_wider(names_from = c(type), 
                       values_from = c(median))
  
  error_ts <- data_ts_wide |>
    dplyr::select(-SPF) |>
    dplyr::mutate(
      median_err = err(data_ts_wide[,c("AI","Human")]),
      dir_err = dir_err(data_ts_wide[,c("AI","Human")])
    ) 
  
  data_wide <- data[[jj]] |>
    unique() |>
    dplyr::select(-c(survey,type_ordered)) |>
    tidyr::pivot_wider(names_from = c(type),
                       values_from = c(value))
  
  error <- data_wide |>
    dplyr::select(-SPF) |>
    dplyr::mutate(
      ind_err = err(data_wide[,c("AI","Human")]),
      dir_err = dir_err(data_wide[,c("AI","Human")])
    )
  
  accuracy <- error_ts |>
    dplyr::group_by(id) |>
    dplyr::mutate(median_err = 100*median_err/Human,
                  median_err = ifelse(median_err %in% c(-Inf,Inf),NA,median_err)) |>
    dplyr::summarise_at("median_err",mae) |>
    dplyr::left_join(error |>
                       dplyr::group_by(id) |>
                       dplyr::mutate(ind_err = 100*ind_err/Human,
                                     ind_err = ifelse(ind_err %in% c(-Inf,Inf),NA,ind_err)) |>
                       dplyr::summarise_at("ind_err",mae) )
  
  
  # # Correlations by quarter
  # for (ii in 1:nrow(horizons)) {
  #  
  #   correlations <- data.frame(
  #     date_q = sort(unique(data[[jj]]$date_q)),
  #     estimate = NA,
  #     CI_lower = NA,
  #     CI_upper = NA
  #   )
  #  
  #   for(tt in 1:dim(correlations)[1]) {
  #    
  #     error_tt_ii <- error |>
  #       dplyr::filter(date_q %in% correlations$date_q[tt],
  #       id %in% horizons[ii,"id"]) |>
  #       na.omit()
  #     #error_tt_ii[1,"AI"] = 10.00011
  #    
  #     tmp <- stats::cor.test(error_tt_ii$AI, error_tt_ii$Human)
  #     correlations[tt,"estimate"] = tmp$estimate
  #     correlations[tt,"CI_lower"] = tmp$conf.int[1]
  #     correlations[tt,"CI_upper"] = tmp$conf.int[2]
  #   }
  # }
  
  # Correlations by forecaster
  for (ii in 1:nrow(horizons)) {
    
    correlations <- data.frame(
      Name = sort(unique(data[[jj]]$Name)),
      estimate = NA,
      CI_lower = NA,
      CI_upper = NA
    )
    
    for(kk in 1:dim(correlations)[1]) {
      
      error_kk_ii <- error |>
        dplyr::filter(Name %in% correlations$Name[kk],
                      id %in% horizons[ii,"id"]) |>
        na.omit()
      
      if(dim(error_kk_ii)[1]>3){
        tmp <- stats::cor.test(error_kk_ii$AI, error_kk_ii$Human)
        correlations[kk,"estimate"] = tmp$estimate
        correlations[kk,"CI_lower"] = tmp$conf.int[1]
        correlations[kk,"CI_upper"] = tmp$conf.int[2]
      }
    }
    
    correlations <- correlations |> na.omit()
    
    p <-
    ggplot2::ggplot(data = correlations |> 
                      dplyr::mutate(row = factor(paste0("#",dplyr::row_number()), 
                                                 levels=paste0("#",dplyr::row_number()))
                                                         ),
                    ggplot2::aes(x=row, y=estimate)) +
      ggplot2::geom_point() +
      ggplot2::geom_pointrange(ggplot2::aes(ymin=CI_lower,ymax=CI_upper), fatten = .5, size = .5) +
      ggplot2::theme_light(base_size = 10) +
      ggplot2::theme(axis.title = ggplot2::element_blank(),
                     panel.grid.major = ggplot2::element_blank(),
                     panel.grid.minor = ggplot2::element_blank(),
                     legend.position = "none",
                     #axis.text.x = ggplot2::element_blank(),
                     #axis.ticks.x = ggplot2::element_blank()
                     )
    
    pdf(paste0("figures/correlations_",horizons[ii,"id"],"_WSJ.pdf"),
        width=w, height=h*0.45)
    print(p)
    dev.off()
  
  }
  
  # Pooled OLS
  fit <- lm(AI ~ Human, data=error |> dplyr::filter(id==3))
  car::linearHypothesis(fit, rhs=matrix(c(1,0),ncol=1), hypothesis.matrix=matrix(c(0,1,1,0),nrow=2))
  
  estim_test <- function(lm.mod, h0.value = 0) {
    coefm <- as.data.frame(summary(lm.mod)$coefficients)
    n <- length(lm.mod$residuals)
    coefm$`t value` <- (coefm$Estimate - h0.value)/coefm$`Std. Error`
    coefm$`Pr(>|t|)` <- 2*pt(-abs(coefm$`t value`), df=lm.mod$df.residual)
    coefm
  }
  estim_test(fit, h0.value=1)
  
  id_select <- 0
  data_select <- data_wide |> 
    dplyr::filter(id %in% id_select) |>
    dplyr::pull(Human)
  
  ks.test(x = data_wide |> 
            dplyr::filter(id %in% id_select) |>
            dplyr::pull(Human),
          y = data_wide |> 
            dplyr::filter(id %in% id_select) |>
            dplyr::pull(AI))
  
}



