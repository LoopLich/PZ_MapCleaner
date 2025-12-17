#!/usr/bin/env python3
"""
Project Zomboid Map Cleaner

A command-line tool to delete map files from Project Zomboid save directories.
This script allows you to specify rectangular areas and delete corresponding map files.
"""

import sys
import argparse
from typing import List, Tuple, Set
from pathlib import Path


class ChunkCoordinate:
    """Represents a chunk coordinate in the Project Zomboid map."""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"ChunkCoordinate({self.x}, {self.y})"
    
    def __eq__(self, other):
        if not isinstance(other, ChunkCoordinate):
            return False
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))


def get_coord_from_map_name(filename: str) -> ChunkCoordinate:
    """
    Extract coordinates from map filename.
    
    Args:
        filename: Map filename like "map_12_34.bin"
    
    Returns:
        ChunkCoordinate object with x and y coordinates
    
    Raises:
        ValueError: If filename format is invalid
    """
    filename = filename.replace("map_", "").replace(".bin", "")
    parts = filename.split("_")
    if len(parts) != 2:
        raise ValueError(f"Invalid map filename format: expected 2 coordinate parts, got {len(parts)}")
    try:
        return ChunkCoordinate(int(parts[0]), int(parts[1]))
    except ValueError as e:
        raise ValueError(f"Invalid coordinate values in filename: {e}")


def coordinate_to_filename(x: int, y: int, filetype: str) -> str:
    """
    Convert coordinates to filename.
    
    Args:
        x: X coordinate
        y: Y coordinate
        filetype: Type of file ('M' for map, 'C' for chunk, 'Z' for zpop)
    
    Returns:
        Filename string
    """
    if filetype == "M":
        return f"map_{x}_{y}.bin"
    elif filetype == "C":
        cx = x // 30
        cy = y // 30
        return f"chunkdata_{cx}_{cy}.bin"
    elif filetype == "Z":
        cx = x // 30
        cy = y // 30
        return f"zpop_{cx}_{cy}.bin"
    else:
        raise ValueError(f"Unknown filetype: {filetype}")


def scan_directory(directory_path: Path) -> List[ChunkCoordinate]:
    """
    Scan directory for map files and extract coordinates.
    
    Args:
        directory_path: Path to the save directory
    
    Returns:
        List of ChunkCoordinate objects found in the directory
    """
    coords = []
    
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not directory_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")
    
    for entry in directory_path.iterdir():
        if entry.is_file() and entry.name.startswith("map_"):
            try:
                coord = get_coord_from_map_name(entry.name)
                coords.append(coord)
            except (ValueError, IndexError):
                # Skip files that don't match the expected pattern
                continue
    
    return coords


