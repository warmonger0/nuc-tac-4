"""
Image processing utilities for handling image uploads, storage, and retrieval.
Provides functions for image metadata extraction, database operations,
and folder management.
"""

import sqlite3
import hashlib
import imghdr
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import logging

from core.sql_security import (
    execute_query_safely,
    validate_identifier,
    SQLSecurityError
)
from core.image_security import (
    validate_image_file,
    check_file_size,
    sanitize_filename,
    detect_malicious_content,
    ImageSecurityError
)

logger = logging.getLogger(__name__)


class ImageProcessorError(Exception):
    """Raised when image processing fails."""
    pass


def process_image_upload(
    file_content: bytes,
    original_filename: str,
    folder_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process an image upload with validation and metadata extraction.

    Args:
        file_content: Binary content of the image file
        original_filename: Original filename from upload
        folder_id: Optional folder ID to associate with image

    Returns:
        Dict containing processed image information

    Raises:
        ImageProcessorError: If processing fails
    """
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(original_filename)

        # Validate file size
        check_file_size(len(file_content))

        # Validate image file and get type
        is_valid, file_type = validate_image_file(safe_filename, file_content)

        # Check for malicious content
        detect_malicious_content(file_content, file_type)

        # Extract metadata
        metadata = extract_metadata(file_content, file_type)

        # Generate unique filename using hash
        file_hash = hashlib.md5(file_content).hexdigest()[:16]
        unique_filename = f"{file_hash}_{safe_filename}"

        return {
            'filename': unique_filename,
            'original_name': safe_filename,
            'file_type': file_type,
            'file_size': len(file_content),
            'folder_id': folder_id,
            'binary_data': file_content,
            'metadata': metadata
        }

    except (ImageSecurityError, ImageProcessorError) as e:
        raise ImageProcessorError(f"Image processing failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in process_image_upload: {str(e)}")
        raise ImageProcessorError(f"Unexpected error processing image: {str(e)}")


def extract_metadata(file_content: bytes, file_type: str) -> Dict[str, Any]:
    """
    Extract metadata from image file.

    Args:
        file_content: Binary content of the image
        file_type: Type of image file

    Returns:
        Dict containing metadata (dimensions, format, etc.)
    """
    metadata = {
        'format': file_type.upper(),
        'size_bytes': len(file_content)
    }

    # Use imghdr to detect image type
    detected_type = imghdr.what(None, h=file_content)
    if detected_type:
        metadata['detected_format'] = detected_type

    # Note: For dimensions, we would need PIL/Pillow which is not in std lib
    # For v1, we'll skip dimensions to maintain "std libraries only" requirement
    # This can be added in future with Pillow

    return metadata


def save_image_to_db(
    conn: sqlite3.Connection,
    image_data: Dict[str, Any]
) -> int:
    """
    Save image binary data and metadata to database.

    Args:
        conn: SQLite connection object
        image_data: Dictionary containing image data from process_image_upload

    Returns:
        int: ID of the inserted image record

    Raises:
        ImageProcessorError: If database operation fails
    """
    try:
        # Validate folder_id if provided
        if image_data.get('folder_id'):
            folder = get_folder_by_id(conn, image_data['folder_id'])
            if not folder:
                raise ImageProcessorError(f"Folder with ID {image_data['folder_id']} does not exist")

        # Insert image record
        cursor = execute_query_safely(
            conn,
            """
            INSERT INTO image_files (
                filename, original_name, file_type, file_size,
                folder_id, upload_date, binary_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            params=(
                image_data['filename'],
                image_data['original_name'],
                image_data['file_type'],
                image_data['file_size'],
                image_data.get('folder_id'),
                datetime.now(),
                image_data['binary_data']
            )
        )

        conn.commit()
        image_id = cursor.lastrowid
        logger.info(f"Image saved to database: ID={image_id}, filename={image_data['original_name']}")

        return image_id

    except SQLSecurityError as e:
        raise ImageProcessorError(f"Security validation failed: {str(e)}")
    except sqlite3.Error as e:
        raise ImageProcessorError(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in save_image_to_db: {str(e)}")
        raise ImageProcessorError(f"Failed to save image: {str(e)}")


def get_image_by_id(conn: sqlite3.Connection, image_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve image data by ID.

    Args:
        conn: SQLite connection object
        image_id: ID of the image to retrieve

    Returns:
        Dict containing image data or None if not found
    """
    try:
        cursor = execute_query_safely(
            conn,
            """
            SELECT
                id, filename, original_name, file_type, file_size,
                folder_id, upload_date, binary_data
            FROM image_files
            WHERE id = ?
            """,
            params=(image_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'filename': row[1],
            'original_name': row[2],
            'file_type': row[3],
            'file_size': row[4],
            'folder_id': row[5],
            'upload_date': row[6],
            'binary_data': row[7]
        }

    except Exception as e:
        logger.error(f"Error retrieving image {image_id}: {str(e)}")
        return None


def list_images_by_folder(
    conn: sqlite3.Connection,
    folder_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List images, optionally filtered by folder.

    Args:
        conn: SQLite connection object
        folder_id: Optional folder ID to filter by
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of image metadata dictionaries
    """
    try:
        if folder_id is not None:
            cursor = execute_query_safely(
                conn,
                """
                SELECT
                    i.id, i.filename, i.original_name, i.file_type, i.file_size,
                    i.folder_id, i.upload_date, f.folder_name
                FROM image_files i
                LEFT JOIN image_folders f ON i.folder_id = f.id
                WHERE i.folder_id = ?
                ORDER BY i.upload_date DESC
                LIMIT ? OFFSET ?
                """,
                params=(folder_id, limit, offset)
            )
        else:
            cursor = execute_query_safely(
                conn,
                """
                SELECT
                    i.id, i.filename, i.original_name, i.file_type, i.file_size,
                    i.folder_id, i.upload_date, f.folder_name
                FROM image_files i
                LEFT JOIN image_folders f ON i.folder_id = f.id
                ORDER BY i.upload_date DESC
                LIMIT ? OFFSET ?
                """,
                params=(limit, offset)
            )

        rows = cursor.fetchall()
        images = []

        for row in rows:
            images.append({
                'id': row[0],
                'filename': row[1],
                'original_name': row[2],
                'file_type': row[3],
                'file_size': row[4],
                'folder_id': row[5],
                'upload_date': row[6],
                'folder_name': row[7] if len(row) > 7 else None
            })

        return images

    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        return []


def delete_image(conn: sqlite3.Connection, image_id: int) -> bool:
    """
    Delete an image from the database.

    Args:
        conn: SQLite connection object
        image_id: ID of the image to delete

    Returns:
        bool: True if deleted successfully
    """
    try:
        cursor = execute_query_safely(
            conn,
            "DELETE FROM image_files WHERE id = ?",
            params=(image_id,)
        )

        conn.commit()
        deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Image deleted: ID={image_id}")

        return deleted

    except Exception as e:
        logger.error(f"Error deleting image {image_id}: {str(e)}")
        return False


# Folder management functions

def create_folder(conn: sqlite3.Connection, folder_name: str) -> int:
    """
    Create a new image folder.

    Args:
        conn: SQLite connection object
        folder_name: Name of the folder to create

    Returns:
        int: ID of the created folder

    Raises:
        ImageProcessorError: If folder creation fails
    """
    try:
        # Validate folder name (similar to table name validation)
        validate_identifier(folder_name, "folder")

        # Check if folder already exists
        cursor = execute_query_safely(
            conn,
            "SELECT id FROM image_folders WHERE folder_name = ?",
            params=(folder_name,)
        )

        if cursor.fetchone():
            raise ImageProcessorError(f"Folder '{folder_name}' already exists")

        # Create folder
        cursor = execute_query_safely(
            conn,
            """
            INSERT INTO image_folders (folder_name, created_at, updated_at)
            VALUES (?, ?, ?)
            """,
            params=(folder_name, datetime.now(), datetime.now())
        )

        conn.commit()
        folder_id = cursor.lastrowid
        logger.info(f"Folder created: ID={folder_id}, name={folder_name}")

        return folder_id

    except SQLSecurityError as e:
        raise ImageProcessorError(f"Invalid folder name: {str(e)}")
    except sqlite3.IntegrityError:
        raise ImageProcessorError(f"Folder '{folder_name}' already exists")
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        raise ImageProcessorError(f"Failed to create folder: {str(e)}")


def get_folder_by_id(conn: sqlite3.Connection, folder_id: int) -> Optional[Dict[str, Any]]:
    """
    Get folder information by ID.

    Args:
        conn: SQLite connection object
        folder_id: ID of the folder

    Returns:
        Dict containing folder data or None if not found
    """
    try:
        cursor = execute_query_safely(
            conn,
            """
            SELECT id, folder_name, created_at, updated_at
            FROM image_folders
            WHERE id = ?
            """,
            params=(folder_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'folder_name': row[1],
            'created_at': row[2],
            'updated_at': row[3]
        }

    except Exception as e:
        logger.error(f"Error getting folder {folder_id}: {str(e)}")
        return None


def list_all_folders(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    List all folders with image counts.

    Args:
        conn: SQLite connection object

    Returns:
        List of folder data dictionaries with image counts
    """
    try:
        cursor = execute_query_safely(
            conn,
            """
            SELECT
                f.id,
                f.folder_name,
                f.created_at,
                f.updated_at,
                COUNT(i.id) as image_count
            FROM image_folders f
            LEFT JOIN image_files i ON f.id = i.folder_id
            GROUP BY f.id, f.folder_name, f.created_at, f.updated_at
            ORDER BY f.folder_name
            """
        )

        rows = cursor.fetchall()
        folders = []

        for row in rows:
            folders.append({
                'id': row[0],
                'folder_name': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'image_count': row[4]
            })

        return folders

    except Exception as e:
        logger.error(f"Error listing folders: {str(e)}")
        return []


def rename_folder(conn: sqlite3.Connection, folder_id: int, new_name: str) -> bool:
    """
    Rename an existing folder.

    Args:
        conn: SQLite connection object
        folder_id: ID of the folder to rename
        new_name: New name for the folder

    Returns:
        bool: True if renamed successfully

    Raises:
        ImageProcessorError: If rename fails
    """
    try:
        # Validate new folder name
        validate_identifier(new_name, "folder")

        # Check if folder exists
        folder = get_folder_by_id(conn, folder_id)
        if not folder:
            raise ImageProcessorError(f"Folder with ID {folder_id} does not exist")

        # Check if new name already exists
        cursor = execute_query_safely(
            conn,
            "SELECT id FROM image_folders WHERE folder_name = ? AND id != ?",
            params=(new_name, folder_id)
        )

        if cursor.fetchone():
            raise ImageProcessorError(f"Folder '{new_name}' already exists")

        # Rename folder
        execute_query_safely(
            conn,
            """
            UPDATE image_folders
            SET folder_name = ?, updated_at = ?
            WHERE id = ?
            """,
            params=(new_name, datetime.now(), folder_id)
        )

        conn.commit()
        logger.info(f"Folder renamed: ID={folder_id}, old={folder['folder_name']}, new={new_name}")

        return True

    except SQLSecurityError as e:
        raise ImageProcessorError(f"Invalid folder name: {str(e)}")
    except ImageProcessorError:
        raise
    except Exception as e:
        logger.error(f"Error renaming folder: {str(e)}")
        raise ImageProcessorError(f"Failed to rename folder: {str(e)}")


def delete_folder(conn: sqlite3.Connection, folder_id: int) -> bool:
    """
    Delete a folder if it contains no images.

    Args:
        conn: SQLite connection object
        folder_id: ID of the folder to delete

    Returns:
        bool: True if deleted successfully

    Raises:
        ImageProcessorError: If folder contains images or deletion fails
    """
    try:
        # Check if folder exists
        folder = get_folder_by_id(conn, folder_id)
        if not folder:
            raise ImageProcessorError(f"Folder with ID {folder_id} does not exist")

        # Check if folder contains images
        cursor = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM image_files WHERE folder_id = ?",
            params=(folder_id,)
        )

        image_count = cursor.fetchone()[0]
        if image_count > 0:
            raise ImageProcessorError(
                f"Cannot delete folder '{folder['folder_name']}' because it contains {image_count} image(s). "
                f"Please delete or move the images first."
            )

        # Delete folder
        execute_query_safely(
            conn,
            "DELETE FROM image_folders WHERE id = ?",
            params=(folder_id,)
        )

        conn.commit()
        logger.info(f"Folder deleted: ID={folder_id}, name={folder['folder_name']}")

        return True

    except ImageProcessorError:
        raise
    except Exception as e:
        logger.error(f"Error deleting folder: {str(e)}")
        raise ImageProcessorError(f"Failed to delete folder: {str(e)}")
