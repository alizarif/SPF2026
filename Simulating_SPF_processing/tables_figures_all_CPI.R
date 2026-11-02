setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Figure settings
w = 6.5
h = 4.5

# Table settings
options(knitr.kable.NA = '') # Ignore NA in tables
gof_map <- modelsummary::gof_map
gof_map$omit[gof_map$clean %in% c("R2","F","AIC","BIC","Log.Lik.","RMSE")] = TRUE
options(modelsummary_format_numeric_latex = "plain")

# Names of surveys (AI first, then human SPF)
survey_names <- c("AI","Human")

# Define mapping between SPF and AI forecasts incl. their labels
mapping_full <- data.frame(
  label = c("Current quarter","One quarter ahead","Two quarters ahead",
            "Three quarters ahead","Four quarters ahead","Current year",
            "One year ahead"),
  id_spf = c("CPI2","CPI3","CPI4","CPI5","CPI6","CPIA","CPIB"),
  id_ai = c("t_0","t_1","t_2","t_3","t_4","Y_0","Y_1"),
  id_realized = c("cpi_0","cpi_1","cpi_2","cpi_3","cpi_4","cpi_A","cpi_B"),
  id = c(0,1,2,3,4,"A","B")
)

# Select which forecast to include
mapping <- mapping_full[c(1,2,3,5),]

# Load model output
output <- read.csv("data/merged_file_CPI_SPF6_fixed_date.csv") |>
  dplyr::mutate(date_q = lubridate::as_date(Date_Q,format="%Y-%m-%d %H:%M:%S")) |>
  dplyr::filter(!(Name %in% "No Name Provided")) |> 
  dplyr::mutate(Forecasts = gsub(paste(c("[(]", "[)]"), collapse = "|"), "",Forecasts))
tmp <- as.data.frame(do.call(rbind, strsplit(as.character(output$Forecasts),', ')))
names(tmp) <- mapping_full$id_ai
tmp <- apply(tmp,2,as.numeric)
output <- cbind(output, tmp)

# Load characteristics and real-time data
addendum <- read.csv("data/individual_forecasters.csv") |>
  dplyr::mutate(date_q = lubridate::as_date(date_q,format="%Y Q%q")) |>
  dplyr::select(-unique_id) |> 
  dplyr::filter(!(Name %in% "No Name Provided")) |>
  unique()
  
# Realized forecasted series
realized <- read.csv("data/SPF1_C.csv") |>
  dplyr::mutate(date_q = lubridate::as_date(date_q,format="%Y Q%q")) |> 
  dplyr::select(date_q,cpi) |>
  unique() |>
  na.omit() |>
  dplyr::arrange(date_q) |>
  dplyr::mutate(cpi_0 = cpi,
                cpi_1 = dplyr::lead(cpi, 1), 
                cpi_2 = dplyr::lead(cpi, 2), 
                cpi_3 = dplyr::lead(cpi, 3), 
                cpi_4 = dplyr::lead(cpi, 4), 
                cpi_A = NA,
                cpi_B = NA) |>
  dplyr::select(-cpi)

# Merge data sets
data <- output |> 
  dplyr::left_join(charac, by=c("Name","date_q")) |>
  dplyr::left_join(realized, by=c("date_q"))

# Permute data to long format (human is median, AI is individual forecasts)
data_long <- data |> 
  tidyr::pivot_longer(cols=c(mapping$id_ai,mapping$id_spf), 
                      names_to = "id_forecast", 
                      values_to = "forecast") |>
  dplyr::select(date_q,id_forecast,forecast) |>
  dplyr::mutate(forecast_type = ifelse(id_forecast %in% mapping$id_ai,
                                       survey_names[1],
                                       survey_names[2])) |>
  dplyr::left_join(tidyr::pivot_longer(mapping,
                                       cols=c(id_spf,id_ai),
                                       names_to="tmp",
                                       values_to = "id_forecast") |>
                     dplyr::select(-tmp), by="id_forecast") |>
  dplyr::mutate(forecast_type_ordered = factor(forecast_type, 
                                               levels=c(survey_names[2],
                                                        survey_names[1]))) |>
  dplyr::left_join(realized, by = "date_q") |>
  dplyr::mutate(realized = dplyr::case_when(id==0 ~ cpi_0,
                                            id==1 ~ cpi_1,
                                            id==2 ~ cpi_2,
                                            id==3 ~ cpi_3,
                                            id==4 ~ cpi_4,
                                            id=="A" ~ cpi_A,
                                            id=="B" ~ cpi_B)) |>
  dplyr::select(-c(cpi_0,cpi_1,cpi_2,cpi_3,cpi_4,cpi_A,cpi_B))


