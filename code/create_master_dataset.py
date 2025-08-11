import geopandas as gpd
import pandas as pd
import logging
import os
from rasterstats import zonal_stats

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Input data paths
BASE_LAYER_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "02 GIS Data (Neighborhood & Grid levels)", "Neighborhoods", "Neighborhoods_5.0.shp")
POVERTY_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "25 Poverty Data", "socioeconomic_poverty_2024.shp")
INFORMAL_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "27 Residence Living in Informal Settlements", "socioeconomic_informal_residence_2023.shp")
LANDSUB_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "12 Land subsidence", "landsub_2024_int_value.tif")
BLDG_AGE_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "04 BldgAge_Building Age", "building_age.shp")
BUILTUP_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "03 Rate of built vs non-built development", "BuiltUp_2024.tif")
DRAINAGE_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "08 Drainage system data", "Primary Drainage System", "Saluran_Drainase_Primer.shp")
POP_DEN_VECTOR_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "21 Population density", "Population Density (Vector)", "Pop_Den_2015-2024.shp")
AGE_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "22 Age", "Population based on Age", "socioeconomic_age_2024.shp")
EDUCATION_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "23 Education", "Population based Education", "socioeconomic_education_2024.shp")
GENDER_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "24 Gender", "socioeconomic_gender_2024.shp")
CASH_ASSISTANCE_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "26 Cash Assistance (BLT)", "socioeconomic_cash_assistance_2024.shp")
TOPO_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "10 Topography", "dsm.tif")
POP_DEN_RASTER_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "21 Population density", "Population Density (Raster)", "Dens_2024_.tif")
BLDG_AREA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "05 BldgAr_Building Area", "building_area.shp")
PROP_RES_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "06 Proportion of Residential Area", "proportion_residential_area.shp")
WATER_PUMPS_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "09 Water pumps locations", "Waterpump_Stasioner.shp")
ISA_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "07 Impervious Surface Areas", "Jakarta_ISA_2024.tif")
DIST_RIVER_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "11 Distance to rivers", "distance_to_river.tif")
RAINFALL_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "13 Rainfall", "rainfall_2024_int_value.tif")
LST_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "14 Land surface temperature", "lst_2024.tif")
NDVI_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "15 NDVI", "NDVI_2024.tif")
NL_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "20 Night Light Data", "nl_2024.tif")
NDBI_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "16 NDBI", "Landcover 1 May 2025", "NDBI_2024.tif")
FLOOD_MAP_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "18 Flood vs No Flood", "DKI Jakarta", "February 2023FloodMap.tif")
FLOOD_DEPTH_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_data", "19 How depth does the flood is", "Flood geodataframe", "flood_data_2024.geojson")

# Output data path
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed_data")
OUTPUT_FILENAME = "master_dataset.gpkg"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_vector_data(path, crs=None):
    """Loads a vector dataset and optionally sets the CRS."""
    try:
        gdf = gpd.read_file(path)
        if crs is not None:
            if gdf.crs != crs:
                gdf = gdf.to_crs(crs)
        logging.info(f"Successfully loaded vector data from {path}")
        return gdf
    except Exception as e:
        logging.error(f"Error loading vector data from {path}: {e}")
        return None

def calculate_zonal_stats(gdf, raster_path, stats, column_name):
    """Calculates zonal statistics and merges them into a GeoDataFrame."""
    try:
        # Check if raster file exists
        if not os.path.exists(raster_path):
            logging.warning(f"Raster file not found: {raster_path}")
            gdf[column_name] = 0
            return gdf
            
        zonal_stats_result = zonal_stats(gdf, raster_path, stats=stats)
        stats_df = pd.DataFrame(zonal_stats_result)
        
        # Handle cases where the statistics might be None
        if stats in stats_df.columns:
            gdf[column_name] = stats_df[stats].fillna(0)
        else:
            logging.warning(f"Statistics '{stats}' not found in results for {raster_path}")
            gdf[column_name] = 0
            
        logging.info(f"Successfully calculated zonal statistics for {raster_path}")
        return gdf
    except Exception as e:
        logging.error(f"Error calculating zonal statistics for {raster_path}: {e}")
        gdf[column_name] = 0
        return gdf

