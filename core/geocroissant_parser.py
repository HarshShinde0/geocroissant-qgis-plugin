# -*- coding: utf-8 -*-
"""
GeoCroissant JSON Parser

Parses GeoCroissant metadata files and extracts relevant information
for visualization and data loading in QGIS.
"""

import json
from typing import Any, Dict, List, Optional


class GeoCroissantParser:
    """Parser for GeoCroissant JSON metadata files."""

    def __init__(self, file_path: str) -> None:
        """
        Initialize parser with a GeoCroissant JSON file.

        :param file_path: Path to the GeoCroissant JSON file
        """
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load and parse the JSON file."""
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def get_name(self) -> str:
        """Get dataset name."""
        return self.data.get("name", "Unknown Dataset")

    def get_version(self) -> str:
        """Get dataset version."""
        return self.data.get("version", "1.0.0")

    def get_license(self) -> str:
        """Get dataset license."""
        return self.data.get("license", "Unknown")

    def get_description(self) -> str:
        """Get dataset description."""
        return self.data.get("description", "")

    def get_bounding_box(self) -> Optional[List[float]]:
        """
        Get the dataset bounding box.

        :returns: List [west, south, east, north] or None
        """
        bbox = self.data.get("geocr:BoundingBox")
        if bbox and len(bbox) >= 4:
            return bbox[:4]
        return None

    def get_temporal_extent(self) -> Optional[Dict[str, str]]:
        """
        Get the temporal extent.

        :returns: Dict with startDate and endDate, or None
        """
        return self.data.get("geocr:temporalExtent")

    def get_spatial_resolution(self) -> str:
        """Get spatial resolution."""
        return self.data.get("geocr:spatialResolution", "Unknown")

    def get_crs(self) -> str:
        """Get coordinate reference system."""
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

            # Check if item_id is in the file identifier
            if item_id in file_id or item_id in file_name or item_id in content_url:
                # Check file type match
                if file_type.lower() in file_id.lower():
                    return file_obj
                if file_type.lower() in file_name.lower():
                    return file_obj
                if file_type.lower() in content_url.lower():
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
