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

To see what map files and safehouses exist in a save directory:

```bash
python map_cleaner.py /path/to/save/folder --list
```

This will show:
- Number of map files found
- Coverage area (min/max X and Y coordinates)
- Dimensions of the mapped area
- **Number of safehouses found**
- **Details of each safehouse (owner, players, region)**

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

**Safehouse Protection Options:**
- `--no-safehouse-protection`: **DANGEROUS!** Disable safehouse protection (allows deletion of safehouse areas)
- `--safehouse-padding N`: Set padding around safehouses (default: 4 cells). Higher values protect more area around safehouses.

## Safehouse Protection

**By default, this tool protects your safehouses from deletion!** The script automatically reads safehouse data from `map_meta.bin` and excludes those areas (plus a configurable padding) from deletion.

- **Default padding**: 4 cells around each safehouse
- Safehouses are loaded automatically when present
- Protection can be disabled with `--no-safehouse-protection` (use with extreme caution!)
- Padding can be adjusted with `--safehouse-padding N`

## Examples

### Example 1: List map coverage and safehouses
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --list
```

### Example 2: Preview deletion with safehouse protection (dry run)
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data --dry-run
```

### Example 3: Delete map data with custom safehouse padding
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data --safehouse-padding 6
```

### Example 4: Delete all file types with safehouse protection
```bash
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data --chunk-data --zpop-data
```

### Example 5: Delete without safehouse protection (DANGEROUS!)
```bash
# Only use if you're absolutely sure you want to delete safehouse areas
python map_cleaner.py "/home/user/Zomboid/Saves/Survivor/MyWorld" --area 10 20 30 40 --map-data --no-safehouse-protection
```

## File Types Explained

- **Map Data (`map_*.bin`)**: Contains the visible map tiles and explored areas
- **Chunk Data (`chunkdata_*.bin`)**: Contains detailed chunk information (30x30 map tiles per chunk)
- **Zpop Data (`zpop_*.bin`)**: Contains zombie population data for chunks (30x30 map tiles per chunk)

## Supported Directory Structures

This tool supports both legacy and modern Project Zomboid save directory structures:

**Legacy Structure** (single-player saves):
```
save_folder/
  ├── map_10_20.bin
  ├── map_11_21.bin
  ├── chunkdata_0_0.bin
  └── zpop_0_0.bin
```

**Modern Structure** (multiplayer/server saves):
```
save_folder/
  ├── map/
  │   ├── 10/
  │   │   ├── 20
  │   │   └── 21
  │   └── 11/
  │       ├── 20
  │       └── 21
  └── chunkdata/
      ├── chunkdata_0_0.bin
      └── chunkdata_0_1.bin
```

The tool automatically detects and handles both structures.

## Finding Your Save Directory

Default save locations:
- **Windows**: `C:\Users\YourUsername\Zomboid\Saves\`
- **Linux**: `~/.zomboid/Saves/` or `~/Zomboid/Saves/`
- **Mac**: `~/Library/Application Support/Zomboid/Saves/`

**For single-player saves:**
Within the Saves directory, navigate to your world (e.g., `Survivor` or `Apocalypse`) and then your specific save name.

**For multiplayer/server saves:**
Navigate to `Saves/Multiplayer/` and then your server name. The save directory will contain `map/`, `chunkdata/`, and possibly `map_meta.bin` files.

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
- **Check if files are protected by safehouse areas** - the script shows how many files were protected

**Warning: "Failed to load safehouses"**
- The `map_meta.bin` file may be missing or corrupted
- Safehouse protection will be disabled if this occurs
- You can still proceed with deletion, but safehouses won't be protected

**Safehouses not showing up**
- Make sure you're in the correct save directory (should contain `map_meta.bin`)
- Safehouses only exist in multiplayer or if you've claimed a safehouse in single player

## License

This project is provided as-is for use with Project Zomboid save files.
