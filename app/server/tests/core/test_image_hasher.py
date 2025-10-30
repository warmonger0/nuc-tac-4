"""
Tests for image_hasher module - perceptual hashing and duplicate detection.
"""

import pytest
import sqlite3
from pathlib import Path
from core import image_hasher


# Test fixtures - sample image data
@pytest.fixture
def sample_png_path():
    """Path to sample PNG test image"""
    return Path(__file__).parent.parent / "test_images" / "sample.png"


@pytest.fixture
def sample_jpg_path():
    """Path to sample JPG test image"""
    return Path(__file__).parent.parent / "test_images" / "sample.jpg"


@pytest.fixture
def sample_png_data(sample_png_path):
    """Binary data of sample PNG"""
    with open(sample_png_path, 'rb') as f:
        return f.read()


@pytest.fixture
def sample_jpg_data(sample_jpg_path):
    """Binary data of sample JPG"""
    with open(sample_jpg_path, 'rb') as f:
        return f.read()


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create images table with phash column
    cursor.execute("""
        CREATE TABLE images (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            folder TEXT NOT NULL,
            size INTEGER NOT NULL,
            format TEXT NOT NULL,
            created_at TEXT NOT NULL,
            file_path TEXT NOT NULL,
            phash TEXT
        )
    """)

    conn.commit()
    yield conn
    conn.close()


class TestComputePhash:
    """Tests for compute_phash function"""

    def test_compute_phash_png(self, sample_png_data):
        """Test computing hash for PNG image"""
        phash = image_hasher.compute_phash(sample_png_data)

        assert phash is not None
        assert isinstance(phash, str)
        assert len(phash) == 16  # 64-bit hash as 16 hex characters

    def test_compute_phash_jpg(self, sample_jpg_data):
        """Test computing hash for JPG image"""
        phash = image_hasher.compute_phash(sample_jpg_data)

        assert phash is not None
        assert isinstance(phash, str)
        assert len(phash) == 16

    def test_identical_images_same_hash(self, sample_png_data):
        """Test that identical images produce identical hashes"""
        hash1 = image_hasher.compute_phash(sample_png_data)
        hash2 = image_hasher.compute_phash(sample_png_data)

        assert hash1 == hash2

    def test_invalid_image_data_raises_error(self):
        """Test that invalid image data raises ValueError"""
        invalid_data = b"not an image"

        with pytest.raises(ValueError, match="Failed to compute perceptual hash"):
            image_hasher.compute_phash(invalid_data)

    def test_empty_image_data_raises_error(self):
        """Test that empty data raises ValueError"""
        empty_data = b""

        with pytest.raises(ValueError):
            image_hasher.compute_phash(empty_data)


class TestCompareHashes:
    """Tests for compare_hashes function"""

    def test_identical_hashes_return_1(self, sample_png_data):
        """Test that identical hashes have similarity of 1.0"""
        hash1 = image_hasher.compute_phash(sample_png_data)
        hash2 = image_hasher.compute_phash(sample_png_data)

        similarity = image_hasher.compare_hashes(hash1, hash2)

        assert similarity == 1.0

    def test_different_hashes_return_less_than_1(self, sample_png_data, sample_jpg_data):
        """Test that different images have similarity less than 1.0"""
        hash1 = image_hasher.compute_phash(sample_png_data)
        hash2 = image_hasher.compute_phash(sample_jpg_data)

        similarity = image_hasher.compare_hashes(hash1, hash2)

        assert 0.0 <= similarity < 1.0

    def test_similarity_in_valid_range(self, sample_png_data, sample_jpg_data):
        """Test that similarity is always between 0.0 and 1.0"""
        hash1 = image_hasher.compute_phash(sample_png_data)
        hash2 = image_hasher.compute_phash(sample_jpg_data)

        similarity = image_hasher.compare_hashes(hash1, hash2)

        assert 0.0 <= similarity <= 1.0

    def test_invalid_hash_format_raises_error(self):
        """Test that invalid hash format raises ValueError"""
        invalid_hash = "not_a_valid_hash"
        valid_hash = "0" * 16

        with pytest.raises(ValueError, match="Failed to compare hashes"):
            image_hasher.compare_hashes(invalid_hash, valid_hash)


class TestComputeAndStoreHash:
    """Tests for compute_and_store_hash function"""

    def test_compute_and_store_hash(self, test_db, sample_png_data):
        """Test computing and storing hash in database"""
        # Insert a test image record
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("test123", "test.png", "default", 1000, "png", "2024-01-01", "/path/to/test.png"))
        test_db.commit()

        # Compute and store hash
        phash = image_hasher.compute_and_store_hash(test_db, "test123", sample_png_data)

        # Verify hash was stored
        cursor.execute("SELECT phash FROM images WHERE id = ?", ("test123",))
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == phash
        assert len(phash) == 16


