#!/usr/bin/env python3
"""
Test suite for the Project Zomboid Map Cleaner script.

Run with: python3 test_map_cleaner.py
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from map_cleaner import (
    ChunkCoordinate,
    get_coord_from_map_name,
    coordinate_to_filename,
    scan_directory,
    delete_files_in_area
)


class TestChunkCoordinate(unittest.TestCase):
    """Test ChunkCoordinate class."""
    
    def test_creation(self):
        coord = ChunkCoordinate(10, 20)
        self.assertEqual(coord.x, 10)
        self.assertEqual(coord.y, 20)
    
    def test_equality(self):
        coord1 = ChunkCoordinate(10, 20)
        coord2 = ChunkCoordinate(10, 20)
        coord3 = ChunkCoordinate(15, 20)
        self.assertEqual(coord1, coord2)
        self.assertNotEqual(coord1, coord3)
    
    def test_hash(self):
        coord1 = ChunkCoordinate(10, 20)
        coord2 = ChunkCoordinate(10, 20)
        coord_set = {coord1, coord2}
        self.assertEqual(len(coord_set), 1)
    
    def test_equality_with_non_coordinate(self):
        coord = ChunkCoordinate(10, 20)
        self.assertNotEqual(coord, "not a coordinate")
        self.assertNotEqual(coord, 42)
        self.assertNotEqual(coord, None)


class TestFilenameParsing(unittest.TestCase):
    """Test filename parsing and generation functions."""
    
    def test_get_coord_from_map_name(self):
        coord = get_coord_from_map_name("map_12_34.bin")
        self.assertEqual(coord.x, 12)
        self.assertEqual(coord.y, 34)
    
    def test_get_coord_from_negative(self):
        coord = get_coord_from_map_name("map_-5_-10.bin")
        self.assertEqual(coord.x, -5)
        self.assertEqual(coord.y, -10)
    
    def test_coordinate_to_filename_map(self):
        filename = coordinate_to_filename(12, 34, "M")
        self.assertEqual(filename, "map_12_34.bin")
    
    def test_coordinate_to_filename_chunk(self):
        filename = coordinate_to_filename(30, 60, "C")
        self.assertEqual(filename, "chunkdata_1_2.bin")
    
    def test_coordinate_to_filename_zpop(self):
        filename = coordinate_to_filename(30, 60, "Z")
        self.assertEqual(filename, "zpop_1_2.bin")
    
    def test_coordinate_to_filename_invalid(self):
        with self.assertRaises(ValueError):
            coordinate_to_filename(10, 20, "X")
    
    def test_get_coord_from_invalid_format(self):
        with self.assertRaises(ValueError):
            get_coord_from_map_name("map_12.bin")  # Missing second coordinate
    
    def test_get_coord_from_non_numeric(self):
        with self.assertRaises(ValueError):
            get_coord_from_map_name("map_abc_def.bin")  # Non-numeric coordinates


class TestDirectoryScanning(unittest.TestCase):
    """Test directory scanning functionality."""
    
    def setUp(self):
        """Create temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)
    
    def test_scan_empty_directory(self):
        coords = scan_directory(self.test_path)
        self.assertEqual(len(coords), 0)
    
    def test_scan_with_map_files(self):
        # Create test files
        (self.test_path / "map_10_20.bin").touch()
        (self.test_path / "map_11_21.bin").touch()
        (self.test_path / "chunkdata_0_0.bin").touch()  # Ignored - scan_directory only looks for map_*.bin
        (self.test_path / "other_file.txt").touch()  # Ignored - not a map file
        
        coords = scan_directory(self.test_path)
        self.assertEqual(len(coords), 2)
        
        # Check coordinates
        coord_set = {(c.x, c.y) for c in coords}
        self.assertIn((10, 20), coord_set)
        self.assertIn((11, 21), coord_set)
    
    def test_scan_nonexistent_directory(self):
        with self.assertRaises(FileNotFoundError):
            scan_directory(Path("/nonexistent/path"))
    
    def test_scan_file_not_directory(self):
        test_file = self.test_path / "test.txt"
        test_file.touch()
        with self.assertRaises(NotADirectoryError):
            scan_directory(test_file)
    
    def test_scan_modern_structure(self):
        """Test scanning files in modern map/X/Y structure."""
        # Create modern structure: map/X/Y
        map_dir = self.test_path / "map"
        map_dir.mkdir()
        
        # Create coordinate directories and files
        for x in [10, 11]:
            x_dir = map_dir / str(x)
            x_dir.mkdir()
            for y in [20, 21]:
                (x_dir / str(y)).touch()
        
        coords = scan_directory(self.test_path)
        self.assertEqual(len(coords), 4)
        
        # Check coordinates
        coord_set = {(c.x, c.y) for c in coords}
        self.assertIn((10, 20), coord_set)
        self.assertIn((10, 21), coord_set)
        self.assertIn((11, 20), coord_set)
        self.assertIn((11, 21), coord_set)
    
    def test_scan_mixed_structure(self):
        """Test scanning files in both legacy and modern structures."""
        # Create legacy structure
        (self.test_path / "map_5_6.bin").touch()
        
        # Create modern structure
        map_dir = self.test_path / "map"
        map_dir.mkdir()
        x_dir = map_dir / "10"
        x_dir.mkdir()
        (x_dir / "20").touch()
        
        coords = scan_directory(self.test_path)
        self.assertEqual(len(coords), 2)
        
        # Check coordinates
        coord_set = {(c.x, c.y) for c in coords}
        self.assertIn((5, 6), coord_set)
        self.assertIn((10, 20), coord_set)