# Define time series
data_ts <- data_long |>
  dplyr::group_by(date_q,forecast_type,forecast_type_ordered,id) |>
  dplyr::summarise_at("forecast", 
                      list(median = function(x) median(x,na.rm=T),
                           mean = function(x) mean(x,na.rm=T),
                           p25 = function(x) quantile(x,0.25,na.rm=T),
                           p75 = function(x) quantile(x,0.75,na.rm=T))
  ) |>
  dplyr::ungroup() |>
  dplyr::left_join(data_long |> 
                     dplyr::select(date_q,id,realized) |>
                     unique(),
                   by = c("date_q","id")) |>
  dplyr::mutate(forecast_error = median-realized) |>
  unique()

# FRED data series
fredr::fredr_set_key(Sys.getenv("FRED_API_KEY")) # unique API key for this script/project
nber_rec <- fredr::fredr(series_id = "USREC",
                         observation_start = min(data$date_q),
                         observation_end = max(data$date_q))

# Join recession variable from FRED with data_ts
data_ts <- data_ts |> 
  dplyr::left_join(nber_rec |>
                     dplyr::rename("date_q"="date", "nber_rec"="value") |>
                     dplyr::select(date_q,nber_rec),
                   by="date_q")

# Individual SPF forecasts
data_SPFmicro <- read.csv("data/SPFmicrodata/CPI-Table 1.csv",
                          na.strings=c("NA","NaN", " ","#N/A")) |>
  dplyr::mutate(date_q = lubridate::as_date(paste0(YEAR," Q",QUARTER),format="%Y Q%q")) |>
  dplyr::select(-YEAR,-QUARTER) |>
  dplyr::right_join(data_ts[,"date_q"] |> unique()) |> # cut data sample
  dplyr::select(c(date_q,mapping$id_spf)) |>
  dplyr::rename_with(~mapping$id,mapping$id_spf) |>
  tidyr::pivot_longer(-date_q, names_to = 'id', values_to = 'forecast') |>
  dplyr::mutate(forecast_type = "Human") |>
  dplyr::left_join(mapping |> dplyr::select(-id_ai), by="id") |>
  dplyr::rename("id_forecast" = "id_spf") |>
  dplyr::left_join(realized, by = "date_q") |>
  dplyr::mutate(realized = dplyr::case_when(id==0 ~ cpi_0,
                                            id==1 ~ cpi_1,
                                            id==2 ~ cpi_2,
                                            id==3 ~ cpi_3,
                                            id==4 ~ cpi_4,
                                            id=="A" ~ cpi_A,
                                            id=="B" ~ cpi_B)) |>
  dplyr::select(-c(cpi_0,cpi_1,cpi_2,cpi_3,cpi_4,cpi_A,cpi_B))

data_long_all_individual <- 
  data_long |> 
  dplyr::filter(forecast_type %in% survey_names[1]) |>
  dplyr::select(-forecast_type_ordered) |>
  dplyr::bind_rows(data_SPFmicro)


# Human AI legend
p <- ggplot2::ggplot(data = data_ts |> 
                       dplyr::filter(id %in% mapping[1,"id"])) +
  ggplot2::geom_line(ggplot2::aes(x=date_q, y=median, 
                                  color=forecast_type_ordered, 
                                  size=forecast_type_ordered)) +
  ggplot2::scale_color_manual(values = c("darkgray", "black")) +
  ggplot2::scale_size_manual(values = c(1.3,0.5)) +
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


################################################################################
# Figure: Number of forecasters over time

number_forecasters <- data |> 
  dplyr::group_by(date_q) |>
  dplyr::summarise(n = dplyr::n()) |>
  dplyr::ungroup() |>
  dplyr::left_join(
    data_SPFmicro |> 
      dplyr::group_by(date_q,id) |>
      dplyr::summarise(n_SPF = dplyr::n()) |>
      dplyr::ungroup()) |>
  dplyr::rename_with(~survey_names,c(n,n_SPF)) |>
  tidyr::pivot_longer(all_of(survey_names),
                      names_to = "forecast_type", 
                      values_to = "n") |>
  dplyr::mutate(forecast_type_ordered = factor(forecast_type, 
                                               levels=c(survey_names[2],
                                                        survey_names[1])))