class TestFindSimilarImages:
    """Tests for find_similar_images function"""

    def test_find_exact_duplicate(self, test_db, sample_png_data):
        """Test finding exact duplicate image"""
        phash = image_hasher.compute_phash(sample_png_data)

        # Insert test image with same hash
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img1", "test.png", "default", 1000, "png", "2024-01-01", "/path/test.png", phash))
        test_db.commit()

        # Find similar images
        similar = image_hasher.find_similar_images(test_db, phash, "default", threshold=0.95)

        assert len(similar) == 1
        assert similar[0][0] == "img1"  # image_id
        assert similar[0][1] == "test.png"  # filename
        assert similar[0][3] == 1.0  # similarity

    def test_find_no_duplicates_empty_folder(self, test_db, sample_png_data):
        """Test finding duplicates in empty folder returns no results"""
        phash = image_hasher.compute_phash(sample_png_data)

        similar = image_hasher.find_similar_images(test_db, phash, "default", threshold=0.95)

        assert len(similar) == 0

    def test_find_duplicates_different_folder(self, test_db, sample_png_data):
        """Test that images in different folders are not found"""
        phash = image_hasher.compute_phash(sample_png_data)

        # Insert image in different folder
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img1", "test.png", "other_folder", 1000, "png", "2024-01-01", "/path/test.png", phash))
        test_db.commit()

        # Search in default folder
        similar = image_hasher.find_similar_images(test_db, phash, "default", threshold=0.95)

        assert len(similar) == 0

    def test_threshold_filtering(self, test_db, sample_png_data, sample_jpg_data):
        """Test that threshold properly filters results"""
        hash1 = image_hasher.compute_phash(sample_png_data)
        hash2 = image_hasher.compute_phash(sample_jpg_data)

        # Insert both images
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img1", "test1.png", "default", 1000, "png", "2024-01-01", "/path/test1.png", hash1))
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img2", "test2.jpg", "default", 1000, "jpg", "2024-01-01", "/path/test2.jpg", hash2))
        test_db.commit()

        # Find with high threshold - should only find exact match
        similar = image_hasher.find_similar_images(test_db, hash1, "default", threshold=0.99)

        assert len(similar) == 1
        assert similar[0][0] == "img1"

    def test_invalid_threshold_raises_error(self, test_db, sample_png_data):
        """Test that invalid threshold raises ValueError"""
        phash = image_hasher.compute_phash(sample_png_data)

        with pytest.raises(ValueError, match="Threshold must be between"):
            image_hasher.find_similar_images(test_db, phash, "default", threshold=1.5)

        with pytest.raises(ValueError, match="Threshold must be between"):
            image_hasher.find_similar_images(test_db, phash, "default", threshold=-0.1)

    def test_results_sorted_by_similarity(self, test_db, sample_png_data):
        """Test that results are sorted by similarity (highest first)"""
        hash1 = image_hasher.compute_phash(sample_png_data)

        # Create slightly different hashes (by modifying last character)
        hash2 = hash1[:-1] + ('0' if hash1[-1] != '0' else '1')
        hash3 = hash1[:-2] + '00'

        # Insert images with different similarity levels
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img1", "exact.png", "default", 1000, "png", "2024-01-01", "/path/1.png", hash1))
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img2", "similar.png", "default", 1000, "png", "2024-01-01", "/path/2.png", hash2))
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img3", "less_similar.png", "default", 1000, "png", "2024-01-01", "/path/3.png", hash3))
        test_db.commit()

        # Find similar images
        similar = image_hasher.find_similar_images(test_db, hash1, "default", threshold=0.8)

        # Verify sorted by similarity descending
        assert len(similar) >= 2
        for i in range(len(similar) - 1):
            assert similar[i][3] >= similar[i + 1][3]


class TestGetImageHash:
    """Tests for get_image_hash function"""

    def test_get_existing_hash(self, test_db, sample_png_data):
        """Test retrieving existing hash"""
        phash = image_hasher.compute_phash(sample_png_data)

        # Insert image with hash
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img1", "test.png", "default", 1000, "png", "2024-01-01", "/path/test.png", phash))
        test_db.commit()

        # Retrieve hash
        retrieved_hash = image_hasher.get_image_hash(test_db, "img1")

        assert retrieved_hash == phash

    def test_get_nonexistent_image_returns_none(self, test_db):
        """Test that retrieving hash for nonexistent image returns None"""
        result = image_hasher.get_image_hash(test_db, "nonexistent")

        assert result is None

    def test_get_hash_for_image_without_hash(self, test_db):
        """Test retrieving hash for image without hash (NULL)"""
        # Insert image without hash
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO images (id, filename, folder, size, format, created_at, file_path, phash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("img1", "test.png", "default", 1000, "png", "2024-01-01", "/path/test.png", None))
        test_db.commit()

        # Retrieve hash
        result = image_hasher.get_image_hash(test_db, "img1")

        assert result is None
