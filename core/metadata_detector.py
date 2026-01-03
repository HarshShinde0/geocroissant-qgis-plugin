# -*- coding: utf-8 -*-
"""
Universal Metadata Format Detector

Detects and adapts to various metadata formats:
- GeoCroissant (Croissant-based)
- NASA CMR-UMM (Unified Metadata Model)
- STAC (SpatioTemporal Asset Catalog)
- Generic GeoJSON-like formats
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class MetadataFormat(Enum):
    """Supported metadata formats."""
    GEOCROISSANT = "geocroissant"
    CMR_UMM = "cmr_umm"
    STAC = "stac"
    GENERIC = "generic"


class MetadataDetector:
    """Detects metadata format and provides format-agnostic interface."""

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Initialize the detector.

        :param data: Parsed JSON data
        """
        self.data = data
        self.format = self._detect_format()

    def _detect_format(self) -> MetadataFormat:
        """
        Detect the metadata format.

        :returns: MetadataFormat enum
        """
        # Check for CMR-UMM format (NASA)
        if "umm" in self.data and "meta" in self.data:
            return MetadataFormat.CMR_UMM
        
        # Check for STAC format
        if self.data.get("stac_version") or (
            self.data.get("type") == "FeatureCollection" and 
            "links" in self.data
        ):
            return MetadataFormat.STAC
        
        # Check for GeoCroissant format
        if "recordSet" in self.data or "distribution" in self.data:
            return MetadataFormat.GEOCROISSANT
        
        # Default to generic
        return MetadataFormat.GENERIC

    def get_format(self) -> MetadataFormat:
        """Get detected format."""
        return self.format

    def get_name(self) -> str:
        """Get dataset name from any format."""
        if self.format == MetadataFormat.CMR_UMM:
            # CMR-UMM format
            umm = self.data.get("umm", {})
            collection_ref = umm.get("CollectionReference", {})
            return collection_ref.get("EntryTitle", 
                   umm.get("GranuleUR", "Unknown Dataset"))
        
        elif self.format == MetadataFormat.STAC:
            return self.data.get("title", self.data.get("id", "Unknown Dataset"))
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            return self.data.get("name", "Unknown Dataset")
        
        else:
            return self.data.get("name", 
                   self.data.get("title", 
                   self.data.get("id", "Unknown Dataset")))

    def get_description(self) -> str:
        """Get dataset description."""
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            collection_ref = umm.get("CollectionReference", {})
            entry_title = collection_ref.get("EntryTitle", "")
            return entry_title if entry_title else ""
        
        return (self.data.get("description") or 
                self.data.get("abstract") or "")

    def get_spatial_extent(self) -> Optional[Dict[str, Any]]:
        """
        Get spatial extent bounding box.

        :returns: Dict with west, south, east, north or None
        """
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            spatial = umm.get("SpatialExtent", {})
            horizontal = spatial.get("HorizontalSpatialDomain", {})
            geometry = horizontal.get("Geometry", {})
            polygons = geometry.get("GPolygons", [])
            
            if polygons:
                boundary = polygons[0].get("Boundary", {})
                points = boundary.get("Points", [])
                if points:
                    lons = [p.get("Longitude", 0) for p in points]
                    lats = [p.get("Latitude", 0) for p in points]
                    return {
                        "west": min(lons),
                        "south": min(lats),
                        "east": max(lons),
                        "north": max(lats),
                    }
            return None
        
        elif self.format == MetadataFormat.STAC:
            bbox = self.data.get("bbox")
            if bbox and len(bbox) >= 4:
                return {
                    "west": bbox[0],
                    "south": bbox[1],
                    "east": bbox[2],
                    "north": bbox[3],
                }
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            bbox = self.data.get("geocr:BoundingBox")
            if bbox and len(bbox) >= 4:
                return {
                    "west": bbox[0],
                    "south": bbox[1],
                    "east": bbox[2],
                    "north": bbox[3],
                }
        
        return None

    def get_temporal_extent(self) -> Optional[Dict[str, str]]:
        """
        Get temporal extent.

        :returns: Dict with start and end dates or None
        """
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            temporal = umm.get("TemporalExtent", {})
            range_dt = temporal.get("RangeDateTime", {})
            
            start = range_dt.get("BeginningDateTime")
            end = range_dt.get("EndingDateTime")
            
            if start or end:
                return {
                    "start": start or "",
                    "end": end or "",
                }
            return None
        
        elif self.format == MetadataFormat.STAC:
            start = self.data.get("start_datetime")
            end = self.data.get("end_datetime")
            if start or end:
                return {"start": start or "", "end": end or ""}
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            temporal = self.data.get("geocr:temporalExtent")
            if temporal:
                return temporal
        
        return None

    def get_crs(self) -> str:
        """Get coordinate reference system."""
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            attributes = umm.get("AdditionalAttributes", [])
            
            for attr in attributes:
                if attr.get("Name") == "HORIZONTAL_CS_CODE":
                    values = attr.get("Values", [])
                    if values:
                        return values[0]
            
            return "EPSG:4326"
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            return self.data.get("geocr:coordinateReferenceSystem", "EPSG:4326")
        
        return "EPSG:4326"

    def get_spatial_resolution(self) -> Optional[str]:
        """Get spatial resolution."""
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            attributes = umm.get("AdditionalAttributes", [])
            
            for attr in attributes:
                if attr.get("Name") == "SPATIAL_RESOLUTION":
                    values = attr.get("Values", [])
                    if values:
                        return f"{values[0]} m"
            return None
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            return self.data.get("geocr:spatialResolution")
        
        return None

    def get_download_urls(self) -> List[Dict[str, str]]:
        """
        Get all download URLs with descriptions.

        :returns: List of dicts with 'url', 'name', 'type'
        """
        urls = []
        
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            related_urls = umm.get("RelatedUrls", [])
            
            for url_obj in related_urls:
                url_type = url_obj.get("Type", "")
                if "GET DATA" in url_type or "DOWNLOAD" in url_type:
                    urls.append({
                        "url": url_obj.get("URL", ""),
                        "name": url_obj.get("Description", ""),
                        "type": url_type,
                    })
            
            return urls
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            distribution = self.data.get("distribution", [])
            for item in distribution:
                if item.get("@type") == "cr:FileObject":
                    urls.append({
                        "url": item.get("contentUrl", ""),
                        "name": item.get("name", ""),
                        "type": item.get("encodingFormat", ""),
                    })
            return urls
        
        return []

    def get_metadata_items(self) -> List[Tuple[str, str]]:
        """
        Get all key metadata items.

        :returns: List of (key, value) tuples
        """
        items = []
        
        if self.format == MetadataFormat.CMR_UMM:
            umm = self.data.get("umm", {})
            
            # Basic info
            items.append(("Provider", self.data.get("meta", {}).get("provider-id", "-")))
            items.append(("Concept ID", self.data.get("meta", {}).get("concept-id", "-")))
            items.append(("Format", self.data.get("meta", {}).get("format", "-")))
            
            # Temporal
            temporal = self.get_temporal_extent()
            if temporal:
                items.append(("Start Date", temporal.get("start", "-")))
                items.append(("End Date", temporal.get("end", "-")))
            
            # Spatial attributes
            attributes = umm.get("AdditionalAttributes", [])
            attr_dict = {attr.get("Name"): attr.get("Values", []) for attr in attributes}
            
            for key in ["CLOUD_COVERAGE", "MGRS_TILE_ID", "SPATIAL_COVERAGE", "ACCODE"]:
                if key in attr_dict and attr_dict[key]:
                    items.append((key.replace("_", " "), str(attr_dict[key][0])))
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            items.append(("Version", self.data.get("version", "-")))
            items.append(("License", self.data.get("license", "-")))
            items.append(("Conforms To", self.data.get("conformsTo", "-")))
        
        return items

    def get_assets(self) -> List[Dict[str, Any]]:
        """
        Get all available assets/files.

        :returns: List of asset dicts
        """
        assets = []
        
        if self.format == MetadataFormat.CMR_UMM:
            urls = self.get_download_urls()
            for i, url in enumerate(urls):
                assets.append({
                    "id": f"asset_{i}",
                    "url": url.get("url"),
                    "title": url.get("name"),
                    "description": url.get("type"),
                })
        
        elif self.format == MetadataFormat.STAC:
            stac_assets = self.data.get("assets", {})
            for asset_id, asset_info in stac_assets.items():
                assets.append({
                    "id": asset_id,
                    "url": asset_info.get("href", ""),
                    "title": asset_info.get("title", asset_id),
                    "description": asset_info.get("description", ""),
                    "media_type": asset_info.get("type", ""),
                })
        
        elif self.format == MetadataFormat.GEOCROISSANT:
            distribution = self.data.get("distribution", [])
            for item in distribution:
                assets.append({
                    "id": item.get("@id", ""),
                    "url": item.get("contentUrl", ""),
                    "title": item.get("name", ""),
                    "description": item.get("description", ""),
                    "media_type": item.get("encodingFormat", ""),
                })
        
        return assets
