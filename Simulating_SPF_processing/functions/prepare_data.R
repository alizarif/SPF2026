
prepare_data <- function(input_filename="data/multivariable_SPF6.xlsx",
                         output_filename="data/baseline_data.rda") {

# Names of surveys (AI first, then human SPF)
survey_names <- c("AI","Human")

# Define horizons between Human and AI forecasts incl. their labels
horizons_full <- data.frame(
  label = c("Current quarter","One quarter ahead","Two quarters ahead",
            "Three quarters ahead","Four quarters ahead","Current year",
            "One year ahead"),
  id_human_output = c("2","3","4","5","6","A","B"),
  id_human = c("H0","H1","H2","H3","H4","HA","HB"),
  id_ai_output = c("t","t+1","t+2","t+3","t+4","y1","y2"),
  id_ai = c("A0","A1","A2","A3","A4","AA","AB"),
  id_realized = c("R0","R1","R2","R3","R4","RA","RB"),
  id = c(0,1,2,3,4,"A","B")
)

# Select which forecast to include
if (grepl("outofsample",input_filename)) {
  horizons <- horizons_full[c(1,2,3),]
} else {
  horizons <- horizons_full[c(1,2,5),]  
}

# Load overview of variable names
variables <- read.csv("data/data_overview.csv")
variables <- variables[-c(1,13,14,23,24),]
variables <- variables |>
  dplyr::rename("variable"="SPF.data.name",
                "variable_real_time_data"="Real.time.market.data.name",
                "variable_AI_output"="AI.output.names") |>
  dplyr::mutate(variable_realized = paste0(variable,"_R"))

# Load model output
output <- readxl::read_excel(input_filename) 

# OOS: Remove crazy outliers
if (input_filename == "data/merged_results_spf_format_oos.xlsx") {
  output <- output |>
    dplyr::filter(`GDP Price Index_t`<10000)
  
  output[which(output$`GDP Price Index_t`<10),'GDP Price Index_t'] = 100*output[which(output$`GDP Price Index_t`<10),'GDP Price Index_t']
  output[which(output$`GDP Price Index_t+1`<10),'GDP Price Index_t+1'] = 100*output[which(output$`GDP Price Index_t+1`<10),'GDP Price Index_t+1']
  output[which(output$`GDP Price Index_t+2`<10),'GDP Price Index_t+2'] = 100*output[which(output$`GDP Price Index_t+2`<10),'GDP Price Index_t+2']
  output[which(output$`GDP Price Index_t+3`<10),'GDP Price Index_t+3'] = 100*output[which(output$`GDP Price Index_t+3`<10),'GDP Price Index_t+3']
  output[which(output$`GDP Price Index_t+4`<10),'GDP Price Index_t+4'] = 100*output[which(output$`GDP Price Index_t+4`<10),'GDP Price Index_t+4']
  output[which(output$`GDP Price Index_y1`<10),'GDP Price Index_y1'] = 100*output[which(output$`GDP Price Index_y1`<10),'GDP Price Index_y1']
  output[which(output$`GDP Price Index_y2`<10),'GDP Price Index_y2'] = 100*output[which(output$`GDP Price Index_y2`<10),'GDP Price Index_y2']
}

# Recall: Add BAA from later run..
if (input_filename == "data/generic_forecaster_results_fixed.xlsx") {
  output2 <- readxl::read_excel('data/generic_forecaster_recall_fixed.xlsx')
  output <- output |> dplyr::left_join(output2[,c('Date_Q','BAA Corp Bond Yield_t')])  
}

if (any(names(output)=='Ablation_Type')) {
  output = output |> dplyr::select(-c('Ablation_Type')) 
}

if (!(input_filename %in% c("data/merged_file_llama_70b_cleaned.xlsx","data/merged_file_deepseek_cleaned.xlsx"))) {
  output <- output |>
    dplyr::mutate(date_q = lubridate::as_date(Date_Q)) 
  
} else {
  output <- output |>
    dplyr::mutate(date_q = lubridate::as_date(output$Date_Q,'format','%Y Q%q'))
}

if (grepl("outofsample",input_filename)) {
  output <- output |>
    dplyr::filter(date_q >= '2024-01-01')
}

if("Index" %in% colnames(output)) {
  output <- output |> dplyr::select(-Index)
}
  
if("Name" %in% colnames(output)) {
  output <- output |>
  dplyr::filter(!(Name %in% "No Name Provided"))
} else {
  output$Name <-NA  
}

# Extract AI survey forecasts
if (input_filename %in% "data/merged_file_multi_N_runs_cleaned.xlsx") {
  output <- output |> dplyr::select(-'Run')
}

ai_survey <- output |>
  dplyr::select(c(date_q,Name)) |>
  dplyr::bind_cols(output |> 
                     dplyr::select(-c(date_q,Name,Date_Q,`Initial Instruction`,`Initial Prompt`,
                                      `Initial Response`,`Initial Instruction Response`,
                                      `Follow-up Prompt`,`Follow-up Instruction`,
                                      `Follow-up Response`,`Forecasts`,`Reasoning Prompt`,
                                      `Reasoning Instruction`,`Reasoning Response`)))

ai_variables <- stringr::str_split(
  names(ai_survey |> 
          dplyr::select(-c(date_q,Name))), 
  stringr::fixed("_"))

names(ai_survey) <- c("date_q","Name", lapply(ai_variables, 
                                              function(x) {
                                                paste0(variables[variables$variable_AI_output==x[1],"variable"],"_",
                                                       horizons_full[horizons_full$id_ai_output==x[2],"id_ai"])}) |>
                        unlist())

# Load characteristics, human forecasts, and real-time data 
addendum <- read.csv("data/individual_forecasters.csv") |>
  dplyr::mutate(date_q = lubridate::as_date(date_q,format="%Y Q%q")) |>
  dplyr::select(-unique_id) |> 
  dplyr::filter(!(Name %in% "No Name Provided")) |>
  unique() |>
  dplyr::mutate(cpi_0 = cpi)

# Characteristics
characteristics <- addendum |>
  dplyr::select(date_q, Name, affiliation, is_first_time, affiliation_type, 
                afilliation_types, gender, title, titles, graduation_year, 
                education, alma.mater, country_origin, company_location, 
                linkedin, homepage, notes, interviews, social_media, twitter, 
                social_media_status)
characteristics_names <- names(characteristics)

# Human forecasts
# human_survey <- addendum |> 
#   dplyr::select(date_q,
#                 lapply(variables$variable,
#                        function(x) {paste0(x,horizons_full$id_human_output)}) |> 
#                   unlist()) |>
#   unique()
# names(human_survey) <- c("date_q", 
#                          lapply(variables$variable,
#                                 function(x) {paste0(x,"_",horizons_full$id_human)}) |> 
#                            unlist())

human_survey <- read.csv('data/SPF_full_ts.csv') |>
  dplyr::mutate(date_q = lubridate::as_date(date_q,format="%Y Q%q")) |> 
  dplyr::select(date_q,
                lapply(variables$variable,
                       function(x) {paste0(x,horizons_full$id_human_output)}) |> 
                  unlist()) |>
  unique()
human_survey <- cbind(human_survey$date_q,as.data.frame(sapply(human_survey |> dplyr::select(-date_q), as.numeric)))
names(human_survey) <- c("date_q", 
                         lapply(variables$variable,
                                function(x) {paste0(x,"_",horizons_full$id_human)}) |> 
                           unlist())

# Construct realized forecasts
realized_lagged <- read.csv("data/median_and_realtime_formatted.csv") |>
  dplyr::mutate(date_q = lubridate::as_date(date_q,format="%Y Q%q")) |> 
  dplyr::select(date_q,variables$variable_real_time_data[variables$variable_real_time_data != ""]) |>
  unique() 

T <- dim(realized_lagged)[1]
N <- dim(realized_lagged)[2]

realized_post2023q4 <- read.csv("data/realized_post2023q4.csv") |> t() |> as.data.frame()
names(realized_post2023q4) <- realized_post2023q4[1,]
realized_post2023q4 <- realized_post2023q4[2:dim(realized_post2023q4)[1],]
realized_post2023q4$date_q <- lubridate::as_date(gsub("X","",row.names(realized_post2023q4)),format="%Yq%q")
row.names(realized_post2023q4) = c() 
realized_post2023q4 <- cbind(realized_post2023q4$date_q,as.data.frame(sapply(realized_post2023q4, as.numeric)) |> dplyr::select(variables$variable))
names(realized_post2023q4)[1] = 'date_q'

realized <- data.frame(date_q = realized_lagged$date_q[1:(T-1)]) |>
  dplyr::bind_cols(realized_lagged[2:T,2:N]) |>
  dplyr::rename_with(~variables$variable[variables$variable_real_time_data != ""],
                     variables$variable_real_time_data[variables$variable_real_time_data != ""]) |>
  dplyr::left_join(read.csv("data/PQvQd.csv") |>
                     dplyr::mutate(date_q = lubridate::as_date(DATE,format="%Y:Q%q"),
                                   PGDP = P24Q3) |>
                     dplyr::select(date_q,PGDP)) |> 
  dplyr::select(c(date_q,variables$variable)) |>
  dplyr::bind_rows(realized_post2023q4) |> 
  tidyr::pivot_longer(-date_q,names_to = "variable",
                      values_to = "value") |>
  dplyr::left_join(variables, by="variable") |>
  dplyr::select(c("date_q","variable_realized","value")) |>
  tidyr::pivot_wider(names_from = "variable_realized", values_from = "value") 

construct_realized <- function(varname) {
  out <- realized |> 
    dplyr::select(varname) |>
    dplyr::mutate(V1 = dplyr::lead(get(varname),1),
                  V2 = dplyr::lead(get(varname),2),
                  V3 = dplyr::lead(get(varname),3),
                  V4 = dplyr::lead(get(varname),4),
                  V5 = NA,
                  V6 = NA
    )
  names(out) <- paste0(varname,c("0","1","2","3","4","A","B"))
  return(out)
}

realized <- realized |>
  dplyr::select(date_q) |>
  dplyr::bind_cols(do.call(cbind.data.frame, lapply(variables$variable_realized,construct_realized)))

# Starting dates
start_dates <- data.frame(
  variable = c("EMP","BAABOND","TBOND","CORECPI","PCE","COREPCE"),
  start_date = as.Date(c("2003-07-01","2010-01-01","1992-01-01","2007-01-01","2007-01-01","2007-01-01"))
)

# Merge data sets
data <- ai_survey |> 
  dplyr::left_join(characteristics, by=c("Name","date_q")) |>
  dplyr::left_join(human_survey, by=c("date_q")) |>
  dplyr::left_join(realized, by=c("date_q"))

if (length(output$Name |> unique())>1) {
  
  # Characteristics
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
        grepl("Finance", education, fixed=T) ~ "Economics/Finance",
        grepl("J.D.", education, fixed=T) ~ "Law",
        grepl("Law", education, fixed=T) ~ "Law",
        grepl("Management", education, fixed=T) ~ "Business/Management",
        grepl("Business", education, fixed=T) ~ "Business/Management",
        grepl("Public", education, fixed=T) ~ "Public Administration",
        grepl("MPA", education, fixed=T) ~ "Public Administration",
        grepl("Statistics", education, fixed=T) ~ "Econometrics/Statistics",
        grepl("Econometrics", education, fixed=T) ~ "Econometrics/Statistics",
        grepl("Engineering", education, fixed=T) ~ "Econometrics/Statistics"
      ),
      education_field = ifelse(is.na(education_field %in% "<NA>"),"Unknown",education_field),
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
        interviews %in% "yes" & social_media %in% "yes"  ~ "Interviews + Twitter",
        interviews %in% "yes" & social_media %in% c("no",NA,"")  ~ "Interviews only",
        interviews %in% c("no",NA,"") & social_media %in% "yes"  ~ "Twitter only",
        interviews %in% c("no") & social_media %in% c("no") ~ "No public appearance",
        interviews %in% c(NA,"") & social_media %in% c(NA,"") ~ "Unknown")
    )
  
  characteristics_names <- c(characteristics_names,
                             "gender2","continent_origin","education_level",
                             "education_field","cohort","title2","affiliation_type2",
                             "social_media_status2","interviews2")
}