class TestFileDeletion(unittest.TestCase):
    """Test file deletion functionality."""
    
    def setUp(self):
        """Create temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)
    
    def test_delete_map_files_dry_run(self):
        # Create test files
        (self.test_path / "map_10_20.bin").touch()
        (self.test_path / "map_10_21.bin").touch()
        
        files_checked, files_deleted, files_protected = delete_files_in_area(
            self.test_path, 10, 20, 11, 22,
            delete_map_data=True,
            dry_run=True
        )
        
        self.assertEqual(files_checked, 2)
        self.assertEqual(files_deleted, 2)
        self.assertEqual(files_protected, 0)
        # Files should still exist in dry run
        self.assertTrue((self.test_path / "map_10_20.bin").exists())
        self.assertTrue((self.test_path / "map_10_21.bin").exists())
    
    def test_delete_map_files(self):
        # Create test files
        (self.test_path / "map_10_20.bin").touch()
        (self.test_path / "map_10_21.bin").touch()
        (self.test_path / "map_15_25.bin").touch()  # Outside area
        
        files_checked, files_deleted, files_protected = delete_files_in_area(
            self.test_path, 10, 20, 11, 22,
            delete_map_data=True,
            dry_run=False
        )
        
        self.assertEqual(files_checked, 2)
        self.assertEqual(files_deleted, 2)
        self.assertEqual(files_protected, 0)
        # Files in area should be deleted
        self.assertFalse((self.test_path / "map_10_20.bin").exists())
        self.assertFalse((self.test_path / "map_10_21.bin").exists())
        # File outside area should remain
        self.assertTrue((self.test_path / "map_15_25.bin").exists())
    
    def test_delete_no_file_types_selected(self):
        files_checked, files_deleted, files_protected = delete_files_in_area(
            self.test_path, 0, 0, 10, 10,
            delete_map_data=False,
            delete_chunk_data=False,
            delete_zpop_data=False
        )
        
        self.assertEqual(files_checked, 0)
        self.assertEqual(files_deleted, 0)
        self.assertEqual(files_protected, 0)
    
    def test_delete_multiple_file_types(self):
        # Create test files
        (self.test_path / "map_30_60.bin").touch()
        (self.test_path / "chunkdata_1_2.bin").touch()
        (self.test_path / "zpop_1_2.bin").touch()
        
        files_checked, files_deleted, files_protected = delete_files_in_area(
            self.test_path, 30, 60, 31, 61,
            delete_map_data=True,
            delete_chunk_data=True,
            delete_zpop_data=True
        )
        
        self.assertEqual(files_checked, 1)
        self.assertEqual(files_deleted, 3)
        self.assertEqual(files_protected, 0)
        self.assertFalse((self.test_path / "map_30_60.bin").exists())
        self.assertFalse((self.test_path / "chunkdata_1_2.bin").exists())
        self.assertFalse((self.test_path / "zpop_1_2.bin").exists())
    
    def test_delete_modern_structure(self):
        """Test deletion of files in modern map/X/Y structure."""
        # Create modern structure
        map_dir = self.test_path / "map"
        map_dir.mkdir()
        x_dir = map_dir / "10"
        x_dir.mkdir()
        (x_dir / "20").touch()
        (x_dir / "21").touch()
        
        files_checked, files_deleted, files_protected = delete_files_in_area(
            self.test_path, 10, 20, 11, 22,
            delete_map_data=True,
            dry_run=False
        )
        
        self.assertEqual(files_checked, 2)
        self.assertEqual(files_deleted, 2)
        self.assertEqual(files_protected, 0)
        # Files should be deleted
        self.assertFalse((x_dir / "20").exists())
        self.assertFalse((x_dir / "21").exists())
    
    def test_delete_modern_chunkdata(self):
        """Test deletion of chunkdata files in modern structure."""
        # Create modern chunkdata structure
        chunkdata_dir = self.test_path / "chunkdata"
        chunkdata_dir.mkdir()
        (chunkdata_dir / "chunkdata_0_34.bin").touch()
        (chunkdata_dir / "chunkdata_1_35.bin").touch()
        
        # Chunk 0_34 covers map coordinates 0-29, 1020-1049 (30x30 tiles per chunk)
        files_checked, files_deleted, files_protected = delete_files_in_area(
            self.test_path, 0, 1020, 30, 1050,
            delete_chunk_data=True,
            dry_run=False
        )
        
        # We check 30x30 = 900 coordinates, but only 1 chunkdata file should be deleted
        self.assertEqual(files_checked, 900)
        self.assertEqual(files_deleted, 1)
        self.assertEqual(files_protected, 0)
        self.assertFalse((chunkdata_dir / "chunkdata_0_34.bin").exists())
        # Other chunk should remain
        self.assertTrue((chunkdata_dir / "chunkdata_1_35.bin").exists())


if __name__ == "__main__":
    unittest.main()
