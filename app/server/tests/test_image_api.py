"""
Tests for image upload API endpoints
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
import io

# Import the app
from server import app


@pytest.fixture
def test_images_dir():
    """Create a temporary images directory for testing"""
    temp_dir = tempfile.mkdtemp()

    # Monkey patch the IMAGES_DIR
    import core.image_processor
    original_images_dir = core.image_processor.IMAGES_DIR
    core.image_processor.IMAGES_DIR = Path(temp_dir)

    yield Path(temp_dir)

    # Cleanup
    core.image_processor.IMAGES_DIR = original_images_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def sample_images():
    """Load sample test images"""
    test_images_path = Path(__file__).parent / "test_images"

    images = {}
    for image_file in test_images_path.iterdir():
        if image_file.is_file():
            with open(image_file, "rb") as f:
                images[image_file.name] = f.read()

    return images


class TestImageUpload:
    """Test image upload endpoints"""

    def test_upload_single_image(self, client, test_images_dir, sample_images):
        """Test uploading a single image"""
        response = client.post(
            "/api/images/upload?folder=default",
            files=[("files", ("test.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "test.png"
        assert data[0]["folder"] == "default"
        assert data[0]["format"] == "png"
        assert data[0]["error"] is None or data[0]["error"] == ""

    def test_upload_multiple_images(self, client, test_images_dir, sample_images):
        """Test uploading multiple images"""
        files = [
            ("files", ("test1.png", io.BytesIO(sample_images["sample.png"]), "image/png")),
            ("files", ("test2.jpg", io.BytesIO(sample_images["sample.jpg"]), "image/jpeg")),
            ("files", ("test3.gif", io.BytesIO(sample_images["sample.gif"]), "image/gif"))
        ]

        response = client.post("/api/images/upload?folder=default", files=files)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Check all uploads succeeded
        for item in data:
            assert item["error"] is None or item["error"] == ""

    def test_upload_to_custom_folder(self, client, test_images_dir, sample_images):
        """Test uploading to a custom folder"""
        # First create the folder
        client.post("/api/folders", json={"folder_name": "custom-folder"})

        # Upload image
        response = client.post(
            "/api/images/upload?folder=custom-folder",
            files=[("files", ("test.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        assert response.status_code == 200
        data = response.json()
        assert data[0]["folder"] == "custom-folder"

    def test_upload_invalid_format(self, client, test_images_dir):
        """Test uploading an invalid file format"""
        fake_file = io.BytesIO(b"fake text content")

        response = client.post(
            "/api/images/upload?folder=default",
            files=[("files", ("test.txt", fake_file, "text/plain"))]
        )

        assert response.status_code == 200
        data = response.json()
        assert data[0]["error"] is not None
        assert "unsupported" in data[0]["error"].lower() or "format" in data[0]["error"].lower()

    def test_upload_mixed_valid_invalid(self, client, test_images_dir, sample_images):
        """Test uploading a mix of valid and invalid files"""
        files = [
            ("files", ("test.png", io.BytesIO(sample_images["sample.png"]), "image/png")),
            ("files", ("test.txt", io.BytesIO(b"text"), "text/plain")),
            ("files", ("test.jpg", io.BytesIO(sample_images["sample.jpg"]), "image/jpeg"))
        ]

        response = client.post("/api/images/upload?folder=default", files=files)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Check that valid files succeeded and invalid failed
        successful = [item for item in data if not item["error"]]
        failed = [item for item in data if item["error"]]

        assert len(successful) == 2
        assert len(failed) == 1


class TestImageRetrieval:
    """Test image retrieval endpoints"""

    def test_list_images_empty(self, client, test_images_dir):
        """Test listing images returns valid structure"""
        response = client.get("/api/images")

        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert "images" in data
        assert isinstance(data["images"], list)
        assert data["total_count"] == len(data["images"])

    def test_list_images_with_data(self, client, test_images_dir, sample_images):
        """Test listing images after uploading some"""
        # Get initial count
        initial_response = client.get("/api/images")
        initial_count = initial_response.json()["total_count"]

        # Upload some images
        client.post(
            "/api/images/upload?folder=default",
            files=[
                ("files", ("test1.png", io.BytesIO(sample_images["sample.png"]), "image/png")),
                ("files", ("test2.jpg", io.BytesIO(sample_images["sample.jpg"]), "image/jpeg"))
            ]
        )

        # List images
        response = client.get("/api/images")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == initial_count + 2
        assert len(data["images"]) == initial_count + 2

    def test_list_images_by_folder(self, client, test_images_dir, sample_images):
        """Test listing images filtered by folder"""
        import uuid

        # Create unique folder names to avoid collisions
        folder1 = f"folder1-{uuid.uuid4().hex[:8]}"
        folder2 = f"folder2-{uuid.uuid4().hex[:8]}"

        # Create folders
        client.post("/api/folders", json={"folder_name": folder1})
        client.post("/api/folders", json={"folder_name": folder2})

        # Upload to different folders
        client.post(
            f"/api/images/upload?folder={folder1}",
            files=[("files", ("test1.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        client.post(
            f"/api/images/upload?folder={folder2}",
            files=[
                ("files", ("test2.jpg", io.BytesIO(sample_images["sample.jpg"]), "image/jpeg")),
                ("files", ("test3.gif", io.BytesIO(sample_images["sample.gif"]), "image/gif"))
            ]
        )

        # List folder1 images
        response = client.get(f"/api/images?folder={folder1}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

        # List folder2 images
        response = client.get(f"/api/images?folder={folder2}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2

    def test_get_specific_image(self, client, test_images_dir, sample_images):
        """Test retrieving a specific image file"""
        # Upload an image
        upload_response = client.post(
            "/api/images/upload?folder=default",
            files=[("files", ("test.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        image_id = upload_response.json()[0]["image_id"]

        # Get the image
        response = client.get(f"/api/images/{image_id}")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")
        assert len(response.content) > 0

    def test_get_nonexistent_image(self, client, test_images_dir):
        """Test retrieving a non-existent image"""
        response = client.get("/api/images/nonexistent-id")

        assert response.status_code == 404


class TestImageDeletion:
    """Test image deletion endpoints"""

    def test_delete_image(self, client, test_images_dir, sample_images):
        """Test deleting an image"""
        # Get initial count
        initial_response = client.get("/api/images")
        initial_count = initial_response.json()["total_count"]

        # Upload an image
        upload_response = client.post(
            "/api/images/upload?folder=default",
            files=[("files", ("test.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        image_id = upload_response.json()[0]["image_id"]

        # Verify it was added
        after_upload = client.get("/api/images")
        assert after_upload.json()["total_count"] == initial_count + 1

        # Delete the image
        response = client.delete(f"/api/images/{image_id}")

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify count is back to initial
        list_response = client.get("/api/images")
        assert list_response.json()["total_count"] == initial_count

    def test_delete_nonexistent_image(self, client, test_images_dir):
        """Test deleting a non-existent image"""
        response = client.delete("/api/images/nonexistent-id")

        assert response.status_code == 404


class TestFolderManagement:
    """Test folder management endpoints"""

    def test_list_folders(self, client, test_images_dir):
        """Test listing folders"""
        response = client.get("/api/folders")

        assert response.status_code == 200
        data = response.json()
        assert "default" in data["folders"]

    def test_create_folder(self, client, test_images_dir):
        """Test creating a folder"""
        response = client.post("/api/folders", json={"folder_name": "test-folder"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

        # Verify it exists
        list_response = client.get("/api/folders")
        assert "test-folder" in list_response.json()["folders"]

    def test_create_duplicate_folder(self, client, test_images_dir):
        """Test creating a duplicate folder"""
        client.post("/api/folders", json={"folder_name": "test-folder"})
        response = client.post("/api/folders", json={"folder_name": "test-folder"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "already exists" in data["message"].lower()

    def test_rename_folder(self, client, test_images_dir):
        """Test renaming a folder"""
        import uuid

        # Create unique folder names
        old_name = f"old-name-{uuid.uuid4().hex[:8]}"
        new_name = f"new-name-{uuid.uuid4().hex[:8]}"

        # Create a folder
        client.post("/api/folders", json={"folder_name": old_name})

        # Rename it
        response = client.put(
            f"/api/folders/{old_name}",
            json={"old_name": old_name, "new_name": new_name}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

        # Verify new name exists and old doesn't
        list_response = client.get("/api/folders")
        folders = list_response.json()["folders"]
        assert new_name in folders
        assert old_name not in folders

    def test_delete_folder(self, client, test_images_dir):
        """Test deleting a folder"""
        # Create a folder
        client.post("/api/folders", json={"folder_name": "test-folder"})

        # Delete it
        response = client.delete("/api/folders/test-folder")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

        # Verify it's gone
        list_response = client.get("/api/folders")
        assert "test-folder" not in list_response.json()["folders"]

    def test_delete_default_folder(self, client, test_images_dir):
        """Test that default folder cannot be deleted"""
        response = client.delete("/api/folders/default")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_upload_with_special_characters_in_filename(self, client, test_images_dir, sample_images):
        """Test uploading files with special characters in filename"""
        response = client.post(
            "/api/images/upload?folder=default",
            files=[("files", ("test@#$%.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        assert response.status_code == 200
        data = response.json()
        # Should succeed - filename is sanitized on server side
        assert data[0]["error"] is None or data[0]["error"] == ""

    def test_upload_with_unicode_filename(self, client, test_images_dir, sample_images):
        """Test uploading files with unicode characters"""
        response = client.post(
            "/api/images/upload?folder=default",
            files=[("files", ("测试图片.png", io.BytesIO(sample_images["sample.png"]), "image/png"))]
        )

        assert response.status_code == 200

    def test_folder_name_sanitization(self, client, test_images_dir):
        """Test that folder names are properly sanitized"""
        response = client.post("/api/folders", json={"folder_name": "../../../etc/passwd"})

        assert response.status_code == 200
        # Folder should be created with sanitized name
        list_response = client.get("/api/folders")
        folders = list_response.json()["folders"]

        # Should not contain path traversal
        assert not any("/" in folder or ".." in folder for folder in folders)
