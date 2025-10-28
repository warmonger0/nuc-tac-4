import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
import uuid
from core.data_models import ImageMetadata

# Supported image formats
SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']

# Base directory for image storage
IMAGES_DIR = Path(__file__).parent.parent / "images"


def get_supported_formats() -> List[str]:
    """Returns list of supported image formats."""
    return SUPPORTED_FORMATS


def validate_image_format(filename: str) -> bool:
    """
    Validates if the file has a supported image format.

    Args:
        filename: Name of the file to validate

    Returns:
        True if format is supported, False otherwise
    """
    file_ext = Path(filename).suffix.lower()
    return file_ext in SUPPORTED_FORMATS


def sanitize_folder_name(folder_name: str) -> str:
    """
    Sanitizes folder name to prevent directory traversal attacks.

    Args:
        folder_name: The folder name to sanitize

    Returns:
        Sanitized folder name
    """
    # Remove any path separators and special characters
    sanitized = folder_name.replace('/', '').replace('\\', '').replace('..', '')
    # Only allow alphanumeric, dash, underscore
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c in ['-', '_'])
    return sanitized or "default"


def initialize_image_database(conn: sqlite3.Connection) -> None:
    """
    Initializes the images and folders tables in the database.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Create images table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            folder TEXT NOT NULL,
            size INTEGER NOT NULL,
            format TEXT NOT NULL,
            created_at TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    """)

    # Create indexes for efficient querying
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_images_folder
        ON images(folder)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_images_created_at
        ON images(created_at)
    """)

    # Create folders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # Ensure default folder exists
    try:
        cursor.execute(
            "INSERT INTO folders (name, created_at) VALUES (?, ?)",
            ("default", datetime.now().isoformat())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Default folder already exists
        pass

    # Ensure images directory exists
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    default_folder_path = IMAGES_DIR / "default"
    default_folder_path.mkdir(exist_ok=True)


def save_image_to_disk(file_data: bytes, folder: str, filename: str) -> str:
    """
    Saves image file to disk.

    Args:
        file_data: Binary image data
        folder: Folder name to save the image in
        filename: Name of the file

    Returns:
        Absolute path to the saved file

    Raises:
        IOError: If unable to save file
    """
    folder = sanitize_folder_name(folder)
    folder_path = IMAGES_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    # Generate unique filename to avoid collisions
    file_ext = Path(filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = folder_path / unique_filename

    try:
        with open(file_path, 'wb') as f:
            f.write(file_data)
        return str(file_path)
    except Exception as e:
        raise IOError(f"Failed to save image: {str(e)}")


def save_image_metadata(conn: sqlite3.Connection, metadata: ImageMetadata) -> None:
    """
    Saves image metadata to database.

    Args:
        conn: SQLite database connection
        metadata: ImageMetadata object with image information
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO images (id, filename, folder, size, format, created_at, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        metadata.image_id,
        metadata.filename,
        metadata.folder,
        metadata.size,
        metadata.format,
        metadata.created_at.isoformat(),
        metadata.file_path
    ))
    conn.commit()


def get_images(conn: sqlite3.Connection, folder: Optional[str] = None) -> List[ImageMetadata]:
    """
    Retrieves images from database, optionally filtered by folder.

    Args:
        conn: SQLite database connection
        folder: Optional folder name to filter by

    Returns:
        List of ImageMetadata objects
    """
    cursor = conn.cursor()

    if folder:
        cursor.execute("""
            SELECT id, filename, folder, size, format, created_at, file_path
            FROM images
            WHERE folder = ?
            ORDER BY created_at DESC
        """, (folder,))
    else:
        cursor.execute("""
            SELECT id, filename, folder, size, format, created_at, file_path
            FROM images
            ORDER BY created_at DESC
        """)

    images = []
    for row in cursor.fetchall():
        images.append(ImageMetadata(
            image_id=row[0],
            filename=row[1],
            folder=row[2],
            size=row[3],
            format=row[4],
            created_at=datetime.fromisoformat(row[5]),
            file_path=row[6]
        ))

    return images


def get_image_by_id(conn: sqlite3.Connection, image_id: str) -> Optional[ImageMetadata]:
    """
    Retrieves a specific image by ID.

    Args:
        conn: SQLite database connection
        image_id: Image ID to retrieve

    Returns:
        ImageMetadata object or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, folder, size, format, created_at, file_path
        FROM images
        WHERE id = ?
    """, (image_id,))

    row = cursor.fetchone()
    if row:
        return ImageMetadata(
            image_id=row[0],
            filename=row[1],
            folder=row[2],
            size=row[3],
            format=row[4],
            created_at=datetime.fromisoformat(row[5]),
            file_path=row[6]
        )
    return None