p <- ggplot2::ggplot(data = number_forecasters,
                     mapping = ggplot2::aes(x=date_q, y=n)) +
  ggplot2::geom_line(ggplot2::aes(color=forecast_type_ordered, 
                                  size=forecast_type_ordered)) +
  ggplot2::scale_color_manual(values=c("darkgray", "black")) +
  ggplot2::scale_size_manual(values=c(1.4,0.5)) +
  ggplot2::scale_y_continuous(breaks = seq(20,70,10), limits = c(25,70)) +
  ggplot2::theme_light(base_size = 10) +
  ggplot2::theme(axis.title = ggplot2::element_blank(),
                 panel.grid.major = ggplot2::element_blank(), 
                 panel.grid.minor = ggplot2::element_blank(),
                 legend.position="none") 
  
pdf(paste0("figures/num_forecasters_over_time.pdf"), 
    width=w, height=h)
print(p)
dev.off()


################################################################################
# Figure: Forecaster survival in sample

data_summary <- data |> 
  dplyr::group_by(Name) |>
  dplyr::summarise(duration = dplyr::n(),
                   start = as.numeric(dplyr::first(date_q))) |>
  dplyr::ungroup()

data_summary <- data_summary[order(-data_summary$start,-data_summary$duration),] 

tmp <- data |>
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

################################################################################
# Figure: Characteristics over time

characteristics <- c("gender2","continent_origin","education_level",
                     "education_field","cohort","title2","affiliation_type2",
                     "social_media_status2")