# Permute data to long format (human is median, AI is individual forecasts)
data_long <- data |> 
  tidyr::pivot_longer(cols = -all_of(characteristics_names), 
                      names_to = "id_forecast", 
                      values_to = "value") |>
  dplyr::mutate(id = stringr::str_sub(id_forecast,-1))

tmp <- do.call(rbind.data.frame,stringr::str_split(data_long$id_forecast,'_'))
names(tmp) <- c("V1","V2")
tmp$V3 <- substr(tmp$V2,1,1)

data_long <- data_long |> 
  dplyr::mutate(type = substr(tmp$V2,1,1),
                variable = tmp$V1,
                type = ifelse(type=="A",survey_names[1],
                              ifelse(type=="H",survey_names[2],"Realized")),
                type_ordered = factor(type, levels=c(survey_names[2],
                                                     survey_names[1],
                                                     "Realized"))) |>
  dplyr::left_join(variables |> 
                     dplyr::select(variable_longname,variable),
                   by = c("variable"="variable")) |>
  dplyr::rename("variable_name"="variable_longname")

# FRED data series
fredr::fredr_set_key(Sys.getenv("FRED_API_KEY")) # unique API key for this script/project
nber_rec <- fredr::fredr(series_id = "USREC",
                         observation_start = min(data$date_q),
                         observation_end = max(data$date_q))