def delete_image(conn: sqlite3.Connection, image_id: str) -> bool:
    """
    Deletes an image from database and filesystem.

    Args:
        conn: SQLite database connection
        image_id: Image ID to delete

    Returns:
        True if successful, False otherwise
    """
    # Get image metadata first
    image = get_image_by_id(conn, image_id)
    if not image:
        return False

    # Delete from filesystem
    try:
        file_path = Path(image.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        # Continue even if file deletion fails
        pass

    # Delete from database
    cursor = conn.cursor()
    cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
    conn.commit()

    return cursor.rowcount > 0


def create_folder(conn: sqlite3.Connection, folder_name: str) -> Tuple[bool, str]:
    """
    Creates a new folder in database and filesystem.

    Args:
        conn: SQLite database connection
        folder_name: Name of the folder to create

    Returns:
        Tuple of (success, message)
    """
    folder_name = sanitize_folder_name(folder_name)

    if not folder_name:
        return False, "Invalid folder name"

    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO folders (name, created_at) VALUES (?, ?)",
            (folder_name, datetime.now().isoformat())
        )
        conn.commit()

        # Create folder on filesystem
        folder_path = IMAGES_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        return True, f"Folder '{folder_name}' created successfully"
    except sqlite3.IntegrityError:
        return False, f"Folder '{folder_name}' already exists"
    except Exception as e:
        return False, f"Failed to create folder: {str(e)}"


def get_folders(conn: sqlite3.Connection) -> List[str]:
    """
    Retrieves all folder names from database.

    Args:
        conn: SQLite database connection

    Returns:
        List of folder names
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM folders ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def rename_folder(conn: sqlite3.Connection, old_name: str, new_name: str) -> Tuple[bool, str]:
    """
    Renames a folder in database and filesystem.

    Args:
        conn: SQLite database connection
        old_name: Current folder name
        new_name: New folder name

    Returns:
        Tuple of (success, message)
    """
    old_name = sanitize_folder_name(old_name)
    new_name = sanitize_folder_name(new_name)

    if not new_name:
        return False, "Invalid new folder name"

    if old_name == "default":
        return False, "Cannot rename default folder"

    cursor = conn.cursor()

    try:
        # Update folder name in database
        cursor.execute(
            "UPDATE folders SET name = ? WHERE name = ?",
            (new_name, old_name)
        )

        if cursor.rowcount == 0:
            return False, f"Folder '{old_name}' not found"

        # Update all images in this folder
        cursor.execute(
            "UPDATE images SET folder = ? WHERE folder = ?",
            (new_name, old_name)
        )

        conn.commit()

        # Rename folder on filesystem
        old_path = IMAGES_DIR / old_name
        new_path = IMAGES_DIR / new_name

        if old_path.exists():
            shutil.move(str(old_path), str(new_path))

        return True, f"Folder renamed from '{old_name}' to '{new_name}'"
    except sqlite3.IntegrityError:
        return False, f"Folder '{new_name}' already exists"
    except Exception as e:
        conn.rollback()
        return False, f"Failed to rename folder: {str(e)}"


def delete_folder(conn: sqlite3.Connection, folder_name: str) -> Tuple[bool, str]:
    """
    Deletes a folder and moves its images to the default folder.

    Args:
        conn: SQLite database connection
        folder_name: Name of the folder to delete

    Returns:
        Tuple of (success, message)
    """
    folder_name = sanitize_folder_name(folder_name)

    if folder_name == "default":
        return False, "Cannot delete default folder"

    cursor = conn.cursor()

    try:
        # Check if folder exists
        cursor.execute("SELECT name FROM folders WHERE name = ?", (folder_name,))
        if not cursor.fetchone():
            return False, f"Folder '{folder_name}' not found"

        # Move all images to default folder
        cursor.execute(
            "UPDATE images SET folder = 'default' WHERE folder = ?",
            (folder_name,)
        )

        image_count = cursor.rowcount

        # Delete folder from database
        cursor.execute("DELETE FROM folders WHERE name = ?", (folder_name,))

        conn.commit()

        # Move images on filesystem
        old_path = IMAGES_DIR / folder_name
        default_path = IMAGES_DIR / "default"

        if old_path.exists():
            # Move all files to default folder
            for file_path in old_path.iterdir():
                if file_path.is_file():
                    dest_path = default_path / file_path.name
                    shutil.move(str(file_path), str(dest_path))

            # Remove empty folder
            shutil.rmtree(old_path)

        return True, f"Folder '{folder_name}' deleted. {image_count} images moved to 'default' folder"
    except Exception as e:
        conn.rollback()
        return False, f"Failed to delete folder: {str(e)}"