data <- data |>
  dplyr::mutate(
    gender2 = dplyr::case_when(
      gender %in% "male" ~ "Male",
      gender %in% "female" ~ "Female",
      gender %in% c(NA,"") ~ "Unknown"),
    continent_origin = dplyr::case_when(
      country_origin %in% c("USA") ~ "USA",
      country_origin %in% c("Mexico","Canada","Brazil") ~ "Americas (excl. USA)",
      country_origin %in% c("Belgium","Italy","Germany","Austria","Czech Republic","Ireland","England") ~ "Europe",
      country_origin %in% c("India","China","South Korea","Iran","Israel","Russia","Singapore") ~ "Asia",
      country_origin %in% c(NA,"") ~ "Unknown"),
    education_level = dplyr::case_when(
      grepl("Ph.D.", education, fixed = T) ~ "Ph.D.",
      education %in% "Postgraduate" ~ "Ph.D.",
      grepl("Doctor", education, fixed = T) ~ "Ph.D.",      
      grepl("J.D.", education, fixed = T) ~ "Ph.D.",      
      grepl("MSc", education, fixed = T) ~ "Master's",
      grepl("M.Sc.", education, fixed = T) ~ "Master's",
      grepl("MA", education, fixed = T) ~ "Master's",
      grepl("M.A.", education, fixed = T) ~ "Master's",
      grepl("M.S.", education, fixed = T) ~ "Master's",
      grepl("M.Phil.", education, fixed = T) ~ "Master's",
      grepl("Master", education, fixed = T) ~ "Master's",  
      grepl("Law Degree", education, fixed = T) ~ "Master's",
      grepl("ABD", education, fixed = T) ~ "Master's",
      grepl("MBA", education, fixed = T) ~ "MBA/MPA",
      grepl("MPA", education, fixed = T) ~ "MBA/MPA",
      grepl("B.A.", education, fixed = T) ~ "Bachelor's",
      grepl("B.S.", education, fixed = T) ~ "Bachelor's",
      education %in% c(NA,"") ~ "Unknown"),
    education_field = dplyr::case_when(
      grepl("economics", education, fixed=T) ~ "Economics/Finance",
      grepl("Economics", education, fixed=T) ~ "Economics/Finance",
      grepl("J.D.", education, fixed=T) ~ "Law",
      grepl("Law", education, fixed=T) ~ "Law",
      grepl("Management", education, fixed=T) ~ "Business/Management",
      grepl("Business", education, fixed=T) ~ "Business/Management",
      grepl("Finance", education, fixed=T) ~ "Finance",
      grepl("Public", education, fixed=T) ~ "Public Administration",
      grepl("MPA", education, fixed=T) ~ "Public Administration",
      grepl("Statistics", education, fixed=T) ~ "Econometrics/Statistics",
      grepl("Econometrics", education, fixed=T) ~ "Econometrics/Statistics",
      grepl("Engineering", education, fixed=T) ~ "Econometrics/Statistics"
      ),
    education_field = ifelse(is.na(education_field),"Unknown",education_field),
    cohort = dplyr::case_when(
      grepl("194", graduation_year, fixed=T) ~ "-1969",
      grepl("195", graduation_year, fixed=T) ~ "-1969",
      grepl("196", graduation_year, fixed=T) ~ "-1969",
      grepl("197", graduation_year, fixed=T) ~ "1970-1989",
      grepl("198", graduation_year, fixed=T) ~ "1970-1989",
      grepl("199", graduation_year, fixed=T) ~ "1990-2009",
      grepl("200", graduation_year, fixed=T) ~ "1990-2009",
      grepl("201", graduation_year, fixed=T) ~ "2010-",
      grepl("202", graduation_year, fixed=T) ~ "2010-",
      graduation_year %in% c(NA,"") ~ "Unknown"),
    title2 = dplyr::case_when(
      grepl("Chief Economist", title, fixed=F) ~ "Chief Economist",
      grepl("Economis", title, fixed=F) ~ "Economist",
      grepl("Economic", title, fixed=F) ~ "Economist",
      grepl("Professor", title, fixed=F) ~ "Academic Role",
      grepl("Scholar", title, fixed=F) ~ "Academic Role",
      grepl("Editor", title, fixed=F) ~ "Academic Role",
      grepl("Dean", title, fixed=F) ~ "Academic Role",
      grepl("Researcher", title, fixed=F) ~ "Academic Role",
      grepl("Consultant", title, fixed=F) ~ "Consultant/Analyst",
      grepl("Associate", title, fixed=F) ~ "Consultant/Analyst",
      grepl("Specialist", title, fixed=F) ~ "Consultant/Analyst",
      grepl("Assistant", title, fixed=F) ~ "Consultant/Analyst",
      grepl("Analyst", title, fixed=F) ~ "Consultant/Analyst",
      grepl("Forecaster", title, fixed=F) ~ "Consultant/Analyst",
      grepl("Portfolio Manager", title, fixed=T) ~ "Consultant/Analyst",
      grepl("President", title, fixed=F) ~ "Executive Role",
      grepl("Director", title, fixed=F) ~ "Executive Role",
      grepl("VP", title, fixed=F) ~ "Executive Role",
      grepl("Manager", title, fixed=F) ~ "Executive Role",
      grepl("Head", title, fixed=F) ~ "Executive Role",
      grepl("Officer", title, fixed=F) ~ "Executive Role",
      grepl("Chairman", title, fixed=F) ~ "Executive Role",
      grepl("Principal", title, fixed=F) ~ "Executive Role",
      ),
    title2 = ifelse(is.na(title2),"Unknown",title2),
    affiliation_type2 = dplyr::case_when(
      grepl("Consulting", affiliation_type, fixed=F) ~ "Consulting",
      grepl("Investment Advisory", affiliation_type, fixed=T) ~ "Asset Management",
      grepl("Forecasting Firm", affiliation_type, fixed=T) ~ "Other",
      grepl("Research Firm", affiliation_type, fixed=T) ~ "Other",
      grepl("Association", affiliation_type, fixed=T) ~ "Other",
      grepl("Government-Sponsored Entity", affiliation_type, fixed=T) ~ "Other",
      grepl("Insurance", affiliation_type, fixed=F) ~ "Other",
      grepl("Payment Services", affiliation_type, fixed=F) ~ "Other",
      grepl("Manufacturer", affiliation_type, fixed=F) ~ "Manufacturing",
      affiliation_type %in% c(NA,"") ~ "Unknown"),
    affiliation_type2 = ifelse(is.na(affiliation_type2),affiliation_type,affiliation_type2),
    twitter2 = T,
    twitter2 = ifelse(twitter %in% c("",NA),F,T),
    interviews2 = dplyr::case_when(
      interviews %in% "yes" ~ "Yes",
      interviews %in% "no" ~ "No",
      interviews %in% c(NA,"") ~ "Unknown"),
    social_media_status2 = dplyr::case_when(
      social_media_status %in% "You give interviews to the media, and have an active twitter account." ~ "Interviews + Twitter",
      social_media_status %in% "You have an active twitter account." ~ "Twitter",
      social_media_status %in% "You give interviews to the media." ~ "Interviews",
      social_media_status %in% c(NA,"") ~ "Unknown")
  )


