"""
Image security utilities for validating and securing image file uploads.
Provides functions for file type validation, magic number verification,
size checking, and filename sanitization.
"""

import re
from typing import Tuple

# Supported image file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Magic number signatures for file type validation
# Format: file_type -> (magic_bytes, offset)
MAGIC_NUMBERS = {
    'png': (b'\x89PNG\r\n\x1a\n', 0),
    'jpg': (b'\xff\xd8\xff', 0),
    'jpeg': (b'\xff\xd8\xff', 0),
    'gif': (b'GIF87a', 0),
    'gif89': (b'GIF89a', 0),
    'bmp': (b'BM', 0),
    'webp': (b'RIFF', 0),  # WebP has RIFF header
}

# Default maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


class ImageSecurityError(Exception):
    """Raised when image security validation fails."""
    pass


def validate_image_file(filename: str, file_content: bytes) -> Tuple[bool, str]:
    """
    Validate an image file by checking extension and magic numbers.

    Args:
        filename: Name of the file
        file_content: Binary content of the file

    Returns:
        Tuple[bool, str]: (is_valid, file_type or error_message)

    Raises:
        ImageSecurityError: If validation fails
    """
    # Check file extension
    file_extension = get_file_extension(filename)
    if not file_extension:
        raise ImageSecurityError("File has no extension")

    if file_extension not in ALLOWED_EXTENSIONS:
        raise ImageSecurityError(
            f"Unsupported file type: .{file_extension}. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Check magic number
    detected_type = check_magic_number(file_content)
    if not detected_type:
        raise ImageSecurityError(
            f"File does not appear to be a valid image. "
            f"Magic number check failed for .{file_extension} file"
        )

    # For JPEG files, accept both jpg and jpeg extensions
    if file_extension in ['jpg', 'jpeg'] and detected_type in ['jpg', 'jpeg']:
        return True, file_extension

    # For GIF, accept both GIF87a and GIF89a
    if file_extension == 'gif' and detected_type in ['gif', 'gif89']:
        return True, 'gif'

    # For other types, extension must match detected type
    if file_extension != detected_type and detected_type != 'webp_verified':
        raise ImageSecurityError(
            f"File extension .{file_extension} does not match file content ({detected_type})"
        )

    return True, file_extension


def get_file_extension(filename: str) -> str:
    """
    Extract and validate file extension from filename.

    Args:
        filename: Name of the file

    Returns:
        str: Lowercase file extension without dot
    """
    if '.' not in filename:
        return ""

    extension = filename.rsplit('.', 1)[1].lower()
    return extension


def check_magic_number(file_content: bytes) -> str:
    """
    Check file magic number to verify actual file type.

    Args:
        file_content: Binary content of the file

    Returns:
        str: Detected file type or empty string if not recognized
    """
    if not file_content or len(file_content) < 12:
        return ""

    # Check for PNG
    if file_content[:8] == MAGIC_NUMBERS['png'][0]:
        return 'png'

    # Check for JPEG
    if file_content[:3] == MAGIC_NUMBERS['jpg'][0]:
        return 'jpg'

    # Check for GIF87a
    if file_content[:6] == MAGIC_NUMBERS['gif'][0]:
        return 'gif'

    # Check for GIF89a
    if file_content[:6] == MAGIC_NUMBERS['gif89'][0]:
        return 'gif89'

    # Check for BMP
    if file_content[:2] == MAGIC_NUMBERS['bmp'][0]:
        return 'bmp'

    # Check for WebP (RIFF header + WEBP signature)
    if file_content[:4] == MAGIC_NUMBERS['webp'][0]:
        # WebP has "WEBP" at offset 8
        if len(file_content) >= 12 and file_content[8:12] == b'WEBP':
            return 'webp_verified'

    return ""


def check_file_size(file_size: int, max_size: int = MAX_FILE_SIZE) -> bool:
    """
    Check if file size is within acceptable limits.

    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes (default 10MB)

    Returns:
        bool: True if within limits

    Raises:
        ImageSecurityError: If file size exceeds limit
    """
    if file_size <= 0:
        raise ImageSecurityError("File is empty (0 bytes)")

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        raise ImageSecurityError(
            f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb:.0f}MB)"
        )

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and malicious filenames.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename

    Raises:
        ImageSecurityError: If filename is invalid
    """
    if not filename:
        raise ImageSecurityError("Filename cannot be empty")

    # Check for path traversal attempts before removing path
    if '..' in filename:
        raise ImageSecurityError("Filename cannot contain '..'")

    # Remove any path components
    filename = filename.replace('\\', '/').split('/')[-1]

    # Remove or replace potentially dangerous characters
    # Allow: alphanumeric, spaces, hyphens, underscores, periods
    if not re.match(r'^[a-zA-Z0-9\s._-]+$', filename):
        raise ImageSecurityError(
            "Filename contains invalid characters. "
            "Only alphanumeric, spaces, hyphens, underscores, and periods are allowed"
        )

    # Check filename length (typical filesystem limit is 255)
    if len(filename) > 255:
        raise ImageSecurityError("Filename is too long (maximum 255 characters)")

    # Check for hidden files
    if filename.startswith('.'):
        raise ImageSecurityError("Hidden files (starting with '.') are not allowed")

    # Ensure there's a valid extension
    if '.' not in filename:
        raise ImageSecurityError("Filename must have an extension")

    # Check for multiple extensions (e.g., file.jpg.exe)
    parts = filename.split('.')
    if len(parts) > 2:
        # Allow multiple dots in filename but only if the last part is the extension
        # and the rest are part of the name (e.g., my.file.name.jpg is OK)
        pass

    return filename


def detect_malicious_content(file_content: bytes, file_type: str) -> bool:
    """
    Perform basic detection of potentially malicious content in image files.

    Args:
        file_content: Binary content of the file
        file_type: Detected file type

    Returns:
        bool: True if file appears safe

    Raises:
        ImageSecurityError: If malicious content is detected
    """
    # Check for embedded scripts (basic check)
    # Look for common script tags that shouldn't be in binary image files
    dangerous_patterns = [
        b'<script',
        b'javascript:',
        b'<iframe',
        b'<embed',
        b'<object',
        b'<?php',
        b'<%',  # ASP/JSP
    ]

    file_content_lower = file_content.lower()

    for pattern in dangerous_patterns:
        if pattern in file_content_lower:
            raise ImageSecurityError(
                "File contains potentially malicious content (embedded scripts detected)"
            )

    # Check file size sanity
    if len(file_content) > MAX_FILE_SIZE:
        raise ImageSecurityError("File exceeds maximum size limit")

    return True
