"""File hashing utilities for content-based change detection.

Provides SHA-256 hashing for efficient incremental build caching.
"""

import hashlib
from pathlib import Path
from typing import Optional


def compute_file_hash(file_path: str) -> Optional[str]:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file.

    Returns:
        Hexadecimal SHA-256 hash or None if file not found.
    """
    try:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (FileNotFoundError, IOError):
        return None


def compute_string_hash(content: str) -> str:
    """Compute SHA-256 hash of string content.

    Args:
        content: String content.

    Returns:
        Hexadecimal SHA-256 hash.
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def compute_dict_hash(data: dict) -> str:
    """Compute SHA-256 hash of dictionary (JSON representation).

    Args:
        data: Dictionary to hash.

    Returns:
        Hexadecimal SHA-256 hash.
    """
    import json
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return compute_string_hash(json_str)


def compute_directory_hash(directory: str) -> Optional[str]:
    """Compute combined hash of all files in directory.

    Hashes files in sorted order for deterministic results.

    Args:
        directory: Path to directory.

    Returns:
        Hexadecimal SHA-256 hash or None if directory not found.
    """
    try:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return None

        sha256 = hashlib.sha256()

        # Hash all files in sorted order (include paths to detect renames)
        for file_path in sorted(dir_path.rglob('*')):
            if file_path.is_file():
                try:
                    # Include relative path to detect file renames
                    rel_path = str(file_path.relative_to(dir_path))
                    sha256.update(rel_path.encode('utf-8'))
                    file_hash = compute_file_hash(str(file_path))
                    if file_hash:
                        sha256.update(file_hash.encode('utf-8'))
                except (IOError, OSError):
                    pass

        return sha256.hexdigest()
    except (FileNotFoundError, OSError):
        return None


def verify_hash(file_path: str, expected_hash: str) -> bool:
    """Verify file hash matches expected value.

    Args:
        file_path: Path to file.
        expected_hash: Expected SHA-256 hash.

    Returns:
        True if hash matches.
    """
    actual_hash = compute_file_hash(file_path)
    return actual_hash == expected_hash if actual_hash else False
