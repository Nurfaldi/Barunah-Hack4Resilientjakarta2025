# load library
library(sf)
library(tidyverse)
library(janitor)
library(here)

# set working directory
source("code/utils.R")
ensure_root()

# list all datasets available
data_dir <- normalizePath(file.path("data"), mustWork = TRUE)

data_paths <- list.files(
  path = data_dir,
  pattern = "(?i)\\.(shp|tif)$", # only .shp and .tif
  recursive = TRUE,
  full.names = TRUE,
  ignore.case = TRUE
)

files_tbl <- tibble(full_path = data_paths) %>%
  mutate(
    file_ext  = tolower(tools::file_ext(full_path)),
    file_type = dplyr::case_when(
      file_ext == "shp" ~ "vector",
      file_ext == "tif" ~ "raster",
      TRUE ~ NA_character_
    ),
    # folder relative to data/ (strip leading "data/" or "../data/")
    folder_path = dirname(full_path),
    folder_name = {
      # escape backslashes in data_dir for a safe regex
      dd <- gsub("\\\\", "\\\\\\\\", data_dir)
      # remove the leading data_dir and any following slash/backslash
      rel <- sub(paste0("^", dd, "[/\\\\]?"), "", folder_path)
      ifelse(rel == "" | rel == ".", ".", rel)
    },
    file_name = basename(full_path)
  ) %>%
  select(folder_name, file_name, file_type) %>%
  arrange(folder_name)

# data wrangling
## age dataset
age_long  <- load_shapefiles_bind(
  data_dir = "data/extracted_data/22 Age/Population based on Age",
  pattern = "^socioeconomic_age_\\d{4}\\.shp$",
  year_regex = "\\d{4}",
  year_col = "year",
  keep_geom = FALSE,
  quiet = TRUE
)

age_wide  <- age_long %>% 
  pivot_wider(
    id_cols = c("objectid","wadmkd","year"),
    names_from = "age",
    names_prefix = "age_",
    values_from = "pop"
  ) %>% 
  clean_names()

age_df  <- age_wide %>% 
  rowwise() %>% 
  transmute(
    objectid, wadmkd, year,
    age_young = (age_00_04 + age_05_09)/sum(c_across(starts_with("age_"))), # extending the range of vulnerable age groups
    age_old = (age_65_69 + age_70_74 + age_74)/sum(c_across(starts_with("age_")))
  ) %>% 
  ungroup()

## gender dataset
gender_long  <- load_shapefiles_bind(
  data_dir = "data/extracted_data/24 Gender",
  pattern = "^socioeconomic_gender_\\d{4}\\.shp$",
  year_regex = "\\d{4}",
  year_col = "year",
  keep_geom = FALSE,
  quiet = TRUE
)

gender_df  <- gender_long %>% 
  transmute(
    objectid, wadmkd, year,
    female_pop = p/l_p
  )

## education dataset

