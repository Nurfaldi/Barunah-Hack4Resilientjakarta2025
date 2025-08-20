# code/utils.R

ensure_root <- function() {
  if (basename(getwd()) == "code" && dir.exists("../data")) {
    setwd("..")
    message("Moved working directory to root: ", getwd())
  } else if (dir.exists("data")) {
    message("Working directory is root: ", getwd())
  } else {
    stop("Run from root or code/ folder.")
  }
}

normalize <- function(x) {
  (x - min(x, na.rm = TRUE)) / (max(x, na.rm = TRUE) - min(x, na.rm = TRUE))
}


#' Load multiple shapefiles of similar structure and reshape
#'
#' @param data_dir Path to folder containing shapefiles
#' @param pattern Regex pattern to match files (default socioeconomic_age_YYYY.shp)
#' @param id_cols Vector of column names to keep as identifiers (e.g. c("kel_code", "year"))
#' @param names_from Column to pivot into wide columns (e.g. "age")
#' @param values_from Column containing values (e.g. "pop")
#' @param fill Value to fill missing cells (default = 0)
#'
#' @return A list with two tibbles: long and wide
#'
#' @examples
#' res <- load_and_reshape(
#'   data_dir = "data/22 Age/Population based on Age",
#'   id_cols = c("kel_code", "year"),
#'   names_from = "age",
#'   values_from = "pop"
#' )
#' res$long
#' res$wide
#'
# code/utils.R

load_shapefiles_bind <- function(
  data_dir,
  pattern,
  year_regex = "\\d{4}",
  year_col = "year",
  keep_geom = FALSE,
  quiet = TRUE,
  rename_dict = NULL
) {
  # Namespaced calls to avoid forcing library() globally
  files <- list.files(path = data_dir, pattern = pattern, full.names = TRUE)
  if (length(files) == 0) {
    stop("No shapefiles found in ", data_dir, " using pattern: ", pattern)
  }

  # Read each file, add year column
  rows_list <- purrr::map(files, function(fpath) {
    yr <- stringr::str_extract(basename(fpath), year_regex)

    # read shapefile
    sf_obj <- sf::st_read(fpath, quiet = quiet)

    # Apply dictionary-based renaming if provided
    if (!is.null(rename_dict)) {
      sf_obj <- dplyr::rename(sf_obj, !!!rename_dict)
    }

    # attach year (NA if missing)
    sf_obj[[year_col]] <- if (!is.na(yr)) as.integer(yr) else NA_integer_

    if (!keep_geom) {
      sf::st_drop_geometry(sf_obj)
    } else {
      sf_obj
    }
  })

  # If keeping geometry, ensure consistent CRS by transforming all to first file's CRS
  if (keep_geom) {
    first_crs <- sf::st_crs(rows_list[[1]])
    # detect if any crs differs
    crs_chars <- purrr::map_chr(rows_list, ~ as.character(sf::st_crs(.x)))
    if (length(unique(crs_chars)) > 1) {
      message("Multiple CRSs detected among shapefiles. Transforming all to the CRS of the first file.")
      rows_list <- purrr::map(rows_list, ~ sf::st_transform(.x, first_crs))
    }
  }

  # Bind rows into a single tibble / sf object
  out <- dplyr::bind_rows(rows_list) %>% janitor::clean_names()

  # Return (sf if keep_geom = TRUE, tibble if FALSE)
  out
}

zscore_safe <- function(x) {
  if (sd(x, na.rm = TRUE) == 0 || all(is.na(x))) {
    return(rep(0, length(x)))  # all values identical or NA → set to 0
  } else {
    return(as.numeric(scale(x)))
  }
}