epu <- fredr::fredr(series_id = "USEPUINDXD",
                    observation_start = min(data$date_q),
                    observation_end = max(data$date_q)) |>
  na.omit() |>
  dplyr::mutate(quarter = lubridate::quarter(date),
                year = lubridate::year(date)) |>
  dplyr::group_by(quarter,year) |>
  dplyr::slice_min(order_by = date, n=1) |>
  dplyr::ungroup()

vix <- fredr::fredr(series_id = "VIXCLS",
                    observation_start = min(data$date_q),
                    observation_end = max(data$date_q)) |>
  na.omit() |>
  dplyr::mutate(quarter = lubridate::quarter(date),
                year = lubridate::year(date)) |>
  dplyr::group_by(quarter,year) |>
  dplyr::slice_min(order_by = date, n=1) |>
  dplyr::ungroup()

# Define time series
data_ts <- data_long |>
  dplyr::group_by(date_q,type,type_ordered,id,variable,variable_name) |>
  dplyr::summarise_at("value", 
                      list(median = function(x) median(x,na.rm=TRUE),
                           mean = function(x) mean(x,na.rm=TRUE),
                           p25 = function(x) quantile(x,0.25,na.rm=TRUE),
                           p75 = function(x) quantile(x,0.75,na.rm=TRUE),
                           p10 = function(x) quantile(x,0.10,na.rm=TRUE),
                           p90 = function(x) quantile(x,0.90,na.rm=TRUE),
                           min = function(x) min(x,na.rm=TRUE),
                           max = function(x) max(x,na.rm=TRUE))
  ) |>
  dplyr::ungroup() |>
  dplyr::filter(!(type=="Realized")) |>
  dplyr::left_join(data_long |>
                     dplyr::filter(type=="Realized") |>
                     dplyr::select(date_q,variable,value,id) |>
                     dplyr::rename("realized"="value") |>
                     unique())

