# -*- coding: utf-8 -*-
"""
Tests for GeoCroissant Parser

Run with: python -m pytest tests/test_parser.py -v
Or: python tests/test_parser.py
"""

import os
import json
import tempfile
import unittest
import sys

# Add the core directory directly to avoid importing core/__init__.py
core_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"
)
sys.path.insert(0, core_dir)

# Import parser module directly (without going through core/__init__.py)
from geocroissant_parser import GeoCroissantParser  # noqa: E402


class TestGeoCroissantParser(unittest.TestCase):
    """Test cases for GeoCroissantParser."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = {
            "@context": {
                "@vocab": "https://schema.org/",
                "cr": "http://mlcommons.org/croissant/",
                "geocr": "http://mlcommons.org/croissant/geocr/",
            },
            "@type": "sc:Dataset",
            "name": "Test Dataset",
            "version": "1.0.0",
            "license": "CC-BY-4.0",
            "geocr:BoundingBox": [-118.93, 54.07, 174.73, 73.86],
            "geocr:temporalExtent": {
                "startDate": "2020-01-01T00:00:00Z",
                "endDate": "2020-12-31T23:59:59Z",
            },
            "geocr:spatialResolution": "30m",
            "geocr:coordinateReferenceSystem": "EPSG:4326",
            "distribution": [
                {
                    "@type": "cr:FileObject",
                    "@id": "tile_001/cog",
                    "name": "tile_001/cog",
                    "contentUrl": "s3://bucket/tile_001.tif",
                    "encodingFormat": "image/tiff",
                },
                {
                    "@type": "cr:FileObject",
                    "@id": "tile_001/csv",
                    "name": "tile_001/csv",
                    "contentUrl": "s3://bucket/tile_001.csv",
                    "encodingFormat": "text/csv",
                },
            ],
            "recordSet": [
                {
                    "@type": "cr:RecordSet",
                    "@id": "items",
                    "field": [
                        {"@id": "items/id", "name": "id"},
                        {"@id": "items/bbox", "name": "bbox"},
                    ],
                    "data": [
                        {
                            "items/id": "tile_001",
                            "items/bbox": [-118.93, 68.74, -115.73, 69.86],
                        },
                        {
                            "items/id": "tile_002",
                            "items/bbox": [106.76, 69.95, 110.04, 71.04],
                        },
                    ],
                }
            ],
            "references": [
                {
                    "@type": "CreativeWork",
                    "name": "STAC Catalog",
                    "url": "https://stac.example.org/",
                }
            ],
        }

        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(self.sample_data, self.temp_file)
        self.temp_file.close()

        self.parser = GeoCroissantParser(self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_file.name)

    def test_get_name(self):
        """Test getting dataset name."""
        self.assertEqual(self.parser.get_name(), "Test Dataset")

    def test_get_version(self):
        """Test getting dataset version."""
        self.assertEqual(self.parser.get_version(), "1.0.0")

    def test_get_license(self):
        """Test getting dataset license."""
        self.assertEqual(self.parser.get_license(), "CC-BY-4.0")

    def test_get_bounding_box(self):
        """Test getting bounding box."""
        bbox = self.parser.get_bounding_box()
        self.assertIsNotNone(bbox)
        self.assertEqual(len(bbox), 4)
        self.assertAlmostEqual(bbox[0], -118.93)
        self.assertAlmostEqual(bbox[3], 73.86)

    def test_get_temporal_extent(self):
        """Test getting temporal extent."""
        temporal = self.parser.get_temporal_extent()
        self.assertIsNotNone(temporal)
        self.assertEqual(temporal["startDate"], "2020-01-01T00:00:00Z")

    def test_get_spatial_resolution(self):
        """Test getting spatial resolution."""
        self.assertEqual(self.parser.get_spatial_resolution(), "30m")

    def test_get_crs(self):
        """Test getting CRS."""
        self.assertEqual(self.parser.get_crs(), "EPSG:4326")

    def test_get_distribution_files(self):
        """Test getting distribution files."""
        files = self.parser.get_distribution_files()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]["@id"], "tile_001/cog")

    def test_get_items(self):
        """Test getting items from recordSet."""
        items = self.parser.get_items()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["id"], "tile_001")

    def test_get_item_count(self):
        """Test getting item count."""
        self.assertEqual(self.parser.get_item_count(), 2)

    def test_get_references(self):
        """Test getting references."""
        refs = self.parser.get_references()
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["name"], "STAC Catalog")

    def test_find_distribution_file(self):
        """Test finding distribution file by ID and type."""
        cog_file = self.parser.find_distribution_file("tile_001", "cog")
        self.assertIsNotNone(cog_file)
        self.assertIn("tif", cog_file["contentUrl"])

        csv_file = self.parser.find_distribution_file("tile_001", "csv")
        self.assertIsNotNone(csv_file)
        self.assertIn("csv", csv_file["contentUrl"])


if __name__ == "__main__":
    unittest.main()
