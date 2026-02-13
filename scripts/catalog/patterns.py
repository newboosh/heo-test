"""Pattern matching utilities for file classification."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Optional


def match_directory_pattern(file_path: str | Path, pattern: str) -> bool:
    """Match a file path against a directory glob pattern.

    Args:
        file_path: The file path to check (relative to project root).
        pattern: A glob pattern like "app/services/**" or "**/utils/**".

    Returns:
        True if the file path matches the pattern.
    """
    # Normalize the file path
    path_str = str(file_path).lstrip("./")
    pattern = pattern.lstrip("./")

    # Handle ** patterns with proper glob semantics
    if "**" in pattern:
        # Build a regex pattern manually for proper ** handling
        # ** matches zero or more directories
        parts = []
        segments = pattern.split("/")
        for seg in segments:
            if seg == "**":
                # Match zero or more directory levels
                parts.append("(?:.*/)?")
            else:
                # Convert glob wildcards to regex
                seg_re = seg.replace(".", r"\.")
                seg_re = seg_re.replace("*", "[^/]*")
                seg_re = seg_re.replace("?", "[^/]")
                parts.append(seg_re)

        # Join with / and anchor
        regex_pattern = "^" + "/".join(parts).replace("/(?:.*/)?/", "/(?:.*/)?")
        # Handle leading **
        if pattern.startswith("**/"):
            regex_pattern = "^(?:.*/)?".join(regex_pattern.split("^(?:.*/)?/", 1))

        try:
            return bool(re.match(regex_pattern, path_str))
        except re.error:
            return False

    # For patterns without **, use fnmatch but ensure * doesn't cross directory boundaries
    # Split both by / and match segment by segment
    path_parts = path_str.split("/")
    pattern_parts = pattern.split("/")

    if len(path_parts) != len(pattern_parts):
        return False

    for path_part, pattern_part in zip(path_parts, pattern_parts):
        if not fnmatch.fnmatch(path_part, pattern_part):
            return False

    return True


def match_filename_pattern(file_path: str | Path, pattern: str) -> bool:
    """Match a filename against a filename pattern.

    Args:
        file_path: The file path (uses only the filename part).
        pattern: A filename pattern like "test_*.py" or "Dockerfile*".

    Returns:
        True if the filename matches the pattern.
    """
    filename = Path(file_path).name
    return fnmatch.fnmatch(filename, pattern)


def _is_text_file(file_path: Path) -> bool:
    """Check if a file is likely a text file."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            # Check for null bytes (common in binary files)
            if b"\x00" in chunk:
                return False
            # Try to decode as UTF-8
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                return False
    except IOError:
        return False


def match_content_pattern(
    file_path: str | Path,
    pattern: str,
    filetypes: Optional[list[str]] = None,
    max_file_size: int = 1048576,
) -> bool:
    """Match file content against a regex pattern.

    Args:
        file_path: The file to check.
        pattern: A regex pattern to search for.
        filetypes: Optional list of file extensions to match (e.g., [".py", ".ts"]).
                   If None, matches any text file.
        max_file_size: Maximum file size to scan (default 1MB).

    Returns:
        True if the content matches the pattern.
    """
    file_path = Path(file_path)

    # Check filetype restriction (case-insensitive)
    if filetypes is not None:
        suffix = file_path.suffix.lower()
        filetypes_lower = [ft.lower() for ft in filetypes]
        if suffix not in filetypes_lower:
            return False

    # Check file exists and is a file
    if not file_path.is_file():
        return False

    # Check file size
    try:
        if file_path.stat().st_size > max_file_size:
            return False
    except OSError:
        return False

    # Check if it's a text file
    if not _is_text_file(file_path):
        return False

    # Read and match
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return bool(re.search(pattern, content))
    except (IOError, OSError):
        return False


def get_confidence_for_match(rule_type: str, pattern: str) -> str:
    """Determine confidence level for a pattern match.

    Args:
        rule_type: The type of rule (directory, filename, content, ast_content).
        pattern: The pattern that matched.

    Returns:
        Confidence level: "high", "medium", or "low".
    """
    if rule_type == "directory":
        return "high"

    if rule_type == "ast_content":
        return "high"

    if rule_type == "filename":
        return "medium"

    if rule_type == "content":
        # Longer, more specific patterns are higher confidence
        # Count the non-metacharacter content
        stripped = re.sub(r"[.*+?^${}()|[\]\\]", "", pattern)
        if len(stripped) >= 15:
            return "high"
        elif len(stripped) >= 8:
            return "medium"
        else:
            return "low"

    return "low"
