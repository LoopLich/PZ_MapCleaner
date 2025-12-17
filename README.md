# Project Zomboid Map Cleaner

A Python command-line tool to clean/delete map files from Project Zomboid save directories.

## Overview

This tool allows you to delete map files from specific rectangular areas in your Project Zomboid save games. This can be useful for:
- Removing unwanted explored areas
- Resetting specific map regions
- Managing save file sizes

## Requirements

- Python 3.6 or higher
- No external dependencies required (uses only standard library)

## Installation

1. Clone or download this repository
2. Make the script executable (Unix/Linux/Mac):
   ```bash
   chmod +x map_cleaner.py
   ```

## Usage

### List Map Coverage

To see what map files exist in a save directory:

```bash
python map_cleaner.py /path/to/save/folder --list
```

This will show:
- Number of map files found
- Coverage area (min/max X and Y coordinates)
- Dimensions of the mapped area

### Delete Map Files

To delete map files in a specific area:

```bash
python map_cleaner.py /path/to/save/folder --area START_X START_Y END_X END_Y [OPTIONS]
```

**Area Coordinates:**
- `START_X START_Y`: Starting coordinates (inclusive)
- `END_X END_Y`: Ending coordinates (exclusive)
- Example: `--area 10 20 30 40` will delete files from (10,20) to (29,39)

**File Type Options:**
- `--map-data`: Delete map data files (`map_*.bin`)
- `--chunk-data`: Delete chunk data files (`chunkdata_*.bin`)
- `--zpop-data`: Delete zombie population files (`zpop_*.bin`)

At least one file type option must be specified.

**Other Options:**
- `--dry-run`: Preview what would be deleted without actually deleting files

## Examples

### Example 1: Preview deletion (dry run)
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data --dry-run
```

### Example 2: Delete only map data
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data
```

### Example 3: Delete all file types
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data --chunk-data --zpop-data
```

### Example 4: List map coverage first, then delete
```bash
# First, see what you have
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --list

# Then delete a specific area
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 0 0 50 50 --map-data
```

## File Types Explained

- **Map Data (`map_*.bin`)**: Contains the visible map tiles and explored areas
- **Chunk Data (`chunkdata_*.bin`)**: Contains detailed chunk information (30x30 map tiles per chunk)
- **Zpop Data (`zpop_*.bin`)**: Contains zombie population data for chunks (30x30 map tiles per chunk)

## Finding Your Save Directory

Default save locations:
- **Windows**: `C:\Users\YourUsername\Zomboid\Saves\`
- **Linux**: `~/.zomboid/Saves/` or `~/Zomboid/Saves/`
- **Mac**: `~/Library/Application Support/Zomboid/Saves/`

Within the Saves directory, navigate to your world (e.g., `Survivor` or `Apocalypse`) and then your specific save name.

## Safety Tips

1. **Always backup your save files before using this tool!**
2. Use `--dry-run` first to preview what will be deleted
3. Start with small areas to test
4. Use `--list` to understand your map coverage before deletion

## Migration from Web App

This Python script replaces the previous browser-based web application. Key differences:

- **Command-line interface** instead of graphical UI
- **Direct file system access** instead of browser File System Access API
- **Coordinate-based area selection** instead of drawing on a map
- **Batch processing** instead of interactive selection

The core functionality remains the same: deleting map files in specified rectangular areas.

## Troubleshooting

**Error: "Directory not found"**
- Check that the path is correct and the directory exists
- Use quotes around paths with spaces

**Error: "Select at least one filetype to delete"**
- You must specify at least one of: `--map-data`, `--chunk-data`, or `--zpop-data`

**No files deleted**
- Check that files exist in the specified area using `--list`
- Verify your coordinate ranges are correct
- Ensure you have write permissions to the directory

## License

This project is provided as-is for use with Project Zomboid save files.
