#!/usr/bin/env python3
"""
Project Zomboid Map Cleaner

A command-line tool to delete map files from Project Zomboid save directories.
This script allows you to specify rectangular areas and delete corresponding map files.
"""

import sys
import argparse
import struct
from typing import List, Tuple, Set, Optional
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


class Region:
    """Represents a rectangular region with from and to coordinates."""
    def __init__(self, from_x: int, from_y: int, to_x: int, to_y: int):
        self.from_x = from_x
        self.from_y = from_y
        self.to_x = to_x
        self.to_y = to_y
    
    def __repr__(self):
        return f"Region(({self.from_x}, {self.from_y}) -> ({self.to_x}, {self.to_y}))"
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this region."""
        return self.from_x <= x < self.to_x and self.from_y <= y < self.to_y
    
    def expand(self, padding: int) -> 'Region':
        """Expand the region by the given padding in all directions."""
        return Region(
            self.from_x - padding,
            self.from_y - padding,
            self.to_x + padding,
            self.to_y + padding
        )


class SafeHouse:
    """Represents a safehouse with its region and metadata."""
    def __init__(self, region: Region, owner: str, players: List[str], title: str):
        self.region = region
        self.owner = owner
        self.players = players
        self.title = title
    
    def __repr__(self):
        return f"SafeHouse({self.title}, owner={self.owner}, region={self.region})"


class BinaryReader:
    """Helper class to read binary data from Project Zomboid files."""
    def __init__(self, data: bytes):
        self.data = data
        self.position = 0
        self.marked_position = None
    
    def mark(self):
        """Mark the current position for later reset."""
        self.marked_position = self.position
    
    def reset(self):
        """Reset to the marked position or beginning."""
        if self.marked_position is not None:
            self.position = self.marked_position
            self.marked_position = None
        else:
            self.position = 0
    
    def read_int8(self) -> int:
        """Read a signed 8-bit integer."""
        try:
            value = struct.unpack_from('>b', self.data, self.position)[0]
            self.position += 1
            return value
        except struct.error as e:
            raise ValueError(f"Failed to read int8 at position {self.position}: {e}")
    
    def read_int16(self) -> int:
        """Read a signed 16-bit integer (big-endian)."""
        try:
            value = struct.unpack_from('>h', self.data, self.position)[0]
            self.position += 2
            return value
        except struct.error as e:
            raise ValueError(f"Failed to read int16 at position {self.position}: {e}")
    
    def read_int32(self) -> int:
        """Read a signed 32-bit integer (big-endian)."""
        try:
            value = struct.unpack_from('>i', self.data, self.position)[0]
            self.position += 4
            return value
        except struct.error as e:
            raise ValueError(f"Failed to read int32 at position {self.position}: {e}")
    
    def read_string(self, length: Optional[int] = None) -> str:
        """Read a string. If length is None, read length from int16 first."""
        if length is None:
            length = self.read_int16()
        
        if length == 0:
            return ""
        
        if self.position + length > len(self.data):
            raise ValueError(f"Cannot read {length} bytes at position {self.position}: insufficient data")
        
        string_bytes = self.data[self.position:self.position + length]
        self.position += length
        
        # Convert bytes to string and handle null termination
        try:
            string = string_bytes.decode('utf-8')
        except UnicodeDecodeError:
            string = string_bytes.decode('latin-1')
        
        null_index = string.find('\0')
        if null_index >= 0:
            string = string[:null_index]
        
        return string
    
    def skip_bytes(self, count: int):
        """Skip a number of bytes."""
        if self.position + count > len(self.data):
            raise ValueError(f"Cannot skip {count} bytes at position {self.position}: insufficient data")
        self.position += count


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


def load_safehouses(directory_path: Path) -> List[SafeHouse]:
    """
    Load safehouse data from map_meta.bin file.
    
    Args:
        directory_path: Path to the save directory
    
    Returns:
        List of SafeHouse objects
    """
    safehouses = []
    meta_file = directory_path / "map_meta.bin"
    
    if not meta_file.exists():
        return safehouses
    
    try:
        with open(meta_file, 'rb') as f:
            data = f.read()
        
        reader = BinaryReader(data)
        reader.mark()
        
        # Check file type
        file_type = reader.read_string(4)
        
        version = 0
        if file_type == "META":
            version = reader.read_int32()
        else:
            version = 33
            reader.reset()
        
        if version < 194:
            print(f"Warning: map_meta.bin version {version} not fully supported. Safehouse protection may not work correctly.")
            return safehouses
        
        # Read map bounds
        min_x = reader.read_int32()
        min_y = reader.read_int32()
        max_x = reader.read_int32()
        max_y = reader.read_int32()
        
        # Skip room and building definitions
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                # Skip room definitions
                room_def_count = reader.read_int32()
                for _ in range(room_def_count):
                    if version < 194:
                        reader.skip_bytes(4)
                    else:
                        reader.skip_bytes(8)
                    if version >= 160:
                        reader.skip_bytes(2)
                    else:
                        reader.skip_bytes(1)
                        if version >= 34:
                            reader.skip_bytes(1)
                
                # Skip building definitions
                building_def_count = reader.read_int32()
                for _ in range(building_def_count):
                    if version >= 194:
                        reader.skip_bytes(8)
                    reader.skip_bytes(1)
                    if version >= 57:
                        reader.skip_bytes(4)
                    if version >= 74:
                        reader.skip_bytes(1)
                    if version >= 107:
                        reader.skip_bytes(1)
                    if version >= 111 and version < 121:
                        reader.skip_bytes(4)
                    if version >= 125:
                        reader.skip_bytes(4)
        
        if version <= 112:
            # Version too old, no safehouse support
            return safehouses
        
        # Try to read safehouses - may fail if file ends before safehouse section
        try:
            safehouse_count = reader.read_int32()
        except (ValueError, IndexError):
            # No safehouse data or unexpected end of file
            return safehouses
        
        for i in range(safehouse_count):
            try:
                x = reader.read_int32()
                y = reader.read_int32()
                w = reader.read_int32()
                h = reader.read_int32()
                owner = reader.read_string()
                
                player_count = reader.read_int32()
                players = []
                for _ in range(player_count):
                    players.append(reader.read_string())
                
                reader.skip_bytes(8)  # long - last visited
                
                title = f"{owner}'s safe house"
                if version >= 101:
                    title = reader.read_string()
                
                if version >= 177:
                    player_respawn_count = reader.read_int32()
                    for _ in range(player_respawn_count):
                        reader.read_string()
                
                # Convert to map coordinates (divide by 10)
                region = Region(
                    x // 10,
                    y // 10,
                    (x + w + 9) // 10,  # Ceiling division
                    (y + h + 9) // 10
                )
                
                safehouses.append(SafeHouse(region, owner, players, title))
            except (ValueError, IndexError) as e:
                # Failed to read this safehouse, skip it and continue
                # This can happen if the file format doesn't match exactly
                break
    
    except ValueError as e:
        # This is expected if the file format doesn't match exactly or there are no safehouses
        # Silently ignore and continue without safehouse protection
        return []
    except Exception as e:
        print(f"Warning: Could not parse map_meta.bin (this is normal if no safehouses exist): {e}")
        return []
    
    return safehouses


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
    
    Supports two directory structures:
    1. Legacy: map_X_Y.bin files in the root directory
    2. Modern: map/X/Y files where X is a directory and Y is a file
    
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
    
    # Check for legacy structure: map_X_Y.bin files in root
    for entry in directory_path.iterdir():
        if entry.is_file() and entry.name.startswith("map_"):
            try:
                coord = get_coord_from_map_name(entry.name)
                coords.append(coord)
            except (ValueError, IndexError):
                # Skip files that don't match the expected pattern
                continue
    
    # Check for modern structure: map/X/Y files
    map_dir = directory_path / "map"
    if map_dir.exists() and map_dir.is_dir():
        for x_dir in map_dir.iterdir():
            if x_dir.is_dir():
                try:
                    x = int(x_dir.name)
                    for y_file in x_dir.iterdir():
                        if y_file.is_file():
                            try:
                                y = int(y_file.name)
                                coords.append(ChunkCoordinate(x, y))
                            except (ValueError, OSError):
                                # Skip files with non-numeric names
                                continue
                except (ValueError, OSError):
                    # Skip directories with non-numeric names
                    continue
    
    return coords


def list_map_coverage(directory_path: Path) -> None:
    """
    List the map coverage and safehouses in the directory.
    
    Args:
        directory_path: Path to the save directory
    """
    coords = scan_directory(directory_path)
    safehouses = load_safehouses(directory_path)
    
    if not coords:
        print("No map files found in directory.")
        print("Make sure you're pointing to the correct save folder.")
        print("Expected structure: map_*.bin files in root OR map/X/Y files in subdirectories.")
    else:
        coords.sort(key=lambda c: (c.x, c.y))
        
        min_x = min(c.x for c in coords)
        max_x = max(c.x for c in coords)
        min_y = min(c.y for c in coords)
        max_y = max(c.y for c in coords)
        
        print(f"Found {len(coords)} map files")
        print(f"Coverage area: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
        print(f"Dimensions: {max_x - min_x + 1} x {max_y - min_y + 1}")
    
    print(f"\nFound {len(safehouses)} safehouse(s)")
    if safehouses:
        print("\nSafehouses:")
        for i, sh in enumerate(safehouses, 1):
            print(f"  {i}. {sh.title}")
            print(f"     Owner: {sh.owner}")
            print(f"     Players: {', '.join(sh.players) if sh.players else 'None'}")
            print(f"     Region: X=[{sh.region.from_x}, {sh.region.to_x}), Y=[{sh.region.from_y}, {sh.region.to_y})")


def _delete_file_if_exists(
    directory_path: Path,
    filename: str,
    deleted_files: Set[str],
    dry_run: bool,
    x: Optional[int] = None,
    y: Optional[int] = None
) -> bool:
    """
    Helper function to delete a single file.
    
    Supports both legacy and modern directory structures:
    - Legacy: map_X_Y.bin, chunkdata_X_Y.bin, zpop_X_Y.bin in root
    - Modern: map/X/Y files for map data, chunkdata/chunkdata_X_Y.bin for chunk data
    
    Args:
        directory_path: Path to the directory containing the file
        filename: Name of the file to delete (legacy structure)
        deleted_files: Set of already deleted filenames
        dry_run: If True, only show what would be deleted without actually deleting
        x: X coordinate (for modern structure)
        y: Y coordinate (for modern structure)
    
    Returns:
        True if file was deleted (or would be deleted in dry run), False otherwise
    """
    # Try legacy structure first: files in root
    filepath = directory_path / filename
    file_key = filename
    
    # If legacy file doesn't exist, try modern structure
    if not filepath.exists():
        if x is not None and y is not None and filename.startswith("map_"):
            # Modern structure: map/X/Y
            filepath = directory_path / "map" / str(x) / str(y)
            file_key = f"map/{x}/{y}"
        elif filename.startswith("chunkdata_"):
            # Modern structure: chunkdata/chunkdata_X_Y.bin
            filepath = directory_path / "chunkdata" / filename
            file_key = f"chunkdata/{filename}"
        elif filename.startswith("zpop_"):
            # Modern structure: zpop files might also be in a subdirectory
            # Try zpop subdirectory first, fall back to chunkdata
            zpop_path = directory_path / "zpop" / filename
            if zpop_path.exists():
                filepath = zpop_path
                file_key = f"zpop/{filename}"
            else:
                filepath = directory_path / "chunkdata" / filename
                file_key = f"chunkdata/{filename}"
    
    if filepath.exists() and file_key not in deleted_files:
        if dry_run:
            print(f"Would delete: {file_key}")
        else:
            try:
                filepath.unlink()
                print(f"Deleted: {file_key}")
            except Exception as e:
                print(f"Error deleting {file_key}: {e}")
        deleted_files.add(file_key)
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
    dry_run: bool = False,
    safehouse_protection: bool = True,
    safehouse_padding: int = 4
) -> Tuple[int, int, int]:
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
        safehouse_protection: If True, protect safehouses from deletion
        safehouse_padding: Number of cells to protect around safehouses
    
    Returns:
        Tuple of (files_checked, files_deleted, files_protected)
    """
    if not any([delete_map_data, delete_chunk_data, delete_zpop_data]):
        print("Error: Select at least one file type to delete")
        return 0, 0, 0
    
    # Load safehouses if protection is enabled
    excluded_regions: List[Region] = []
    if safehouse_protection:
        safehouses = load_safehouses(directory_path)
        excluded_regions = [sh.region.expand(safehouse_padding) for sh in safehouses]
        if safehouses:
            print(f"Safehouse protection enabled: protecting {len(safehouses)} safehouse(s) with {safehouse_padding} cell padding")
    
    files_checked = 0
    files_deleted = 0
    files_protected = 0
    deleted_files: Set[str] = set()
    
    print(f"{'DRY RUN: ' if dry_run else ''}Processing area: X=[{start_x}, {end_x}), Y=[{start_y}, {end_y})")
    
    for x in range(start_x, end_x):
        for y in range(start_y, end_y):
            files_checked += 1
            
            # Check if this coordinate is in a protected safehouse region
            is_protected = False
            if excluded_regions:
                for region in excluded_regions:
                    if region.contains_point(x, y):
                        is_protected = True
                        break
            
            if is_protected:
                files_protected += 1
                continue
            
            # Delete map data
            if delete_map_data:
                filename = coordinate_to_filename(x, y, "M")
                if _delete_file_if_exists(directory_path, filename, deleted_files, dry_run, x, y):
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
    
    return files_checked, files_deleted, files_protected


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Project Zomboid Map Cleaner - Delete map files from save directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List map coverage and safehouses
  %(prog)s /path/to/save/folder --list
  
  # Delete map data in area (dry run, with safehouse protection)
  %(prog)s /path/to/save/folder --area 10 20 30 40 --map-data --dry-run
  
  # Delete all file types in area with custom safehouse padding
  %(prog)s /path/to/save/folder --area 10 20 30 40 --map-data --chunk-data --zpop-data --safehouse-padding 6
  
  # Delete without safehouse protection (dangerous!)
  %(prog)s /path/to/save/folder --area 10 20 30 40 --map-data --no-safehouse-protection
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
    
    parser.add_argument(
        "--no-safehouse-protection",
        action="store_true",
        help="Disable safehouse protection (WARNING: allows deletion of safehouse areas)"
    )
    
    parser.add_argument(
        "--safehouse-padding",
        type=int,
        default=4,
        metavar="N",
        help="Number of cells to protect around safehouses (default: 4)"
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
    
    # Validate safehouse padding
    if args.safehouse_padding < 0:
        print("Error: Safehouse padding must be non-negative.", file=sys.stderr)
        return 1
    
    try:
        files_checked, files_deleted, files_protected = delete_files_in_area(
            directory_path,
            start_x,
            start_y,
            end_x,
            end_y,
            delete_map_data=args.map_data,
            delete_chunk_data=args.chunk_data,
            delete_zpop_data=args.zpop_data,
            dry_run=args.dry_run,
            safehouse_protection=not args.no_safehouse_protection,
            safehouse_padding=args.safehouse_padding
        )
        
        print(f"\n{'DRY RUN ' if args.dry_run else ''}Summary:")
        print(f"  Files checked: {files_checked}")
        print(f"  Files protected (safehouses): {files_protected}")
        print(f"  Files {'would be ' if args.dry_run else ''}deleted: {files_deleted}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
