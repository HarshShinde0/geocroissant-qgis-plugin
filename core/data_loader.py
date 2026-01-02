# -*- coding: utf-8 -*-
"""
Data Loaders for GeoCroissant Tools

Loads raster (COG) and vector (CSV) data from various sources
including S3, HTTP, and local files.
"""

from typing import Optional
import re

from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
)


class COGLoader:
    """
    Loads Cloud-Optimized GeoTIFF (COG) files.

    Supports loading from:
    - S3 URLs (s3://bucket/path)
    - HTTP/HTTPS URLs
    - Local file paths
    """

    def __init__(self, url: str, layer_name: str = "COG") -> None:
        """
        Initialize the COG loader.

        :param url: URL or path to the COG file
        :param layer_name: Name for the loaded layer
        """
        self.original_url = url
        self.url = self._convert_url(url)
        self.layer_name = layer_name

    def _convert_url(self, url: str) -> str:
        """
        Convert URL to GDAL-compatible virtual filesystem path.

        :param url: Original URL
        :returns: GDAL virtual filesystem path
        """
        if url.startswith("s3://"):
            # Convert s3://bucket/path to /vsis3/bucket/path
            return url.replace("s3://", "/vsis3/")

        elif url.startswith("http://") or url.startswith("https://"):
            # Use /vsicurl/ for HTTP(S) URLs
            return f"/vsicurl/{url}"

        elif url.startswith("gs://"):
            # Google Cloud Storage
            return url.replace("gs://", "/vsigs/")

        elif url.startswith("az://") or url.startswith("abfs://"):
            # Azure Blob Storage
            return url.replace("az://", "/vsiaz/").replace("abfs://", "/vsiaz/")

        else:
            # Assume local file path
            return url

    def load(self) -> Optional[QgsRasterLayer]:
        """
        Load the COG as a raster layer.

        :returns: QgsRasterLayer or None if loading fails
        """
        layer = QgsRasterLayer(self.url, self.layer_name)

        if layer.isValid():
            return layer

        # Try alternative URL formats
        if self.original_url.startswith("s3://"):
            # Try as public S3 URL
            bucket_match = re.match(r"s3://([^/]+)/(.+)", self.original_url)
            if bucket_match:
                bucket = bucket_match.group(1)
                path = bucket_match.group(2)
                public_url = f"https://{bucket}.s3.amazonaws.com/{path}"
                alt_url = f"/vsicurl/{public_url}"

                layer = QgsRasterLayer(alt_url, self.layer_name)
                if layer.isValid():
                    return layer

        return None

    def get_gdal_path(self) -> str:
        """Get the GDAL virtual filesystem path."""
        return self.url


class CSVLoader:
    """
    Loads CSV files as point vector layers.

    Supports loading from:
    - S3 URLs (s3://bucket/path)
    - HTTP/HTTPS URLs
    - Local file paths
    """

    def __init__(
        self,
        url: str,
        layer_name: str = "CSV",
        x_field: str = "longitude",
        y_field: str = "latitude",
        crs: str = "EPSG:4326",
    ) -> None:
        """
        Initialize the CSV loader.

        :param url: URL or path to the CSV file
        :param layer_name: Name for the loaded layer
        :param x_field: Name of the longitude/X field
        :param y_field: Name of the latitude/Y field
        :param crs: Coordinate reference system
        """
        self.original_url = url
        self.url = self._convert_url(url)
        self.layer_name = layer_name
        self.x_field = x_field
        self.y_field = y_field
        self.crs = crs

    def _convert_url(self, url: str) -> str:
        """
        Convert URL to GDAL-compatible path for CSV.

        :param url: Original URL
        :returns: URL suitable for CSV loading
        """
        if url.startswith("s3://"):
            # Convert to public S3 URL
            bucket_match = re.match(r"s3://([^/]+)/(.+)", url)
            if bucket_match:
                bucket = bucket_match.group(1)
                path = bucket_match.group(2)
                return f"https://{bucket}.s3.amazonaws.com/{path}"
            return url.replace("s3://", "https://")

        elif url.startswith("gs://"):
            # Convert to public GCS URL
            return url.replace("gs://", "https://storage.googleapis.com/")

        else:
            return url

    def load(self) -> Optional[QgsVectorLayer]:
        """
        Load the CSV as a point vector layer.

        :returns: QgsVectorLayer or None if loading fails
        """
        # Construct the URI for delimited text provider
        # Try common coordinate field names
        x_fields = [self.x_field, "lon", "lng", "x", "long"]
        y_fields = [self.y_field, "lat", "y"]

        for x_f in x_fields:
            for y_f in y_fields:
                uri = (
                    f"{self.url}?type=csv"
                    f"&xField={x_f}"
                    f"&yField={y_f}"
                    f"&crs={self.crs}"
                    f"&spatialIndex=yes"
                    f"&subsetIndex=no"
                    f"&watchFile=no"
                )

                layer = QgsVectorLayer(uri, self.layer_name, "delimitedtext")

                if layer.isValid() and layer.featureCount() > 0:
                    return layer

        # Fallback: load without geometry
        uri = f"{self.url}?type=csv&geomType=none"
        layer = QgsVectorLayer(uri, self.layer_name, "delimitedtext")

        if layer.isValid():
            return layer

        return None


class GeoPackageLoader:
    """
    Loads GeoPackage files.

    Supports loading from local paths and HTTP URLs.
    """

    def __init__(
        self, url: str, layer_name: str = "GeoPackage", table_name: Optional[str] = None
    ) -> None:
        """
        Initialize the GeoPackage loader.

        :param url: URL or path to the GeoPackage file
        :param layer_name: Name for the loaded layer
        :param table_name: Specific table to load (optional)
        """
        self.url = url
        self.layer_name = layer_name
        self.table_name = table_name

    def load(self) -> Optional[QgsVectorLayer]:
        """
        Load the GeoPackage as a vector layer.

        :returns: QgsVectorLayer or None if loading fails
        """
        if self.table_name:
            uri = f"{self.url}|layername={self.table_name}"
        else:
            uri = self.url

        layer = QgsVectorLayer(uri, self.layer_name, "ogr")

        if layer.isValid():
            return layer

        return None
