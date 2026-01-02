# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCroissantTools
                                 A QGIS plugin
 Load and visualize GeoCroissant ML-ready geospatial datasets
                              -------------------
        begin                : 2026-01-02
        git sha              : $Format:%H$
        copyright            : (C) 2026 by Harsh Shinde
        email                : harshinde.hks@gmail.com
 ***************************************************************************/

 This plugin provides access to GeoCroissant datasets, a metadata format
 for ML-ready geospatial data developed by MLCommons.
 https://github.com/HarshShinde0/geocroissant-qgis-plugin

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import configparser


# noinspection PyPep8Naming
def classFactory(iface):
    """Load GeoCroissantTools class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .GeoCroissantPlugin import GeoCroissantTools

    return GeoCroissantTools(iface)


# Define plugin wide constants
PLUGIN_NAME = "GeoCroissant Tools"
DEFAULT_COLOR = "#4CAF50"
TILE_COLOR = "#2196F3"
BBOX_COLOR = "#FF5722"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_PREFIX = ":plugins/GeoCroissantTools/img/"

# Read metadata.txt
METADATA = configparser.ConfigParser()
METADATA.read(os.path.join(BASE_DIR, "metadata.txt"), encoding="utf-8")

__version__ = METADATA["general"]["version"]
__author__ = METADATA["general"]["author"]
__email__ = METADATA["general"]["email"]
__web__ = METADATA["general"]["homepage"]
__help__ = METADATA["general"]["help"]
