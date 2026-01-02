# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCroissantTools
                                 A QGIS plugin
 Load and visualize GeoCroissant ML-ready geospatial datasets
                              -------------------
        begin                : 2026-01-02
        copyright            : (C) 2026 by Harsh Shinde
        email                : harshinde.hks@gmail.com
 ***************************************************************************/
"""

import os.path

from qgis.gui import QgisInterface
from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QTranslator, qVersion, QCoreApplication, QLocale

from .gui import GeoCroissantDialogMain


class GeoCroissantTools:
    """QGIS Plugin Implementation."""

    def __init__(self, iface: QgisInterface) -> None:
        """Constructor.

        :param iface: An interface instance that provides the hook to
            manipulate the QGIS application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.dialog = GeoCroissantDialogMain(iface)

        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Initialize locale
        try:
            locale = QgsSettings().value("locale/userLocale")
            if not locale:
                locale = QLocale().name()
            locale = locale[0:2]

            locale_path = os.path.join(
                self.plugin_dir, "i18n", f"geocroissant_{locale}.qm"
            )

            if os.path.exists(locale_path):
                self.translator = QTranslator()
                self.translator.load(locale_path)

                if qVersion() > "4.3.3":
                    QCoreApplication.installTranslator(self.translator)
        except TypeError:
            pass

    def initGui(self) -> None:
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.dialog.initGui()

    def unload(self) -> None:
        """Remove menu entry and toolbar icons."""
        self.dialog.unload()