def main():
    """Main function to create the master dataset."""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Load base layer
    gdf = load_vector_data(BASE_LAYER_PATH)
    if gdf is None:
        return

    # --- Process and Merge Data ---
    # Vector data
    vector_layers = {
        'poverty': POVERTY_DATA_PATH,
        'informal': INFORMAL_DATA_PATH,
        'bldg_age': BLDG_AGE_PATH,
        'pop_den_vector': POP_DEN_VECTOR_PATH,
        'age': AGE_PATH,
        'education': EDUCATION_PATH,
        'gender': GENDER_PATH,
        'cash_assistance': CASH_ASSISTANCE_PATH,
        'bldg_area': BLDG_AREA_PATH,
        'prop_res': PROP_RES_PATH,
        'water_pumps': WATER_PUMPS_PATH,
        'flood_depth': FLOOD_DEPTH_PATH
    }

    for name, path in vector_layers.items():
        layer_gdf = load_vector_data(path, crs=gdf.crs)
        if layer_gdf is not None:
            # Clean up any existing index_right columns in both dataframes
            if 'index_right' in gdf.columns:
                gdf = gdf.drop(columns=['index_right'])
                logging.info(f"Dropped 'index_right' from main gdf before processing {name}.")
            
            if 'index_right' in layer_gdf.columns:
                layer_gdf = layer_gdf.drop(columns=['index_right'])
                logging.info(f"Dropped 'index_right' from {name} layer_gdf.")

            # Reset indices to prevent conflicts
            gdf = gdf.reset_index(drop=True)
            layer_gdf = layer_gdf.reset_index(drop=True)

            logging.info(f"Processing {name} layer with {len(layer_gdf)} features")

            if name in ['bldg_age', 'bldg_area']:
                # Calculate mean for building age and area
                sjoined_gdf = gpd.sjoin(gdf, layer_gdf, how="left", predicate="intersects")
                
                # Get the column name for the metric
                metric_col = None
                if name == 'bldg_age' and 'age' in layer_gdf.columns:
                    metric_col = 'age'
                elif name == 'bldg_area' and 'area' in layer_gdf.columns:
                    metric_col = 'area'
                elif name == 'bldg_age' and 'BldgAge' in layer_gdf.columns:
                    metric_col = 'BldgAge'
                elif name == 'bldg_area' and 'BldgArea' in layer_gdf.columns:
                    metric_col = 'BldgArea'
                
                if metric_col and metric_col in sjoined_gdf.columns:
                    mean_values = sjoined_gdf.groupby(sjoined_gdf.index)[metric_col].mean()
                    gdf[f'mean_{name}'] = mean_values.fillna(0)
                else:
                    logging.warning(f"Could not find appropriate column for {name} calculation")
                    gdf[f'mean_{name}'] = 0
                    
            elif name == 'water_pumps':
                # Count water pumps
                sjoined_gdf = gpd.sjoin(gdf, layer_gdf, how="left", predicate="intersects")
                count_values = sjoined_gdf.groupby(sjoined_gdf.index).size()
                gdf[f'{name}_count'] = count_values.fillna(0)
                
            else:
                # Regular spatial join
                temp_gdf = gpd.sjoin(gdf, layer_gdf, how="left", predicate="intersects")
                
                # Handle duplicates by taking the first occurrence for each base feature
                if temp_gdf.index.has_duplicates:
                    temp_gdf = temp_gdf.groupby(temp_gdf.index).first()
                
                # Get new columns from the join (excluding geometry and index columns)
                new_cols = [col for col in temp_gdf.columns 
                           if col not in gdf.columns and col not in ['geometry', 'index_right']]
                
                # Add new columns to main gdf
                for col in new_cols:
                    gdf[col] = temp_gdf[col]

            logging.info(f"Successfully processed {name} layer")

    # Drainage data (special vector case)
    drainage_gdf = load_vector_data(DRAINAGE_PATH, crs=gdf.crs)
    if drainage_gdf is not None:
        try:
            drainage_intersect = gpd.overlay(gdf, drainage_gdf, how='intersection')
            if len(drainage_intersect) > 0:
                drainage_intersect['length'] = drainage_intersect.geometry.length
                
                # Check if OBJECTID exists, otherwise use the index
                group_col = 'OBJECTID' if 'OBJECTID' in drainage_intersect.columns else drainage_intersect.index.name or 'index'
                if group_col == 'index':
                    drainage_intersect = drainage_intersect.reset_index()
                    group_col = 'index'
                
                drainage_length = drainage_intersect.groupby(group_col)['length'].sum()
                
                # Merge based on available column
                merge_on = 'OBJECTID' if 'OBJECTID' in gdf.columns else gdf.index.name or 'index'
                if merge_on == 'index':
                    gdf = gdf.reset_index()
                    merge_on = 'index'
                
                gdf = gdf.merge(drainage_length.rename('drainage_length'), 
                               left_on=merge_on, right_index=True, how='left')
            else:
                gdf['drainage_length'] = 0
                logging.info("No drainage intersections found, setting drainage_length to 0")
        except Exception as e:
            logging.error(f"Error processing drainage data: {e}")
            gdf['drainage_length'] = 0

    # Raster data
    raster_layers = {
        'land_subsidence_mean': (LANDSUB_DATA_PATH, 'mean'),
        'builtup_mean': (BUILTUP_DATA_PATH, 'mean'),
        'topo_mean': (TOPO_DATA_PATH, 'mean'),
        'pop_den_mean': (POP_DEN_RASTER_PATH, 'mean'),
        'isa_mean': (ISA_DATA_PATH, 'mean'),
        'dist_river_mean': (DIST_RIVER_PATH, 'mean'),
        'rainfall_mean': (RAINFALL_PATH, 'mean'),
        'lst_mean': (LST_PATH, 'mean'),
        'ndvi_mean': (NDVI_PATH, 'mean'),
        'nl_mean': (NL_PATH, 'mean'),
        'ndbi_mean': (NDBI_PATH, 'mean'),
        'flood_map_mean': (FLOOD_MAP_PATH, 'mean')
    }

    for col_name, (path, stat) in raster_layers.items():
        gdf = calculate_zonal_stats(gdf, path, stat, col_name)

    # --- Final Data Cleaning ---
    # Drop duplicate columns (if any)
    gdf = gdf.loc[:,~gdf.columns.duplicated()]

    # Handle missing values (fill with 0 for numerical columns)
    numeric_cols = gdf.select_dtypes(include=['number']).columns
    gdf[numeric_cols] = gdf[numeric_cols].fillna(0)

    # Report dataset statistics
    logging.info(f"Created {len(gdf)} records")
    logging.info(f"Dataset contains {len(gdf.columns)} columns")
    logging.info(f"Column names: {list(gdf.columns)}")

    # --- Save Master Dataset ---
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    try:
        gdf.to_file(output_path, driver='GPKG')
        logging.info(f"Master dataset saved to {output_path}")
        
        # Verify the saved file
        test_gdf = gpd.read_file(output_path)
        logging.info(f"Verification: Successfully read {len(test_gdf)} records from saved file")
        
    except Exception as e:
        logging.error(f"Error saving master dataset: {e}")

if __name__ == "__main__":
    main()
