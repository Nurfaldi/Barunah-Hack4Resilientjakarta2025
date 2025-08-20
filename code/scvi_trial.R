# load data for 2024's selected data

# load library
library(sf)
library(tidyverse)
library(janitor)
library(here)
library(osmdata)
library(readxl)
library(htmlwidgets)

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

jakarta_bbox  <- kel_geom %>% st_bbox()

## population factor

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

### occupation
occupation_raw  <- read_xlsx("data/extracted_data/data-jumlah-penduduk-berdasarkan-pekerjaan-per-kelurahan-di-provinsi-dki-jakarta-(1755609354534).xlsx") %>% 
  clean_names() %>% 
  distinct() %>% 
  drop_na() %>% 
  select(wadmkd = nama_kelurahan, jenis_pekerjaan, jumlah) %>% 
  mutate(jumlah = as.integer(jumlah)) %>% 
  pivot_wider(
    id_cols = wadmkd,
    names_from = jenis_pekerjaan,
    values_from = jumlah,
    values_fill = 0
  ) %>% 
  clean_names() %>% 
  mutate(pop = rowSums(across(!contains("wadmkd")), na.rm = TRUE))


unemployment_df  <- occupation_raw %>% 
  transmute(
    wadmkd,
    unemmployment_pop = (belum_tidak_bekerja + pensiunan)/pop
  )

vul_emp  <- c("petani_pekebun","nelayan_perikanan","peternak","karyawan_honorer","tukang_cukur","tukang_listrik",
"buruh_harian_lepas", "pembantu_rumah_tangga","buruh_nelayan_perikanan","tukang_batu","buruh_tani_perkebunan",
"buruh_perternakkan","tukang_las_pandai_besi","tukang_jahit","tukang_sol_sepatu","tukang_kayu","guru","tukang_gigi",
"perawat","mekanik","sopir","belum_tidak_bekerja")

vulemp_df  <- occupation_raw %>% 
  mutate(vulemp = rowSums(across(all_of(vul_emp)), na.rm = TRUE)) %>% 
  ungroup() %>% 
  mutate(vulemp_pop = vulemp/pop) %>% 
  select(wadmkd, vulemp_pop)

## infrastructure capacity

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

## risk exposure
### groundwater
gwater_raw  <- read_xlsx("data/extracted_data/data-penggunaan-air-tanah-pada-pelanggan-air-tanah-di-dki-jakarta-(1755620362817).xlsx") %>% 
  clean_names() %>% 
  mutate(
    pemanfaatan = as.numeric(pemanfaatan),
    kecamatan = str_to_title(kecamatan),
    kecamatan = case_when(
      kecamatan == "Keb Lama" ~ "Kebayoran Lama",
      kecamatan == "Keb Baru" ~ "Kebayoran Baru",
      kecamatan == "Pulogadung" ~ "Pulo Gadung",
      kecamatan == "Kramatjati" ~ "Kramat Jati",
      kecamatan == "Pal Merah\n" ~ "Palmerah",
      TRUE ~ kecamatan
    )
  ) %>% 
  filter(pemanfaatan > 0) %>% 
  summarise(
    avg_usage = mean(pemanfaatan, na.rm = T),
    .by = kecamatan
  )

gwater_df  <- nb_raw %>% 
  select(objectid = objectid_1, kecamatan = wadmkc, wadmkd, t_build_a) %>% 
  group_by(kecamatan) %>% 
  mutate(total_area = sum(t_build_a, na.rm = T)) %>% 
  ungroup() %>% 
  mutate(
    kecamatan = str_to_title(kecamatan),
    kecamatan = case_when(
      kecamatan == "Kali Deres" ~ "Kalideres",
      kecamatan == "Setia Budi" ~ "Setiabudi",
      TRUE ~ kecamatan
    ),
    build_area_prop = t_build_a/total_area
  ) %>% 
  left_join(
    gwater_raw,
    by = "kecamatan"
  ) %>% 
  mutate(
    gw_usage = avg_usage * build_area_prop
  ) %>% 
  select(objectid, wadmkd, gw_usage) %>% 
  replace(is.na(.),0)

