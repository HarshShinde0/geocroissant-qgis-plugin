# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCroissantDialog
                                 A QGIS plugin
 Load and visualize GeoCroissant ML-ready geospatial datasets
                              -------------------
        begin                : 2026-01-02
        copyright            : (C) 2026 by Harsh Shinde
        email                : harshinde.hks@gmail.com
 ***************************************************************************/
"""

import os
import webbrowser
from typing import Optional, Dict, Any, List

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QAction,
    QDockWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QWidget,
    QMenu,
)
from qgis.PyQt.QtCore import Qt

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRectangle,
    Qgis,
)
from qgis.gui import QgisInterface

from GeoCroissantTools import PLUGIN_NAME, __version__, __email__, __web__, __help__
from GeoCroissantTools.utils import gui_utils
from GeoCroissantTools.core.geocroissant_parser import GeoCroissantParser
from GeoCroissantTools.core.layer_builder import TileLayerBuilder, BboxLayerBuilder
from GeoCroissantTools.core.data_loader import COGLoader, CSVLoader


def on_help_click() -> None:
    """Open help URL from button/menu entry."""
    webbrowser.open(__help__)


def on_about_click(parent) -> None:
    """Show about dialog."""
    info = QCoreApplication.translate(
        "@default",
        f"<b>{PLUGIN_NAME}</b> provides access to ML-ready geospatial datasets "
        f'using the <a href="https://mlcommons.org/croissant">GeoCroissant</a> metadata format.'
        f"<br><br>"
        f"<b>Features:</b><br>"
        f"• Load GeoCroissant JSON metadata<br>"
        f"• Visualize dataset extents and tiles<br>"
        f"• Load Cloud-Optimized GeoTIFFs (COGs)<br>"
        f"• View training data as point layers<br>"
        f"<br>"
        f"Author: MLCommons GeoCroissant Team<br>"
        f'Email: <a href="mailto:{__email__}">{__email__}</a><br>'
        f'Web: <a href="{__web__}">{__web__}</a><br>'
        f"Version: {__version__}",
    )
    QMessageBox.information(
        parent, QCoreApplication.translate("@default", f"About {PLUGIN_NAME}"), info
    )


class GeoCroissantDialogMain:
    """Defines all mandatory QGIS plugin dialog components."""

    def __init__(self, iface: QgisInterface) -> None:
        """
        :param iface: the current QGIS interface
        :type iface: QgisInterface
        """
        self.iface = iface
        self.project = QgsProject.instance()

        self.first_start = True
        self.dlg: Optional[GeoCroissantDialog] = None
        self.dock_widget: Optional[QDockWidget] = None
        self.menu: Optional[QMenu] = None
        self.actions: List[QAction] = []

    def initGui(self) -> None:
        """Called when plugin is activated (on QGIS startup or in Plugin Manager)."""

        icon_plugin = gui_utils.get_icon("geocr.jpg")

        self.actions = [
            QAction(
                icon_plugin,
                PLUGIN_NAME,
                self.iface.mainWindow(),
            ),
            # About dialog
            QAction(
                gui_utils.get_icon("icon_about.png"),
                self.tr("About"),
                self.iface.mainWindow(),
            ),
            # Help page
            QAction(
                gui_utils.get_icon("icon_help.png"),
                self.tr("Help"),
                self.iface.mainWindow(),
            ),
        ]

        # Create menu
        self.menu = QMenu(PLUGIN_NAME)
        self.menu.setIcon(icon_plugin)
        self.menu.addActions(self.actions)

        # Add menu to Plugins menu
        self.iface.addPluginToMenu("_tmp", self.actions[1])
        self.iface.pluginMenu().addMenu(self.menu)
        self.iface.removePluginMenu("_tmp", self.actions[1])
        self.iface.addToolBarIcon(self.actions[0])

        # Connect slots to events
        self.actions[0].triggered.connect(self._init_gui_control)
        self.actions[1].triggered.connect(
            lambda: on_about_click(self.iface.mainWindow())
        )
        self.actions[2].triggered.connect(on_help_click)

        # Add keyboard shortcut
        self.iface.registerMainWindowAction(self.actions[0], "Ctrl+Shift+G")

    def unload(self) -> None:
        """Called when QGIS closes or plugin is deactivated in Plugin Manager."""

        self.iface.pluginMenu().removeAction(self.menu.menuAction())
        self.iface.removeToolBarIcon(self.actions[0])

        # Remove action for keyboard shortcut
        self.iface.unregisterMainWindowAction(self.actions[0])

        # Remove dock widget if exists
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget = None

        if self.dlg:
            del self.dlg
            self.dlg = None

    def _init_gui_control(self) -> None:
        """Slot for main plugin button. Initializes the GUI and shows it."""

        if self.first_start:
            self.first_start = False
            self.dlg = GeoCroissantDialog(self.iface, self.iface.mainWindow())

            # Create dock widget
            self.dock_widget = QDockWidget(PLUGIN_NAME, self.iface.mainWindow())
            self.dock_widget.setWidget(self.dlg)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        else:
            if self.dock_widget:
                self.dock_widget.show()
                self.dock_widget.raise_()

    def tr(self, string: str) -> str:
        return QCoreApplication.translate(str(self.__class__.__name__), string)


class GeoCroissantDialog(QWidget):
    """Main dialog widget for GeoCroissant Tools."""

    def __init__(self, iface: QgisInterface, parent=None) -> None:
        """
        :param iface: QGIS interface
        :param parent: parent window for modality
        """
        super().__init__(parent)
        self._iface = iface
        self.project = QgsProject.instance()
        self.canvas = self._iface.mapCanvas()

        # Data storage
        self.geocroissant_data: Optional[Dict[str, Any]] = None
        self.parser: Optional[GeoCroissantParser] = None
        self.current_file_path: Optional[str] = None

        # Layer references
        self.tiles_layer: Optional[QgsVectorLayer] = None
        self.bbox_layer: Optional[QgsVectorLayer] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)

        # === Load Section ===
        load_group = QGroupBox("Load GeoCroissant")
        load_layout = QHBoxLayout(load_group)

        self.btn_load = QPushButton("Browse...")
        self.btn_load.setIcon(gui_utils.get_icon("icon_folder.png"))
        self.btn_load.clicked.connect(self._on_load_click)

        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setWordWrap(True)

        load_layout.addWidget(self.btn_load)
        load_layout.addWidget(self.lbl_file, 1)

        main_layout.addWidget(load_group)

        # === Tab Widget ===
        self.tabs = QTabWidget()

        # --- Info Tab ---
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)

        self.info_table = QTableWidget()
        self.info_table.setColumnCount(2)
        self.info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.info_table.horizontalHeader().setStretchLastSection(True)
        self.info_table.setEditTriggers(QTableWidget.NoEditTriggers)

        info_layout.addWidget(self.info_table)

        # Spatial info
        spatial_group = QGroupBox("Spatial Properties")
        spatial_layout = QVBoxLayout(spatial_group)

        self.lbl_bbox = QLabel("Bounding Box: -")
        self.lbl_crs = QLabel("CRS: -")
        self.lbl_resolution = QLabel("Resolution: -")
        self.lbl_temporal = QLabel("Temporal: -")

        spatial_layout.addWidget(self.lbl_bbox)
        spatial_layout.addWidget(self.lbl_crs)
        spatial_layout.addWidget(self.lbl_resolution)
        spatial_layout.addWidget(self.lbl_temporal)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_show_bbox = QPushButton("Show Extent")
        self.btn_show_bbox.clicked.connect(self._on_show_bbox_click)
        self.btn_show_bbox.setEnabled(False)

        self.btn_zoom_extent = QPushButton("Zoom to Extent")
        self.btn_zoom_extent.clicked.connect(self._on_zoom_extent_click)
        self.btn_zoom_extent.setEnabled(False)

        btn_layout.addWidget(self.btn_show_bbox)
        btn_layout.addWidget(self.btn_zoom_extent)
        spatial_layout.addLayout(btn_layout)

        info_layout.addWidget(spatial_group)

        self.tabs.addTab(info_tab, "Info")

        # --- Tiles Tab ---
        tiles_tab = QWidget()
        tiles_layout = QVBoxLayout(tiles_tab)

        self.tiles_list = QListWidget()
        self.tiles_list.itemDoubleClicked.connect(self._on_tile_double_click)

        tiles_btn_layout = QHBoxLayout()
        self.btn_show_tiles = QPushButton("Show All Tiles")
        self.btn_show_tiles.clicked.connect(self._on_show_tiles_click)
        self.btn_show_tiles.setEnabled(False)

        self.btn_load_selected_cog = QPushButton("Load COG")
        self.btn_load_selected_cog.clicked.connect(self._on_load_cog_click)
        self.btn_load_selected_cog.setEnabled(False)

        self.btn_load_selected_csv = QPushButton("Load CSV")
        self.btn_load_selected_csv.clicked.connect(self._on_load_csv_click)
        self.btn_load_selected_csv.setEnabled(False)

        tiles_btn_layout.addWidget(self.btn_show_tiles)
        tiles_btn_layout.addWidget(self.btn_load_selected_cog)
        tiles_btn_layout.addWidget(self.btn_load_selected_csv)

        tiles_layout.addWidget(QLabel("Tiles (double-click to zoom):"))
        tiles_layout.addWidget(self.tiles_list)
        tiles_layout.addLayout(tiles_btn_layout)

        self.tabs.addTab(tiles_tab, "Tiles")

        # --- Files Tab ---
        files_tab = QWidget()
        files_layout = QVBoxLayout(files_tab)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["Name", "Type", "URL"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.itemDoubleClicked.connect(self._on_file_double_click)

        files_layout.addWidget(QLabel("Distribution Files (double-click to load):"))
        files_layout.addWidget(self.files_table)

        self.tabs.addTab(files_tab, "Files")

        # --- References Tab ---
        refs_tab = QWidget()
        refs_layout = QVBoxLayout(refs_tab)

        self.refs_list = QListWidget()
        self.refs_list.itemDoubleClicked.connect(self._on_ref_double_click)

        refs_layout.addWidget(QLabel("References (double-click to open):"))
        refs_layout.addWidget(self.refs_list)

        self.tabs.addTab(refs_tab, "References")

        main_layout.addWidget(self.tabs, 1)

        self.setLayout(main_layout)

    def _on_load_click(self) -> None:
        """Handle load button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GeoCroissant JSON File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            self._load_geocroissant(file_path)

    def _load_geocroissant(self, file_path: str) -> None:
        """Load and parse a GeoCroissant JSON file."""
        try:
            self.parser = GeoCroissantParser(file_path)
            self.geocroissant_data = self.parser.data
            self.current_file_path = file_path

            # Update UI
            self.lbl_file.setText(os.path.basename(file_path))
            self._populate_info()
            self._populate_tiles()
            self._populate_files()
            self._populate_references()

            # Enable buttons
            self.btn_show_bbox.setEnabled(True)
            self.btn_zoom_extent.setEnabled(True)
            self.btn_show_tiles.setEnabled(True)

            self._iface.messageBar().pushMessage(
                PLUGIN_NAME,
                f"Loaded: {self.parser.get_name()}",
                level=Qgis.MessageLevel.Success,
                duration=3,
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading File",
                f"Failed to load GeoCroissant file:\n{str(e)}",
            )

    def _populate_info(self) -> None:
        """Populate the info table with dataset metadata."""
        if not self.parser:
            return

        info_items = [
            ("Name", self.parser.get_name()),
            ("Version", self.parser.get_version()),
            ("License", self.parser.get_license()),
            ("Conforms To", self.parser.data.get("conformsTo", "-")),
            ("Date Published", self.parser.data.get("datePublished", "-")),
            ("Items Count", str(self.parser.get_item_count())),
        ]

        self.info_table.setRowCount(len(info_items))
        for i, (key, value) in enumerate(info_items):
            self.info_table.setItem(i, 0, QTableWidgetItem(key))
            self.info_table.setItem(
                i, 1, QTableWidgetItem(str(value) if value else "-")
            )

        # Spatial properties
        bbox = self.parser.get_bounding_box()
        if bbox:
            self.lbl_bbox.setText(
                f"Bounding Box: [{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]"
            )
        else:
            self.lbl_bbox.setText("Bounding Box: -")

        self.lbl_crs.setText(f"CRS: {self.parser.get_crs()}")
        self.lbl_resolution.setText(
            f"Resolution: {self.parser.get_spatial_resolution()}"
        )

        temporal = self.parser.get_temporal_extent()
        if temporal:
            self.lbl_temporal.setText(
                f"Temporal: {temporal.get('startDate', '?')} → {temporal.get('endDate', '?')}"
            )
        else:
            self.lbl_temporal.setText("Temporal: -")

    def _populate_tiles(self) -> None:
        """Populate the tiles list from recordSet items."""
        self.tiles_list.clear()

        if not self.parser:
            return

        items = self.parser.get_items()
        for item in items:
            item_id = item.get("id", "Unknown")
            bbox = item.get("bbox", [])
            bbox_str = f" [{bbox[0]:.1f}, {bbox[1]:.1f}]" if len(bbox) >= 2 else ""

            list_item = QListWidgetItem(f"{item_id}{bbox_str}")
            list_item.setData(Qt.UserRole, item)
            self.tiles_list.addItem(list_item)

        self.btn_load_selected_cog.setEnabled(len(items) > 0)
        self.btn_load_selected_csv.setEnabled(len(items) > 0)

    def _populate_files(self) -> None:
        """Populate the files table from distribution."""
        self.files_table.setRowCount(0)

        if not self.parser:
            return

        files = self.parser.get_distribution_files()
        self.files_table.setRowCount(len(files))

        for i, file_obj in enumerate(files):
            name = file_obj.get("name", file_obj.get("@id", "Unknown"))
            encoding = file_obj.get("encodingFormat", "Unknown")
            url = file_obj.get("contentUrl", "-")

            self.files_table.setItem(i, 0, QTableWidgetItem(name))
            self.files_table.setItem(i, 1, QTableWidgetItem(encoding))

            url_item = QTableWidgetItem(url[:60] + "..." if len(url) > 60 else url)
            url_item.setData(Qt.UserRole, file_obj)
            self.files_table.setItem(i, 2, url_item)

    def _populate_references(self) -> None:
        """Populate the references list."""
        self.refs_list.clear()

        if not self.parser:
            return

        refs = self.parser.get_references()
        for ref in refs:
            name = ref.get("name", "Unknown")
            url = ref.get("url", "")

            list_item = QListWidgetItem(f"{name}: {url}")
            list_item.setData(Qt.UserRole, ref)
            self.refs_list.addItem(list_item)

    def _on_show_bbox_click(self) -> None:
        """Show the dataset bounding box on the map."""
        if not self.parser:
            return

        bbox = self.parser.get_bounding_box()
        if not bbox:
            QMessageBox.warning(
                self, "No Bounding Box", "This dataset has no bounding box defined."
            )
            return

        crs = self.parser.get_crs()
        builder = BboxLayerBuilder(bbox, crs, self.parser.get_name())
        self.bbox_layer = builder.create_layer()

        if self.bbox_layer:
            self.project.addMapLayer(self.bbox_layer)
            self._iface.messageBar().pushMessage(
                PLUGIN_NAME,
                "Bounding box layer added",
                level=Qgis.MessageLevel.Info,
                duration=2,
            )

    def _on_zoom_extent_click(self) -> None:
        """Zoom to the dataset extent."""
        if not self.parser:
            return

        bbox = self.parser.get_bounding_box()
        if not bbox:
            return

        rect = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])

        self.canvas.setExtent(rect)
        self.canvas.refresh()

    def _on_show_tiles_click(self) -> None:
        """Show all tiles as a vector layer."""
        if not self.parser:
            return

        items = self.parser.get_items()
        if not items:
            QMessageBox.warning(
                self, "No Tiles", "This dataset has no tile items defined."
            )
            return

        crs = self.parser.get_crs()
        builder = TileLayerBuilder(items, crs, self.parser.get_name())
        self.tiles_layer = builder.create_layer()

        if self.tiles_layer:
            self.project.addMapLayer(self.tiles_layer)
            self._iface.messageBar().pushMessage(
                PLUGIN_NAME,
                f"Added {len(items)} tiles",
                level=Qgis.MessageLevel.Info,
                duration=2,
            )

    def _on_tile_double_click(self, item: QListWidgetItem) -> None:
        """Zoom to a specific tile."""
        tile_data = item.data(Qt.UserRole)
        if not tile_data:
            return

        bbox = tile_data.get("bbox", [])
        if len(bbox) >= 4:
            rect = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])
            self.canvas.setExtent(rect)
            self.canvas.refresh()

    def _on_load_cog_click(self) -> None:
        """Load COG for selected tile."""
        current_item = self.tiles_list.currentItem()
        if not current_item or not self.parser:
            return

        tile_data = current_item.data(Qt.UserRole)
        tile_id = tile_data.get("id", "")

        # Find matching COG file
        cog_file = self.parser.find_distribution_file(tile_id, "cog")
        if not cog_file:
            cog_file = self.parser.find_distribution_file(tile_id, ".tif")

        if cog_file:
            url = cog_file.get("contentUrl", "")
            loader = COGLoader(url, tile_id)
            layer = loader.load()

            if layer and layer.isValid():
                self.project.addMapLayer(layer)
                self._iface.messageBar().pushMessage(
                    PLUGIN_NAME,
                    f"Loaded COG: {tile_id}",
                    level=Qgis.MessageLevel.Success,
                    duration=3,
                )
            else:
                QMessageBox.warning(
                    self, "Load Failed", f"Could not load COG from: {url}"
                )
        else:
            QMessageBox.warning(
                self, "No COG Found", f"No COG file found for tile: {tile_id}"
            )

    def _on_load_csv_click(self) -> None:
        """Load CSV for selected tile."""
        current_item = self.tiles_list.currentItem()
        if not current_item or not self.parser:
            return

        tile_data = current_item.data(Qt.UserRole)
        tile_id = tile_data.get("id", "")

        # Find matching CSV file
        csv_file = self.parser.find_distribution_file(tile_id, "csv")

        if csv_file:
            url = csv_file.get("contentUrl", "")
            loader = CSVLoader(url, tile_id)
            layer = loader.load()

            if layer and layer.isValid():
                self.project.addMapLayer(layer)
                self._iface.messageBar().pushMessage(
                    PLUGIN_NAME,
                    f"Loaded CSV: {tile_id}",
                    level=Qgis.MessageLevel.Success,
                    duration=3,
                )
            else:
                QMessageBox.warning(
                    self, "Load Failed", f"Could not load CSV from: {url}"
                )
        else:
            QMessageBox.warning(
                self, "No CSV Found", f"No CSV file found for tile: {tile_id}"
            )

    def _on_file_double_click(self, item: QTableWidgetItem) -> None:
        """Load a file from the distribution table."""
        row = item.row()
        url_item = self.files_table.item(row, 2)
        if not url_item:
            return

        file_obj = url_item.data(Qt.UserRole)
        if not file_obj:
            return

        url = file_obj.get("contentUrl", "")
        encoding = file_obj.get("encodingFormat", "")
        name = file_obj.get("name", file_obj.get("@id", "layer"))

        if "tiff" in encoding.lower() or "geotiff" in encoding.lower():
            loader = COGLoader(url, name)
            layer = loader.load()
            if layer and layer.isValid():
                self.project.addMapLayer(layer)
        elif "csv" in encoding.lower():
            loader = CSVLoader(url, name)
            layer = loader.load()
            if layer and layer.isValid():
                self.project.addMapLayer(layer)
        else:
            webbrowser.open(url)

    def _on_ref_double_click(self, item: QListWidgetItem) -> None:
        """Open a reference URL in browser."""
        ref_data = item.data(Qt.UserRole)
        if ref_data:
            url = ref_data.get("url", "")
            if url:
                webbrowser.open(url)
