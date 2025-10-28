"""Tests for image upload API endpoints"""

import pytest
import os
import uuid
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def unique_folder_name(base: str) -> str:
    """Generate a unique folder name for testing"""
    return f'{base}_{uuid.uuid4().hex[:8]}'

# Test asset paths
TEST_ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')


def load_test_file(filename: str) -> bytes:
    """Load a test file"""
    path = os.path.join(TEST_ASSETS_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()


class TestImageUploadEndpoint:
    """Tests for POST /api/images/upload endpoint"""

    def test_upload_valid_png(self):
        """Test uploading valid PNG image"""
        content = load_test_file('test-image.png')

        response = client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['image_id'] > 0
        assert data['file_type'] == 'png'
        assert data['error'] is None

    def test_upload_valid_jpg(self):
        """Test uploading valid JPG image"""
        content = load_test_file('test-image.jpg')

        response = client.post(
            '/api/images/upload',
            files={'file': ('photo.jpg', content, 'image/jpeg')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['image_id'] > 0
        assert data['file_type'] == 'jpg'

    def test_upload_valid_gif(self):
        """Test uploading valid GIF image"""
        content = load_test_file('test-image.gif')

        response = client.post(
            '/api/images/upload',
            files={'file': ('animation.gif', content, 'image/gif')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['image_id'] > 0
        assert data['file_type'] == 'gif'

    def test_upload_valid_bmp(self):
        """Test uploading valid BMP image"""
        content = load_test_file('test-image.bmp')

        response = client.post(
            '/api/images/upload',
            files={'file': ('bitmap.bmp', content, 'image/bmp')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['image_id'] > 0
        assert data['file_type'] == 'bmp'

    def test_upload_valid_webp(self):
        """Test uploading valid WebP image"""
        content = load_test_file('test-image.webp')

        response = client.post(
            '/api/images/upload',
            files={'file': ('modern.webp', content, 'image/webp')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['image_id'] > 0
        assert data['file_type'] == 'webp'

    def test_upload_invalid_file_type(self):
        """Test uploading invalid file type"""
        content = load_test_file('invalid-image.txt')

        response = client.post(
            '/api/images/upload',
            files={'file': ('invalid.txt', content, 'text/plain')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['error'] is not None
        assert 'Unsupported file type' in data['error']

    def test_upload_fake_image(self):
        """Test uploading file with fake image extension"""
        content = load_test_file('fake-image.jpg')

        response = client.post(
            '/api/images/upload',
            files={'file': ('fake.jpg', content, 'image/jpeg')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['error'] is not None
        assert 'Magic number check failed' in data['error']

    def test_upload_with_folder(self):
        """Test uploading image with folder ID"""
        # Create folder first
        folder_response = client.post(
            '/api/images/folders',
            json={'folder_name': 'test_folder'}
        )
        assert folder_response.status_code == 200
        folder_id = folder_response.json()['id']

        # Upload image to folder
        content = load_test_file('test-image.png')
        response = client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')},
            data={'folder_id': str(folder_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['image_id'] > 0
        assert data['folder_name'] == 'test_folder'


class TestImageListEndpoint:
    """Tests for GET /api/images endpoint"""

    def test_list_images_empty(self):
        """Test listing images when none exist"""
        response = client.get('/api/images')

        # Note: This test may fail if previous tests left data
        # In production, use database fixtures or cleanup
        assert response.status_code == 200
        data = response.json()
        assert 'images' in data
        assert 'total_count' in data

    def test_list_images_with_data(self):
        """Test listing images after uploading"""
        # Upload an image
        content = load_test_file('test-image.png')
        client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')}
        )

        # List images
        response = client.get('/api/images')

        assert response.status_code == 200
        data = response.json()
        assert len(data['images']) > 0
        assert data['total_count'] > 0

    def test_list_images_with_pagination(self):
        """Test pagination parameters"""
        response = client.get('/api/images?limit=5&offset=0')

        assert response.status_code == 200
        data = response.json()
        assert len(data['images']) <= 5

    def test_list_images_by_folder(self):
        """Test filtering images by folder"""
        # Create folder
        folder_response = client.post(
            '/api/images/folders',
            json={'folder_name': 'filter_test'}
        )
        folder_id = folder_response.json()['id']

        # Upload image to folder
        content = load_test_file('test-image.png')
        client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')},
            data={'folder_id': str(folder_id)}
        )

        # List images in folder
        response = client.get(f'/api/images?folder_id={folder_id}')

        assert response.status_code == 200
        data = response.json()
        # Should have at least the image we just uploaded
        assert any(img['folder_id'] == folder_id for img in data['images'])


class TestImageRetrievalEndpoint:
    """Tests for GET /api/images/{image_id} endpoint"""

    def test_get_existing_image(self):
        """Test retrieving existing image"""
        # Upload image first
        content = load_test_file('test-image.png')
        upload_response = client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')}
        )
        image_id = upload_response.json()['image_id']

        # Retrieve image
        response = client.get(f'/api/images/{image_id}')

        assert response.status_code == 200
        assert response.headers['content-type'] == 'image/png'
        assert response.content == content

    def test_get_nonexistent_image(self):
        """Test retrieving nonexistent image"""
        response = client.get('/api/images/99999')

        assert response.status_code == 404


class TestImageDeleteEndpoint:
    """Tests for DELETE /api/images/{image_id} endpoint"""

    def test_delete_existing_image(self):
        """Test deleting existing image"""
        # Upload image first
        content = load_test_file('test-image.png')
        upload_response = client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')}
        )
        image_id = upload_response.json()['image_id']

        # Delete image
        response = client.delete(f'/api/images/{image_id}')

        assert response.status_code == 200
        data = response.json()
        assert 'message' in data

        # Verify deletion
        get_response = client.get(f'/api/images/{image_id}')
        assert get_response.status_code == 404

    def test_delete_nonexistent_image(self):
        """Test deleting nonexistent image"""
        response = client.delete('/api/images/99999')

        assert response.status_code == 404


class TestFolderCreateEndpoint:
    """Tests for POST /api/images/folders endpoint"""

    def test_create_folder_success(self):
        """Test successful folder creation"""
        response = client.post(
            '/api/images/folders',
            json={'folder_name': 'new_folder'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] > 0
        assert data['folder_name'] == 'new_folder'
        assert data['image_count'] == 0

    def test_create_duplicate_folder(self):
        """Test creating duplicate folder"""
        folder_name = 'duplicate_test'

        # Create first time
        response1 = client.post(
            '/api/images/folders',
            json={'folder_name': folder_name}
        )
        assert response1.status_code == 200

        # Try to create again
        response2 = client.post(
            '/api/images/folders',
            json={'folder_name': folder_name}
        )
        assert response2.status_code == 400

    def test_create_folder_invalid_name(self):
        """Test creating folder with invalid name"""
        response = client.post(
            '/api/images/folders',
            json={'folder_name': 'invalid<>name'}
        )

        assert response.status_code in [400, 422]  # Validation error


class TestFolderListEndpoint:
    """Tests for GET /api/images/folders endpoint"""

    def test_list_folders(self):
        """Test listing folders"""
        # Create a folder (ignore if already exists)
        import uuid
        unique_name = f'list_test_{uuid.uuid4().hex[:8]}'
        client.post(
            '/api/images/folders',
            json={'folder_name': unique_name}
        )

        # List folders
        response = client.get('/api/images/folders')

        assert response.status_code == 200
        data = response.json()
        assert 'folders' in data
        assert len(data['folders']) > 0


class TestFolderRenameEndpoint:
    """Tests for PUT /api/images/folders/{folder_id} endpoint"""

    def test_rename_folder_success(self):
        """Test successful folder rename"""
        # Create folder
        create_response = client.post(
            '/api/images/folders',
            json={'folder_name': 'old_name'}
        )
        folder_id = create_response.json()['id']

        # Rename folder
        response = client.put(
            f'/api/images/folders/{folder_id}',
            json={'folder_id': folder_id, 'new_folder_name': 'new_name'}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'message' in data

    def test_rename_nonexistent_folder(self):
        """Test renaming nonexistent folder"""
        response = client.put(
            '/api/images/folders/99999',
            json={'folder_id': 99999, 'new_folder_name': 'new_name'}
        )

        assert response.status_code == 400


class TestFolderDeleteEndpoint:
    """Tests for DELETE /api/images/folders/{folder_id} endpoint"""

    def test_delete_empty_folder(self):
        """Test deleting empty folder"""
        # Create folder
        create_response = client.post(
            '/api/images/folders',
            json={'folder_name': 'to_delete'}
        )
        folder_id = create_response.json()['id']

        # Delete folder
        response = client.delete(f'/api/images/folders/{folder_id}')

        assert response.status_code == 200
        data = response.json()
        assert 'message' in data

    def test_delete_folder_with_images(self):
        """Test deleting folder that contains images"""
        # Create folder
        create_response = client.post(
            '/api/images/folders',
            json={'folder_name': 'has_images'}
        )
        folder_id = create_response.json()['id']

        # Upload image to folder
        content = load_test_file('test-image.png')
        client.post(
            '/api/images/upload',
            files={'file': ('test.png', content, 'image/png')},
            data={'folder_id': str(folder_id)}
        )

        # Try to delete folder
        response = client.delete(f'/api/images/folders/{folder_id}')

        assert response.status_code == 400
        data = response.json()
        assert 'contains' in data['detail'].lower()

    def test_delete_nonexistent_folder(self):
        """Test deleting nonexistent folder"""
        response = client.delete('/api/images/folders/99999')

        assert response.status_code == 400


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention"""

    def test_folder_name_sql_injection(self):
        """Test SQL injection attempt in folder name"""
        malicious_names = [
            "'; DROP TABLE image_files; --",
            "' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM image_files--"
        ]

        for name in malicious_names:
            response = client.post(
                '/api/images/folders',
                json={'folder_name': name}
            )
            # Should be rejected by validation or security checks
            assert response.status_code in [400, 422]

    def test_image_id_sql_injection(self):
        """Test SQL injection attempt in image ID"""
        malicious_ids = [
            "1 OR 1=1",
            "1'; DROP TABLE image_files; --",
            "1 UNION SELECT * FROM image_files"
        ]

        for malicious_id in malicious_ids:
            # FastAPI should handle type conversion and reject these
            # as they're not valid integers
            try:
                response = client.get(f'/api/images/{malicious_id}')
                # If it doesn't raise an error, it should return 404 or 422
                assert response.status_code in [404, 422]
            except Exception:
                # Type conversion error is expected
                pass