## merge data

all_indicators  <- nb_raw %>% 
  select(
    # identifier
    objectid = objectid_1, wadmkd,
    # population
    pop_dens24,
    low_edu24,
    # infra and env
    drn_sys,
    n_pump = pumps_lc,
    imperv_area = mibcb,
    veg_cov24,
    t_build_a,
    topo,
    # risk
    dist_rv,
    dist_coast = dtc,
    flo_depth24,
    flo_freq24 = flood24,
    land_sub24,
    rain24
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
    vulemp_df,
    by = c("wadmkd")
  ) %>% 
  left_join(
    infrormalres_df,
    by = c("objectid","wadmkd")
  ) %>% 
  left_join(
    gwater_df,
    by = c("objectid","wadmkd")
  ) %>% 
  rename(
    id_obj = objectid,
    id_kel = wadmkd
  ) %>% 
  mutate(
    id_kel = str_to_lower(id_kel)
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
    n_pump = -1 * n_pump,
    topo = -1 * topo,
    veg_cov24 = -1 * veg_cov24
  )

dom_inf_env <- c("drn_sys","n_pump","topo","veg_cov24","imperv_area","n_informal","t_build_a")
dom_pop  <- c("age_old","age_young","fem_pop","pop_growth","pop_dens24","vulemp_pop","low_edu24")
dom_risk <- c("dist_coast","dist_rv","flo_depth24","flo_freq24","gw_usage","land_sub24","rain24")

scvi_unweighted_df <- all_indicators_z %>% 
  transmute(
    id_obj, id_kel,
    index_risk = rowSums(across(all_of(dom_risk)), na.rm = TRUE),
    index_population    = rowSums(across(all_of(dom_pop)), na.rm = TRUE),
    index_infenv      = rowSums(across(all_of(dom_inf_env)), na.rm = TRUE),
    scvi              = rowSums(across(starts_with("index")), na.rm = TRUE)
  )

scvi_unweighted_df %>% write_csv("data/processed_data/scvi_unweighted_2024.csv")

scvi_uw_bar  <- scvi_unweighted_df %>% arrange(desc(scvi)) %>% head(8) %>%
  ggplot(aes(x = scvi, y = reorder(id_kel, scvi))) +
    geom_col(fill = "#cf551c", width = 0.75) +
    labs(
      title = "Top 10 SCVI (unweighted)",
      x = "SCVI Index",
      y = "Kelurahan"
    ) +
    theme_minimal(base_size = 12) +
    theme(
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      axis.text.y = element_text(size = 8),
      axis.title.y = element_text(size = 10),
      axis.title.x = element_text(size = 10),
      plot.margin = margin(10, 10, 10, 10)
    )
  

scvi_unweight_sf <- kel_geom %>% 
  mutate(id_kel = str_to_lower(id_kel)) %>% 
  left_join(
    scvi_unweighted_df,
    by = c("id_obj","id_kel")
  ) %>% 
  st_cast("MULTIPOLYGON") %>% 
  st_as_sf() %>% 
  st_set_crs(st_crs(kel_geom))

st_write(scvi_unweight_sf, "data/processed_data/scvi_jakarta_2024.geojson", driver = "GeoJSON", delete_dsn = TRUE)

scvi_unweighted_plot <- ggplot(scvi_unweight_sf) +
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
  scale_fill_gradient(low = "#fdf2e9", high = "#cf551c", name = "SCVI") +
  theme_minimal()

ggsave(plot = scvi_unweighted_plot,filename = "output/image/scvi_unweighted_map.png",width = 8,height = 8,dpi = 300)
ggsave(plot = scvi_uw_bar, filename = "output/image/scvi_unweighted_bar.png",width = 13, height = 8, dpi = 300)


# plotly will use the "text" aesthetic for tooltips
scvi_unweighted_plotly  <- ggplotly(scvi_unweighted_plot, tooltip = "text")

saveWidget(scvi_unweighted_plotly,"output/web/kelurahan_scvi.html", selfcontained = TRUE)

