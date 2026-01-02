# GeoCroissant Tools

A QGIS plugin for loading and visualizing ML-ready geospatial datasets using the GeoCroissant metadata format.

## Features

- Load GeoCroissant JSON metadata files
- Visualize dataset extents and tile boundaries
- Load Cloud-Optimized GeoTIFFs (COGs)
- View training data as point layers

## Requirements

- **QGIS**: 3.0 or higher
- **Platform**: Windows, Linux, macOS
- **Dependencies**: No external Python packages required (uses QGIS built-in libraries)

## Installation

### From QGIS Plugin Manager

1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins...`
3. Search for "GeoCroissant Tools"
4. Click `Install`

### From ZIP

1. Download the latest release from [Releases](https://github.com/HarshShinde0/geocroissant-qgis-plugin/releases)
2. In QGIS: `Plugins` → `Manage and Install Plugins...` → `Install from ZIP`
3. Select the downloaded ZIP file

### Manual Installation

Copy the `GeoCroissantTools` folder to your QGIS plugins directory:

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins` |
| Linux | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins` |
| macOS | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins` |

Restart QGIS and enable the plugin in `Plugins` → `Manage and Install Plugins...`

## Usage

1. Click the GeoCroissant Tools icon in the toolbar (or `Plugins` → `GeoCroissant Tools`)
2. Click **Browse** to load a GeoCroissant JSON file
3. Use the tabs to explore the dataset:
   - **Info**: Dataset metadata and spatial properties
   - **Tiles**: Browse and load individual tiles
   - **Files**: Access distribution files (COGs, CSVs)
   - **References**: External links and references

## Author

**Harsh Shinde**  
Email: harshinde.hks@gmail.com  
GitHub: [@HarshShinde0](https://github.com/HarshShinde0)

## Links

- **Repository**: https://github.com/HarshShinde0/geocroissant-qgis-plugin
- **Issue Tracker**: https://github.com/HarshShinde0/geocroissant-qgis-plugin/issues