# Compute forecast errors (removing outliers)
remove_outliers <- function(x, realized) {
  std <- sd(realized,na.rm=T)
  med <- mean(realized,na.rm=T)
  y <- x
  y[y < med-3*std] <- (med-3*std) 
  y[y > med+3*std] <- (med+3*std)
  y
}

data_ts <- data_ts |>
  dplyr::group_by(type,type_ordered,id,variable,variable_name) |>
  dplyr::mutate(median_ = remove_outliers(median,realized)) |>
  dplyr::ungroup() |>
  dplyr::mutate(forecast_error = median_-realized) |>
  unique() |> 
  dplyr::left_join(nber_rec |>
                     dplyr::rename("date_q"="date", "nber_rec"="value") |>
                     dplyr::select(date_q,nber_rec),
                   by="date_q") |>
  dplyr::left_join(vix |>
                     dplyr::rename("date_q"="date", "vix"="value") |>
                     dplyr::select(date_q,vix),
                   by="date_q") |>
  dplyr::left_join(epu |>
                     dplyr::rename("date_q"="date", "epu"="value") |>
                     dplyr::select(date_q,epu),
                   by="date_q")

# Individual SPF forecasts
if (!(grepl("outofsample",input_filename))) {
  
  read_excel_allsheets <- function(filename, tibble = FALSE) {
    sheets <- readxl::excel_sheets(filename)
    x <- lapply(sheets, function(X) readxl::read_excel(filename, sheet = X))
    if(!tibble) x <- lapply(x, as.data.frame)
    names(x) <- sheets
    x
  }
  SPFmicrodata.list <- read_excel_allsheets("data/SPFmicrodata.xlsx")
  
  for (ii in 1:length(SPFmicrodata.list)) {
    
    if (ii==1) {
      SPFmicrodata <- SPFmicrodata.list[[ii]]
    } else {
      SPFmicrodata <- SPFmicrodata |>
        dplyr::left_join(SPFmicrodata.list[[ii]], by=c("YEAR","QUARTER","ID","INDUSTRY"))
    }
    
  }
  
  tmp <- c(1,4,7,10)
  SPFmicrodata$date_q <- as.Date(paste0(SPFmicrodata$YEAR,"-",tmp[SPFmicrodata$QUARTER],"-01"))
  SPFmicrodata <- SPFmicrodata |>
    dplyr::select(-c(YEAR,QUARTER)) |>
    dplyr::mutate(
      INDUSTRY = as.numeric(INDUSTRY),
      SPF_industry_id = dplyr::case_when(
        INDUSTRY %in% 1 ~ "Financial",
        INDUSTRY %in% 2 ~ "Non-Financial", 
        INDUSTRY %in% 3 ~ "Unknown",
        INDUSTRY %in% NA ~ "Unknown"
      ))
  
  SPFmicrodata_long <- SPFmicrodata |>
    tidyr::pivot_longer(cols = -c(date_q,ID,SPF_industry_id,INDUSTRY), 
                        names_to = "id_forecast",
                        values_to = "value") |>
    dplyr::mutate(id_human_output = stringr::str_sub(id_forecast,-1),
                  variable = stringr::str_sub(id_forecast,1,-2),
                  value = as.numeric(value)) |>
    dplyr::filter(variable %in% variables$variable,
                  id_human_output %in% horizons_full$id_human_output) |>
    dplyr::left_join(variables |> 
                       dplyr::select(variable_longname,variable),
                     by = c("variable"="variable")) |>
    dplyr::left_join(horizons_full |>
                       dplyr::select(id,id_human_output)) |>
    dplyr::rename("variable_name"="variable_longname",
                  "SPF_human_id"="ID") |>
    dplyr::select(date_q,id,SPF_human_id,SPF_industry_id,variable,variable_name,value) |>
    dplyr::filter(date_q>=min(data_ts$date_q),
                  date_q<=max(data_ts$date_q)) 
  
}

