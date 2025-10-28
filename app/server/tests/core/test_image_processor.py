import pytest
import sqlite3
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from core.image_processor import (
    validate_image_format,
    sanitize_folder_name,
    initialize_image_database,
    save_image_to_disk,
    save_image_metadata,
    get_images,
    get_image_by_id,
    delete_image,
    create_folder,
    get_folders,
    rename_folder,
    delete_folder,
    IMAGES_DIR
)
from core.data_models import ImageMetadata


@pytest.fixture
def test_db():
    """Create a temporary database for testing"""
    conn = sqlite3.connect(":memory:")
    initialize_image_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def test_images_dir():
    """Create a temporary images directory for testing"""
    temp_dir = tempfile.mkdtemp()
    # Temporarily replace IMAGES_DIR
    original_images_dir = Path(str(IMAGES_DIR))

    # Monkey patch the IMAGES_DIR
    import core.image_processor
    core.image_processor.IMAGES_DIR = Path(temp_dir)

    yield Path(temp_dir)

    # Cleanup
    core.image_processor.IMAGES_DIR = original_images_dir
    shutil.rmtree(temp_dir)


class TestValidation:
    """Test validation functions"""

    def test_validate_image_format_valid(self):
        """Test validation with valid image formats"""
        assert validate_image_format("test.png") == True
        assert validate_image_format("test.jpg") == True
        assert validate_image_format("test.jpeg") == True
        assert validate_image_format("test.gif") == True
        assert validate_image_format("test.webp") == True
        assert validate_image_format("test.bmp") == True

    def test_validate_image_format_case_insensitive(self):
        """Test validation is case insensitive"""
        assert validate_image_format("test.PNG") == True
        assert validate_image_format("test.JPG") == True
        assert validate_image_format("test.GIF") == True

    def test_validate_image_format_invalid(self):
        """Test validation with invalid formats"""
        assert validate_image_format("test.txt") == False
        assert validate_image_format("test.pdf") == False
        assert validate_image_format("test.doc") == False
        assert validate_image_format("test") == False

    def test_sanitize_folder_name(self):
        """Test folder name sanitization"""
        assert sanitize_folder_name("test-folder") == "test-folder"
        assert sanitize_folder_name("test_folder") == "test_folder"
        assert sanitize_folder_name("test folder") == "testfolder"
        assert sanitize_folder_name("../../../etc/passwd") == "etcpasswd"
        assert sanitize_folder_name("test/folder") == "testfolder"
        assert sanitize_folder_name("test\\folder") == "testfolder"
        assert sanitize_folder_name("test@#$%folder") == "testfolder"

    def test_sanitize_folder_name_empty(self):
        """Test sanitization returns 'default' for empty input"""
        assert sanitize_folder_name("") == "default"
        assert sanitize_folder_name("@#$%") == "default"


class TestDatabase:
    """Test database operations"""

    def test_initialize_image_database(self, test_db):
        """Test database initialization creates tables"""
        cursor = test_db.cursor()

        # Check images table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
        assert cursor.fetchone() is not None

        # Check folders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='folders'")
        assert cursor.fetchone() is not None

        # Check default folder exists
        cursor.execute("SELECT name FROM folders WHERE name='default'")
        assert cursor.fetchone() is not None

    def test_save_and_get_image_metadata(self, test_db):
        """Test saving and retrieving image metadata"""
        metadata = ImageMetadata(
            image_id="test-id-123",
            filename="test.png",
            folder="default",
            size=1024,
            format="png",
            created_at=datetime.now(),
            file_path="/path/to/test.png"
        )

        save_image_metadata(test_db, metadata)

        # Retrieve by ID
        retrieved = get_image_by_id(test_db, "test-id-123")
        assert retrieved is not None
        assert retrieved.image_id == metadata.image_id
        assert retrieved.filename == metadata.filename
        assert retrieved.folder == metadata.folder
        assert retrieved.size == metadata.size
        assert retrieved.format == metadata.format

    def test_get_images_all(self, test_db):
        """Test retrieving all images"""
        # Add multiple images
        for i in range(3):
            metadata = ImageMetadata(
                image_id=f"test-id-{i}",
                filename=f"test{i}.png",
                folder="default",
                size=1024 * i,
                format="png",
                created_at=datetime.now(),
                file_path=f"/path/to/test{i}.png"
            )
            save_image_metadata(test_db, metadata)

        images = get_images(test_db)
        assert len(images) == 3

    def test_get_images_by_folder(self, test_db):
        """Test retrieving images filtered by folder"""
        # Add images to different folders
        for i in range(2):
            metadata = ImageMetadata(
                image_id=f"default-{i}",
                filename=f"test{i}.png",
                folder="default",
                size=1024,
                format="png",
                created_at=datetime.now(),
                file_path=f"/path/to/test{i}.png"
            )
            save_image_metadata(test_db, metadata)

        for i in range(3):
            metadata = ImageMetadata(
                image_id=f"custom-{i}",
                filename=f"test{i}.png",
                folder="custom",
                size=1024,
                format="png",
                created_at=datetime.now(),
                file_path=f"/path/to/test{i}.png"
            )
            save_image_metadata(test_db, metadata)

        default_images = get_images(test_db, "default")
        assert len(default_images) == 2

        custom_images = get_images(test_db, "custom")
        assert len(custom_images) == 3

    def test_delete_image(self, test_db):
        """Test deleting an image"""
        metadata = ImageMetadata(
            image_id="test-delete",
            filename="test.png",
            folder="default",
            size=1024,
            format="png",
            created_at=datetime.now(),
            file_path="/path/to/test.png"
        )
        save_image_metadata(test_db, metadata)

        # Delete image
        success = delete_image(test_db, "test-delete")
        assert success == True

        # Verify it's gone
        retrieved = get_image_by_id(test_db, "test-delete")
        assert retrieved is None

    def test_delete_nonexistent_image(self, test_db):
        """Test deleting a non-existent image returns False"""
        success = delete_image(test_db, "nonexistent")
        assert success == False