for (ii in characteristics) {
  
  data_summary <- data |> 
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
  
  p <- ggplot2::ggplot(data = data_summary |> dplyr::filter(name==ii), 
                       mapping = ggplot2::aes(date_q, n, fill=value)) +
    ggstream::geom_stream(type="proportional") +
    ggplot2::labs(x = "",
                  y = "",
                  fill = "") +
    ggplot2::scale_fill_brewer(palette = "Set2") +
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
    ggplot2::scale_fill_brewer(palette = "Set2") +
    ggplot2::theme_minimal(base_size = 10) +
    ggplot2::theme(legend.position = "none")
  
  pdf(paste0("figures/",ii,"_over_time.pdf"), 
      width=w/2, height=h*0.6)
  print(p)
  dev.off()
}


################################################################################
# Figure: Plot time series of median of SPF vs AI
for (ii in 1:nrow(mapping)) {
  
  p <- ggplot2::ggplot(data = data_ts |> 
                         dplyr::filter(id %in% mapping[ii,"id"]),
                       ggplot2::aes(x=date_q, y=median)) +
    ggplot2::geom_line(ggplot2::aes(color=forecast_type_ordered, 
                                    size=forecast_type_ordered)) +
    ggplot2::scale_color_manual(values=c("darkgray", "black")) +
    ggplot2::scale_y_continuous(labels = function(x) paste0(x, "%")) +
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
    
    pdf(paste0("figures/ts_median_",mapping[ii,"id"],".pdf"), 
        width=w/2, height=h*0.6)
    print(p)
    dev.off()
    
}

################################################################################
# Figure: Plot box plots SPF vs AI

p <- ggplot2::ggplot(data = data_long_all_individual |> 
                       dplyr::mutate(is_annual = 
                                       ifelse(is.na(as.numeric(data_long_all_individual$id)),
                                              T,F)) |>
                       dplyr::filter(id %in% mapping$id) |>
                       dplyr::mutate(id = paste(id)), 
                     ggplot2::aes(x=id, y=forecast, fill=id)) +
  ggplot2::geom_boxplot(show.legend = F,
                        outliers = F,
                        alpha=0.9)  + 
  ggplot2::scale_y_continuous(labels = function(x) paste0(x, "%")) +
  ggplot2::scale_x_discrete(labels = mapping$label,
                            guide = ggplot2::guide_axis(angle=45)) +
  ggplot2::scale_fill_brewer(palette="Accent") +
  ggplot2::theme(axis.title = ggplot2::element_blank(),
                 panel.grid.major = ggplot2::element_blank(), 
                 panel.grid.minor = ggplot2::element_blank()) +
  ggplot2::facet_wrap(~forecast_type) 

pdf(paste0("figures/boxplots.pdf"), width=w, height=h)
print(p)
dev.off()
  
################################################################################
# Table: Accuracy of AI vs SPF median/mean forecasts 

filename = 'tables/accuracy_ai_against_spf.txt'

err <- function(x) {dplyr::pull(x,1)-dplyr::pull(x,2)}
mae <- function(x) {mean(abs(x), na.rm=T)}

data_ts_wide <- data_ts |> 
  dplyr::select(c(date_q,id,forecast_type,mean,median,p25,p75,nber_rec)) |> 
  tidyr::pivot_wider(names_from = c(forecast_type), 
                     values_from = c(median,mean,p25,p75))

error_ts <- data_ts_wide |>
  dplyr::mutate(
    median_err = err(data_ts_wide[,grepl('median',names(data_ts_wide))]),
    mean_err = err(data_ts_wide[,grepl('mean',names(data_ts_wide))])
    ) 

accuracy <- error_ts |>
  dplyr::filter(id %in% mapping$id) |>
  dplyr::group_by(id) |>
  dplyr::summarise_at(c("median_err","mean_err"),mae) |>
  dplyr::left_join(
    error_ts[data_ts_wide$nber_rec==1,] |>
      dplyr::group_by(id) |>
      dplyr::summarise_at(c("median_err_rec"="median_err",
                            "mean_err_rec"="mean_err"),
                          mae),
    by="id") |>
  dplyr::left_join(
    error_ts[data_ts_wide$nber_rec==0,] |>
      dplyr::group_by(id) |>
      dplyr::summarise_at(c("median_err_norec"="median_err",
                            "mean_err_norec"="mean_err"),
                          mae),
    by="id") |>
  dplyr::left_join(mapping |> dplyr::select(id,label), by="id") |>
  dplyr::mutate(empty=NA) |>
  dplyr::select("label","median_err","median_err_rec",
                "empty","mean_err","mean_err_rec")


