fig_lasso_characteristics <- function() {
  
  variables_select = variables$variable #c("CPI","TBILL","RGDP","UNEMP")
  
  for (ii in horizons$id) {
    
    beta_list <- list()
    count = 0 
    for (jj in variables_select) {  
    
      count = count+1
    
      Y <- data_long |>
        dplyr::filter(variable %in% jj,
                      id %in% ii,
                      type %in% "AI") |>
        dplyr::select(date_q,Name,value,all_of(kk)) |>
        dplyr::left_join(data_long |> 
                           dplyr::filter(id %in% ii,
                                         variable %in% jj,
                                         type %in% "Realized") |>
                           dplyr::select(date_q,value) |>
                           dplyr::rename("Realized" = "value") |>
                           unique(),
                         by="date_q") |>
        dplyr::mutate(forecast_error = abs((value-Realized)/Realized),
                      forecast_error = ifelse(forecast_error %in% c(-Inf,Inf),NA,forecast_error)) |>
        na.omit() |>
        unique() 
      
      X <- Y |> 
        dplyr::mutate(gender_Male = ifelse(gender2=="Male",1,0),
                      gender_Female = ifelse(gender2=="Female",1,0),
                      cohort_1969 = ifelse(cohort=="-1969",1,0),
                      cohort_1970_1989 = ifelse(cohort=="1970-1989",1,0),
                      cohort_1990_2009 = ifelse(cohort=="1990-2009",1,0),
                      cohort_2010_ = ifelse(cohort=="2010-",1,0),
                      continent_origin_Asia = ifelse(continent_origin=="Asia",1,0),
                      continent_origin_Europe = ifelse(continent_origin=="Asia",1,0),
                      continent_origin_USA = ifelse(continent_origin=="USA",1,0),
                      continent_origin_Americas = ifelse(continent_origin=="Americas (excl. USA)",1,0),
                      social_media_interviews = ifelse(social_media_status2=="Interviews only",1,0),
                      social_media_interviews_twitter = ifelse(social_media_status2=="Interviews + Twitter",1,0),
                      social_media_twitter = ifelse(social_media_status2=="Twitter only",1,0),
                      social_media_none = ifelse(social_media_status2=="No public appearance",1,0),
                      education_level_master = ifelse(education_level=="Master's",1,0),
                      education_level_bachelor = ifelse(education_level=="Bachelor's",1,0),
                      education_level_mba = ifelse(education_level=="MBA/MPA",1,0),
                      education_level_phd = ifelse(education_level=="Ph.D.",1,0),
                      education_field_econfin = ifelse(education_field=="Economics/Finance",1,0),
                      education_field_publicadmin = ifelse(education_field=="Public Administration",1,0),
                      education_field_busmgmt = ifelse(education_field=="Business/Management",1,0),
                      education_field_econstat = ifelse(education_field=="Econometrics/Statistics",1,0),
                      education_field_law = ifelse(education_field=="Law",1,0),
                      affiliation_cons = ifelse(affiliation_type2=="Consulting",1,0),
                      affiliation_univ = ifelse(affiliation_type2=="University",1,0),
                      affiliation_manuf = ifelse(affiliation_type2=="Manufacturing",1,0),
                      affiliation_invbank = ifelse(affiliation_type2=="Investment Banking",1,0),
                      affiliation_commbank = ifelse(affiliation_type2=="Commercial Banking",1,0),
                      affiliation_assetmgmt = ifelse(affiliation_type2=="Asset Management",1,0),
                      title_chief = ifelse(title2=="Chief Economist",1,0),
                      title_economist = ifelse(title2=="Economist",1,0),
                      title_executive = ifelse(title2=="Executive Role",1,0),
                      title_academic = ifelse(title2=="Academic Role",1,0),
                      title_consultant = ifelse(title2=="Consultant/Analyst",1,0)
        ) |>
        dplyr::select("gender_Male":"title_consultant")
      
      groupindex <- seq(1,dim(X)[2],1)
      #groupindex <- c(rep(1,2),rep(2,4),rep(3,4),rep(4,4),rep(5,4),rep(6,5),rep(7,6),rep(8,5))
      
      mdl <- midasml::reg.panel.sgl(x = X, 
                                    y = Y$forecast_error, 
                                    gindex = groupindex, 
                                    method = "pooled")
    
      beta_list[[count]] <- mdl$ic.fit$aic.fit$beta
        
    }
    
    dat <- do.call(cbind,beta_list)
    
    quantile_breaks <- function(xs, n = 10) {
      breaks <- quantile(xs, probs = seq(0, 1, length.out = n))
      breaks[!duplicated(breaks)]
    }
    
    mat_breaks <- quantile_breaks(dat, n = 80)
    
    dat <- as.data.frame(dat)
    names(dat) <- variables$variable_longname
    row.names(dat) <- c(
      "Gender: Male",
      "Gender: Female",
      "Graduation year: -1969",
      "Graduation year: 1970-1989",
      "Graduation year: 1990-2009",
      "Graduation year: 2010-",
      "Origin: Asia",
      "Origin: Europe",
      "Origin: USA",
      "Origin: Americas (excl. USA)",
      "Public appearance: Interviews Only",
      "Public appearance: Interviews + Twitter",
      "Public appearance: Twitter Only",
      "Public Appearance: None",
      "Education level: Master's",
      "Education level: Bachelors's",
      "Education level: MBA/MPA",
      "Education level: Ph.D.",
      "Education field: Economics/Finance",
      "Education field: Public Administration",
      "Education field: Business/Management",
      "Education field: Econometrics/Statistics",
      "Education field: Law",
      "Affiliation: Consulting",
      "Affiliation: University",
      "Affiliation: Manufacturing",
      "Affiliation: Investment Banking",
      "Affiliation: Commercial Banking",
      "Affiliation: Asset Management",
      "Title: Chief Economist",
      "Title: Economist",
      "Title: Executive Role",
      "Title: Academic Role",
      "Title: Consultant"
    )
    
    pheatmap::pheatmap(dat, 
                       display_numbers = TRUE, 
                       color = colorRampPalette(c('darkblue','white','#D55E00'))(8), 
                       breaks = c(-20,-10,-0.1,-0.005,0,0.005,0.1,10,20),
                       cluster_rows = FALSE, 
                       cluster_cols = FALSE, 
                       fontsize_number = 6,
                       fontsize_row = 6,
                       fontsize_col = 6,
                       show_rownames = TRUE,
                       show_colnames = TRUE,
                       legend = FALSE,
                       filename = paste0("figures/lasso_characteristics_aic_",ii,".pdf"),
                       width=w*1.025, 
                       height=h*1.75)
    
  }
  
 
}