class TestFolderManagement:
    """Test folder management operations"""

    def test_create_folder(self, test_db, test_images_dir):
        """Test creating a new folder"""
        success, message = create_folder(test_db, "test-folder")
        assert success == True

        # Check it's in database
        folders = get_folders(test_db)
        assert "test-folder" in folders

    def test_create_duplicate_folder(self, test_db, test_images_dir):
        """Test creating a folder that already exists"""
        create_folder(test_db, "test-folder")
        success, message = create_folder(test_db, "test-folder")
        assert success == False
        assert "already exists" in message.lower()

    def test_get_folders(self, test_db):
        """Test retrieving all folders"""
        create_folder(test_db, "folder1")
        create_folder(test_db, "folder2")
        create_folder(test_db, "folder3")

        folders = get_folders(test_db)
        assert "default" in folders
        assert "folder1" in folders
        assert "folder2" in folders
        assert "folder3" in folders

    def test_rename_folder(self, test_db, test_images_dir):
        """Test renaming a folder"""
        create_folder(test_db, "old-name")

        # Add an image to the folder
        metadata = ImageMetadata(
            image_id="test-id",
            filename="test.png",
            folder="old-name",
            size=1024,
            format="png",
            created_at=datetime.now(),
            file_path="/path/to/test.png"
        )
        save_image_metadata(test_db, metadata)

        # Rename folder
        success, message = rename_folder(test_db, "old-name", "new-name")
        assert success == True

        # Check folder name changed
        folders = get_folders(test_db)
        assert "new-name" in folders
        assert "old-name" not in folders

        # Check image folder updated
        images = get_images(test_db, "new-name")
        assert len(images) == 1

    def test_rename_nonexistent_folder(self, test_db, test_images_dir):
        """Test renaming a non-existent folder"""
        success, message = rename_folder(test_db, "nonexistent", "new-name")
        assert success == False
        assert "not found" in message.lower()

    def test_rename_to_existing_folder(self, test_db, test_images_dir):
        """Test renaming to an existing folder name"""
        create_folder(test_db, "folder1")
        create_folder(test_db, "folder2")

        success, message = rename_folder(test_db, "folder1", "folder2")
        assert success == False
        assert "already exists" in message.lower()

    def test_delete_folder(self, test_db, test_images_dir):
        """Test deleting a folder"""
        create_folder(test_db, "test-folder")

        # Add images to the folder
        for i in range(2):
            metadata = ImageMetadata(
                image_id=f"test-{i}",
                filename=f"test{i}.png",
                folder="test-folder",
                size=1024,
                format="png",
                created_at=datetime.now(),
                file_path=f"/path/to/test{i}.png"
            )
            save_image_metadata(test_db, metadata)

        # Delete folder
        success, message = delete_folder(test_db, "test-folder")
        assert success == True

        # Check folder is gone
        folders = get_folders(test_db)
        assert "test-folder" not in folders

        # Check images moved to default
        default_images = get_images(test_db, "default")
        assert len(default_images) == 2

    def test_delete_default_folder(self, test_db, test_images_dir):
        """Test that default folder cannot be deleted"""
        success, message = delete_folder(test_db, "default")
        assert success == False
        assert "cannot delete" in message.lower()


class TestFileOperations:
    """Test file operations"""

    def test_save_image_to_disk(self, test_images_dir):
        """Test saving image file to disk"""
        # Temporarily patch IMAGES_DIR
        import core.image_processor
        original_images_dir = core.image_processor.IMAGES_DIR
        core.image_processor.IMAGES_DIR = test_images_dir

        try:
            image_data = b"fake image data"
            file_path = save_image_to_disk(image_data, "test-folder", "test.png")

            # Check file exists
            assert Path(file_path).exists()

            # Check content
            with open(file_path, "rb") as f:
                assert f.read() == image_data
        finally:
            core.image_processor.IMAGES_DIR = original_images_dir

    def test_save_image_creates_folder(self, test_images_dir):
        """Test that save_image_to_disk creates folder if it doesn't exist"""
        import core.image_processor
        original_images_dir = core.image_processor.IMAGES_DIR
        core.image_processor.IMAGES_DIR = test_images_dir

        try:
            image_data = b"fake image data"
            file_path = save_image_to_disk(image_data, "new-folder", "test.png")

            # Check folder was created
            assert (test_images_dir / "new-folder").exists()
            assert Path(file_path).exists()
        finally:
            core.image_processor.IMAGES_DIR = original_images_dir
