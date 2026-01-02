# -*- coding: utf-8 -*-
"""
GUI Utilities for GeoCroissant Tools

Provides helper functions for loading icons and UI files.
"""

import os
from qgis.PyQt.QtGui import QIcon


def get_icon(icon_name: str) -> QIcon:
    """
    Returns a plugin icon.

    :param icon_name: Icon file name (e.g., "icon_geocroissant.png")
    :returns: QIcon object
    """
    base_dir = os.path.join(os.path.dirname(__file__), "..", "gui", "img")

    # Try the exact filename first
    path = os.path.join(base_dir, icon_name)
    if os.path.exists(path):
        return QIcon(path)

    # Try with .svg extension if not found
    name_without_ext = os.path.splitext(icon_name)[0]
    svg_path = os.path.join(base_dir, f"{name_without_ext}.svg")
    if os.path.exists(svg_path):
        return QIcon(svg_path)

    # Try with .png extension
    png_path = os.path.join(base_dir, f"{name_without_ext}.png")
    if os.path.exists(png_path):
        return QIcon(png_path)

    # Return empty icon if file doesn't exist
    return QIcon()


def get_ui_file_path(file_name: str) -> str:
    """
    Returns the full path to a UI file.

    :param file_name: UI file name (e.g., "main_dialog.ui")
    :returns: Full path to the UI file
    """
    path = os.path.join(os.path.dirname(__file__), "..", "gui", file_name)

    return path
