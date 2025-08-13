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
        
        total_datasets = sum(len(datasets) for datasets in self.vector_datasets.values())
        print(f"\n📈 Total vector datasets loaded: {total_datasets} across {len(self.vector_datasets)} folders")
        return dict(self.vector_datasets)
    
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
                            # Create histogram for numeric data
                            data_values = df[col].dropna()
                            if len(data_values) > 0:
                                ax.hist(data_values, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                                ax.set_title(f"{col}\n(n={len(data_values):,})", fontsize=10)
                                ax.set_xlabel(col, fontsize=8)
                                ax.set_ylabel('Frequency', fontsize=8)
                                
                                # Add statistics
                                stats_text = f"Mean: {data_values.mean():.2f}\nStd: {data_values.std():.2f}"
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
        """Plot a single vector dataset."""
        gdf = dataset_info['data']
        data_type = dataset_info['data_type']
        
        # Add Jakarta boundaries as context if available
        if self.neighborhoods is not None:
            self.neighborhoods.boundary.plot(ax=ax, color='lightgray', linewidth=0.5, alpha=0.7)
        elif self.jakarta_boundaries is not None:
            self.jakarta_boundaries.boundary.plot(ax=ax, color='lightgray', linewidth=0.8)
        
        # Plot the dataset
        color = colors.get(data_type, '#95a5a6')
        
        if data_type == 'point':
            gdf.plot(ax=ax, color=color, markersize=20, alpha=0.7, edgecolor='white', linewidth=0.5)
        elif data_type == 'line':
            gdf.plot(ax=ax, color=color, linewidth=1.5, alpha=0.8)
        elif data_type == 'polygon':
            # Check if we have numeric data for coloring
            numeric_cols = dataset_info.get('numeric_columns', [])
            if numeric_cols and len(numeric_cols) > 0:
                # Use first numeric column for coloring
                col_name = numeric_cols[0]
                if gdf[col_name].std() > 0:  # Check for variation
                    gdf.plot(ax=ax, column=col_name, cmap='viridis', alpha=0.7, 
                           edgecolor='white', linewidth=0.2, legend=True,
                           legend_kwds={'shrink': 0.8, 'aspect': 20})
                else:
                    gdf.plot(ax=ax, color=color, alpha=0.7, edgecolor='white', linewidth=0.2)
            else:
                gdf.plot(ax=ax, color=color, alpha=0.7, edgecolor='white', linewidth=0.2)
        else:
            gdf.plot(ax=ax, color=color, alpha=0.7)
        
        # Set equal aspect ratio
        ax.set_aspect('equal', adjustable='box')
    
    def _plot_raster_dataset(self, ax, dataset_info: Dict):
        """Plot a single raster dataset."""
        file_path = dataset_info['file_path']
        
        # Read and plot raster
        with rasterio.open(file_path) as src:
            # Sample the data for plotting (to avoid memory issues)
            if src.width > 2000 or src.height > 2000:
                # Downsample large rasters
                scale_factor = max(src.width // 2000, src.height // 2000, 1)
                data = src.read(1, out_shape=(src.height // scale_factor, src.width // scale_factor))
            else:
                data = src.read(1)
            
            # Handle nodata
            if src.nodata is not None:
                data = np.ma.masked_equal(data, src.nodata)
            
            # Plot with colormap
            im = ax.imshow(data, cmap='viridis', alpha=0.8)
            
            # Add colorbar
            plt.colorbar(im, ax=ax, shrink=0.8, aspect=20)
        
        ax.set_aspect('equal', adjustable='box')
    
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