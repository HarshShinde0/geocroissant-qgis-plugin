# -*- coding: utf-8 -*-
"""
Data Loaders for GeoCroissant Tools

Loads raster (COG) and vector (CSV) data from various sources
including S3, HTTP, and local files.
"""

from typing import Optional
import re
import os
import tempfile
import urllib.request

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
    Loads CSV files as point vector layers using OGR driver.

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
        self.layer_name = layer_name
        self.x_field = x_field
        self.y_field = y_field
        self.crs = crs

    def _download_file(self, url: str) -> Optional[str]:
        """
        Download a remote file to a temporary location.

        :param url: URL to download from
        :returns: Path to temporary file or None if download fails
        """
        try:
            if url.startswith("s3://"):
                # Convert s3:// to HTTPS for download
                bucket_match = re.match(r"s3://([^/]+)/(.+)", url)
                if bucket_match:
                    bucket = bucket_match.group(1)
                    path = bucket_match.group(2)
                    url = f"https://{bucket}.s3.amazonaws.com/{path}"

            # Download the file
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.csv') as tmp:
                tmp_path = tmp.name
                urllib.request.urlretrieve(url, tmp_path)
                return tmp_path
        except Exception:
            return None

    def load(self) -> Optional[QgsVectorLayer]:
        """
        Load the CSV as a point vector layer using OGR.

        :returns: QgsVectorLayer or None if loading fails
        """
        # For remote files, download first
        file_path = self.original_url
        is_temp = False
        
        if self.original_url.startswith(("s3://", "http://", "https://", "gs://", "az://", "abfs://")):
            downloaded_path = self._download_file(self.original_url)
            if downloaded_path:
                file_path = downloaded_path
                is_temp = True
            else:
                return None

        try:
            # Use OGR CSV driver which is more robust
            # OGR handles CSV better than delimitedtext for detecting headers and fields
            uri = file_path
            
            # Try loading with OGR CSV driver
            layer = QgsVectorLayer(uri, self.layer_name, "ogr")
            
            if layer.isValid() and layer.featureCount() > 0:
                return layer
            
            # Fallback: Try with delimitedtext for specific coordinate fields
            x_fields = [self.x_field, "lon", "lng", "x", "long", "longitude"]
            y_fields = [self.y_field, "lat", "y", "latitude"]

            for x_f in x_fields:
                for y_f in y_fields:
                    # Build proper URI with quoted path for delimitedtext
                    quoted_path = file_path.replace("\\", "/")
                    uri = (
                        f'file:///{quoted_path}?type=csv'
                        f'&xField={x_f}'
                        f'&yField={y_f}'
                        f'&crs={self.crs}'
                        f'&delimiter=,'
                    )

                    try:
                        layer = QgsVectorLayer(uri, self.layer_name, "delimitedtext")
                        if layer.isValid() and layer.featureCount() > 0:
                            return layer
                    except Exception:
                        continue

            # If nothing worked, return a basic non-spatial CSV layer
            try:
                layer = QgsVectorLayer(file_path, self.layer_name, "ogr")
                if layer.isValid():
                    return layer
            except Exception:
                pass

            return None
            
        finally:
            # Clean up temporary file
            if is_temp and file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except Exception:
                    pass


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

class NetCDFLoader:
    """
    Loads NetCDF (Network Common Data Form) files.

    Supports loading from:
    - HTTP/HTTPS URLs
    - Local file paths
    - S3 URLs (if supported by GDAL)
    """

    def __init__(self, url: str, layer_name: str = "NetCDF") -> None:
        """
        Initialize the NetCDF loader.

        :param url: URL or path to the NetCDF file
        :param layer_name: Name for the loaded layer
        """
        self.original_url = url
        self.local_file = self._ensure_local_file(url)
        self.layer_name = layer_name

    def _ensure_local_file(self, url: str) -> str:
        """
        Ensure we have a local file path. Download if needed.

        :param url: URL or local path
        :returns: Local file path
        """
        if url.startswith("http://") or url.startswith("https://"):
            # Download to temporary file
            try:
                temp_file = os.path.join(
                    tempfile.gettempdir(),
                    os.path.basename(url).split("?")[0]  # Remove query params
                )
                urllib.request.urlretrieve(url, temp_file)
                return temp_file
            except Exception as e:
                raise RuntimeError(f"Failed to download NetCDF file: {e}")
        else:
            # Local file
            return url

    def load(self) -> Optional[QgsRasterLayer]:
        """
        Load the NetCDF as a raster layer.

        Note: GDAL may open specific subdatasets. If this fails,
        the file may need to be opened manually in QGIS.

        :returns: QgsRasterLayer or None if loading fails
        """
        if not os.path.exists(self.local_file):
            return None

        # Try to load as raster (GDAL handles NetCDF files)
        layer = QgsRasterLayer(self.local_file, self.layer_name)

        if layer.isValid():
            return layer

        # NetCDF files may have subdatasets; try with NETCDF: prefix
        # Example: NETCDF:"file.nc":variable_name
        try:
            # List available subdatasets and try the first one
            layer = QgsRasterLayer(f'NETCDF:"{self.local_file}":0', self.layer_name)
            if layer.isValid():
                return layer
        except Exception:
            pass

        return None