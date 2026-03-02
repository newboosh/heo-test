#!/usr/bin/env python3
"""backfill-frontmatter.py — Add description frontmatter to bare command files.

Usage:
    python3 scripts/backfill-frontmatter.py            # dry-run (show what would change)
    python3 scripts/backfill-frontmatter.py --write     # apply changes

Extracts description from the first paragraph after the H1 heading.
Skips files that already have frontmatter.
"""

import argparse
import os
import re
import sys

COMMANDS_DIR = os.path.join(os.path.dirname(__file__), "..", "commands")


def extract_description(content: str) -> str:
    """Extract a one-line description from the first paragraph after the H1."""
    lines = content.split("\n")
    # Find the H1 line
    h1_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            h1_idx = i
            break
    if h1_idx is None:
        return ""

    # Collect the first non-empty paragraph after H1
    para_lines = []
    started = False
    for line in lines[h1_idx + 1 :]:
        stripped = line.strip()
        if not started:
            if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
                started = True
                para_lines.append(stripped)
        else:
            if not stripped or stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("|") or stripped.startswith(">"):
                break
            para_lines.append(stripped)

    desc = " ".join(para_lines)
    # Truncate at ~120 chars on a word boundary
    if len(desc) > 120:
        desc = desc[:120].rsplit(" ", 1)[0]
        if not desc.endswith("."):
            desc = desc.rstrip(",;:") + "..."
    return desc


def has_frontmatter(content: str) -> bool:
    return content.startswith("---\n")


def add_frontmatter(content: str, description: str) -> str:
    safe_desc = description.replace('"', '\\"')
    return f'---\ndescription: "{safe_desc}"\n---\n\n{content}'


def main():
    parser = argparse.ArgumentParser(description="Backfill frontmatter on bare command files")
    parser.add_argument("--write", action="store_true", help="Apply changes (default: dry-run)")
    args = parser.parse_args()

    commands_dir = os.path.normpath(COMMANDS_DIR)
    if not os.path.isdir(commands_dir):
        print(f"ERROR: commands directory not found: {commands_dir}", file=sys.stderr)
        sys.exit(1)

    changed = 0
    skipped = 0

    for fname in sorted(os.listdir(commands_dir)):
        if not fname.endswith(".md"):
            continue

        fpath = os.path.join(commands_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        if has_frontmatter(content):
            skipped += 1
            continue

        desc = extract_description(content)
        if not desc:
            print(f"  WARN: no description extracted for {fname}", file=sys.stderr)
            desc = fname[:-3].replace("-", " ").title()

        name = fname[:-3]
        if args.write:
            new_content = add_frontmatter(content, desc)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  WROTE {name}: {desc}")
        else:
            print(f"  {name}: {desc}")
        changed += 1

    action = "Updated" if args.write else "Would update"
    print(f"\n{action} {changed} files, skipped {skipped} (already have frontmatter)")


if __name__ == "__main__":
    main()
