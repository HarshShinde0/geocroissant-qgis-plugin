# -*- coding: utf-8 -*-
"""
GeoCroissant JSON Parser

Parses various metadata formats (GeoCroissant, NASA CMR-UMM, STAC, etc)
and extracts relevant information for visualization and data loading in QGIS.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from .metadata_detector import MetadataDetector, MetadataFormat


class GeoCroissantParser:
    """Parser for various geospatial metadata formats."""

    def __init__(self, file_path: str) -> None:
        """
        Initialize parser with a metadata JSON file.

        Automatically detects format (GeoCroissant, CMR-UMM, STAC, etc)

        :param file_path: Path to the metadata JSON file
        """
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self.detector: Optional[MetadataDetector] = None
        self._load()

    def _load(self) -> None:
        """Load and parse the JSON file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            
            # Initialize detector for format-agnostic parsing
            self.detector = MetadataDetector(self.data)
        except Exception as e:
            print(f"Error loading file {self.file_path}: {e}")
            self.detector = None

    def get_name(self) -> str:
        """Get dataset name."""
        try:
            if self.detector:
                name = self.detector.get_name()
                if name and name != "Unknown Dataset":
                    return name
        except Exception as e:
            print(f"Error getting name from detector: {e}")
        
        # Fallback approaches
        return self.data.get("name", "Unknown Dataset")

    def get_version(self) -> str:
        """Get dataset version."""
        if self.detector and self.detector.format == MetadataFormat.GEOCROISSANT:
            return self.data.get("version", "1.0.0")
        return "1.0.0"

    def get_license(self) -> str:
        """Get dataset license."""
        if self.detector and self.detector.format == MetadataFormat.GEOCROISSANT:
            return self.data.get("license", "Unknown")
        return "Unknown"

    def get_description(self) -> str:
        """Get dataset description."""
        if self.detector:
            return self.detector.get_description()
        return self.data.get("description", "")

    def get_bounding_box(self) -> Optional[List[float]]:
        """
        Get the dataset bounding box.

        :returns: List [west, south, east, north] or None
        """
        if self.detector:
            extent = self.detector.get_spatial_extent()
            if extent:
                return [extent["west"], extent["south"], extent["east"], extent["north"]]
        
        # Fallback to old format
        bbox = self.data.get("geocr:BoundingBox")
        if bbox and len(bbox) >= 4:
            return bbox[:4]
        return None

    def get_temporal_extent(self) -> Optional[Dict[str, str]]:
        """
        Get the temporal extent.

        :returns: Dict with startDate and endDate, or None
        """
        if self.detector:
            temporal = self.detector.get_temporal_extent()
            if temporal:
                # Normalize keys
                return {
                    "startDate": temporal.get("start", ""),
                    "endDate": temporal.get("end", ""),
                }
        
        return self.data.get("geocr:temporalExtent")

    def get_spatial_resolution(self) -> str:
        """Get spatial resolution."""
        if self.detector:
            resolution = self.detector.get_spatial_resolution()
            if resolution:
                return resolution
        return self.data.get("geocr:spatialResolution", "Unknown")

    def get_crs(self) -> str:
        """Get coordinate reference system."""
        if self.detector:
            crs = self.detector.get_crs()
            if crs and crs != "EPSG:4326":
                return crs
        
        return self.data.get("geocr:coordinateReferenceSystem", "EPSG:4326")

    def get_distribution_files(self) -> List[Dict[str, Any]]:
        """
        Get all distribution file objects.

        :returns: List of file objects with contentUrl, encodingFormat, etc.
        """
        distribution = self.data.get("distribution", [])
        return [d for d in distribution if d.get("@type") == "cr:FileObject"]

    def get_file_sets(self) -> List[Dict[str, Any]]:
        """
        Get all file set objects.

        :returns: List of file set objects
        """
        distribution = self.data.get("distribution", [])
        return [d for d in distribution if d.get("@type") == "cr:FileSet"]

    def get_record_sets(self) -> List[Dict[str, Any]]:
        """
        Get all record sets.

        :returns: List of record set objects
        """
        return self.data.get("recordSet", [])

    def get_items(self) -> List[Dict[str, Any]]:
        """
        Get all items from recordSet data.

        Extracts items from the recordSet structure, returning a list of
        dictionaries with id, datetime, bbox, and assets.

        :returns: List of item dictionaries
        """
        items = []
        record_sets = self.get_record_sets()

        for record_set in record_sets:
            data = record_set.get("data", [])
            fields = record_set.get("field", [])

            # Get field name prefix (e.g., "icesat2-boreal-v2.1-agb_items/")
            prefix = ""
            if fields:
                first_field_id = fields[0].get("@id", "")
                if "/" in first_field_id:
                    prefix = first_field_id.rsplit("/", 1)[0] + "/"

            for item_data in data:
                item = {}

                # Extract values using the prefix
                for key in ["id", "datetime", "bbox", "assets"]:
                    full_key = f"{prefix}{key}"
                    if full_key in item_data:
                        item[key] = item_data[full_key]

                # Fallback to direct keys
                if not item:
                    for k, v in item_data.items():
                        # Strip prefix from key
                        simple_key = k.split("/")[-1] if "/" in k else k
                        item[simple_key] = v

                if item:
                    items.append(item)

        return items

    def get_item_count(self) -> int:
        """Get the number of items."""
        return len(self.get_items())

    def get_dataset_type(self) -> str:
        """
        Detect dataset type based on structure.

        :returns: "tiles" if recordSet contains data items, "files" otherwise
        """
        record_sets = self.get_record_sets()
        for record_set in record_sets:
            if record_set.get("data"):
                return "tiles"
        return "files"

    def get_references(self) -> List[Dict[str, Any]]:
        """
        Get all reference links.

        :returns: List of reference objects with name and url
        """
        return self.data.get("references", [])

    def find_distribution_file(
        self, item_id: str, file_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a distribution file matching an item ID and file type.

        :param item_id: The item/tile ID to search for
        :param file_type: The file type to match (e.g., "cog", "csv", ".tif")
        :returns: Matching file object or None
        """
        files = self.get_distribution_files()

        for file_obj in files:
            file_id = file_obj.get("@id", "")
            file_name = file_obj.get("name", "")
            content_url = file_obj.get("contentUrl", "")
            encoding_format = file_obj.get("encodingFormat", "")

            # Check if item_id is in the file identifier
            if item_id in file_id or item_id in file_name or item_id in content_url:
                # Check file type match - try multiple variations
                file_type_lower = file_type.lower()
                
                # Direct checks
                if file_type_lower in file_id.lower():
                    return file_obj
                if file_type_lower in file_name.lower():
                    return file_obj
                if file_type_lower in content_url.lower():
                    return file_obj
                
                # Check encoding format for CSV
                if file_type_lower == "csv" and "text/csv" in encoding_format.lower():
                    return file_obj
                if file_type_lower == "csv" and ".csv" in content_url.lower():
                    return file_obj
                
                # Check for COG/TIF variations
                if file_type_lower in ["cog", ".tif", "tif"] and ("cog" in file_id.lower() or ".tif" in content_url.lower() or "geotiff" in encoding_format.lower()):
                    return file_obj

        return None

    def get_visualizations(self) -> Dict[str, Any]:
        """
        Get visualization configurations.

        :returns: Dict of visualization configs
        """
        return self.data.get("geocr:visualizations", {})

    def get_summaries(self) -> Dict[str, Any]:
        """
        Get dataset summaries (platforms, instruments, etc.).

        :returns: Dict of summary information
        """
        return self.data.get("geocr:summaries", {})

    def is_live_dataset(self) -> bool:
        """Check if this is a live (updating) dataset."""
        return self.data.get("isLiveDataset", False)

    def get_keywords(self) -> List[str]:
        """Get dataset keywords."""
        return self.data.get("keywords", [])

    def to_dict(self) -> Dict[str, Any]:
        """Return the raw data dictionary."""
        return self.data

    def get_format(self) -> str:
        """
        Get detected metadata format.

        :returns: Format name (geocroissant, cmr_umm, stac, generic)
        """
        if self.detector:
            return self.detector.format.value
        return "unknown"

    def get_assets(self) -> List[Dict[str, Any]]:
        """
        Get all available assets dynamically.

        Works with any supported format.

        :returns: List of asset dictionaries with url, name, type
        """
        if self.detector:
            return self.detector.get_assets()
        
        # Fallback
        distribution = self.data.get("distribution", [])
        return [d for d in distribution if d.get("@type") == "cr:FileObject"]

    def get_downloadable_files(self) -> List[Dict[str, str]]:
        """
        Get all downloadable file URLs from any format.

        :returns: List of dicts with 'url', 'name', 'type'
        """
        if self.detector:
            return self.detector.get_download_urls()
        
        return []

    def get_all_metadata(self) -> List[Tuple[str, str]]:
        """
        Get all metadata items from detector.

        :returns: List of (key, value) tuples
        """
        if self.detector:
            return self.detector.get_metadata_items()
        
        return []
