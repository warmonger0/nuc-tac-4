"""
Image hashing module for perceptual hash computation and duplicate detection.

This module provides functions to compute perceptual hashes (pHash) of images
and compare them for similarity detection. Uses DCT-based perceptual hashing
for rotation and scale invariance.
"""

import imagehash
from PIL import Image
from io import BytesIO
import sqlite3
from typing import List, Tuple, Optional


def compute_phash(image_data: bytes) -> str:
    """
    Compute perceptual hash of an image.

    Args:
        image_data: Raw image data as bytes

    Returns:
        Perceptual hash as hex string

    Raises:
        ValueError: If image data is invalid or cannot be processed
        IOError: If image cannot be opened
    """
    try:
        # Open image from bytes
        image = Image.open(BytesIO(image_data))

        # Load the image data to ensure it's fully decoded
        image.load()

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')

        # Compute perceptual hash using DCT-based algorithm
        phash = imagehash.phash(image, hash_size=8)

        # Return as hex string
        return str(phash)

    except Exception as e:
        raise ValueError(f"Failed to compute perceptual hash: {str(e)}")


def compare_hashes(hash1: str, hash2: str) -> float:
    """
    Compare two perceptual hashes and return similarity score.

    Args:
        hash1: First perceptual hash (hex string)
        hash2: Second perceptual hash (hex string)

    Returns:
        Similarity score from 0.0 (completely different) to 1.0 (identical)

    Raises:
        ValueError: If hashes are invalid format
    """
    try:
        # Parse hex strings back to hash objects
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)

        # Compute Hamming distance (number of different bits)
        distance = h1 - h2

        # Convert distance to similarity score
        # Hash size is 8x8 = 64 bits, so max distance is 64
        max_distance = 64
        similarity = 1.0 - (distance / max_distance)

        return similarity

    except Exception as e:
        raise ValueError(f"Failed to compare hashes: {str(e)}")


def compute_and_store_hash(conn: sqlite3.Connection, image_id: int, image_data: bytes) -> str:
    """
    Compute perceptual hash for an image and store it in the database.

    Args:
        conn: SQLite database connection
        image_id: ID of the image record
        image_data: Raw image data as bytes

    Returns:
        Computed perceptual hash as hex string

    Raises:
        ValueError: If hash computation fails
        sqlite3.Error: If database update fails
    """
    # Compute hash
    phash = compute_phash(image_data)

    # Store in database
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE images SET phash = ? WHERE id = ?",
        (phash, image_id)
    )
    conn.commit()

    return phash


def find_similar_images(
    conn: sqlite3.Connection,
    phash: str,
    folder: str,
    threshold: float = 0.95
) -> List[Tuple[int, str, str, float]]:
    """
    Find images in a folder with similar perceptual hashes.

    Args:
        conn: SQLite database connection
        phash: Perceptual hash to compare against
        folder: Folder name to search within
        threshold: Similarity threshold (0.0-1.0), default 0.95

    Returns:
        List of tuples (image_id, filename, phash, similarity_score)
        sorted by similarity (highest first)

    Raises:
        ValueError: If threshold is invalid
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")

    cursor = conn.cursor()

    # Query all images in the folder that have a phash
    cursor.execute(
        """
        SELECT id, filename, phash
        FROM images
        WHERE folder = ? AND phash IS NOT NULL
        """,
        (folder,)
    )

    similar_images = []

    # Compare each image's hash with the target hash
    for row in cursor.fetchall():
        image_id, filename, stored_hash = row

        try:
            similarity = compare_hashes(phash, stored_hash)

            # Only include images above the threshold
            if similarity >= threshold:
                similar_images.append((image_id, filename, stored_hash, similarity))

        except ValueError:
            # Skip images with invalid hashes
            continue

    # Sort by similarity (highest first)
    similar_images.sort(key=lambda x: x[3], reverse=True)

    return similar_images


def get_image_hash(conn: sqlite3.Connection, image_id: int) -> Optional[str]:
    """
    Retrieve the perceptual hash for an image from the database.

    Args:
        conn: SQLite database connection
        image_id: ID of the image record

    Returns:
        Perceptual hash as hex string, or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("SELECT phash FROM images WHERE id = ?", (image_id,))
    result = cursor.fetchone()
    return result[0] if result else None