# Create table with designated filename
writeLines(knitr::kable(accuracy, "latex", 
                        digits=2, 
                        align = c('l',rep('d{1.2}',2),'l',rep('d{1.2}',2)), 
                        booktabs=T),
           filename)
           
tbl <- readLines(filename)
tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
tbl <- c(tbl[1:2],
         " & \\multicolumn{2}{c}{Median forecasts} && \\multicolumn{2}{c}{Mean forecasts} \\\\",
         " \\cmidrule{2-3} \\cmidrule{5-6}",
          "& \\multicolumn{1}{c}{Full sample} & \\multicolumn{1}{c}{Recessions} && \\multicolumn{1}{c}{Full sample} & \\multicolumn{1}{c}{Recessions} \\\\",
         tbl[4:length(tbl)])
writeLines(tbl,filename)

################################################################################
# Table: Kolmogorov-Smirnov tests of distributions of AI vs SPF forecasts

for (ii in mapping$id) {
  
  data_long_ii <- data_long_all_individual |> dplyr::filter(id %in% ii)
  
  stats::ks.test(data_long_ii |> 
                   dplyr::filter(forecast_type %in% survey_names[1]) |>
                   dplyr::pull(forecast),
                 data_long_ii |> 
                   dplyr::filter(forecast_type %in% survey_names[2]) |>
                   dplyr::pull(forecast))  
}

################################################################################
# Figure: Scatter plot of AI and SPF individual forecasts

# Match individual forecasts by lowest forecast error
data_long_all_individual$forecast_error <- err(data_long_all_individual |> 
                                                 dplyr::select(forecast,realized))

data_all_individuals_match <- data_long_all_individual |>
  dplyr::left_join(number_forecasters |> 
                     dplyr::select(-forecast_type_ordered) |>
                     tidyr::pivot_wider(names_from=forecast_type,
                                        values_from=n) |>
                     dplyr::rename_with(~c("n_AI","n_Human"),survey_names), 
                   by=c("date_q","id")) |>
  dplyr::mutate(n = pmin(n_AI,n_Human)) |>
  dplyr::group_by(date_q,forecast_type,id) |>
  dplyr::arrange(abs(forecast_error)) |>
  dplyr::slice(1:n) |>
  dplyr::mutate(idx = 1:n) |>
  dplyr::ungroup() |>
  dplyr::select(-c(id_forecast,n,n_AI,n_Human,id_realized,forecast_error)) |>
  tidyr::pivot_wider(names_from = forecast_type, values_from = forecast)
 
ii=3
p <- ggplot2::ggplot(data_all_individuals_match) +
  ggplot2::geom_point(ggplot2::aes(x=get(survey_names[2]),
                                   y=get(survey_names[1]))) +
  ggplot2::geom_abline(intercept = 0, slope = 1)

pdf(paste0("figures/scatter_ai_spf_",mapping[ii,"id"],".pdf"), width=w, height=h)
print(p)
dev.off()

################################################################################
# Table: Regress AI vs SPF individual forecasts 

filename = 'tables/regress_ai_spf.txt'

mdl_list <- list()
wald_list <- list()

for (ii in 1:dim(mapping)[1]) {
  
  mdl_list[[ii]] <- lm(
    formula = get(survey_names[2]) ~ get(survey_names[1]),
    data = data_all_individuals_match)
  
  wald_list[[ii]] <- car::linearHypothesis(mdl_list[[ii]], 
                                           c("(Intercept) = 0",
                                             'get(survey_names[1]) = 1'),
                                           test="Chisq")
  
}

modelsummary::msummary(mdl_list,
                       stars=TRUE,
                       gof_map = gof_map,
                       coef_map = c('(Intercept)' = 'Intercept',
                                    'get(mapping[ii, "id_ai"])' = 'Coefficient'),
                       output = gsub('txt','tex',filename),
                       fmt = 2)

