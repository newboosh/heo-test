"""File classification engine."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from scripts.catalog.config import CatalogConfig, Rule
from scripts.catalog.patterns import (
    match_directory_pattern,
    match_filename_pattern,
    match_content_pattern,
    get_confidence_for_match,
)
from scripts.catalog.ast_analyzer import match_ast_condition


@dataclass
class ClassificationResult:
    """Result of directory classification including skipped files."""

    classifications: list["FileClassification"]
    skipped_count: int = 0
    skipped_files: list[str] = field(default_factory=list)


@dataclass
class FileClassification:
    """Classification result for a single file."""

    file_path: str  # Relative to project root
    primary_category: str
    categories: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    confidence: str = "low"


def _match_rule(
    rule: Rule,
    file_path: Path,
    relative_path: str,
    config: CatalogConfig,
) -> bool:
    """Check if a file matches a single rule."""
    if rule.type == "directory" and rule.pattern:
        return match_directory_pattern(relative_path, rule.pattern)

    elif rule.type == "filename" and rule.pattern:
        return match_filename_pattern(file_path, rule.pattern)

    elif rule.type == "content" and rule.pattern:
        return match_content_pattern(
            file_path,
            rule.pattern,
            filetypes=rule.filetypes,
            max_file_size=config.max_file_size,
        )

    elif rule.type == "ast_content" and rule.condition:
        return match_ast_condition(file_path, rule.condition)

    return False


def _get_rule_string(rule: Rule) -> str:
    """Get a string representation of a rule for matched_rules list."""
    if rule.type == "ast_content":
        return f"ast_content:{rule.condition}"
    return f"{rule.type}:{rule.pattern}"


def _get_highest_confidence(confidences: list[str]) -> str:
    """Get the highest confidence level from a list."""
    order = {"high": 3, "medium": 2, "low": 1}
    if not confidences:
        return "low"
    return max(confidences, key=lambda c: order.get(c, 0))


def classify_file(
    file_path: Path | str,
    root_dir: Path | str,
    config: CatalogConfig,
) -> FileClassification:
    """Classify a single file according to configuration rules.

    Args:
        file_path: Absolute path to the file.
        root_dir: Project root directory.
        config: Catalog configuration.

    Returns:
        FileClassification with category assignments.
    """
    file_path = Path(file_path)
    root_dir = Path(root_dir)

    # Get relative path
    try:
        relative_path = str(file_path.relative_to(root_dir))
    except ValueError:
        relative_path = str(file_path)

    matched_categories: list[tuple[str, str, str]] = []  # (category, rule_str, confidence)

    # Check each category's rules
    for category in config.classification.categories:
        for rule in category.rules:
            if _match_rule(rule, file_path, relative_path, config):
                rule_str = _get_rule_string(rule)
                confidence = get_confidence_for_match(rule.type, rule.pattern or rule.condition or "")
                matched_categories.append((category.name, rule_str, confidence))
                # Only count each category once (first matching rule)
                break

    if not matched_categories:
        # No matches - use default category
        return FileClassification(
            file_path=relative_path,
            primary_category=config.classification.default_category,
            categories=[config.classification.default_category],
            matched_rules=[],
            confidence="low",
        )

    # Extract unique categories preserving order
    categories = []
    matched_rules = []
    confidences = []
    seen = set()

    for cat, rule_str, conf in matched_categories:
        if cat not in seen:
            categories.append(cat)
            seen.add(cat)
        matched_rules.append(rule_str)
        confidences.append(conf)

    # Determine primary category using priority order
    priority_order = config.classification.priority_order
    if priority_order:
        # Find the highest priority category among matches
        for priority_cat in priority_order:
            if priority_cat in categories:
                primary = priority_cat
                break
        else:
            # No matching priority category, use first match
            primary = categories[0]
    else:
        primary = categories[0]

    return FileClassification(
        file_path=relative_path,
        primary_category=primary,
        categories=categories,
        matched_rules=matched_rules,
        confidence=_get_highest_confidence(confidences),
    )


def _should_skip_dir(dir_name: str, skip_dirs: list[str]) -> bool:
    """Check if a directory should be skipped."""
    return dir_name in skip_dirs or dir_name.startswith(".")


def _should_skip_file(file_path: Path) -> bool:
    """Check if a file should be skipped (e.g., hidden files)."""
    return file_path.name.startswith(".")


def classify_directory(
    root_dir: Path | str,
    config: CatalogConfig,
    index_dirs: Optional[list[str]] = None,
) -> ClassificationResult:
    """Classify all files in a directory tree.

    Args:
        root_dir: Project root directory.
        config: Catalog configuration.
        index_dirs: Specific directories to index. If None, uses config.index_dirs.

    Returns:
        ClassificationResult containing classifications and skipped file info.
    """
    root_dir = Path(root_dir)
    results: list[FileClassification] = []
    skipped_count = 0
    skipped_files: list[str] = []

    # Track visited inodes to detect circular symlinks
    visited_inodes: set[tuple[int, int]] = set()  # (device, inode) pairs

    # Determine which directories to scan
    dirs_to_scan = index_dirs or config.index_dirs

    # If "." is in dirs_to_scan, scan from root
    if "." in dirs_to_scan:
        scan_roots = [root_dir]
    else:
        scan_roots = [root_dir / d for d in dirs_to_scan if (root_dir / d).exists()]

    # If no configured dirs exist, scan from root
    if not scan_roots:
        scan_roots = [root_dir]

    for scan_root in scan_roots:
        for dirpath, dirnames, filenames in os.walk(scan_root, followlinks=config.follow_symlinks):
            current_dir = Path(dirpath)

            # Check for circular symlink on the directory itself
            if config.follow_symlinks:
                try:
                    dir_stat = current_dir.stat()
                    dir_inode = (dir_stat.st_dev, dir_stat.st_ino)
                    if dir_inode in visited_inodes:
                        # Circular symlink detected - skip this directory
                        rel_path = str(current_dir.relative_to(root_dir)) if current_dir != root_dir else "."
                        print(f"Warning: Circular symlink detected, skipping: {rel_path}", file=sys.stderr)
                        skipped_count += 1
                        skipped_files.append(rel_path)
                        dirnames[:] = []  # Don't descend into subdirs
                        continue
                    visited_inodes.add(dir_inode)
                except OSError:
                    pass  # If we can't stat, continue anyway

            # Filter out skip directories (modifying dirnames in place to prevent descent)
            dirnames[:] = [
                d for d in dirnames
                if not _should_skip_dir(d, config.skip_dirs)
            ]

            for filename in filenames:
                file_path = current_dir / filename

                # Skip hidden files
                if _should_skip_file(file_path):
                    continue

                # Skip symlinks if configured
                if file_path.is_symlink() and not config.follow_symlinks:
                    continue

                # Check for circular symlink on files when following symlinks
                if config.follow_symlinks and file_path.is_symlink():
                    try:
                        file_stat = file_path.stat()
                        file_inode = (file_stat.st_dev, file_stat.st_ino)
                        if file_inode in visited_inodes:
                            rel_path = str(file_path.relative_to(root_dir))
                            print(f"Warning: Circular symlink detected, skipping: {rel_path}", file=sys.stderr)
                            skipped_count += 1
                            skipped_files.append(rel_path)
                            continue
                        visited_inodes.add(file_inode)
                    except OSError:
                        pass  # If we can't stat, try to classify anyway

                try:
                    result = classify_file(file_path, root_dir, config)
                    results.append(result)
                except (IOError, OSError, UnicodeDecodeError, ValueError) as e:
                    # Graceful degradation - skip files that can't be classified
                    # IOError/OSError: file access issues
                    # UnicodeDecodeError: binary or non-UTF-8 files
                    # ValueError: path resolution issues
                    rel_path = str(file_path.relative_to(root_dir))
                    print(f"Warning: Skipping {rel_path}: {e}", file=sys.stderr)
                    skipped_count += 1
                    skipped_files.append(rel_path)
                    continue

    return ClassificationResult(
        classifications=results,
        skipped_count=skipped_count,
        skipped_files=skipped_files,
    )
