"""Tests for image security module"""

import pytest
import os
from core.image_security import (
    validate_image_file,
    get_file_extension,
    check_magic_number,
    check_file_size,
    sanitize_filename,
    detect_malicious_content,
    ImageSecurityError,
    MAX_FILE_SIZE
)

# Test asset paths
TEST_ASSETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')


def load_test_file(filename: str) -> bytes:
    """Load a test file"""
    path = os.path.join(TEST_ASSETS_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()


class TestValidateImageFile:
    """Tests for validate_image_file function"""

    def test_valid_png(self):
        """Test validation of valid PNG file"""
        content = load_test_file('test-image.png')
        is_valid, file_type = validate_image_file('test.png', content)
        assert is_valid is True
        assert file_type == 'png'

    def test_valid_jpg(self):
        """Test validation of valid JPG file"""
        content = load_test_file('test-image.jpg')
        is_valid, file_type = validate_image_file('test.jpg', content)
        assert is_valid is True
        assert file_type == 'jpg'

    def test_valid_jpeg(self):
        """Test validation of JPEG extension"""
        content = load_test_file('test-image.jpg')
        is_valid, file_type = validate_image_file('test.jpeg', content)
        assert is_valid is True
        assert file_type == 'jpeg'

    def test_valid_gif(self):
        """Test validation of valid GIF file"""
        content = load_test_file('test-image.gif')
        is_valid, file_type = validate_image_file('test.gif', content)
        assert is_valid is True
        assert file_type == 'gif'

    def test_valid_bmp(self):
        """Test validation of valid BMP file"""
        content = load_test_file('test-image.bmp')
        is_valid, file_type = validate_image_file('test.bmp', content)
        assert is_valid is True
        assert file_type == 'bmp'

    def test_valid_webp(self):
        """Test validation of valid WebP file"""
        content = load_test_file('test-image.webp')
        is_valid, file_type = validate_image_file('test.webp', content)
        assert is_valid is True
        assert file_type == 'webp'

    def test_invalid_extension(self):
        """Test rejection of invalid file extension"""
        content = load_test_file('invalid-image.txt')
        with pytest.raises(ImageSecurityError, match="Unsupported file type"):
            validate_image_file('test.txt', content)

    def test_no_extension(self):
        """Test rejection of file with no extension"""
        content = b'some data'
        with pytest.raises(ImageSecurityError, match="File has no extension"):
            validate_image_file('test', content)

    def test_fake_image_extension(self):
        """Test rejection of file with fake extension"""
        content = load_test_file('fake-image.jpg')
        with pytest.raises(ImageSecurityError, match="Magic number check failed"):
            validate_image_file('fake-image.jpg', content)


class TestGetFileExtension:
    """Tests for get_file_extension function"""

    def test_png_extension(self):
        """Test extraction of PNG extension"""
        assert get_file_extension('test.png') == 'png'

    def test_jpg_extension(self):
        """Test extraction of JPG extension"""
        assert get_file_extension('test.jpg') == 'jpg'

    def test_uppercase_extension(self):
        """Test that extension is lowercased"""
        assert get_file_extension('test.PNG') == 'png'

    def test_no_extension(self):
        """Test file with no extension"""
        assert get_file_extension('test') == ''

    def test_multiple_dots(self):
        """Test file with multiple dots"""
        assert get_file_extension('my.file.name.jpg') == 'jpg'


class TestCheckMagicNumber:
    """Tests for check_magic_number function"""

    def test_png_magic_number(self):
        """Test PNG magic number detection"""
        content = load_test_file('test-image.png')
        assert check_magic_number(content) == 'png'

    def test_jpg_magic_number(self):
        """Test JPG magic number detection"""
        content = load_test_file('test-image.jpg')
        assert check_magic_number(content) == 'jpg'

    def test_gif_magic_number(self):
        """Test GIF magic number detection"""
        content = load_test_file('test-image.gif')
        assert check_magic_number(content) in ['gif', 'gif89']

    def test_bmp_magic_number(self):
        """Test BMP magic number detection"""
        content = load_test_file('test-image.bmp')
        assert check_magic_number(content) == 'bmp'

    def test_webp_magic_number(self):
        """Test WebP magic number detection"""
        content = load_test_file('test-image.webp')
        assert check_magic_number(content) == 'webp_verified'

    def test_invalid_magic_number(self):
        """Test that invalid data returns empty string"""
        content = b'not an image'
        assert check_magic_number(content) == ''

    def test_empty_content(self):
        """Test that empty content returns empty string"""
        assert check_magic_number(b'') == ''


class TestCheckFileSize:
    """Tests for check_file_size function"""

    def test_valid_size(self):
        """Test that valid size passes"""
        assert check_file_size(1024) is True

    def test_max_size(self):
        """Test that max size passes"""
        assert check_file_size(MAX_FILE_SIZE) is True

    def test_over_max_size(self):
        """Test that oversized file is rejected"""
        with pytest.raises(ImageSecurityError, match="exceeds maximum allowed size"):
            check_file_size(MAX_FILE_SIZE + 1)

    def test_zero_size(self):
        """Test that zero size file is rejected"""
        with pytest.raises(ImageSecurityError, match="File is empty"):
            check_file_size(0)

    def test_negative_size(self):
        """Test that negative size is rejected"""
        with pytest.raises(ImageSecurityError, match="File is empty"):
            check_file_size(-1)


class TestSanitizeFilename:
    """Tests for sanitize_filename function"""

    def test_valid_filename(self):
        """Test that valid filename passes"""
        assert sanitize_filename('test.png') == 'test.png'

    def test_filename_with_spaces(self):
        """Test filename with spaces"""
        assert sanitize_filename('my file.png') == 'my file.png'

    def test_filename_with_hyphens(self):
        """Test filename with hyphens"""
        assert sanitize_filename('my-file.png') == 'my-file.png'

    def test_filename_with_underscores(self):
        """Test filename with underscores"""
        assert sanitize_filename('my_file.png') == 'my_file.png'

    def test_path_traversal_attempt(self):
        """Test that path traversal is blocked"""
        with pytest.raises(ImageSecurityError, match="cannot contain"):
            sanitize_filename('../test.png')

    def test_invalid_characters(self):
        """Test that invalid characters are rejected"""
        with pytest.raises(ImageSecurityError, match="contains invalid characters"):
            sanitize_filename('test<>.png')

    def test_empty_filename(self):
        """Test that empty filename is rejected"""
        with pytest.raises(ImageSecurityError, match="cannot be empty"):
            sanitize_filename('')

    def test_hidden_file(self):
        """Test that hidden files are rejected"""
        with pytest.raises(ImageSecurityError, match="Hidden files"):
            sanitize_filename('.hidden.png')

    def test_no_extension(self):
        """Test that file without extension is rejected"""
        with pytest.raises(ImageSecurityError, match="must have an extension"):
            sanitize_filename('test')

    def test_long_filename(self):
        """Test that very long filename is rejected"""
        long_name = 'a' * 300 + '.png'
        with pytest.raises(ImageSecurityError, match="too long"):
            sanitize_filename(long_name)

    def test_path_in_filename(self):
        """Test that path is stripped from filename"""
        assert sanitize_filename('path/to/file.png') == 'file.png'

    def test_windows_path_in_filename(self):
        """Test that Windows path is stripped"""
        assert sanitize_filename('C:\\path\\to\\file.png') == 'file.png'


class TestDetectMaliciousContent:
    """Tests for detect_malicious_content function"""

    def test_clean_png_content(self):
        """Test that clean PNG content passes"""
        content = load_test_file('test-image.png')
        assert detect_malicious_content(content, 'png') is True

    def test_clean_jpg_content(self):
        """Test that clean JPG content passes"""
        content = load_test_file('test-image.jpg')
        assert detect_malicious_content(content, 'jpg') is True

    def test_script_tag_detection(self):
        """Test that embedded script tag is detected"""
        content = b'<script>alert("xss")</script>'
        with pytest.raises(ImageSecurityError, match="malicious content"):
            detect_malicious_content(content, 'png')

    def test_javascript_detection(self):
        """Test that javascript: is detected"""
        content = b'javascript:void(0)'
        with pytest.raises(ImageSecurityError, match="malicious content"):
            detect_malicious_content(content, 'png')

    def test_iframe_detection(self):
        """Test that iframe tag is detected"""
        content = b'<iframe src="evil.com"></iframe>'
        with pytest.raises(ImageSecurityError, match="malicious content"):
            detect_malicious_content(content, 'png')

    def test_php_detection(self):
        """Test that PHP code is detected"""
        content = b'<?php echo "evil"; ?>'
        with pytest.raises(ImageSecurityError, match="malicious content"):
            detect_malicious_content(content, 'png')

    def test_oversized_content(self):
        """Test that oversized content is rejected"""
        content = b'x' * (MAX_FILE_SIZE + 1)
        with pytest.raises(ImageSecurityError, match="exceeds maximum size"):
            detect_malicious_content(content, 'png')

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive"""
        content = b'<SCRIPT>alert("xss")</SCRIPT>'
        with pytest.raises(ImageSecurityError, match="malicious content"):
            detect_malicious_content(content, 'png')