# Format table
tbl <- read.delim(gsub('txt','tex',filename))
tbl <- tbl[3:dim(tbl)[1]-1,1]
idx <- which(grepl("\\toprule",tbl,fixed=T))
num_col <- stringr::str_count(tbl[length(tbl)-3],"&")+1
tbl <- tbl[idx:(length(tbl)-1)]
tbl <- c(tbl[1:2], 
         paste('&',paste(paste0('\\multicolumn{1}{c}{',mapping$label,'}'), collapse=' & '),'\\\\ \\midrule'), 
         tbl[3:length(tbl)])
tbl <- gsub("*** ","^{***} ",tbl,fixed=T)
tbl <- gsub("** ","^{**} ",tbl,fixed=T)
tbl <- gsub("* ","^{*} ",tbl,fixed=T)
tbl <- gsub("+ ","^{+} ",tbl,fixed=T)
tbl <- c(paste0("\\begin{tabular}{l",paste(replicate(num_col-1, "d{1.2}"), collapse = ""),"}"),
         tbl,
         paste0("\\multicolumn{",num_col,"}{r}{\\rule{0pt}{1em}+ p < 0.1, * p < 0.05, ** p < 0.01, *** p < 0.001}"),
         "\\end{tabular}")

idx.NumObs <- which(grepl("Num.Obs.",tbl,fixed=T))
row.NumObs <- strsplit(tbl[idx.NumObs]," ") |> unlist()
NumObs <- strtoi(row.NumObs) 
row.NumObs[!(is.na(NumObs))] <- paste0('\\multicolumn{1}{c}{',NumObs |> na.omit(),'}')
tbl[idx.NumObs] <- paste(row.NumObs, collapse=' ')
tbl <- c(tbl[1:idx.NumObs-1],"\\midrule",tbl[idx.NumObs:length(tbl)])

idx.R2 <- which(grepl("R2",tbl,fixed=T))
row.R2 <- strsplit(tbl[idx.R2]," ") |> unlist()
R2 <- R2 <- as.double(row.R2)
row.R2[!(is.na(R2))] <- paste0(round(na.omit(R2),2))
tbl[idx.R2] <- paste(row.R2, collapse=' ')

# Appendix test coefficients?
#wald_list

# Save table and remove temp tex file
write(tbl,file=filename)
file.remove(gsub('txt','tex',filename))

################################################################################
# Figure: Plot time series of forecast errors of SPF and AI

for (ii in 1:nrow(mapping)) {
  
  p <- ggplot2::ggplot(data = data_ts |> 
                         dplyr::filter(id %in% mapping[ii,"id"]),
                       ggplot2::aes(x=date_q, y=forecast_error)) +
    ggplot2::geom_line(ggplot2::aes(color=forecast_type_ordered, 
                                    size=forecast_type_ordered)) +
    ggplot2::scale_color_manual(values=c("darkgray", "black")) +
    ggplot2::scale_y_continuous(labels = function(x) paste0(x, "%")) +
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
                   legend.position="none")
  
  pdf(paste0("figures/forecast_error_",mapping[ii,"id"],".pdf"), 
      width=w/2, height=h*0.6)
  print(p)
  dev.off()
  
}

################################################################################
# Table: Forecast accuracy of AI and SPF median forecasts 

filename = 'tables/forecast_accuracy_ai_spf.txt'

accuracy <- data_ts |>
  dplyr::filter(id %in% mapping$id) |>
  dplyr::group_by(id,forecast_type) |>
  dplyr::summarise_at("forecast_error",mae) |>
  dplyr::left_join(
    data_ts |> dplyr::filter(nber_rec==1) |>
    dplyr::group_by(id,forecast_type) |>
    dplyr::summarise_at("forecast_error",mae) |>
    dplyr::rename("forecast_error_rec"="forecast_error"),
    by=c("id","forecast_type")) |>
  dplyr::ungroup() |>
  dplyr::left_join(mapping |> dplyr::select(id,label), by="id") |>
  dplyr::mutate(empty=NA) |>
  tidyr::pivot_wider(names_from="forecast_type",
                     values_from=c("forecast_error","forecast_error_rec")) |>
  dplyr::select("label",
                paste0("forecast_error_",survey_names[1]),
                paste0("forecast_error_rec_",survey_names[1]),
                "empty",
                paste0("forecast_error_",survey_names[2]),
                paste0("forecast_error_rec_",survey_names[2]))

# Create table with designated filename
writeLines(knitr::kable(accuracy, "latex", 
                        digits=2, 
                        align = c('l',rep('d{1.2}',2),'l',rep('d{1.2}',2)), 
                        booktabs=T),
           filename)

