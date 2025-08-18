# load data for 2024's selected data

# load library
library(sf)
library(tidyverse)
library(janitor)
library(here)

source("code/utils.R")
ensure_root()

# load data
## neighborhood
nb_raw  <- st_read("data/extracted_data/02 GIS Data (Neighborhood & Grid levels)/Neighborhoods/Neighborhoods_5.0.shp") %>% 
  st_drop_geometry() %>% 
  clean_names()

kel_geom  <- st_read("data/extracted_data/01 Area of Interest/Kelurahan/adm_dki-jakarta_kelurahan.shp") %>% 
  clean_names() %>% 
  select(id_obj = objectid, id_kel = wadmkd) %>% 
  st_make_valid()


## sensitivity
### age old and young

age_df  <- st_read("data/extracted_data/22 Age/Population based on Age/socioeconomic_age_2024.shp") %>% 
  st_drop_geometry() %>% 
  clean_names() %>% 
    pivot_wider(
    id_cols = c("objectid","wadmkd"),
    names_from = "age",
    names_prefix = "age_",
    values_from = "pop"
  ) %>% 
  clean_names() %>% 
  rowwise() %>% 
  transmute(
    objectid, wadmkd,
    age_young = (age_00_04 + age_05_09)/sum(c_across(starts_with("age_"))), # extending the range of vulnerable age groups
    age_old = (age_65_69 + age_70_74 + age_74)/sum(c_across(starts_with("age_")))
  ) %>% 
  ungroup()

### female population
female_df  <- st_read("data/extracted_data/24 Gender/socioeconomic_gender_2024.shx") %>% 
  st_drop_geometry() %>% 
  clean_names() %>% 
  rowwise() %>% 
  transmute(
    objectid, wadmkd,
    fem_pop = p / l_p
  )

### population growth

popgrowth_df  <- st_read("data/extracted_data/24 Gender/socioeconomic_gender_2023.shp") %>% 
  st_drop_geometry() %>% 
  clean_names() %>% 
  select(objectid, wadmkd, pop_23=l_p) %>% 
  left_join(
    st_read("data/extracted_data/24 Gender/socioeconomic_gender_2024.shp") %>% 
      st_drop_geometry() %>% 
      clean_names() %>% 
      select(objectid, wadmkd, pop_24=l_p),
    by = c("objectid","wadmkd")
  ) %>% 
  transmute(
    objectid, wadmkd,
    pop_growth = (pop_24 - pop_23) / pop_23
  )

## adaptive capacity

### informal residents
infrormalres_df  <- st_read("data/extracted_data/27 Residence Living in Informal Settlements/socioeconomic_informal_residence_2023.shp") %>% 
  st_drop_geometry() %>% 
  clean_names() %>% 
  select(objectid, wadmkd, n_informal = total)

### resident area
areares_sf  <- st_read("data/extracted_data/06 Proportion of Residential Area/proportion_residential_area.shp")

areares_sf %>% st_crs

areares  <- st_read("data/extracted_data/06 Proportion of Residential Area/proportion_residential_area.shp") %>% 
  st_drop_geometry() %>% 
  clean_names() %>% 
  transmute(wadmkd, shape_area) %>% 
  summarise(
    res_area = sum(shape_area*1000000),
    .by = wadmkd
  ) %>% 
  ungroup()

### length of drainage
primary_raw  <- st_read("data/extracted_data/08 Drainage system data/Primary Drainage System/Saluran_Drainase_Primer.shp")
secondary_raw  <- st_read("data/extracted_data/08 Drainage system data/Secondary Drainage System/Saluran_Drainase_Sekunder.shp")
tertiary_raw  <- st_read("data/extracted_data/08 Drainage system data/Tertiary Drainage System/Saluran_Drainase_Tersier.shp")

## merge data

all_indicators  <- nb_raw %>% 
  select(
    objectid = objectid_1, wadmkd,
    pop_dens24,
    low_edu24,
    drn_sys,
    dist_rv,
    dist_coast = dtc,
    flo_depth24,
    flo_freq24 = flood24,
    land_sub24,
    n_pump = pumps_lc,
    imperv_area = mibcb
  ) %>% 
  left_join(
    age_df,
    by = c("objectid", "wadmkd")
  ) %>% 
  left_join(
    female_df,
    by = c("objectid","wadmkd")
  ) %>% 
  left_join(
    popgrowth_df,
    by = c("objectid","wadmkd")
  ) %>% 
  left_join(
    infrormalres_df,
    by = c("objectid","wadmkd")
  ) %>% 
  rename(
    id_obj = objectid,
    id_kel = wadmkd
  )

all_indicators_z  <- all_indicators %>% 
  mutate(
    across(
      .cols = -starts_with("id_"),
      .fns = zscore_safe
    )
  ) %>% 
  mutate(
    drn_sys = -1 * drn_sys,
    dist_rv = -1 * dist_rv,
    dist_coast = -1 * dist_coast,
    n_pump = -1 * n_pump
  )

  scvi_df <- all_indicators_z %>% 
    transmute(
      id_obj, id_kel,
      sensitivity_index = rowSums(across(c(age_young, age_old, fem_pop, pop_dens24, pop_growth)), na.rm = TRUE),
      adaptive_index    = rowSums(across(c(low_edu24, drn_sys, n_pump, imperv_area, n_informal)), na.rm = TRUE),
      hazard_index      = rowSums(across(c(dist_rv, dist_coast, flo_depth24, flo_freq24, land_sub24)), na.rm = TRUE),
      scvi              = rowSums(across(ends_with("index")), na.rm = TRUE)
    )
  

scvi_sf <- kel_geom %>% 
  left_join(
    scvi_df,
    by = c("id_obj","id_kel")
  ) %>% 
  st_cast("MULTIPOLYGON") %>% 
  st_as_sf()

st_write(scvi_sf, "data/processed_data/scvi_jakarta_2024.geojson", driver = "GeoJSON")

scvi_plot <- ggplot(scvi_sf) +
  geom_sf(
    aes(
      fill = scvi,
      text = paste0(
        "Kelurahan: ", str_to_title(id_kel), "<br>",
        "SCVI: ", round(scvi, 2)
      )
    ),
    color = "white", size = 0.2
  ) +
  scale_fill_gradient(low = "#fdf2e9", high = "#499c8d", name = "SCVI") +
  theme_minimal()

# plotly will use the "text" aesthetic for tooltips
scvi_plotly  <- ggplotly(scvi_plot, tooltip = "text")

saveWidget(scvi_plotly,"kelurahan_scvi.html", selfcontained = TRUE)