def list_map_coverage(directory_path: Path) -> None:
    """
    List the map coverage in the directory.
    
    Args:
        directory_path: Path to the save directory
    """
    coords = scan_directory(directory_path)
    
    if not coords:
        print("No map files found in directory.")
        return
    
    coords.sort(key=lambda c: (c.x, c.y))
    
    min_x = min(c.x for c in coords)
    max_x = max(c.x for c in coords)
    min_y = min(c.y for c in coords)
    max_y = max(c.y for c in coords)
    
    print(f"Found {len(coords)} map files")
    print(f"Coverage area: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
    print(f"Dimensions: {max_x - min_x + 1} x {max_y - min_y + 1}")


def _delete_file_if_exists(
    directory_path: Path,
    filename: str,
    deleted_files: Set[str],
    dry_run: bool
) -> bool:
    """
    Helper function to delete a single file.
    
    Args:
        directory_path: Path to the directory containing the file
        filename: Name of the file to delete
        deleted_files: Set of already deleted filenames
        dry_run: If True, only show what would be deleted without actually deleting
    
    Returns:
        True if file was deleted (or would be deleted in dry run), False otherwise
    """
    filepath = directory_path / filename
    if filepath.exists() and filename not in deleted_files:
        if dry_run:
            print(f"Would delete: {filename}")
        else:
            try:
                filepath.unlink()
                print(f"Deleted: {filename}")
            except Exception as e:
                print(f"Error deleting {filename}: {e}")
        deleted_files.add(filename)
        return True
    return False


def delete_files_in_area(
    directory_path: Path,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    delete_map_data: bool = True,
    delete_chunk_data: bool = False,
    delete_zpop_data: bool = False,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Delete map files in the specified rectangular area.
    
    Args:
        directory_path: Path to the save directory
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate (exclusive)
        end_y: Ending Y coordinate (exclusive)
        delete_map_data: Whether to delete map data files
        delete_chunk_data: Whether to delete chunk data files
        delete_zpop_data: Whether to delete zpop data files
        dry_run: If True, only show what would be deleted without actually deleting
    
    Returns:
        Tuple of (files_checked, files_deleted)
    """
    if not any([delete_map_data, delete_chunk_data, delete_zpop_data]):
        print("Error: Select at least one file type to delete")
        return 0, 0
    
    files_checked = 0
    files_deleted = 0
    deleted_files: Set[str] = set()
    
    print(f"{'DRY RUN: ' if dry_run else ''}Processing area: X=[{start_x}, {end_x}), Y=[{start_y}, {end_y})")
    
    for x in range(start_x, end_x):
        for y in range(start_y, end_y):
            files_checked += 1
            
            # Delete map data
            if delete_map_data:
                filename = coordinate_to_filename(x, y, "M")
                if _delete_file_if_exists(directory_path, filename, deleted_files, dry_run):
                    files_deleted += 1
            
            # Delete chunk data
            if delete_chunk_data:
                filename = coordinate_to_filename(x, y, "C")
                if _delete_file_if_exists(directory_path, filename, deleted_files, dry_run):
                    files_deleted += 1
            
            # Delete zpop data
            if delete_zpop_data:
                filename = coordinate_to_filename(x, y, "Z")
                if _delete_file_if_exists(directory_path, filename, deleted_files, dry_run):
                    files_deleted += 1
    
    return files_checked, files_deleted


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Project Zomboid Map Cleaner - Delete map files from save directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List map coverage in a directory
  %(prog)s /path/to/save/folder --list
  
  # Delete map data in area (dry run)
  %(prog)s /path/to/save/folder --area 10 20 30 40 --map-data --dry-run
  
  # Delete all file types in area
  %(prog)s /path/to/save/folder --area 10 20 30 40 --map-data --chunk-data --zpop-data
  
  # Delete only chunk and zpop data
  %(prog)s /path/to/save/folder --area 10 20 30 40 --chunk-data --zpop-data
        """
    )
    
    parser.add_argument(
        "directory",
        type=str,
        help="Path to the Project Zomboid save directory"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List map coverage and exit"
    )
    
    parser.add_argument(
        "--area",
        nargs=4,
        type=int,
        metavar=("START_X", "START_Y", "END_X", "END_Y"),
        help="Rectangular area to clean (coordinates are inclusive for start, exclusive for end)"
    )
    
    parser.add_argument(
        "--map-data",
        action="store_true",
        help="Delete map data files (map_*.bin)"
    )
    
    parser.add_argument(
        "--chunk-data",
        action="store_true",
        help="Delete chunk data files (chunkdata_*.bin)"
    )
    
    parser.add_argument(
        "--zpop-data",
        action="store_true",
        help="Delete zpop data files (zpop_*.bin)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    directory_path = Path(args.directory)
    
    # List mode
    if args.list:
        try:
            list_map_coverage(directory_path)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0
    
    # Delete mode
    if not args.area:
        print("Error: --area is required when not using --list", file=sys.stderr)
        parser.print_help()
        return 1
    
    start_x, start_y, end_x, end_y = args.area
    
    # Validate coordinates
    if start_x >= end_x or start_y >= end_y:
        print("Error: Invalid area coordinates. End coordinates must be greater than start coordinates.", file=sys.stderr)
        return 1
    
    try:
        files_checked, files_deleted = delete_files_in_area(
            directory_path,
            start_x,
            start_y,
            end_x,
            end_y,
            delete_map_data=args.map_data,
            delete_chunk_data=args.chunk_data,
            delete_zpop_data=args.zpop_data,
            dry_run=args.dry_run
        )
        
        print(f"\n{'DRY RUN ' if args.dry_run else ''}Summary:")
        print(f"  Files checked: {files_checked}")
        print(f"  Files {'would be ' if args.dry_run else ''}deleted: {files_deleted}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