tbl <- readLines(filename)
tbl <- tbl[(tbl=="")==F] # Remove empty lines (typically first line)
tbl <- tbl[(tbl=="\\addlinespace")==F] # Remove "\\addlinespace" lines
tbl <- c(tbl[1:2],
         " & \\multicolumn{2}{c}{AI forecasts} && \\multicolumn{2}{c}{SPF forecasts} \\\\",
         " \\cmidrule{2-3} \\cmidrule{5-6}",
         "& \\multicolumn{1}{c}{Full sample} & \\multicolumn{1}{c}{Recessions} && \\multicolumn{1}{c}{Full sample} & \\multicolumn{1}{c}{Recessions} \\\\",
         tbl[4:length(tbl)])
writeLines(tbl,filename)


################################################################################
# Table: Regress characteristics on forecast errors and AI-Human differences

filename = 'tables/regress_characteristicsf.txt'

tmp <- data |> 
  tidyr::pivot_longer(all_of(mapping$id_ai), 
                      names_to = "id_forecast",
                      values_to = "forecast") |>
  dplyr::select(c(date_q,id_forecast,forecast,characteristics)) |>
  dplyr::left_join(data_long |>
                     dplyr::select(date_q,id_forecast,realized) |>
                     unique(),
                   by = c("date_q","id_forecast")) |>
  dplyr::mutate(forecast_error = forecast-realized)

mdl_list <- list()

for (ii in 1:dim(mapping)[1]) {
  
  tmp_ii <- tmp |>
    dplyr::filter(id_forecast %in% mapping[ii,'id_ai'])
  
  mdl_list[[ii]] <- plm::plm(
    formula = forecast ~ get(characteristics[1]),
    data = tmp_ii)
  
}

modelsummary::msummary(mdl_list,
                       stars=TRUE,
                       gof_map = gof_map,
                       coef_map = c('(Intercept)' = 'Intercept',
                                    'get(mapping[ii, "id_ai"])' = 'Coefficient'),
                       output = gsub('txt','tex',filename),
                       fmt = 2)

# Format table
tbl <- read.delim(gsub('txt','tex',filename))
tbl <- tbl[3:dim(tbl)[1]-1,1]
idx <- which(grepl("\\toprule",tbl,fixed=T))
num_col <- stringr::str_count(tbl[length(tbl)-3],"&")+1
tbl <- tbl[idx:(length(tbl)-1)]
tbl <- c(tbl[1:2], 
         paste('&',paste(paste0('\\multicolumn{1}{c}{',mapping$label,'}'), collapse=' & '),'\\\\ \\midrule'), 
         tbl[3:length(tbl)])
tbl <- gsub("*** ","^{***} ",tbl,fixed=T)
tbl <- gsub("** ","^{**} ",tbl,fixed=T)
tbl <- gsub("* ","^{*} ",tbl,fixed=T)
tbl <- gsub("+ ","^{+} ",tbl,fixed=T)
tbl <- c(paste0("\\begin{tabular}{l",paste(replicate(num_col-1, "d{1.2}"), collapse = ""),"}"),
         tbl,
         paste0("\\multicolumn{",num_col,"}{r}{\\rule{0pt}{1em}+ p < 0.1, * p < 0.05, ** p < 0.01, *** p < 0.001}"),
         "\\end{tabular}")

idx.NumObs <- which(grepl("Num.Obs.",tbl,fixed=T))
row.NumObs <- strsplit(tbl[idx.NumObs]," ") |> unlist()
NumObs <- strtoi(row.NumObs) 
row.NumObs[!(is.na(NumObs))] <- paste0('\\multicolumn{1}{c}{',NumObs |> na.omit(),'}')
tbl[idx.NumObs] <- paste(row.NumObs, collapse=' ')
tbl <- c(tbl[1:idx.NumObs-1],"\\midrule",tbl[idx.NumObs:length(tbl)])

idx.R2 <- which(grepl("R2",tbl,fixed=T))
row.R2 <- strsplit(tbl[idx.R2]," ") |> unlist()
R2 <- R2 <- as.double(row.R2)
row.R2[!(is.na(R2))] <- paste0(round(na.omit(R2),2))
tbl[idx.R2] <- paste(row.R2, collapse=' ')

# Appendix test coefficients?
#wald_list

# Save table and remove temp tex file
write(tbl,file=filename)
file.remove(gsub('txt','tex',filename))

