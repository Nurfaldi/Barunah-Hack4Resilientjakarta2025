#!/usr/bin/env python3
"""
Jakarta Comprehensive Data Explorer and Visualizer
==================================================
This script explores and visualizes ALL available datasets from the extracted_data directory,
creating unified plots with Jakarta boundaries and appropriate legends for different data types.

Author: Data Exploration Script
Date: 2025-08-11
"""

import os
import sys
import glob
import warnings
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict

import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.warp
from rasterio.warp import transform_bounds
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
from rasterstats import zonal_stats
import contextily as ctx
from tqdm import tqdm

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8')

class JakartaDataExplorer:
    """Comprehensive data explorer for Jakarta flood resilience datasets."""
    
    def __init__(self, base_path: str):
        """Initialize the explorer with base data path."""
        self.base_path = Path(base_path)
        self.extracted_data_path = self.base_path / "data" / "extracted_data"
        self.metadata_path = self.base_path / "data" / "metadata"
        self.output_path = self.base_path / "data" / "visualizations"
        
        # Create organized output directories
        self.raw_output_path = self.output_path / "raw_data"
        self.processed_output_path = self.output_path / "processed_data"
        self.raw_output_path.mkdir(parents=True, exist_ok=True)
        self.processed_output_path.mkdir(parents=True, exist_ok=True)
        
        # Jakarta boundaries for context
        self.jakarta_boundaries = None
        self.neighborhoods = None
        
        # Data collections organized by folder
        self.vector_datasets = defaultdict(dict)  # folder -> {dataset_name: info}
        self.raster_datasets = defaultdict(dict)
        self.tabular_datasets = defaultdict(dict)
        
        # Metadata for enhanced processing
        self.metadata = self._load_metadata()
        
        print(f"🏢 Jakarta Data Explorer initialized")
        print(f"📁 Base path: {self.base_path}")
        print(f"📊 Data path: {self.extracted_data_path}")
        print(f"🎨 Raw output: {self.raw_output_path}")
        print(f"🔄 Processed output: {self.processed_output_path}")
        print(f"📋 Metadata loaded: {len(self.metadata.get('datasources', {}))} datasources")
    
    def _load_metadata(self) -> Dict:
        """Load metadata files for enhanced data processing."""
        metadata = {'datasources': {}, 'flooding_mapping': {}, 'neighborhood_columns': {}}
        
        try:
            # Load datasource list
            datasource_file = self.metadata_path / "Barunah Data Governance Datasource List.csv"
            if datasource_file.exists():
                df = pd.read_csv(datasource_file)
                for _, row in df.iterrows():
                    metadata['datasources'][row['Index']] = {
                        'title': row['Title'],
                        'description': row['Description'],
                        'data_type': row['Data Type'],
                        'sources': row['Sources']
                    }
            
            # Load flooding mapping
            flooding_file = self.metadata_path / "Barunah Data Governance Flooding Mapping.csv"
            if flooding_file.exists():
                df = pd.read_csv(flooding_file)
                for _, row in df.iterrows():
                    metadata['flooding_mapping'][row['Indicator']] = {
                        'domain': row['Domain'],
                        'dimension': row['Dimension'],
                        'rationale': row['Rationale'],
                        'availability': row['Data Availability']
                    }
            
            # Load neighborhood metadata
            neighborhood_file = self.metadata_path / "Barunah Data Governance Neighborhood Metadata.csv"
            if neighborhood_file.exists():
                df = pd.read_csv(neighborhood_file)
                for _, row in df.iterrows():
                    metadata['neighborhood_columns'][row['Column Name']] = {
                        'full_name': row['Full Name'],
                        'category': row['Data Categories'],
                        'type': row['Type'],
                        'description': row['Description'],
                        'year_start': row['Year Start'],
                        'year_end': row['Year End']
                    }
                    
            print(f"📋 Loaded {len(metadata['datasources'])} datasources, "
                  f"{len(metadata['flooding_mapping'])} flood indicators, "
                  f"{len(metadata['neighborhood_columns'])} column definitions")
                  
        except Exception as e:
            print(f"⚠️  Warning: Could not fully load metadata: {e}")
            
        return metadata
    
    def _get_jakarta_bounds_with_buffer(self, buffer=0.01):
        """Get Jakarta bounds with buffer for consistent plotting."""
        if self.neighborhoods is not None:
            bounds = self.neighborhoods.total_bounds
        elif self.jakarta_boundaries is not None:
            bounds = self.jakarta_boundaries.total_bounds
        else:
            # Default Jakarta bounds if no boundaries available
            bounds = [106.68, -6.37, 106.97, -6.07]
        
        return [
            bounds[0] - buffer,  # minx
            bounds[1] - buffer,  # miny
            bounds[2] + buffer,  # maxx
            bounds[3] + buffer   # maxy
        ]
    
    def _plot_jakarta_context(self, ax):
        """Plot Jakarta boundaries as context."""
        if self.neighborhoods is not None:
            self.neighborhoods.boundary.plot(ax=ax, color='lightgray', linewidth=0.5, alpha=0.7)
        elif self.jakarta_boundaries is not None:
            self.jakarta_boundaries.boundary.plot(ax=ax, color='lightgray', linewidth=0.8, alpha=0.7)
        
    def load_jakarta_boundaries(self) -> bool:
        """Load Jakarta administrative boundaries for context."""
        try:
            # Try loading city boundaries
            city_path = self.extracted_data_path / "01 Area of Interest" / "City" / "adm_dki-jakarta.shp"
            if city_path.exists():
                self.jakarta_boundaries = gpd.read_file(city_path)
                print(f"✅ Loaded Jakarta city boundaries: {len(self.jakarta_boundaries)} features")
            
            # Try loading neighborhood boundaries  
            neighborhood_path = self.extracted_data_path / "02 GIS Data (Neighborhood & Grid levels)" / "Neighborhoods" / "Neighborhoods_5.0.shp"
            if neighborhood_path.exists():
                self.neighborhoods = gpd.read_file(neighborhood_path)
                print(f"✅ Loaded Jakarta neighborhoods: {len(self.neighborhoods)} features")
                
            return True
        except Exception as e:
            print(f"⚠️  Warning: Could not load Jakarta boundaries: {e}")
            return False
    
    def discover_vector_datasets(self) -> Dict[str, Dict]:
        """Discover all vector datasets in the data directory, organized by folder."""
        print("\n🔍 DISCOVERING VECTOR DATASETS...")
        print("=" * 60)
        
        vector_extensions = ['.shp', '.geojson', '.gpkg', '.kml', '.gml']
        vector_files = []
        
        # Recursively find all vector files
        for ext in vector_extensions:
            pattern = f"**/*{ext}"
            found_files = list(self.extracted_data_path.glob(pattern))
            vector_files.extend(found_files)
        
        print(f"📊 Found {len(vector_files)} vector files")
        
        # Analyze each vector file with progress bar
        for file_path in tqdm(vector_files, desc="Loading vector datasets"):
            try:
                # Get folder and dataset names
                rel_path = file_path.relative_to(self.extracted_data_path)
                folder_name = str(rel_path.parts[0])  # Top-level folder
                dataset_name = file_path.stem  # File name without extension
                
                # Load and analyze the dataset
                gdf = gpd.read_file(file_path)
                
                # Determine geometry type
                geom_types = gdf.geometry.geom_type.value_counts()
                primary_geom = geom_types.index[0] if len(geom_types) > 0 else "Unknown"
                
                # Classify data type
                data_type = self._classify_geometry_type(primary_geom)
                
                # Store dataset info by folder
                dataset_info = {
                    'name': dataset_name,
                    'file_path': file_path,
                    'data': gdf,
                    'geometry_type': primary_geom,
                    'data_type': data_type,
                    'feature_count': len(gdf),
                    'columns': list(gdf.columns),
                    'crs': gdf.crs,
                    'bounds': gdf.total_bounds,
                    'numeric_columns': list(gdf.select_dtypes(include=[np.number]).columns)
                }
                
                self.vector_datasets[folder_name][dataset_name] = dataset_info
                
                print(f"✅ {folder_name}/{dataset_name}")
                print(f"   📐 Geometry: {primary_geom}")
                print(f"   📊 Features: {len(gdf):,}")
                print(f"   📋 Columns: {len(gdf.columns)} ({len(dataset_info['numeric_columns'])} numeric)")
                
            except Exception as e:
                print(f"❌ Error loading {file_path.name}: {str(e)[:100]}...")
        
        # Special handling for problematic datasets
        self._handle_special_datasets()
        
        total_datasets = sum(len(datasets) for datasets in self.vector_datasets.values())
        print(f"\n📈 Total vector datasets loaded: {total_datasets} across {len(self.vector_datasets)} folders")
        return dict(self.vector_datasets)
    
    def _handle_special_datasets(self):
        """Handle special cases for problematic datasets with enhanced fixes."""
        print("\n🔧 HANDLING SPECIAL DATASET CASES...")
        
        # Handle merged flood data (Dataset 17) with enhanced processing
        flood_folder = self.extracted_data_path / "17 BPBD flood depth data"
        if flood_folder.exists():
            merged_flood_info = self._create_merged_flood_visualization(flood_folder)
            if merged_flood_info:
                folder_name = "17 BPBD flood depth data"
                if folder_name not in self.vector_datasets:
                    self.vector_datasets[folder_name] = {}
                self.vector_datasets[folder_name]["Merged_Flood_All_Years"] = merged_flood_info
                print("✅ Created merged flood visualization for all years")
        
        # Handle population density vector (Dataset 21) with CRS fixes
        pop_folder = self.extracted_data_path / "21 Population density" / "Population Density (Vector)"
        pop_file = pop_folder / "Pop_Den_2015-2024.shp"
        if pop_file.exists():
            try:
                gdf = gpd.read_file(pop_file)
                print(f"  📈 Population density: {len(gdf)} features, CRS: {gdf.crs}")
                
                # Apply CRS fixes
                target_crs = 'EPSG:4326'
                if gdf.crs != target_crs:
                    try:
                        gdf = gdf.to_crs(target_crs)
                        print(f"    🔄 Reprojected population data to {target_crs}")
                    except Exception as e:
                        print(f"    ⚠️  Population CRS reprojection failed: {e}")
                
                geom_types = gdf.geometry.geom_type.value_counts()
                primary_geom = geom_types.index[0] if len(geom_types) > 0 else "Unknown"
                data_type = self._classify_geometry_type(primary_geom)
                
                dataset_info = {
                    'name': 'Pop_Den_2015-2024',
                    'file_path': pop_file,
                    'data': gdf,
                    'geometry_type': primary_geom,
                    'data_type': data_type,
                    'feature_count': len(gdf),
                    'columns': list(gdf.columns),
                    'crs': gdf.crs,
                    'bounds': gdf.total_bounds,
                    'numeric_columns': list(gdf.select_dtypes(include=[np.number]).columns)
                }
                
                folder_name = "21 Population density"
                if folder_name not in self.vector_datasets:
                    self.vector_datasets[folder_name] = {}
                self.vector_datasets[folder_name]["Pop_Den_2015-2024"] = dataset_info
                print("✅ Added population density vector data with CRS fixes")
                
            except Exception as e:
                print(f"⚠️  Could not load population density vector: {e}")
        
        # Enhanced handling for datasets 22-27 (socioeconomic data)
        socioeconomic_datasets = {
            '22 Age': 'Population based on Age',
            '23 Education': 'Population based Education',
            '24 Gender': None,
            '25 Poverty Data': None,
            '26 Cash Assistance (BLT)': None,
            '27 Residence Living in Informal Settlements': None
        }
        
        for folder_key, subfolder in socioeconomic_datasets.items():
            folder_path = self.extracted_data_path / folder_key
            if subfolder:
                folder_path = folder_path / subfolder
            
            if folder_path.exists():
                # Find the most recent shapefile
                shapefiles = list(folder_path.glob("*.shp"))
                if shapefiles:
                    recent_file = sorted(shapefiles, key=lambda x: x.stem)[-1]
                    try:
                        gdf = gpd.read_file(recent_file)
                        print(f"  📈 Enhanced {folder_key}: {len(gdf)} features, CRS: {gdf.crs}")
                        
                        # Apply CRS fixes
                        if gdf.crs != 'EPSG:4326':
                            try:
                                gdf = gdf.to_crs('EPSG:4326')
                                print(f"    🔄 Reprojected {folder_key} to EPSG:4326")
                            except Exception as e:
                                print(f"    ⚠️  {folder_key} CRS reprojection failed: {e}")
                        
                        # Update existing dataset info with fixes
                        if folder_key in self.vector_datasets:
                            for dataset_name, dataset_info in self.vector_datasets[folder_key].items():
                                dataset_info['data'] = gdf  # Update with fixed CRS
                                dataset_info['crs'] = gdf.crs
                                dataset_info['bounds'] = gdf.total_bounds
                                print(f"    ✅ Updated {dataset_name} with CRS fixes")
                                
                    except Exception as e:
                        print(f"    ❌ Error enhancing {folder_key}: {e}")
    
    def discover_raster_datasets(self) -> Dict[str, Dict]:
        """Discover all raster datasets in the data directory, organized by folder."""
        print("\n🌍 DISCOVERING RASTER DATASETS...")
        print("=" * 60)
        
        raster_extensions = ['.tif', '.tiff', '.img', '.jp2']
        raster_files = []
        
        # Find all raster files
        for ext in raster_extensions:
            pattern = f"**/*{ext}"
            found_files = list(self.extracted_data_path.glob(pattern))
            raster_files.extend(found_files)
        
        print(f"📊 Found {len(raster_files)} raster files")
        
        # Analyze each raster file with progress bar
        for file_path in tqdm(raster_files, desc="Loading raster datasets"):
            try:
                # Get folder and dataset names
                rel_path = file_path.relative_to(self.extracted_data_path)
                folder_name = str(rel_path.parts[0])  # Top-level folder
                dataset_name = file_path.stem  # File name without extension
                
                # Open and analyze the raster
                with rasterio.open(file_path) as src:
                    # Read basic metadata
                    dataset_info = {
                        'name': dataset_name,
                        'file_path': file_path,
                        'width': src.width,
                        'height': src.height,
                        'bands': src.count,
                        'dtype': src.dtypes[0],
                        'crs': src.crs,
                        'bounds': src.bounds,
                        'transform': src.transform,
                        'nodata': src.nodata
                    }
                    
                    # Sample the data to get statistics (faster sampling)
                    sample_size = min(500, src.width, src.height)  # Smaller sample for speed
                    sample_data = src.read(1, window=rasterio.windows.Window(0, 0, sample_size, sample_size))
                    
                    if sample_data is not None and sample_data.size > 0:
                        valid_data = sample_data[sample_data != src.nodata] if src.nodata is not None else sample_data
                        if len(valid_data) > 0:
                            dataset_info['min_value'] = float(np.min(valid_data))
                            dataset_info['max_value'] = float(np.max(valid_data))
                            dataset_info['mean_value'] = float(np.mean(valid_data))
                            dataset_info['std_value'] = float(np.std(valid_data))
                        else:
                            dataset_info.update({'min_value': 0, 'max_value': 0, 'mean_value': 0, 'std_value': 0})
                    else:
                        dataset_info.update({'min_value': 0, 'max_value': 0, 'mean_value': 0, 'std_value': 0})
                    
                self.raster_datasets[folder_name][dataset_name] = dataset_info
                
                print(f"✅ {folder_name}/{dataset_name}")
                print(f"   📐 Size: {dataset_info['width']}x{dataset_info['height']}")
                print(f"   📊 Bands: {dataset_info['bands']}")
                print(f"   📋 Range: {dataset_info.get('min_value', 'N/A'):.2f} - {dataset_info.get('max_value', 'N/A'):.2f}")
                
            except Exception as e:
                print(f"❌ Error loading {file_path.name}: {str(e)[:100]}...")
        
        total_datasets = sum(len(datasets) for datasets in self.raster_datasets.values())
        print(f"\n📈 Total raster datasets loaded: {total_datasets} across {len(self.raster_datasets)} folders")
        return dict(self.raster_datasets)
    
    def discover_tabular_datasets(self) -> Dict[str, Dict]:
        """Discover all tabular datasets in the data directory, organized by folder."""
        print("\n📋 DISCOVERING TABULAR DATASETS...")
        print("=" * 60)
        
        tabular_extensions = ['.csv', '.xlsx', '.xls']
        tabular_files = []
        
        # Find all tabular files
        for ext in tabular_extensions:
            pattern = f"**/*{ext}"
            found_files = list(self.extracted_data_path.glob(pattern))
            tabular_files.extend(found_files)
        
        print(f"📊 Found {len(tabular_files)} tabular files")
        
        # Analyze each tabular file with progress bar
        for file_path in tqdm(tabular_files, desc="Loading tabular datasets"):
            try:
                # Get folder and dataset names
                rel_path = file_path.relative_to(self.extracted_data_path)
                folder_name = str(rel_path.parts[0])  # Top-level folder
                dataset_name = file_path.stem  # File name without extension
                
                # Load the data
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path, engine='openpyxl')
                
                dataset_info = {
                    'name': dataset_name,
                    'file_path': file_path,
                    'data': df,
                    'rows': len(df),
                    'columns': list(df.columns),
                    'numeric_columns': list(df.select_dtypes(include=[np.number]).columns),
                    'categorical_columns': list(df.select_dtypes(include=['object']).columns),
                    'datetime_columns': list(df.select_dtypes(include=['datetime64']).columns)
                }
                
                self.tabular_datasets[folder_name][dataset_name] = dataset_info
                
                print(f"✅ {folder_name}/{dataset_name}")
                print(f"   📊 Rows: {len(df):,}")
                print(f"   📋 Columns: {len(df.columns)} ({len(dataset_info['numeric_columns'])} numeric, {len(dataset_info['categorical_columns'])} categorical)")
                
            except Exception as e:
                print(f"❌ Error loading {file_path.name}: {str(e)[:100]}...")
        
        total_datasets = sum(len(datasets) for datasets in self.tabular_datasets.values())
        print(f"\n📈 Total tabular datasets loaded: {total_datasets} across {len(self.tabular_datasets)} folders")
        return dict(self.tabular_datasets)
    
    def _classify_geometry_type(self, geom_type: str) -> str:
        """Classify geometry type for visualization purposes."""
        if 'Point' in geom_type:
            return 'point'
        elif 'Line' in geom_type:
            return 'line' 
        elif 'Polygon' in geom_type:
            return 'polygon'
        else:
            return 'mixed'
    
    def create_folder_separated_vector_visualizations(self):
        """Create separate visualizations for each folder containing vector datasets with batch processing."""
        print(f"\n🎨 CREATING FOLDER-SEPARATED VECTOR VISUALIZATIONS (RAW DATA)...")
        print("=" * 60)
        
        if not self.vector_datasets:
            print("⚠️  No vector datasets to visualize")
            return []
        
        output_files = []
        
        # Color scheme for different geometry types
        colors = {
            'point': '#ff6b6b',
            'line': '#4ecdc4', 
            'polygon': '#45b7d1',
            'mixed': '#96ceb4'
        }
        
        # Process each folder separately with batch support (max 20 visualizations per image)
        for folder_name, datasets in tqdm(self.vector_datasets.items(), desc="Creating folder visualizations"):
            print(f"\n📁 Processing folder: {folder_name} ({len(datasets)} datasets)")
            
            # Clean folder name for file system
            clean_folder_name = folder_name.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
            folder_output_path = self.raw_output_path / clean_folder_name
            folder_output_path.mkdir(parents=True, exist_ok=True)
            
            # Split datasets into batches of 20 for manageable file sizes
            dataset_items = list(datasets.items())
            batch_size = 20
            batches = [dataset_items[i:i + batch_size] for i in range(0, len(dataset_items), batch_size)]
            
            for batch_idx, batch_datasets in enumerate(batches):
                batch_name = f"batch_{batch_idx + 1}" if len(batches) > 1 else "all"
                output_file = folder_output_path / f'vector_{clean_folder_name}_{batch_name}.png'
                
                if output_file.exists():
                    print(f"⏭️  Skipping {folder_name} batch {batch_idx + 1}: visualization already exists")
                    output_files.append(output_file)
                    continue
                
                # Calculate grid layout for this batch
                n_datasets = len(batch_datasets)
                n_cols = min(4, n_datasets)  # Max 4 columns
                n_rows = (n_datasets + n_cols - 1) // n_cols
                
                # Create figure
                fig_width = n_cols * 5
                fig_height = n_rows * 4
                fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_width, fig_height))
                
                # Always ensure axes is a 2D array for consistent indexing
                if n_datasets == 1:
                    axes = np.array([[axes]])
                elif n_rows == 1 and n_cols > 1:
                    axes = axes.reshape(1, -1)
                elif n_rows > 1 and n_cols == 1:
                    axes = axes.reshape(-1, 1)
                
                # Plot each dataset in this batch
                for i, (dataset_name, info) in enumerate(batch_datasets):
                    row = i // n_cols
                    col = i % n_cols
                    
                    # Now axes is always 2D, so we can use consistent indexing
                    ax = axes[row, col]
                    
                    try:
                        self._plot_vector_dataset(ax, info, colors)
                        
                        # Add dataset info
                        title = f"{dataset_name}\n({info['geometry_type']}, {info['feature_count']:,} features)"
                        ax.set_title(title, fontsize=9, pad=10)
                        
                    except Exception as e:
                        ax.text(0.5, 0.5, f"Error plotting\n{dataset_name}\n{str(e)[:50]}...", 
                               ha='center', va='center', transform=ax.transAxes)
                    
                    ax.set_xlabel('Longitude', fontsize=8)
                    ax.set_ylabel('Latitude', fontsize=8) 
                    ax.tick_params(labelsize=6)
                
                # Hide unused subplots in this batch
                for i in range(n_datasets, n_rows * n_cols):
                    row = i // n_cols
                    col = i % n_cols
                    
                    # Now axes is always 2D, so we can use consistent indexing
                    try:
                        axes[row, col].set_visible(False)
                    except (IndexError, AttributeError):
                        continue  # Skip if subplot doesn't exist
                
                # Add legend for this batch
                legend_elements = [mpatches.Patch(color=color, label=geom_type.title()) 
                                  for geom_type, color in colors.items()]
                fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))
                
                # Add batch info to title
                batch_info = f" - Batch {batch_idx + 1}/{len(batches)}" if len(batches) > 1 else ""
                plt.suptitle(f'Jakarta Raw Vector Data - {folder_name}{batch_info}', fontsize=14, y=0.98)
                plt.tight_layout()
                
                # Save the plot
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close(fig)  # Close to free memory
                
                output_files.append(output_file)
                print(f"✅ Saved batch {batch_idx + 1}/{len(batches)} for {folder_name}: {output_file}")
        
        print(f"\n✅ All vector visualizations completed: {len(output_files)} files saved")
        return output_files
    
    def create_folder_separated_raster_visualizations(self):
        """Create separate visualizations for each folder containing raster datasets with batch processing."""
        print(f"\n🌍 CREATING FOLDER-SEPARATED RASTER VISUALIZATIONS (RAW DATA)...")
        print("=" * 60)
        
        if not self.raster_datasets:
            print("⚠️  No raster datasets to visualize")
            return []
        
        output_files = []
        
        # Process each folder separately with batch support (max 20 visualizations per image)
        for folder_name, datasets in tqdm(self.raster_datasets.items(), desc="Creating raster visualizations"):
            print(f"\n📁 Processing folder: {folder_name} ({len(datasets)} datasets)")
            
            # Clean folder name for file system
            clean_folder_name = folder_name.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
            folder_output_path = self.raw_output_path / clean_folder_name
            folder_output_path.mkdir(parents=True, exist_ok=True)
            
            # Split datasets into batches of 20 for manageable file sizes
            dataset_items = list(datasets.items())
            batch_size = 20
            batches = [dataset_items[i:i + batch_size] for i in range(0, len(dataset_items), batch_size)]
            
            for batch_idx, batch_datasets in enumerate(batches):
                batch_name = f"batch_{batch_idx + 1}" if len(batches) > 1 else "all"
                output_file = folder_output_path / f'raster_{clean_folder_name}_{batch_name}.png'
                
                if output_file.exists():
                    print(f"⏭️  Skipping {folder_name} batch {batch_idx + 1}: visualization already exists")
                    output_files.append(output_file)
                    continue
                
                # Calculate grid layout for this batch
                n_datasets = len(batch_datasets)
                n_cols = min(4, n_datasets)  # Max 4 columns
                n_rows = (n_datasets + n_cols - 1) // n_cols
                
                # Create figure
                fig_width = n_cols * 5
                fig_height = n_rows * 4
                fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_width, fig_height))
                
                # Always ensure axes is a 2D array for consistent indexing
                if n_datasets == 1:
                    axes = np.array([[axes]])
                elif n_rows == 1 and n_cols > 1:
                    axes = axes.reshape(1, -1)
                elif n_rows > 1 and n_cols == 1:
                    axes = axes.reshape(-1, 1)
                
                # Plot each raster dataset in this batch
                for i, (dataset_name, info) in enumerate(batch_datasets):
                    row = i // n_cols
                    col = i % n_cols
                    
                    ax = axes[row, col]
                    
                    try:
                        self._plot_raster_dataset(ax, info)
                        
                        # Add dataset info
                        title = f"{dataset_name}\n({info['width']}x{info['height']}, {info['bands']} bands)"
                        ax.set_title(title, fontsize=9, pad=10)
                        
                    except Exception as e:
                        ax.text(0.5, 0.5, f"Error plotting\n{dataset_name}\n{str(e)[:50]}...", 
                               ha='center', va='center', transform=ax.transAxes)
                    
                    ax.tick_params(labelsize=6)
                
                # Hide unused subplots in this batch
                for i in range(n_datasets, n_rows * n_cols):
                    row = i // n_cols
                    col = i % n_cols
                    
                    try:
                        axes[row, col].set_visible(False)
                    except (IndexError, AttributeError):
                        continue
                
                # Add batch info to title
                batch_info = f" - Batch {batch_idx + 1}/{len(batches)}" if len(batches) > 1 else ""
                plt.suptitle(f'Jakarta Raw Raster Data - {folder_name}{batch_info}', fontsize=14, y=0.98)
                plt.tight_layout()
                
                # Save the plot
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                output_files.append(output_file)
                print(f"✅ Saved raster batch {batch_idx + 1}/{len(batches)} for {folder_name}: {output_file}")
        
        print(f"\n✅ All raster visualizations completed: {len(output_files)} files saved")
        return output_files
    
    def create_comprehensive_tabular_visualizations(self):
        """Create comprehensive visualizations for ALL columns in tabular datasets with organized structure."""
        print(f"\n📊 CREATING COMPREHENSIVE TABULAR VISUALIZATIONS (RAW DATA)...")
        print("=" * 60)
        
        if not self.tabular_datasets:
            print("⚠️  No tabular datasets to visualize")
            return []
        
        output_files = []
        
        # Process each folder separately
        for folder_name, datasets in tqdm(self.tabular_datasets.items(), desc="Creating tabular visualizations"):
            print(f"\n📁 Processing folder: {folder_name} ({len(datasets)} datasets)")
            
            for dataset_name, info in datasets.items():
                try:
                    # Check if visualization already exists - organize in raw data structure
                    clean_folder_name = folder_name.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    clean_dataset_name = dataset_name.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    folder_output_path = self.raw_output_path / clean_folder_name
                    folder_output_path.mkdir(parents=True, exist_ok=True)
                    output_file = folder_output_path / f'tabular_{clean_dataset_name}.png'
                    
                    if output_file.exists():
                        print(f"⏭️  Skipping {folder_name}/{dataset_name}: visualization already exists")
                        output_files.append(output_file)
                        continue
                    
                    df = info['data']
                    numeric_cols = info['numeric_columns']
                    categorical_cols = info['categorical_columns']
                    
                    if len(numeric_cols) == 0 and len(categorical_cols) == 0:
                        print(f"⚠️  Skipping {dataset_name}: no plottable columns")
                        continue
                    
                    # Calculate layout for all columns
                    total_cols = len(numeric_cols) + min(len(categorical_cols), 10)  # Limit categorical
                    if total_cols == 0:
                        continue
                    
                    n_plot_cols = min(4, total_cols)
                    n_plot_rows = (total_cols + n_plot_cols - 1) // n_plot_cols
                    
                    fig, axes = plt.subplots(n_plot_rows, n_plot_cols, 
                                           figsize=(n_plot_cols * 4, n_plot_rows * 3))
                    
                    if total_cols == 1:
                        axes = np.array([axes])
                    elif n_plot_rows == 1:
                        axes = axes.reshape(1, -1)
                    
                    plot_idx = 0
                    
                    # Plot numeric columns
                    for col in numeric_cols:
                        if plot_idx >= total_cols:
                            break
                            
                        row = plot_idx // n_plot_cols
                        col_idx = plot_idx % n_plot_cols
                        ax = axes[row, col_idx] if n_plot_rows > 1 else axes[col_idx]
                        
                        try:
                            # Enhanced histogram for numeric data with better dynamic scaling for socioeconomic data
                            data_values = df[col].dropna()
                            if len(data_values) > 0:
                                # Enhanced dynamic scaling based on actual data distribution
                                if data_values.std() > 0:
                                    # Special handling for socioeconomic datasets (22-27) to show kelurahan-level variation
                                    if any(keyword in folder_name for keyword in ['Age', 'Gender', 'Poverty', 'Cash', 'Informal', 'Education']):
                                        # Use percentile-based scaling for socioeconomic data to show proper variation
                                        p5 = data_values.quantile(0.05)
                                        p95 = data_values.quantile(0.95)
                                        
                                        # Show distribution across full range but highlight main distribution
                                        ax.hist(data_values, bins=25, alpha=0.7, color='steelblue', edgecolor='black')
                                        
                                        # Add vertical lines for key percentiles
                                        ax.axvline(data_values.median(), color='red', linestyle='--', alpha=0.8, label='Median')
                                        ax.axvline(p5, color='orange', linestyle=':', alpha=0.6, label='5th %ile')
                                        ax.axvline(p95, color='orange', linestyle=':', alpha=0.6, label='95th %ile')
                                        
                                        ax.set_title(f"{col}\n(Kelurahan variation: {p5:.0f}-{p95:.0f})", fontsize=10)
                                        
                                        # Enhanced statistics showing kelurahan-level dispersion
                                        cv = (data_values.std() / data_values.mean()) * 100 if data_values.mean() > 0 else 0
                                        stats_text = (f"Median: {data_values.median():.1f}\n"
                                                    f"CV: {cv:.1f}%\n"
                                                    f"P5-P95: {p5:.0f}-{p95:.0f}\n"
                                                    f"Kelurahan: {len(data_values)}")
                                        
                                        # Add legend for percentile lines
                                        ax.legend(fontsize=6, loc='upper right')
                                    else:
                                        # Standard IQR-based approach for other datasets
                                        q25 = data_values.quantile(0.25)
                                        q75 = data_values.quantile(0.75)
                                        iqr = q75 - q25
                                        
                                        # Use IQR-based outlier detection for better range
                                        lower_bound = q25 - 1.5 * iqr
                                        upper_bound = q75 + 1.5 * iqr
                                        
                                        # Filter extreme outliers but keep reasonable range
                                        filtered_data = data_values[
                                            (data_values >= max(lower_bound, data_values.quantile(0.01))) & 
                                            (data_values <= min(upper_bound, data_values.quantile(0.99)))
                                        ]
                                        
                                        if len(filtered_data) > 0:
                                            ax.hist(filtered_data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                                            ax.set_title(f"{col}\n(n={len(data_values):,}, IQR-based)", fontsize=10)
                                            stats_text = (f"Median: {data_values.median():.1f}\n"
                                                        f"IQR: {iqr:.1f}\n"
                                                        f"Range: {filtered_data.min():.0f}-{filtered_data.max():.0f}")
                                        else:
                                            ax.hist(data_values, bins=20, alpha=0.7, color='lightblue', edgecolor='black')
                                            ax.set_title(f"{col}\n(n={len(data_values):,}, full range)", fontsize=10)
                                            stats_text = f"Median: {data_values.median():.2f}\nRange: {data_values.min():.1f}-{data_values.max():.1f}"
                                else:
                                    ax.hist(data_values, bins=10, alpha=0.7, color='lightcoral', edgecolor='black')
                                    ax.set_title(f"{col}\n(n={len(data_values):,}, uniform)", fontsize=10)
                                    stats_text = f"Value: {data_values.iloc[0]:.2f}\n(Constant)"
                                
                                ax.set_xlabel(col, fontsize=8)
                                ax.set_ylabel('Frequency', fontsize=8)
                                
                                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                                       verticalalignment='top', fontsize=7,
                                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                            else:
                                ax.text(0.5, 0.5, f"No data\nfor {col}", ha='center', va='center', 
                                       transform=ax.transAxes)
                        except Exception as e:
                            ax.text(0.5, 0.5, f"Error plotting\n{col}\n{str(e)[:30]}", 
                                   ha='center', va='center', transform=ax.transAxes)
                        
                        plot_idx += 1
                    
                    # Plot categorical columns (limited to prevent overcrowding)
                    for col in categorical_cols[:min(10, len(categorical_cols))]:
                        if plot_idx >= total_cols:
                            break
                            
                        row = plot_idx // n_plot_cols
                        col_idx = plot_idx % n_plot_cols
                        ax = axes[row, col_idx] if n_plot_rows > 1 else axes[col_idx]
                        
                        try:
                            # Create bar chart for categorical data
                            value_counts = df[col].value_counts().head(10)  # Top 10 categories
                            if len(value_counts) > 0:
                                bars = ax.bar(range(len(value_counts)), value_counts.values, 
                                            color='lightcoral', alpha=0.7)
                                ax.set_title(f"{col}\n({len(value_counts)} categories)", fontsize=10)
                                ax.set_xlabel(col, fontsize=8)
                                ax.set_ylabel('Count', fontsize=8)
                                ax.set_xticks(range(len(value_counts)))
                                ax.set_xticklabels(value_counts.index, rotation=45, ha='right', fontsize=7)
                            else:
                                ax.text(0.5, 0.5, f"No data\nfor {col}", ha='center', va='center', 
                                       transform=ax.transAxes)
                        except Exception as e:
                            ax.text(0.5, 0.5, f"Error plotting\n{col}\n{str(e)[:30]}", 
                                   ha='center', va='center', transform=ax.transAxes)
                        
                        plot_idx += 1
                    
                    # Hide unused subplots
                    for i in range(plot_idx, n_plot_rows * n_plot_cols):
                        row = i // n_plot_cols
                        col_idx = i % n_plot_cols
                        if n_plot_rows > 1:
                            axes[row, col_idx].set_visible(False)
                        elif i < len(axes):
                            axes[col_idx].set_visible(False)
                    
                    plt.suptitle(f'Tabular Data Explorer - {folder_name}/{dataset_name}\n'
                               f'({info["rows"]:,} rows, {len(info["columns"])} columns)', 
                               fontsize=12, y=0.98)
                    plt.tight_layout()
                    
                    # Save the plot (output_file already defined above)
                    plt.savefig(output_file, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                    
                    output_files.append(output_file)
                    print(f"✅ Saved tabular visualization: {output_file}")
                    
                except Exception as e:
                    print(f"❌ Error creating visualization for {folder_name}/{dataset_name}: {e}")
        
        print(f"\n✅ All tabular visualizations completed: {len(output_files)} files saved")
        return output_files
    
    def _select_diverse_datasets(self, datasets: Dict, max_count: int) -> Dict:
        """Select diverse datasets for visualization."""
        if len(datasets) <= max_count:
            return datasets
        
        # Prioritize datasets with more features/data and different types
        scored_datasets = []
        
        for name, info in datasets.items():
            score = 0
            
            # Score based on data richness
            if 'feature_count' in info:
                score += min(info['feature_count'] / 1000, 10)  # Cap at 10 points
            if 'numeric_columns' in info:
                score += len(info['numeric_columns']) * 0.5
            if 'rows' in info:
                score += min(info['rows'] / 1000, 10)
            
            # Bonus for different geometry types
            if 'geometry_type' in info:
                if 'Point' in info['geometry_type']:
                    score += 2
                elif 'Line' in info['geometry_type']:
                    score += 3  # Lines are rarer
                elif 'Polygon' in info['geometry_type']:
                    score += 1
            
            scored_datasets.append((name, info, score))
        
        # Sort by score and select top datasets
        scored_datasets.sort(key=lambda x: x[2], reverse=True)
        selected = {name: info for name, info, _ in scored_datasets[:max_count]}
        
        return selected
    
    def _plot_vector_dataset(self, ax, dataset_info: Dict, colors: Dict):
        """Plot a single vector dataset with comprehensive CRS handling and enhanced visibility."""
        gdf = dataset_info['data'].copy()
        data_type = dataset_info['data_type']
        dataset_name = dataset_info.get('name', 'Unknown')
        
        # Define target CRS for visualization (WGS84)
        target_crs = 'EPSG:4326'
        
        # Comprehensive CRS handling with better error handling
        try:
            if gdf.crs is not None:
                current_crs_str = str(gdf.crs)
                print(f"  📍 Original CRS: {current_crs_str}")
                
                # Handle different CRS formats and reproject to WGS84
                if current_crs_str != target_crs:
                    try:
                        gdf = gdf.to_crs(target_crs)
                        print(f"  🔄 Reprojected to {target_crs}")
                    except Exception as e:
                        print(f"  ⚠️  CRS reprojection failed: {e}")
                        # Try alternative reprojection methods
                        try:
                            if 'EPSG:' not in current_crs_str and gdf.crs.to_epsg():
                                gdf = gdf.to_crs(f'EPSG:{gdf.crs.to_epsg()}')
                                gdf = gdf.to_crs(target_crs)
                                print(f"  🔄 Alternative reprojection successful")
                        except:
                            print(f"  ❌ All reprojection methods failed")
            else:
                print(f"  ⚠️  No CRS defined, assuming WGS84")
                gdf = gdf.set_crs(target_crs)
        except Exception as e:
            print(f"  ❌ CRS handling error: {e}")
        
        # Enhanced boundary handling - ALWAYS plot Jakarta context first
        jakarta_bounds = self._get_jakarta_bounds_with_buffer()
        self._plot_jakarta_context(ax)
        
        # Skip empty datasets
        if len(gdf) == 0:
            print(f"  ⚠️  No features to plot for {dataset_name}")
            ax.text(0.5, 0.5, f'No data available\nfor {dataset_name}', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
            return
        
        # Plot the dataset with enhanced visibility based on geometry type
        color = colors.get(data_type, '#95a5a6')
        
        if data_type == 'point':
            # Enhanced point plotting with capacity-based coloring and larger markers
            marker_size = max(20, min(80, 3000 / len(gdf))) if len(gdf) > 0 else 40
            
            # Check for capacity/value-based coloring
            numeric_cols = dataset_info.get('numeric_columns', [])
            capacity_cols = [col for col in numeric_cols if any(keyword in col.lower() 
                           for keyword in ['capacity', 'kapasitas', 'tinggi', 'depth'])]
            
            if capacity_cols and gdf[capacity_cols[0]].notna().any():
                val_col = capacity_cols[0]
                if gdf[val_col].std() > 0:  # Has variation
                    # Use percentile-based scaling
                    vmin = gdf[val_col].quantile(0.05)
                    vmax = gdf[val_col].quantile(0.95)
                    gdf.plot(ax=ax, column=val_col, cmap='viridis', markersize=marker_size, 
                           alpha=0.8, edgecolor='white', linewidth=1, legend=True,
                           legend_kwds={'shrink': 0.6, 'aspect': 15},
                           vmin=vmin, vmax=vmax)
                    print(f"  🎨 Plotted {len(gdf)} points with capacity coloring")
                else:
                    gdf.plot(ax=ax, color=color, markersize=marker_size, alpha=0.8, 
                           edgecolor='white', linewidth=1)
            else:
                gdf.plot(ax=ax, color=color, markersize=marker_size, alpha=0.8, 
                       edgecolor='white', linewidth=1)
                print(f"  🎨 Plotted {len(gdf)} points with uniform color")
                
        elif data_type == 'line':
            # Enhanced line plotting with better visibility
            line_width = 3.0 if len(gdf) < 100 else 2.0
            gdf.plot(ax=ax, color=color, linewidth=line_width, alpha=0.9)
            print(f"  🎨 Plotted {len(gdf)} line features")
            
        elif data_type == 'polygon':
            # Enhanced polygon plotting with dynamic scaling
            numeric_cols = dataset_info.get('numeric_columns', [])
            if numeric_cols and len(numeric_cols) > 0:
                col_name = numeric_cols[0]
                if gdf[col_name].std() > 0:
                    # Use percentile-based scaling for better visualization instead of fixed 0-250
                    vmin = gdf[col_name].quantile(0.05)
                    vmax = gdf[col_name].quantile(0.95)
                    
                    # Choose appropriate colormap based on data type
                    if any(keyword in col_name.lower() for keyword in ['density', 'population', 'dens_']):
                        cmap = 'YlOrRd'
                    elif any(keyword in col_name.lower() for keyword in ['age', 'umur']):
                        cmap = 'viridis'
                    elif any(keyword in col_name.lower() for keyword in ['poverty', 'poor', 'miskin']):
                        cmap = 'Reds'
                    elif any(keyword in col_name.lower() for keyword in ['gender', 'jk_', 'kelamin']):
                        cmap = 'RdYlBu'
                    else:
                        cmap = 'viridis'
                    
                    gdf.plot(ax=ax, column=col_name, cmap=cmap, alpha=0.7, 
                           edgecolor='white', linewidth=0.3, legend=True,
                           legend_kwds={'shrink': 0.7, 'aspect': 20},
                           vmin=vmin, vmax=vmax)
                    print(f"  🎨 Plotted {len(gdf)} polygons with dynamic scaling ({vmin:.1f}-{vmax:.1f})")
                else:
                    gdf.plot(ax=ax, color=color, alpha=0.7, edgecolor='white', linewidth=0.3)
                    print(f"  🎨 Plotted {len(gdf)} polygons with uniform color (no variation)")
            else:
                gdf.plot(ax=ax, color=color, alpha=0.7, edgecolor='white', linewidth=0.3)
                print(f"  🎨 Plotted {len(gdf)} polygons with uniform color (no numeric data)")
        else:
            gdf.plot(ax=ax, color=color, alpha=0.8)
            print(f"  🎨 Plotted {len(gdf)} features with default styling")
        
        # Set proper geographic bounds with Jakarta context
        ax.set_xlim(jakarta_bounds[0], jakarta_bounds[2])
        ax.set_ylim(jakarta_bounds[1], jakarta_bounds[3])
        
        # Set equal aspect ratio and improve axes
        ax.set_aspect('equal', adjustable='box')
        ax.grid(True, alpha=0.3)
        
        # Print data info for debugging
        if len(gdf) > 0:
            bounds = gdf.total_bounds
            print(f"  📊 Data bounds: {bounds[0]:.4f}, {bounds[1]:.4f}, {bounds[2]:.4f}, {bounds[3]:.4f}")
            print(f"  📈 Features plotted: {len(gdf)} with Jakarta context")
        else:
            print(f"  ⚠️  No features to plot")
    
    def _plot_raster_dataset(self, ax, dataset_info: Dict):
        """Plot a single raster dataset with Jakarta context and proper georeferencing."""
        file_path = dataset_info['file_path']
        
        try:
            # Read and plot raster with proper geospatial context
            with rasterio.open(file_path) as src:
                # Get the CRS and transform information
                src_crs = src.crs
                transform = src.transform
                bounds = src.bounds
                
                # Sample the data for plotting (to avoid memory issues)
                if src.width > 2000 or src.height > 2000:
                    # Downsample large rasters
                    scale_factor = max(src.width // 2000, src.height // 2000, 1)
                    data = src.read(1, out_shape=(src.height // scale_factor, src.width // scale_factor))
                    # Adjust transform for downsampled data
                    new_transform = rasterio.Affine(transform.a * scale_factor, transform.b, transform.c,
                                                  transform.d, transform.e * scale_factor, transform.f)
                else:
                    data = src.read(1)
                    new_transform = transform
                
                # Handle nodata
                if src.nodata is not None:
                    data = np.ma.masked_equal(data, src.nodata)
                
                # Determine appropriate extent for plotting
                if src_crs and src_crs.to_string() != 'EPSG:4326':
                    # Try to reproject bounds to WGS84 for consistent plotting
                    try:
                        from rasterio.warp import transform_bounds
                        target_bounds = transform_bounds(src_crs, 'EPSG:4326', *bounds)
                    except:
                        target_bounds = bounds
                else:
                    target_bounds = bounds
                
                # Plot with geographic extent
                im = ax.imshow(data, cmap='viridis', alpha=0.8, 
                             extent=[target_bounds[0], target_bounds[2], target_bounds[1], target_bounds[3]])
                
                # Add Jakarta context if raster is within Jakarta bounds
                jakarta_bounds = self._get_jakarta_bounds_with_buffer()
                
                # Check if raster overlaps with Jakarta
                if (target_bounds[0] < jakarta_bounds[2] and target_bounds[2] > jakarta_bounds[0] and
                    target_bounds[1] < jakarta_bounds[3] and target_bounds[3] > jakarta_bounds[1]):
                    # Raster overlaps with Jakarta - add boundary context
                    self._plot_jakarta_context(ax)
                    
                    # Set Jakarta bounds for consistency
                    ax.set_xlim(jakarta_bounds[0], jakarta_bounds[2])
                    ax.set_ylim(jakarta_bounds[1], jakarta_bounds[3])
                else:
                    # Raster doesn't overlap - use raster bounds
                    ax.set_xlim(target_bounds[0], target_bounds[2])
                    ax.set_ylim(target_bounds[1], target_bounds[3])
                
                # Add colorbar with better formatting
                try:
                    if hasattr(im, 'colorbar') or True:  # Always try to add colorbar
                        plt.colorbar(im, ax=ax, shrink=0.8, aspect=20, 
                                   format='%.2f' if data.max() < 100 else '%.0f')
                except:
                    pass  # Skip colorbar if it fails
            
        except Exception as e:
            print(f"  ❌ Error plotting raster: {e}")
            ax.text(0.5, 0.5, f"Error loading raster\n{file_path.name}\n{str(e)[:50]}...", 
                   ha='center', va='center', transform=ax.transAxes)
        
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel('Longitude', fontsize=8)
        ax.set_ylabel('Latitude', fontsize=8)
    
    def _create_merged_flood_visualization(self, folder_path) -> dict:
        """Create a merged visualization of flood depth data with enhanced processing from quick_flood_fix."""
        try:
            from pathlib import Path
            
            # Find all flood depth files
            flood_folder = Path(folder_path) / "Flood Depth"
            if not flood_folder.exists():
                # Try alternative paths
                flood_files = list(Path(folder_path).glob("**/*Genangan_*.shp"))
            else:
                flood_files = list(flood_folder.glob("Genangan_*.shp"))
            
            if not flood_files:
                print("⚠️  No flood depth files found")
                return None
            
            print(f"📊 Found {len(flood_files)} flood depth files")
            
            # Load and merge flood data with enhanced error handling
            all_flood_data = []
            target_crs = 'EPSG:4326'
            
            for flood_file in flood_files:
                try:
                    gdf = gpd.read_file(flood_file)
                    print(f"  📂 Loading {flood_file.name}: {len(gdf)} features, CRS: {gdf.crs}")
                    
                    # Skip if empty
                    if len(gdf) == 0:
                        print(f"  ⚠️  Empty file: {flood_file.name}")
                        continue
                    
                    # Comprehensive CRS handling
                    if gdf.crs is not None and str(gdf.crs) != target_crs:
                        try:
                            gdf = gdf.to_crs(target_crs)
                            print(f"    🔄 Reprojected to {target_crs}")
                        except Exception as e:
                            print(f"    ⚠️  CRS reprojection failed: {e}")
                            continue
                    elif gdf.crs is None:
                        print(f"    ⚠️  No CRS for {flood_file.name}, assuming WGS84")
                        gdf = gdf.set_crs(target_crs)
                    
                    # Extract year from filename (improved extraction)
                    year_match = [part for part in flood_file.stem.split('_') if part.isdigit()]
                    year = year_match[-1] if year_match else flood_file.stem.split('_')[-1]  # Take last part as year
                    gdf['year'] = year
                    gdf['source_file'] = flood_file.name
                    
                    # Only keep essential columns to avoid data issues (enhanced from quick_flood_fix)
                    essential_cols = ['year', 'source_file', 'geometry']
                    
                    # Check for additional useful columns
                    for col in gdf.columns:
                        if any(keyword in col.lower() for keyword in ['lokasi', 'wilayah', 'location', 'area']):
                            essential_cols.append(col)
                        elif any(keyword in col.lower() for keyword in ['tinggi', 'genangan', 'depth', 'height']):
                            # Only include depth if it has reasonable values (improved validation)
                            try:
                                depth_values = gdf[col].dropna()
                                if len(depth_values) > 0:
                                    # Check for reasonable depth values (0-500cm is reasonable for flooding)
                                    reasonable_depths = depth_values[
                                        (depth_values >= 0) & (depth_values <= 500)
                                    ]
                                    if len(reasonable_depths) > len(depth_values) * 0.5:  # At least 50% reasonable
                                        essential_cols.append(col)
                                        gdf['flood_depth'] = gdf[col]
                                        print(f"    📈 Added depth column {col} with {len(reasonable_depths)}/{len(depth_values)} reasonable values")
                            except:
                                pass
                    
                    # Create clean dataset with only essential columns
                    available_cols = [col for col in essential_cols if col in gdf.columns]
                    gdf_clean = gdf[available_cols].copy()
                    
                    # Add default flood presence if no depth column (simplified approach from quick_flood_fix)
                    if 'flood_depth' not in gdf_clean.columns:
                        gdf_clean['flood_depth'] = 1.0  # Default presence indicator
                    
                    all_flood_data.append(gdf_clean)
                    print(f"    ✅ Added {len(gdf_clean)} flood points for year {year}")
                    
                except Exception as e:
                    print(f"  ❌ Error loading {flood_file.name}: {e}")
                    continue
            
            if not all_flood_data:
                print("⚠️  No valid flood data found")
                return None
            
            # Combine all data
            print(f"  🔗 Combining {len(all_flood_data)} flood datasets...")
            merged_flood = gpd.GeoDataFrame(pd.concat(all_flood_data, ignore_index=True))
            
            # Add frequency analysis by approximate location (enhanced from quick_flood_fix)
            if len(merged_flood) > 0:
                # Round coordinates for frequency analysis (higher precision for better grouping)
                merged_flood['lon_round'] = merged_flood.geometry.x.round(4)
                merged_flood['lat_round'] = merged_flood.geometry.y.round(4)
                location_counts = merged_flood.groupby(['lon_round', 'lat_round']).size()
                merged_flood['flood_frequency'] = merged_flood.set_index(['lon_round', 'lat_round']).index.map(location_counts)
                
                # Additional analysis - identify hotspots
                hotspots = location_counts[location_counts >= 3]  # Locations flooded 3+ times
                print(f"  🔥 Identified {len(hotspots)} flood hotspots (3+ occurrences)")
            
            # Create enhanced dataset info
            numeric_columns = ['flood_depth', 'flood_frequency'] if 'flood_frequency' in merged_flood.columns else ['flood_depth']
            
            dataset_info = {
                'name': 'Merged_Flood_All_Years',
                'data': merged_flood,
                'geometry_type': 'Point', 
                'data_type': 'point',
                'feature_count': len(merged_flood),
                'columns': list(merged_flood.columns),
                'numeric_columns': numeric_columns,
                'crs': merged_flood.crs,
                'bounds': merged_flood.total_bounds if len(merged_flood) > 0 else [0,0,0,0]
            }
            
            print(f"  ✅ Created merged flood dataset: {len(merged_flood)} total flood points across {len(all_flood_data)} years")
            return dataset_info
            
        except Exception as e:
            print(f"❌ Error creating merged flood visualization: {e}")
            return None
    
    def create_comprehensive_report(self):
        """Create a comprehensive report of all discovered datasets."""
        print(f"\n📊 COMPREHENSIVE DATA REPORT")
        print("=" * 80)
        
        total_vector = len(self.vector_datasets)
        total_raster = len(self.raster_datasets)  
        total_tabular = len(self.tabular_datasets)
        total_datasets = total_vector + total_raster + total_tabular
        
        print(f"📈 DATASET SUMMARY:")
        print(f"   📐 Vector datasets: {total_vector}")
        print(f"   🌍 Raster datasets: {total_raster}")
        print(f"   📋 Tabular datasets: {total_tabular}")
        print(f"   🎯 Total datasets: {total_datasets}")
        
        # Vector analysis
        if self.vector_datasets:
            print(f"\n📐 VECTOR DATASET ANALYSIS:")
            geom_types = {}
            total_features = 0
            
            for info in self.vector_datasets.values():
                geom_type = info.get('geometry_type', 'Unknown')
                geom_types[geom_type] = geom_types.get(geom_type, 0) + 1
                total_features += info.get('feature_count', 0)
            
            for geom_type, count in geom_types.items():
                print(f"   • {geom_type}: {count} datasets")
            print(f"   • Total features: {total_features:,}")
        
        # Raster analysis
        if self.raster_datasets:
            print(f"\n🌍 RASTER DATASET ANALYSIS:")
            total_bands = sum(info.get('bands', 0) for info in self.raster_datasets.values())
            avg_size = np.mean([info.get('width', 0) * info.get('height', 0) 
                              for info in self.raster_datasets.values()])
            print(f"   • Total bands: {total_bands}")
            print(f"   • Average size: {avg_size:,.0f} pixels")
        
        # Create summary visualization
        self._create_summary_dashboard()
        
        print(f"\n✅ EXPLORATION COMPLETE!")
        print(f"📁 All visualizations saved to: {self.output_path}")
        print("=" * 80)
    
    def _create_summary_dashboard(self):
        """Create a summary dashboard showing dataset statistics."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Dataset type distribution
        data_types = ['Vector', 'Raster', 'Tabular']
        counts = [len(self.vector_datasets), len(self.raster_datasets), len(self.tabular_datasets)]
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1']
        
        ax1.pie(counts, labels=data_types, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Dataset Type Distribution')
        
        # Vector geometry types
        if self.vector_datasets:
            geom_types = {}
            for info in self.vector_datasets.values():
                geom_type = info.get('geometry_type', 'Unknown')
                geom_types[geom_type] = geom_types.get(geom_type, 0) + 1
            
            ax2.bar(geom_types.keys(), geom_types.values(), color='#96ceb4')
            ax2.set_title('Vector Geometry Types')
            ax2.set_ylabel('Number of Datasets')
            plt.setp(ax2.get_xticklabels(), rotation=45)
        
        # Feature count distribution (vector)
        if self.vector_datasets:
            feature_counts = [info.get('feature_count', 0) for info in self.vector_datasets.values()]
            ax3.hist(feature_counts, bins=20, color='#feca57', alpha=0.7, edgecolor='black')
            ax3.set_title('Vector Dataset Feature Count Distribution')
            ax3.set_xlabel('Number of Features')
            ax3.set_ylabel('Number of Datasets')
            ax3.set_yscale('log')
        
        # Raster size distribution
        if self.raster_datasets:
            raster_sizes = [info.get('width', 0) * info.get('height', 0) 
                          for info in self.raster_datasets.values() if info.get('width', 0) > 0]
            if raster_sizes:
                ax4.hist(raster_sizes, bins=20, color='#ff9ff3', alpha=0.7, edgecolor='black')
                ax4.set_title('Raster Dataset Size Distribution')
                ax4.set_xlabel('Total Pixels')
                ax4.set_ylabel('Number of Datasets')
                ax4.set_xscale('log')
        
        plt.tight_layout()
        
        # Save dashboard
        output_file = self.output_path / 'data_summary_dashboard.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ Summary dashboard saved to: {output_file}")
    
    def discover_processed_datasets(self) -> Dict[str, Dict]:
        """Discover and analyze processed datasets for analytical visualization."""
        print("\n🔄 DISCOVERING PROCESSED DATASETS...")
        print("=" * 60)
        
        processed_path = self.base_path / "data" / "processed_data"
        processed_datasets = {}
        
        if not processed_path.exists():
            print("⚠️  No processed_data directory found")
            return processed_datasets
            
        # Find processed files
        processed_files = []
        for ext in ['.gpkg', '.shp', '.geojson', '.csv', '.parquet']:
            pattern = f"**/*{ext}"
            found_files = list(processed_path.glob(pattern))
            processed_files.extend(found_files)
        
        print(f"📊 Found {len(processed_files)} processed files")
        
        for file_path in tqdm(processed_files, desc="Loading processed datasets"):
            try:
                dataset_name = file_path.stem
                
                if file_path.suffix.lower() in ['.gpkg', '.shp', '.geojson']:
                    # Load as geodataframe
                    gdf = gpd.read_file(file_path)
                    dataset_info = {
                        'name': dataset_name,
                        'file_path': file_path,
                        'data': gdf,
                        'data_type': 'processed_vector',
                        'feature_count': len(gdf),
                        'columns': list(gdf.columns),
                        'numeric_columns': list(gdf.select_dtypes(include=[np.number]).columns),
                        'crs': gdf.crs if hasattr(gdf, 'crs') else None
                    }
                else:
                    # Load as regular dataframe
                    if file_path.suffix.lower() == '.csv':
                        df = pd.read_csv(file_path)
                    elif file_path.suffix.lower() == '.parquet':
                        df = pd.read_parquet(file_path)
                    else:
                        continue
                        
                    dataset_info = {
                        'name': dataset_name,
                        'file_path': file_path,
                        'data': df,
                        'data_type': 'processed_tabular',
                        'rows': len(df),
                        'columns': list(df.columns),
                        'numeric_columns': list(df.select_dtypes(include=[np.number]).columns)
                    }
                
                processed_datasets[dataset_name] = dataset_info
                print(f"✅ {dataset_name} ({dataset_info['data_type']})")
                
            except Exception as e:
                print(f"❌ Error loading {file_path.name}: {str(e)[:100]}...")
        
        print(f"📈 Total processed datasets loaded: {len(processed_datasets)}")
        return processed_datasets

    def create_processed_data_visualizations(self, processed_datasets: Dict):
        """Create comprehensive visualizations for processed datasets with metadata enhancement."""
        print(f"\n🎨 CREATING PROCESSED DATA VISUALIZATIONS WITH METADATA INTEGRATION...")
        print("=" * 60)
        
        if not processed_datasets:
            print("⚠️  No processed datasets to visualize")
            return []
        
        output_files = []
        
        for dataset_name, info in tqdm(processed_datasets.items(), desc="Creating processed visualizations"):
            try:
                # Check if visualization already exists - organize in processed data structure
                output_file = self.processed_output_path / f'enhanced_{dataset_name}.png'
                
                if output_file.exists():
                    print(f"⏭️  Skipping {dataset_name}: visualization already exists")
                    output_files.append(output_file)
                    continue
                
                if info['data_type'] == 'processed_vector':
                    gdf = info['data']
                    numeric_cols = info['numeric_columns']
                    
                    if len(numeric_cols) == 0:
                        print(f"⚠️  Skipping {dataset_name}: no numeric columns")
                        continue
                    
                    # Calculate grid layout for all numeric columns
                    n_cols = min(4, len(numeric_cols))
                    n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
                    
                    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 5, n_rows * 4))
                    
                    # Handle single subplot case
                    if len(numeric_cols) == 1:
                        axes = np.array([axes])
                    elif n_rows == 1 and n_cols > 1:
                        axes = axes.reshape(1, -1)
                    elif n_rows > 1 and n_cols == 1:
                        axes = axes.reshape(-1, 1)
                    
                    for i, col in enumerate(numeric_cols):
                        if i >= len(numeric_cols):
                            break
                            
                        row = i // n_cols
                        col_idx = i % n_cols
                        ax = axes[row, col_idx] if n_rows > 1 or n_cols > 1 else axes[0]
                        
                        try:
                            # Add Jakarta boundaries for context
                            if self.neighborhoods is not None:
                                self.neighborhoods.boundary.plot(ax=ax, color='lightgray', linewidth=0.5, alpha=0.7)
                            elif self.jakarta_boundaries is not None:
                                self.jakarta_boundaries.boundary.plot(ax=ax, color='lightgray', linewidth=0.8)
                            
                            # Get metadata information for enhanced titles
                            col_metadata = self.metadata['neighborhood_columns'].get(col, {})
                            col_title = col_metadata.get('full_name', col)
                            col_category = col_metadata.get('category', 'Unknown')
                            col_description = col_metadata.get('description', '')
                            
                            # Calculate statistics with median as default aggregation
                            if gdf[col].std() > 0:
                                # Use median-based aggregation for visualization
                                median_val = gdf[col].median()
                                mad = np.median(np.abs(gdf[col] - median_val))  # Median Absolute Deviation
                                
                                # Create choropleth map
                                gdf.plot(ax=ax, column=col, cmap='viridis', alpha=0.8, 
                                        edgecolor='white', linewidth=0.2, legend=True,
                                        legend_kwds={'shrink': 0.8, 'aspect': 20})
                                
                                # Add enhanced statistics text with metadata
                                stats_text = f"Median: {median_val:.2f}\nMAD: {mad:.2f}\nRange: {gdf[col].min():.2f}-{gdf[col].max():.2f}"
                                if col_category != 'Unknown':
                                    stats_text += f"\nCategory: {col_category}"
                                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                                       verticalalignment='top', fontsize=7,
                                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                            else:
                                # Uniform data - use single color
                                gdf.plot(ax=ax, color='lightblue', alpha=0.7, edgecolor='white', linewidth=0.2)
                                uniform_text = f"Uniform: {gdf[col].iloc[0]:.2f}"
                                if col_category != 'Unknown':
                                    uniform_text += f"\nCategory: {col_category}"
                                ax.text(0.02, 0.98, uniform_text, 
                                       transform=ax.transAxes, verticalalignment='top', fontsize=7,
                                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                            
                            # Use metadata-enhanced title
                            title = col_title if col_title != col else col
                            subtitle = f"({col})" if col_title != col else "(Median-based)"
                            ax.set_title(f"{title}\n{subtitle}", fontsize=9, pad=10)
                            ax.set_xlabel('Longitude', fontsize=8)
                            ax.set_ylabel('Latitude', fontsize=8)
                            ax.tick_params(labelsize=6)
                            ax.set_aspect('equal', adjustable='box')
                            
                        except Exception as e:
                            ax.text(0.5, 0.5, f"Error plotting\n{col}\n{str(e)[:50]}...", 
                                   ha='center', va='center', transform=ax.transAxes)
                    
                    # Hide unused subplots
                    for i in range(len(numeric_cols), n_rows * n_cols):
                        row = i // n_cols
                        col_idx = i % n_cols
                        if n_rows > 1 or n_cols > 1:
                            try:
                                axes[row, col_idx].set_visible(False)
                            except (IndexError, AttributeError):
                                continue
                    
                    plt.suptitle(f'Processed Data Analysis - {dataset_name}\n'
                               f'({info["feature_count"]:,} features, {len(numeric_cols)} numeric columns)', 
                               fontsize=14, y=0.98)
                    plt.tight_layout()
                    
                    # Save the plot (output_file already defined above)
                    plt.savefig(output_file, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                    
                    output_files.append(output_file)
                    print(f"✅ Saved processed visualization: {output_file}")
                    
            except Exception as e:
                print(f"❌ Error creating processed visualization for {dataset_name}: {e}")
        
        return output_files

    def create_tabular_joined_visualizations(self):
        """Create visualizations with tabular data joined to vector areas using median aggregation."""
        print(f"\n🔗 CREATING TABULAR-JOINED VISUALIZATIONS...")
        print("=" * 60)
        
        if not self.tabular_datasets or self.neighborhoods is None:
            print("⚠️  Missing tabular datasets or neighborhood boundaries for joining")
            return []
        
        output_files = []
        
        # Use neighborhoods as base geometry for joining
        base_gdf = self.neighborhoods.copy()
        
        for folder_name, datasets in self.tabular_datasets.items():
            for dataset_name, info in datasets.items():
                try:
                    df = info['data']
                    numeric_cols = info['numeric_columns']
                    
                    if len(numeric_cols) == 0:
                        print(f"⚠️  Skipping {dataset_name}: no numeric columns")
                        continue
                    
                    # Try to find common columns for joining
                    common_cols = []
                    for col in df.columns:
                        if col.lower() in ['kelurahan', 'district', 'area_name', 'name', 'id']:
                            common_cols.append(col)
                    
                    if not common_cols and len(df) == len(base_gdf):
                        # Same number of rows - assume same order
                        print(f"📊 Joining {dataset_name} by position (same row count)")
                        joined_gdf = base_gdf.copy()
                        for col in numeric_cols:
                            # Use median aggregation for joining
                            if df[col].notna().any():
                                joined_gdf[f"{col}_median"] = df[col].fillna(df[col].median())
                            else:
                                joined_gdf[f"{col}_median"] = 0
                    else:
                        print(f"⚠️  Skipping {dataset_name}: cannot find suitable join columns")
                        continue
                    
                    # Create visualization for joined data
                    plot_cols = [col for col in joined_gdf.columns if col.endswith('_median')]
                    
                    if len(plot_cols) == 0:
                        continue
                    
                    n_plot_cols = min(4, len(plot_cols))
                    n_plot_rows = (len(plot_cols) + n_plot_cols - 1) // n_plot_cols
                    
                    fig, axes = plt.subplots(n_plot_rows, n_plot_cols, 
                                           figsize=(n_plot_cols * 4, n_plot_rows * 3))
                    
                    if len(plot_cols) == 1:
                        axes = np.array([axes])
                    elif n_plot_rows == 1 and n_plot_cols > 1:
                        axes = axes.reshape(1, -1)
                    elif n_plot_rows > 1 and n_plot_cols == 1:
                        axes = axes.reshape(-1, 1)
                    
                    for i, col in enumerate(plot_cols):
                        if i >= len(plot_cols):
                            break
                            
                        row = i // n_plot_cols
                        col_idx = i % n_plot_cols
                        ax = axes[row, col_idx] if n_plot_rows > 1 or n_plot_cols > 1 else axes[0]
                        
                        try:
                            # Create choropleth with median aggregation
                            if joined_gdf[col].std() > 0:
                                joined_gdf.plot(ax=ax, column=col, cmap='viridis', alpha=0.8,
                                               edgecolor='white', linewidth=0.2, legend=True,
                                               legend_kwds={'shrink': 0.8, 'aspect': 20})
                                
                                # Add median-based statistics
                                median_val = joined_gdf[col].median()
                                q25 = joined_gdf[col].quantile(0.25)
                                q75 = joined_gdf[col].quantile(0.75)
                                
                                stats_text = f"Median: {median_val:.2f}\nQ25: {q25:.2f}\nQ75: {q75:.2f}"
                                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                                       verticalalignment='top', fontsize=7,
                                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                            else:
                                joined_gdf.plot(ax=ax, color='lightcoral', alpha=0.7, 
                                               edgecolor='white', linewidth=0.2)
                            
                            clean_col_name = col.replace('_median', '')
                            ax.set_title(f"{clean_col_name}\n(Median aggregated)", fontsize=9, pad=10)
                            ax.set_xlabel('Longitude', fontsize=8)
                            ax.set_ylabel('Latitude', fontsize=8)
                            ax.tick_params(labelsize=6)
                            ax.set_aspect('equal', adjustable='box')
                            
                        except Exception as e:
                            ax.text(0.5, 0.5, f"Error plotting\n{col}\n{str(e)[:30]}", 
                                   ha='center', va='center', transform=ax.transAxes)
                    
                    # Hide unused subplots
                    for i in range(len(plot_cols), n_plot_rows * n_plot_cols):
                        row = i // n_plot_cols
                        col_idx = i % n_plot_cols
                        if n_plot_rows > 1 or n_plot_cols > 1:
                            try:
                                axes[row, col_idx].set_visible(False)
                            except (IndexError, AttributeError):
                                continue
                    
                    clean_folder_name = folder_name.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    clean_dataset_name = dataset_name.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    
                    plt.suptitle(f'Tabular-Joined Analysis - {folder_name}/{dataset_name}\n'
                               f'(Median aggregation, {len(joined_gdf):,} areas)', 
                               fontsize=12, y=0.98)
                    plt.tight_layout()
                    
                    # Save the plot
                    output_file = self.output_path / f'joined_{clean_folder_name}_{clean_dataset_name}.png'
                    plt.savefig(output_file, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                    
                    output_files.append(output_file)
                    print(f"✅ Saved joined visualization: {output_file}")
                    
                except Exception as e:
                    print(f"❌ Error creating joined visualization for {folder_name}/{dataset_name}: {e}")
        
        return output_files

    def run_comprehensive_exploration(self):
        """Run the complete data exploration pipeline."""
        print("🚀 STARTING COMPREHENSIVE JAKARTA DATA EXPLORATION")
        print("=" * 80)
        
        # Load boundaries first
        self.load_jakarta_boundaries()
        
        # Discover all datasets
        self.discover_vector_datasets()
        self.discover_raster_datasets()  
        self.discover_tabular_datasets()
        
        # Discover processed datasets
        processed_datasets = self.discover_processed_datasets()
        
        # Create organized visualizations
        print("\n🎨 Creating organized visualizations...")
        vector_files = self.create_folder_separated_vector_visualizations()
        raster_files = self.create_folder_separated_raster_visualizations()
        tabular_files = self.create_comprehensive_tabular_visualizations()
        
        # Create processed data visualizations
        processed_files = self.create_processed_data_visualizations(processed_datasets)
        
        # Create tabular-joined visualizations with median aggregation
        joined_files = self.create_tabular_joined_visualizations()
        
        # Generate comprehensive report
        self.create_comprehensive_report()
        
        # Count total datasets
        total_vector = sum(len(datasets) for datasets in self.vector_datasets.values())
        total_raster = sum(len(datasets) for datasets in self.raster_datasets.values())
        total_tabular = sum(len(datasets) for datasets in self.tabular_datasets.values())
        
        return {
            'vector_datasets': total_vector,
            'raster_datasets': total_raster,
            'tabular_datasets': total_tabular,
            'processed_datasets': len(processed_datasets),
            'vector_files': len(vector_files),
            'raster_files': len(raster_files),
            'tabular_files': len(tabular_files),
            'processed_files': len(processed_files),
            'joined_files': len(joined_files),
            'raw_output_path': self.raw_output_path,
            'processed_output_path': self.processed_output_path
        }


def main():
    """Main function to run the comprehensive data explorer."""
    
    # Get the project root directory
    script_path = Path(__file__).parent
    project_root = script_path.parent
    
    print("🏢 Jakarta Comprehensive Data Explorer")
    print("=" * 80)
    print(f"📁 Project root: {project_root}")
    
    # Initialize and run explorer
    explorer = JakartaDataExplorer(str(project_root))
    results = explorer.run_comprehensive_exploration()
    
    print("\n🎯 EXPLORATION RESULTS:")
    print(f"✅ Vector datasets analyzed: {results['vector_datasets']}")
    print(f"✅ Raster datasets analyzed: {results['raster_datasets']}")  
    print(f"✅ Tabular datasets analyzed: {results['tabular_datasets']}")
    print(f"🔄 Processed datasets analyzed: {results['processed_datasets']}")
    print(f"🎨 Vector visualization files created: {results.get('vector_files', 0)}")
    print(f"🌍 Raster visualization files created: {results.get('raster_files', 0)}")
    print(f"📊 Tabular visualization files created: {results.get('tabular_files', 0)}")
    print(f"🔄 Processed visualization files created: {results.get('processed_files', 0)}")
    print(f"🔗 Tabular-joined visualization files created: {results.get('joined_files', 0)}")
    print(f"📁 Raw data visualizations: {results['raw_output_path']}")
    print(f"🔄 Processed data visualizations: {results['processed_output_path']}")
    
    return results


if __name__ == "__main__":
    results = main()