# -*- coding: utf-8 -*-
"""
Layer Builders for GeoCroissant Tools

Creates QGIS vector layers from GeoCroissant metadata,
including tile index layers and bounding box layers.
"""

from typing import Any, Dict, List, Optional

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsFields,
    QgsSymbol,
    QgsSimpleFillSymbolLayer,
    QgsSingleSymbolRenderer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor


class TileLayerBuilder:
    """Builds a vector layer showing tile extents from GeoCroissant items."""

    def __init__(
        self,
        items: List[Dict[str, Any]],
        crs: str = "EPSG:4326",
        dataset_name: str = "GeoCroissant",
    ) -> None:
        """
        Initialize the tile layer builder.

        :param items: List of item dictionaries with bbox info
        :param crs: Coordinate reference system string
        :param dataset_name: Name of the dataset for layer naming
        """
        self.items = items
        self.crs = crs
        self.dataset_name = dataset_name

    def create_layer(self) -> Optional[QgsVectorLayer]:
        """
        Create a vector layer with tile polygons.

        :returns: QgsVectorLayer or None if creation fails
        """
        # Create memory layer
        layer = QgsVectorLayer(
            f"Polygon?crs={self.crs}", f"{self.dataset_name}_tiles", "memory"
        )

        if not layer.isValid():
            return None

        provider = layer.dataProvider()

        # Add fields
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.String))
        fields.append(QgsField("datetime", QVariant.String))
        fields.append(QgsField("assets", QVariant.String))
        fields.append(QgsField("west", QVariant.Double))
        fields.append(QgsField("south", QVariant.Double))
        fields.append(QgsField("east", QVariant.Double))
        fields.append(QgsField("north", QVariant.Double))
        provider.addAttributes(fields)
        layer.updateFields()

        # Add features
        features = []
        for item in self.items:
            bbox = item.get("bbox", [])
            if len(bbox) < 4:
                continue

            west, south, east, north = bbox[0], bbox[1], bbox[2], bbox[3]

            # Create polygon from bbox
            polygon = QgsGeometry.fromPolygonXY(
                [
                    [
                        QgsPointXY(west, south),
                        QgsPointXY(east, south),
                        QgsPointXY(east, north),
                        QgsPointXY(west, north),
                        QgsPointXY(west, south),
                    ]
                ]
            )

            feature = QgsFeature()
            feature.setGeometry(polygon)
            feature.setAttributes(
                [
                    item.get("id", ""),
                    item.get("datetime", ""),
                    str(item.get("assets", [])),
                    west,
                    south,
                    east,
                    north,
                ]
            )
            features.append(feature)

        provider.addFeatures(features)
        layer.updateExtents()

        # Apply styling
        self._apply_style(layer)

        return layer

    def _apply_style(self, layer: QgsVectorLayer) -> None:
        """Apply default styling to the tile layer."""
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())

        # Create a semi-transparent blue fill
        fill = QgsSimpleFillSymbolLayer()
        fill.setColor(QColor(33, 150, 243, 50))  # Blue with alpha
        fill.setStrokeColor(QColor(33, 150, 243, 200))
        fill.setStrokeWidth(0.5)

        symbol.changeSymbolLayer(0, fill)
        renderer = QgsSingleSymbolRenderer(symbol)
        layer.setRenderer(renderer)


class BboxLayerBuilder:
    """Builds a vector layer showing the overall dataset bounding box."""

    def __init__(
        self,
        bbox: List[float],
        crs: str = "EPSG:4326",
        dataset_name: str = "GeoCroissant",
    ) -> None:
        """
        Initialize the bbox layer builder.

        :param bbox: Bounding box [west, south, east, north]
        :param crs: Coordinate reference system string
        :param dataset_name: Name of the dataset for layer naming
        """
        self.bbox = bbox
        self.crs = crs
        self.dataset_name = dataset_name

    def create_layer(self) -> Optional[QgsVectorLayer]:
        """
        Create a vector layer with the bounding box polygon.

        :returns: QgsVectorLayer or None if creation fails
        """
        if len(self.bbox) < 4:
            return None

        # Create memory layer
        layer = QgsVectorLayer(
            f"Polygon?crs={self.crs}", f"{self.dataset_name}_extent", "memory"
        )

        if not layer.isValid():
            return None

        provider = layer.dataProvider()

        # Add fields
        fields = QgsFields()
        fields.append(QgsField("name", QVariant.String))
        fields.append(QgsField("west", QVariant.Double))
        fields.append(QgsField("south", QVariant.Double))
        fields.append(QgsField("east", QVariant.Double))
        fields.append(QgsField("north", QVariant.Double))
        provider.addAttributes(fields)
        layer.updateFields()

        west, south, east, north = (
            self.bbox[0],
            self.bbox[1],
            self.bbox[2],
            self.bbox[3],
        )

        # Create polygon from bbox
        polygon = QgsGeometry.fromPolygonXY(
            [
                [
                    QgsPointXY(west, south),
                    QgsPointXY(east, south),
                    QgsPointXY(east, north),
                    QgsPointXY(west, north),
                    QgsPointXY(west, south),
                ]
            ]
        )

        feature = QgsFeature()
        feature.setGeometry(polygon)
        feature.setAttributes(
            [
                self.dataset_name,
                west,
                south,
                east,
                north,
            ]
        )

        provider.addFeatures([feature])
        layer.updateExtents()

        # Apply styling
        self._apply_style(layer)

        return layer

    def _apply_style(self, layer: QgsVectorLayer) -> None:
        """Apply default styling to the bbox layer."""
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())

        # Create a semi-transparent orange fill
        fill = QgsSimpleFillSymbolLayer()
        fill.setColor(QColor(255, 87, 34, 30))  # Orange with alpha
        fill.setStrokeColor(QColor(255, 87, 34, 255))
        fill.setStrokeWidth(1.0)

        symbol.changeSymbolLayer(0, fill)
        renderer = QgsSingleSymbolRenderer(symbol)
        layer.setRenderer(renderer)
