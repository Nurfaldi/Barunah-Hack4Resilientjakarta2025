#!/usr/bin/env python3
"""
Complete Metadata Generator for Jakarta Flood Resilience Datasets
================================================================
This script creates comprehensive metadata for all discovered datasets by combining
existing metadata with actual data discovery from the extracted_data directory.

Author: Data Governance Script
Date: 2025-08-14
"""

import os
import sys
import glob
import pandas as pd
from pathlib import Path
import csv
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

class CompleteMetadataGenerator:
    """Generate complete metadata for all Jakarta datasets."""
    
    def __init__(self, base_path: str):
        """Initialize the metadata generator."""
        self.base_path = Path(base_path)
        self.extracted_data_path = self.base_path / "data" / "extracted_data"
        self.metadata_path = self.base_path / "data" / "metadata"
        self.output_path = self.metadata_path / "Complete_Dataset_Metadata.csv"
        
        # Load existing metadata
        self.existing_metadata = self._load_existing_metadata()
        
        # Discovered datasets structure
        self.discovered_datasets = []
        
        print(f"🏢 Complete Metadata Generator initialized")
        print(f"📁 Base path: {self.base_path}")
        print(f"📊 Data path: {self.extracted_data_path}")
        print(f"📋 Metadata path: {self.metadata_path}")
        print(f"💾 Output file: {self.output_path}")
    
    def _load_existing_metadata(self) -> Dict:
        """Load existing metadata files."""
        metadata = {
            'datasources': {},
            'flooding_mapping': {},
            'neighborhood_columns': {}
        }
        
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
                    
            print(f"📋 Loaded existing metadata: {len(metadata['datasources'])} datasources, "
                  f"{len(metadata['flooding_mapping'])} flood indicators, "
                  f"{len(metadata['neighborhood_columns'])} column definitions")
                  
        except Exception as e:
            print(f"⚠️  Warning: Could not fully load existing metadata: {e}")
            
        return metadata
    
    def discover_all_datasets(self):
        """Discover all datasets in the extracted_data directory."""
        print("\n🔍 DISCOVERING ALL DATASETS...")
        print("=" * 60)
        
        if not self.extracted_data_path.exists():
            print(f"❌ Extracted data path does not exist: {self.extracted_data_path}")
            return
        
        # Get all top-level directories (these are our main categories)
        main_folders = [d for d in self.extracted_data_path.iterdir() if d.is_dir()]
        main_folders.sort()
        
        print(f"📁 Found {len(main_folders)} main data folders")
        
        for folder in main_folders:
            print(f"\n📂 Processing folder: {folder.name}")
            self._analyze_folder(folder)
        
        print(f"\n✅ Dataset discovery completed: {len(self.discovered_datasets)} datasets found")
    
    def _analyze_folder(self, folder: Path):
        """Analyze a single folder for datasets."""
        folder_name = folder.name
        
        # Extract index number from folder name if present
        folder_index = None
        if folder_name.split()[0].isdigit():
            folder_index = int(folder_name.split()[0])
        
        # Get existing metadata for this folder index
        existing_meta = self.existing_metadata['datasources'].get(folder_index, {})
        
        # Find all data files in this folder (recursively)
        data_extensions = {
            '.shp': 'Vector',
            '.geojson': 'Vector', 
            '.gpkg': 'Vector',
            '.kml': 'Vector',
            '.gml': 'Vector',
            '.tif': 'Raster',
            '.tiff': 'Raster',
            '.img': 'Raster',
            '.jp2': 'Raster',
            '.csv': 'Tabular',
            '.xlsx': 'Tabular',
            '.xls': 'Tabular'
        }
        
        # Find all data files
        data_files = []
        for ext in data_extensions.keys():
            pattern = f"**/*{ext}"
            found_files = list(folder.glob(pattern))
            data_files.extend([(f, data_extensions[ext]) for f in found_files])
        
        print(f"  📊 Found {len(data_files)} data files")
        
        # If no data files found, still create an entry for the folder
        if not data_files:
            self._add_dataset_entry(
                folder_index=folder_index,
                folder_name=folder_name,
                dataset_name=folder_name,
                file_path=folder,
                file_type="Folder",
                data_type="Mixed",
                existing_meta=existing_meta
            )
        else:
            # Group files by subdirectory and type
            file_groups = defaultdict(list)
            
            for file_path, data_type in data_files:
                # Get relative path from folder
                rel_path = file_path.relative_to(folder)
                
                # Create grouping key based on parent directory and data type
                if len(rel_path.parts) > 1:
                    parent_dir = rel_path.parts[0]
                    group_key = f"{parent_dir}_{data_type}"
                else:
                    group_key = f"root_{data_type}"
                
                file_groups[group_key].append((file_path, data_type))
            
            # Create entries for each group
            for group_key, group_files in file_groups.items():
                # For groups with multiple files, create individual entries
                if len(group_files) > 5:  # If many files, group them
                    self._add_dataset_entry(
                        folder_index=folder_index,
                        folder_name=folder_name,
                        dataset_name=f"{folder_name}_{group_key}",
                        file_path=group_files[0][0].parent,  # Use directory
                        file_type="Multiple Files",
                        data_type=group_files[0][1],
                        existing_meta=existing_meta,
                        file_count=len(group_files)
                    )
                else:
                    # Create individual entries for each file
                    for file_path, data_type in group_files:
                        self._add_dataset_entry(
                            folder_index=folder_index,
                            folder_name=folder_name,
                            dataset_name=file_path.stem,
                            file_path=file_path,
                            file_type=file_path.suffix,
                            data_type=data_type,
                            existing_meta=existing_meta
                        )
    
    def _add_dataset_entry(self, folder_index: Optional[int], folder_name: str, 
                          dataset_name: str, file_path: Path, file_type: str,
                          data_type: str, existing_meta: Dict, file_count: int = 1):
        """Add a dataset entry to the discovered datasets list."""
        
        # Try to extract year information from filename or path
        years = self._extract_years(str(file_path))
        
        # Determine category based on folder name
        category = self._determine_category(folder_name)
        
        # Get file size if it's a file
        try:
            if file_path.is_file():
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
            else:
                file_size_mb = 0
        except:
            file_size_mb = 0
        
        # Create dataset entry
        dataset_entry = {
            'Index': folder_index or len(self.discovered_datasets) + 1,
            'Folder_Name': folder_name,
            'Dataset_Name': dataset_name,
            'Title': existing_meta.get('title', dataset_name),
            'Description': existing_meta.get('description', f"Dataset from {folder_name}"),
            'Data_Type': data_type,
            'File_Type': file_type,
            'Category': category,
            'Sources': existing_meta.get('sources', 'Unknown'),
            'File_Path': str(file_path.relative_to(self.extracted_data_path)),
            'File_Count': file_count,
            'File_Size_MB': round(file_size_mb, 2),
            'Years_Available': ', '.join(map(str, sorted(years))) if years else 'Unknown',
            'Year_Start': min(years) if years else 'Unknown',
            'Year_End': max(years) if years else 'Unknown',
            'Spatial_Type': self._determine_spatial_type(data_type, dataset_name),
            'Temporal_Type': self._determine_temporal_type(years),
            'Data_Status': 'Available',
            'Notes': self._generate_notes(dataset_name, file_type, years)
        }
        
        self.discovered_datasets.append(dataset_entry)
        print(f"    ✅ Added: {dataset_name} ({data_type}, {file_count} files)")
    
    def _extract_years(self, text: str) -> List[int]:
        """Extract year information from text."""
        import re
        
        # Common year patterns
        year_patterns = [
            r'\b(19|20)\d{2}\b',  # 4-digit years
            r'\b\d{2}\b'          # 2-digit years (interpreted as 20XX)
        ]
        
        years = set()
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2 and match.isdigit():
                    year = int(match)
                    if 15 <= year <= 30:  # Assume 2015-2030
                        years.add(2000 + year)
                elif len(match) == 4 and match.isdigit():
                    year = int(match)
                    if 2000 <= year <= 2030:
                        years.add(year)
        
        return list(years)
    
    def _determine_category(self, folder_name: str) -> str:
        """Determine category based on folder name."""
        name_lower = folder_name.lower()
        
        if any(word in name_lower for word in ['age', 'gender', 'population', 'education', 'poverty']):
            return 'Socio-Demographics'
        elif any(word in name_lower for word in ['flood', 'rain', 'climate', 'temperature', 'subsidence']):
            return 'Climate and Hazards'
        elif any(word in name_lower for word in ['building', 'infrastructure', 'drainage', 'pump', 'road']):
            return 'Infrastructure'
        elif any(word in name_lower for word in ['environment', 'vegetation', 'ndvi', 'surface', 'land']):
            return 'Physical Environment'
        elif any(word in name_lower for word in ['boundary', 'area', 'administrative', 'gis']):
            return 'Administrative and Spatial'
        else:
            return 'Other'
    
    def _determine_spatial_type(self, data_type: str, dataset_name: str) -> str:
        """Determine spatial representation type."""
        name_lower = dataset_name.lower()
        
        if data_type == 'Vector':
            if any(word in name_lower for word in ['point', 'location', 'pump', 'building']):
                return 'Point'
            elif any(word in name_lower for word in ['line', 'road', 'river', 'drainage']):
                return 'Line'
            elif any(word in name_lower for word in ['polygon', 'area', 'boundary', 'neighborhood']):
                return 'Polygon'
            else:
                return 'Mixed'
        elif data_type == 'Raster':
            return 'Grid/Raster'
        else:
            return 'Non-Spatial'
    
    def _determine_temporal_type(self, years: List[int]) -> str:
        """Determine temporal characteristics."""
        if not years:
            return 'Unknown'
        elif len(years) == 1:
            return 'Static'
        elif len(years) > 1:
            return 'Time Series'
        else:
            return 'Unknown'
    
    def _generate_notes(self, dataset_name: str, file_type: str, years: List[int]) -> str:
        """Generate notes for the dataset."""
        notes = []
        
        if years:
            if len(years) > 1:
                notes.append(f"Multi-year dataset ({min(years)}-{max(years)})")
            else:
                notes.append(f"Single year dataset ({years[0]})")
        
        if file_type == "Multiple Files":
            notes.append("Contains multiple data files")
        
        if any(word in dataset_name.lower() for word in ['merged', 'combined', 'all']):
            notes.append("Processed/combined dataset")
        
        return '; '.join(notes) if notes else 'Standard dataset'
    
    def create_complete_metadata_csv(self):
        """Create the complete metadata CSV file."""
        print(f"\n📝 CREATING COMPLETE METADATA CSV...")
        print("=" * 60)
        
        if not self.discovered_datasets:
            print("❌ No datasets discovered to create metadata")
            return
        
        # Define CSV columns
        columns = [
            'Index',
            'Folder_Name', 
            'Dataset_Name',
            'Title',
            'Description',
            'Data_Type',
            'File_Type',
            'Category',
            'Sources',
            'File_Path',
            'File_Count',
            'File_Size_MB',
            'Years_Available',
            'Year_Start',
            'Year_End',
            'Spatial_Type',
            'Temporal_Type',
            'Data_Status',
            'Notes'
        ]
        
        # Sort datasets by index
        sorted_datasets = sorted(self.discovered_datasets, key=lambda x: x['Index'])
        
        # Write to CSV
        try:
            with open(self.output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()
                
                for dataset in sorted_datasets:
                    writer.writerow(dataset)
            
            print(f"✅ Complete metadata CSV created successfully!")
            print(f"📁 Output file: {self.output_path}")
            print(f"📊 Total datasets: {len(sorted_datasets)}")
            
            # Print summary statistics
            self._print_summary_statistics()
            
        except Exception as e:
            print(f"❌ Error creating CSV file: {e}")
    
    def _print_summary_statistics(self):
        """Print summary statistics of the created metadata."""
        print(f"\n📊 METADATA SUMMARY STATISTICS")
        print("=" * 50)
        
        # Count by data type
        data_types = {}
        categories = {}
        temporal_types = {}
        
        for dataset in self.discovered_datasets:
            data_type = dataset['Data_Type']
            category = dataset['Category']
            temporal = dataset['Temporal_Type']
            
            data_types[data_type] = data_types.get(data_type, 0) + 1
            categories[category] = categories.get(category, 0) + 1
            temporal_types[temporal] = temporal_types.get(temporal, 0) + 1
        
        print(f"📈 Data Types:")
        for dtype, count in sorted(data_types.items()):
            print(f"  • {dtype}: {count}")
        
        print(f"\n📂 Categories:")
        for cat, count in sorted(categories.items()):
            print(f"  • {cat}: {count}")
        
        print(f"\n⏰ Temporal Types:")
        for temp, count in sorted(temporal_types.items()):
            print(f"  • {temp}: {count}")
        
        # Calculate total file size
        total_size = sum(d['File_Size_MB'] for d in self.discovered_datasets)
        print(f"\n💾 Total Data Size: {total_size:.2f} MB")
    
    def run_complete_metadata_generation(self):
        """Run the complete metadata generation process."""
        print("🚀 STARTING COMPLETE METADATA GENERATION")
        print("=" * 80)
        
        # Discover all datasets
        self.discover_all_datasets()
        
        # Create complete metadata CSV
        self.create_complete_metadata_csv()
        
        print(f"\n✅ METADATA GENERATION COMPLETED!")
        print(f"📁 Complete metadata saved to: {self.output_path}")
        print("=" * 80)
        
        return {
            'total_datasets': len(self.discovered_datasets),
            'output_file': self.output_path,
            'datasets': self.discovered_datasets
        }


def main():
    """Main function to run the complete metadata generator."""
    
    # Get the project root directory
    script_path = Path(__file__).parent
    project_root = script_path.parent
    
    print("🏢 Jakarta Complete Metadata Generator")
    print("=" * 80)
    print(f"📁 Project root: {project_root}")
    
    # Initialize and run generator
    generator = CompleteMetadataGenerator(str(project_root))
    results = generator.run_complete_metadata_generation()
    
    print(f"\n🎯 GENERATION RESULTS:")
    print(f"✅ Total datasets catalogued: {results['total_datasets']}")
    print(f"📁 Complete metadata file: {results['output_file']}")
    
    return results


if __name__ == "__main__":
    results = main()