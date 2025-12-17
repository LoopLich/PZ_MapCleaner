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
        
        files_checked, files_deleted = delete_files_in_area(
            self.test_path, 10, 20, 11, 22,
            delete_map_data=True,
            dry_run=True
        )
        
        self.assertEqual(files_checked, 2)
        self.assertEqual(files_deleted, 2)
        # Files should still exist in dry run
        self.assertTrue((self.test_path / "map_10_20.bin").exists())
        self.assertTrue((self.test_path / "map_10_21.bin").exists())
    
    def test_delete_map_files(self):
        # Create test files
        (self.test_path / "map_10_20.bin").touch()
        (self.test_path / "map_10_21.bin").touch()
        (self.test_path / "map_15_25.bin").touch()  # Outside area
        
        files_checked, files_deleted = delete_files_in_area(
            self.test_path, 10, 20, 11, 22,
            delete_map_data=True,
            dry_run=False
        )
        
        self.assertEqual(files_checked, 2)
        self.assertEqual(files_deleted, 2)
        # Files in area should be deleted
        self.assertFalse((self.test_path / "map_10_20.bin").exists())
        self.assertFalse((self.test_path / "map_10_21.bin").exists())
        # File outside area should remain
        self.assertTrue((self.test_path / "map_15_25.bin").exists())
    
    def test_delete_no_file_types_selected(self):
        files_checked, files_deleted = delete_files_in_area(
            self.test_path, 0, 0, 10, 10,
            delete_map_data=False,
            delete_chunk_data=False,
            delete_zpop_data=False
        )
        
        self.assertEqual(files_checked, 0)
        self.assertEqual(files_deleted, 0)
    
    def test_delete_multiple_file_types(self):
        # Create test files
        (self.test_path / "map_30_60.bin").touch()
        (self.test_path / "chunkdata_1_2.bin").touch()
        (self.test_path / "zpop_1_2.bin").touch()
        
        files_checked, files_deleted = delete_files_in_area(
            self.test_path, 30, 60, 31, 61,
            delete_map_data=True,
            delete_chunk_data=True,
            delete_zpop_data=True
        )
        
        self.assertEqual(files_checked, 1)
        self.assertEqual(files_deleted, 3)
        self.assertFalse((self.test_path / "map_30_60.bin").exists())
        self.assertFalse((self.test_path / "chunkdata_1_2.bin").exists())
        self.assertFalse((self.test_path / "zpop_1_2.bin").exists())


if __name__ == "__main__":
    unittest.main()
