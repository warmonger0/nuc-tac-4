"""Tests for image processor module"""

import pytest
import sqlite3
import os
import tempfile
from datetime import datetime
from core.image_processor import (
    process_image_upload,
    extract_metadata,
    save_image_to_db,
    get_image_by_id,
    list_images_by_folder,
    delete_image,
    create_folder,
    get_folder_by_id,
    list_all_folders,
    rename_folder,
    delete_folder,
    ImageProcessorError
)
from core.sql_security import execute_query_safely

# Test asset paths
TEST_ASSETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')


def load_test_file(filename: str) -> bytes:
    """Load a test file"""
    path = os.path.join(TEST_ASSETS_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    # Use an in-memory database for testing
    conn = sqlite3.connect(':memory:')

    # Create tables
    execute_query_safely(
        conn,
        """
        CREATE TABLE image_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        allow_ddl=True
    )

    execute_query_safely(
        conn,
        """
        CREATE TABLE image_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            folder_id INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            binary_data BLOB NOT NULL,
            FOREIGN KEY (folder_id) REFERENCES image_folders(id)
        )
        """,
        allow_ddl=True
    )

    execute_query_safely(
        conn,
        "CREATE INDEX idx_image_files_folder_id ON image_files(folder_id)",
        allow_ddl=True
    )

    conn.commit()

    yield conn

    conn.close()


class TestProcessImageUpload:
    """Tests for process_image_upload function"""

    def test_process_valid_png(self):
        """Test processing valid PNG image"""
        content = load_test_file('test-image.png')
        result = process_image_upload(content, 'test.png')

        assert result['original_name'] == 'test.png'
        assert result['file_type'] == 'png'
        assert result['file_size'] == len(content)
        assert result['binary_data'] == content
        assert 'filename' in result
        assert result['filename'] != 'test.png'  # Should be unique

    def test_process_valid_jpg(self):
        """Test processing valid JPG image"""
        content = load_test_file('test-image.jpg')
        result = process_image_upload(content, 'photo.jpg')

        assert result['original_name'] == 'photo.jpg'
        assert result['file_type'] == 'jpg'
        assert result['file_size'] == len(content)

    def test_process_with_folder_id(self):
        """Test processing with folder ID"""
        content = load_test_file('test-image.png')
        result = process_image_upload(content, 'test.png', folder_id=1)

        assert result['folder_id'] == 1

    def test_process_invalid_file(self):
        """Test processing invalid file"""
        content = load_test_file('invalid-image.txt')
        with pytest.raises(ImageProcessorError):
            process_image_upload(content, 'invalid.txt')

    def test_process_fake_image(self):
        """Test processing fake image"""
        content = load_test_file('fake-image.jpg')
        with pytest.raises(ImageProcessorError):
            process_image_upload(content, 'fake.jpg')

    def test_process_special_characters_filename(self):
        """Test processing filename with special characters"""
        content = load_test_file('test-image.png')
        with pytest.raises(ImageProcessorError):
            process_image_upload(content, 'test<>.png')


class TestExtractMetadata:
    """Tests for extract_metadata function"""

    def test_extract_metadata_png(self):
        """Test metadata extraction from PNG"""
        content = load_test_file('test-image.png')
        metadata = extract_metadata(content, 'png')

        assert metadata['format'] == 'PNG'
        assert metadata['size_bytes'] == len(content)

    def test_extract_metadata_jpg(self):
        """Test metadata extraction from JPG"""
        content = load_test_file('test-image.jpg')
        metadata = extract_metadata(content, 'jpg')

        assert metadata['format'] == 'JPG'
        assert metadata['size_bytes'] == len(content)


class TestSaveImageToDb:
    """Tests for save_image_to_db function"""

    def test_save_image_success(self, test_db):
        """Test successful image save"""
        content = load_test_file('test-image.png')
        image_data = process_image_upload(content, 'test.png')

        image_id = save_image_to_db(test_db, image_data)

        assert image_id > 0

        # Verify image was saved
        cursor = test_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM image_files WHERE id = ?", (image_id,))
        assert cursor.fetchone()[0] == 1

    def test_save_image_with_folder(self, test_db):
        """Test saving image with folder"""
        # Create folder first
        folder_id = create_folder(test_db, 'test_folder')

        content = load_test_file('test-image.png')
        image_data = process_image_upload(content, 'test.png', folder_id=folder_id)

        image_id = save_image_to_db(test_db, image_data)

        assert image_id > 0

        # Verify folder association
        cursor = test_db.cursor()
        cursor.execute("SELECT folder_id FROM image_files WHERE id = ?", (image_id,))
        assert cursor.fetchone()[0] == folder_id

    def test_save_image_with_invalid_folder(self, test_db):
        """Test saving image with invalid folder ID"""
        content = load_test_file('test-image.png')
        image_data = process_image_upload(content, 'test.png', folder_id=999)

        with pytest.raises(ImageProcessorError, match="does not exist"):
            save_image_to_db(test_db, image_data)


class TestGetImageById:
    """Tests for get_image_by_id function"""

    def test_get_existing_image(self, test_db):
        """Test retrieving existing image"""
        content = load_test_file('test-image.png')
        image_data = process_image_upload(content, 'test.png')
        image_id = save_image_to_db(test_db, image_data)

        retrieved = get_image_by_id(test_db, image_id)

        assert retrieved is not None
        assert retrieved['id'] == image_id
        assert retrieved['original_name'] == 'test.png'
        assert retrieved['binary_data'] == content

    def test_get_nonexistent_image(self, test_db):
        """Test retrieving nonexistent image"""
        result = get_image_by_id(test_db, 999)
        assert result is None


class TestListImagesByFolder:
    """Tests for list_images_by_folder function"""

    def test_list_all_images(self, test_db):
        """Test listing all images"""
        # Add multiple images
        for i in range(3):
            content = load_test_file('test-image.png')
            image_data = process_image_upload(content, f'test{i}.png')
            save_image_to_db(test_db, image_data)

        images = list_images_by_folder(test_db)

        assert len(images) == 3

    def test_list_images_by_specific_folder(self, test_db):
        """Test listing images by folder"""
        # Create folders
        folder1 = create_folder(test_db, 'folder1')
        folder2 = create_folder(test_db, 'folder2')

        # Add images to different folders
        content = load_test_file('test-image.png')

        image_data1 = process_image_upload(content, 'img1.png', folder_id=folder1)
        save_image_to_db(test_db, image_data1)

        image_data2 = process_image_upload(content, 'img2.png', folder_id=folder2)
        save_image_to_db(test_db, image_data2)

        # List images in folder1
        images = list_images_by_folder(test_db, folder_id=folder1)

        assert len(images) == 1
        assert images[0]['folder_id'] == folder1

    def test_list_with_pagination(self, test_db):
        """Test pagination"""
        # Add 5 images
        for i in range(5):
            content = load_test_file('test-image.png')
            image_data = process_image_upload(content, f'test{i}.png')
            save_image_to_db(test_db, image_data)

        # Get first 2
        images_page1 = list_images_by_folder(test_db, limit=2, offset=0)
        assert len(images_page1) == 2

        # Get next 2
        images_page2 = list_images_by_folder(test_db, limit=2, offset=2)
        assert len(images_page2) == 2

        # Verify different images
        assert images_page1[0]['id'] != images_page2[0]['id']


class TestDeleteImage:
    """Tests for delete_image function"""

    def test_delete_existing_image(self, test_db):
        """Test deleting existing image"""
        content = load_test_file('test-image.png')
        image_data = process_image_upload(content, 'test.png')
        image_id = save_image_to_db(test_db, image_data)

        result = delete_image(test_db, image_id)

        assert result is True

        # Verify deletion
        assert get_image_by_id(test_db, image_id) is None

    def test_delete_nonexistent_image(self, test_db):
        """Test deleting nonexistent image"""
        result = delete_image(test_db, 999)
        assert result is False


class TestCreateFolder:
    """Tests for create_folder function"""

    def test_create_folder_success(self, test_db):
        """Test successful folder creation"""
        folder_id = create_folder(test_db, 'my_folder')

        assert folder_id > 0

        # Verify folder exists
        folder = get_folder_by_id(test_db, folder_id)
        assert folder is not None
        assert folder['folder_name'] == 'my_folder'

    def test_create_duplicate_folder(self, test_db):
        """Test creating duplicate folder"""
        create_folder(test_db, 'my_folder')

        with pytest.raises(ImageProcessorError, match="already exists"):
            create_folder(test_db, 'my_folder')

    def test_create_folder_with_invalid_name(self, test_db):
        """Test creating folder with invalid name"""
        with pytest.raises(ImageProcessorError, match="Invalid folder name"):
            create_folder(test_db, 'folder<>')


class TestListAllFolders:
    """Tests for list_all_folders function"""

    def test_list_empty_folders(self, test_db):
        """Test listing when no folders exist"""
        folders = list_all_folders(test_db)
        assert folders == []

    def test_list_folders_with_image_counts(self, test_db):
        """Test listing folders with image counts"""
        # Create folders
        folder1 = create_folder(test_db, 'folder1')
        folder2 = create_folder(test_db, 'folder2')

        # Add images
        content = load_test_file('test-image.png')

        # 2 images in folder1
        for i in range(2):
            image_data = process_image_upload(content, f'img{i}.png', folder_id=folder1)
            save_image_to_db(test_db, image_data)

        # 1 image in folder2
        image_data = process_image_upload(content, 'img.png', folder_id=folder2)
        save_image_to_db(test_db, image_data)

        folders = list_all_folders(test_db)

        assert len(folders) == 2
        folder1_data = next(f for f in folders if f['id'] == folder1)
        folder2_data = next(f for f in folders if f['id'] == folder2)

        assert folder1_data['image_count'] == 2
        assert folder2_data['image_count'] == 1


class TestRenameFolder:
    """Tests for rename_folder function"""

    def test_rename_folder_success(self, test_db):
        """Test successful folder rename"""
        folder_id = create_folder(test_db, 'old_name')

        result = rename_folder(test_db, folder_id, 'new_name')

        assert result is True

        # Verify rename
        folder = get_folder_by_id(test_db, folder_id)
        assert folder['folder_name'] == 'new_name'

    def test_rename_nonexistent_folder(self, test_db):
        """Test renaming nonexistent folder"""
        with pytest.raises(ImageProcessorError, match="does not exist"):
            rename_folder(test_db, 999, 'new_name')

    def test_rename_to_existing_name(self, test_db):
        """Test renaming to existing folder name"""
        folder1 = create_folder(test_db, 'folder1')
        create_folder(test_db, 'folder2')

        with pytest.raises(ImageProcessorError, match="already exists"):
            rename_folder(test_db, folder1, 'folder2')

    def test_rename_with_invalid_name(self, test_db):
        """Test renaming with invalid name"""
        folder_id = create_folder(test_db, 'valid_name')

        with pytest.raises(ImageProcessorError, match="Invalid folder name"):
            rename_folder(test_db, folder_id, 'invalid<>')


class TestDeleteFolder:
    """Tests for delete_folder function"""

    def test_delete_empty_folder(self, test_db):
        """Test deleting empty folder"""
        folder_id = create_folder(test_db, 'empty_folder')

        result = delete_folder(test_db, folder_id)

        assert result is True

        # Verify deletion
        assert get_folder_by_id(test_db, folder_id) is None

    def test_delete_folder_with_images(self, test_db):
        """Test deleting folder that contains images"""
        folder_id = create_folder(test_db, 'folder_with_images')

        # Add image to folder
        content = load_test_file('test-image.png')
        image_data = process_image_upload(content, 'img.png', folder_id=folder_id)
        save_image_to_db(test_db, image_data)

        with pytest.raises(ImageProcessorError, match="contains.*image"):
            delete_folder(test_db, folder_id)

    def test_delete_nonexistent_folder(self, test_db):
        """Test deleting nonexistent folder"""
        with pytest.raises(ImageProcessorError, match="does not exist"):
            delete_folder(test_db, 999)