data_ts_human <- data_ts |>
  dplyr::filter(type == "Human") |>
  dplyr::select(-c("mean","p25","p75","min","max","p10","p90")) |>
  dplyr::left_join(
    SPFmicrodata_long |>
      dplyr::group_by(date_q,id,variable,variable_name) |>
      dplyr::summarise_at("value", 
                          list(mean = function(x) mean(x,na.rm=TRUE),
                               p25 = function(x) quantile(x,0.25,na.rm=TRUE),
                               p75 = function(x) quantile(x,0.75,na.rm=TRUE),
                               p10 = function(x) quantile(x,0.10,na.rm=TRUE),
                               p90 = function(x) quantile(x,0.90,na.rm=TRUE),
                               min = function(x) min(x,na.rm=TRUE),
                               max = function(x) max(x,na.rm=TRUE))) |>
      dplyr::ungroup()) |>
  dplyr::select(names(data_ts))

data_ts <- data_ts |> 
  dplyr::filter(type == "AI") |>
  dplyr::bind_rows(data_ts_human)
   
# Limit horizons to availability of AI survey / chosen horizons
horizons <- horizons |> 
  dplyr::filter(id %in% (data_long |> 
                           dplyr::filter(type == "AI") |> 
                           dplyr::pull(id) |> 
                           unique()))

# Save data
data_wide <- data
characteristics <- c("gender2","continent_origin","education_level",
                     "education_field","cohort","title2","affiliation_type2",
                     "social_media_status2")
save(data_wide, data_long, data_ts, horizons, horizons_full, variables, survey_names, SPFmicrodata_long, characteristics, file = output_filename)

}

