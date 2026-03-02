#!/usr/bin/env python3
"""generate-help.py — Auto-generate commands/help.md from command/skill frontmatter.

Usage:
    python3 scripts/generate-help.py --generate   # write commands/help.md
    python3 scripts/generate-help.py --check       # exit 0 if up-to-date, 1 if stale
    python3 scripts/generate-help.py --diff        # show unified diff of changes

Requires: PyYAML (already in requirements.txt)
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from typing import Optional

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))

GUIDE_PATH = os.path.join(SCRIPT_DIR, "help-guide.yaml")
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, "commands")
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")
HEADER_PATH = os.path.join(PLUGIN_ROOT, "templates", "help-header.md")
FOOTER_PATH = os.path.join(PLUGIN_ROOT, "templates", "help-footer.md")
OUTPUT_PATH = os.path.join(COMMANDS_DIR, "help.md")

# Plugin namespace prefix — commands are invoked as /heo:<command> when used as a plugin
PLUGIN_PREFIX = "heo:"


# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a markdown file's content string.

    Falls back to regex-based extraction if YAML parsing fails (e.g., unquoted
    backticks).
    """
    content = content.replace("\r\n", "\n")
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        end = content.find("\n---", 4)
        if end == -1:
            return {}
    fm_text = content[4:end]
    try:
        fm = yaml.safe_load(fm_text)
        if isinstance(fm, dict):
            return fm
    except yaml.YAMLError:
        pass
    # Regex fallback for simple key: value pairs
    fm = {}
    for line in fm_text.split("\n"):
        m = re.match(r"^([a-z][a-z0-9_-]*)\s*:\s*(.+)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def extract_first_paragraph(content: str) -> str:
    """Fallback: extract first paragraph after the H1 heading."""
    lines = content.split("\n")
    h1_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            h1_idx = i
            break
    if h1_idx is None:
        return ""
    para_lines = []
    started = False
    for line in lines[h1_idx + 1:]:
        stripped = line.strip()
        if not started:
            if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
                started = True
                para_lines.append(stripped)
        else:
            if not stripped or stripped.startswith("#") or stripped.startswith("```"):
                break
            para_lines.append(stripped)
    return " ".join(para_lines)


# ---------------------------------------------------------------------------
# Source file resolution
# ---------------------------------------------------------------------------

def resolve_source(cmd_name: str) -> Optional[str]:
    """Find the source .md file for a registered command.

    Order: commands/<name>.md → skills/<name>/SKILL.md
    We check the actual source, not the symlink in .claude/commands/.
    """
    cmd_path = os.path.join(COMMANDS_DIR, f"{cmd_name}.md")
    if os.path.isfile(cmd_path):
        return cmd_path
    skill_path = os.path.join(SKILLS_DIR, cmd_name, "SKILL.md")
    if os.path.isfile(skill_path):
        return skill_path
    return None


# ---------------------------------------------------------------------------
# Entry building
# ---------------------------------------------------------------------------

def get_description(fm: dict, content: str) -> str:
    """Resolve description from frontmatter or fallback."""
    desc = fm.get("description", "")
    if not isinstance(desc, str):
        desc = str(desc) if desc is not None else ""
    desc = desc.strip().strip('"').strip("'")
    if not desc:
        desc = extract_first_paragraph(content)
    # Strip leading "Use this skill when..." preamble
    desc = re.sub(r"^Use this (?:skill|command) (?:when |to )", "", desc, flags=re.IGNORECASE)
    # Clean markdown artifacts for table display
    desc = re.sub(r"\*\*(.+?)\*\*", r"\1", desc)  # bold
    desc = re.sub(r"`(.+?)`", r"\1", desc)  # backticks
    # Capitalize first letter after cleanup
    if desc and desc[0].islower():
        desc = desc[0].upper() + desc[1:]
    # Truncate for table
    if len(desc) > 90:
        desc = desc[:90].rsplit(" ", 1)[0]
        if len(desc) > 90:
            desc = desc[:87]
        if not desc.endswith("."):
            desc = desc.rstrip(",;:") + "..."
    return desc


def prefix_usage(usage: str) -> str:
    """Add the plugin namespace prefix to command references in usage strings.

    Replaces `/command` with `/heo:command` inside backtick-delimited spans.
    """
    # Match backtick-wrapped command references like `/<cmd> ...`
    # Negative lookahead to avoid double-prefixing already-prefixed commands
    return re.sub(rf"`/(?!{re.escape(PLUGIN_PREFIX)})([a-z])", f"`/{PLUGIN_PREFIX}\\1", usage)


def get_usage(fm: dict, cmd_name: str) -> str:
    """Resolve usage string from frontmatter fields."""
    # 1. Explicit help-usage
    usage = fm.get("help-usage", "")
    if usage:
        return prefix_usage(str(usage).strip().strip('"').strip("'"))
    # 2. argument-hint (common in skills)
    hint = fm.get("argument-hint", "")
    if hint:
        hint = str(hint).strip().strip('"').strip("'")
        return f"`/{PLUGIN_PREFIX}{cmd_name} {hint}`"
    # 3. Bare command
    return f"`/{PLUGIN_PREFIX}{cmd_name}`"


def get_extra_rows(fm: dict) -> list[dict]:
    """Get additional table rows from help-extra-rows field."""
    extra = fm.get("help-extra-rows", [])
    if not isinstance(extra, list):
        return []
    rows = []
    for entry in extra:
        if isinstance(entry, dict) and "name" in entry:
            rows.append({
                "name": entry["name"],
                "description": entry.get("description", ""),
                "usage": str(entry.get("usage", "")).strip().strip('"').strip("'"),
            })
    return rows


# ---------------------------------------------------------------------------
# Registered commands
# ---------------------------------------------------------------------------

def get_registered_commands() -> set[str]:
    """Get all command names from source directories (excluding help).

    Scans commands/*.md and skills/*/SKILL.md rather than .claude/commands/
    symlinks, since those are created at runtime by the plugin installer.
    """
    names = set()
    # Commands
    if os.path.isdir(COMMANDS_DIR):
        for fname in os.listdir(COMMANDS_DIR):
            if fname.endswith(".md"):
                name = fname[:-3]
                if name != "help":
                    names.add(name)
    # Skills
    if os.path.isdir(SKILLS_DIR):
        for dname in os.listdir(SKILLS_DIR):
            skill_path = os.path.join(SKILLS_DIR, dname, "SKILL.md")
            if os.path.isfile(skill_path):
                names.add(dname)
    return names


# ---------------------------------------------------------------------------
# Table generation
# ---------------------------------------------------------------------------

def escape_pipe(text: str) -> str:
    """Escape bare pipe characters for markdown tables (skip already escaped)."""
    # Replace | that is NOT preceded by a backslash
    return re.sub(r"(?<!\\)\|", r"\\|", text)


def build_standard_table(commands: list[str]) -> list[str]:
    """Build a 3-column table (Command | Description | Usage)."""
    lines = [
        "| Command | Description | Usage |",
        "|---------|-------------|-------|",
    ]
    for cmd_name in commands:
        source = resolve_source(cmd_name)
        if source is None:
            print(f"  WARN: no source for '{cmd_name}', skipping", file=sys.stderr)
            continue

        with open(source, encoding="utf-8") as f:
            content = f.read()
        fm = parse_frontmatter(content)

        # Skip agent-only skills
        if fm.get("agent_only") is True:
            continue

        desc = get_description(fm, content)
        usage = get_usage(fm, cmd_name)

        lines.append(
            f"| `/{PLUGIN_PREFIX}{cmd_name}` | {escape_pipe(desc)} | {escape_pipe(usage)} |"
        )

        # Extra rows (e.g., /tree reset, /tree closedone)
        for extra in get_extra_rows(fm):
            extra_name = extra["name"]
            extra_desc = extra["description"]
            raw_usage = extra.get("usage")
            if raw_usage:
                extra_usage = prefix_usage(str(raw_usage).strip().strip('"').strip("'"))
            else:
                extra_usage = f"`/{PLUGIN_PREFIX}{extra_name}`"
            lines.append(
                f"| `/{PLUGIN_PREFIX}{extra_name}` | {escape_pipe(extra_desc)} | {escape_pipe(extra_usage)} |"
            )

    return lines


def build_compact_table(commands: list[str]) -> list[str]:
    """Build a 2-column table (Skill | Description) for agent support skills."""
    lines = [
        "| Skill | Description |",
        "|-------|-------------|",
    ]
    for cmd_name in commands:
        source = resolve_source(cmd_name)
        if source is None:
            print(f"  WARN: no source for '{cmd_name}', skipping", file=sys.stderr)
            continue

        with open(source, encoding="utf-8") as f:
            content = f.read()
        fm = parse_frontmatter(content)

        # Skip agent-only skills
        if fm.get("agent_only") is True:
            continue

        desc = get_description(fm, content)

        lines.append(f"| `/{PLUGIN_PREFIX}{cmd_name}` | {escape_pipe(desc)} |")

    return lines


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_help() -> str:
    """Generate the full help.md content."""
    # Load guide
    with open(GUIDE_PATH, encoding="utf-8") as f:
        guide = yaml.safe_load(f)

    # Load header and footer
    with open(HEADER_PATH, encoding="utf-8") as f:
        header = f.read().rstrip("\n")
    with open(FOOTER_PATH, encoding="utf-8") as f:
        footer = f.read()

    registered = get_registered_commands()

    # Track which commands are assigned to categories
    assigned = set(guide.get("hidden", []))

    sections = []
    for cat in guide["categories"]:
        cat_name = cat["name"]
        commands = cat.get("commands", [])
        compact = cat.get("compact", False)
        hidden = cat.get("hidden", False)

        if hidden:
            assigned.update(commands)
            continue

        assigned.update(commands)

        section_lines = [f"### {cat_name}", ""]
        if compact:
            section_lines.extend(build_compact_table(commands))
        else:
            section_lines.extend(build_standard_table(commands))

        sections.append("\n".join(section_lines))

    # Check for orphans (registered but not in any category)
    orphans = registered - assigned
    if orphans:
        print(f"  WARN: {len(orphans)} orphan command(s) not in any category: {', '.join(sorted(orphans))}", file=sys.stderr)

    # Assemble
    body = "\n\n".join(sections)
    return f"{header}\n\n{body}\n\n{footer}"


def main():
    parser = argparse.ArgumentParser(description="Generate commands/help.md from frontmatter")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true", help="Write commands/help.md")
    group.add_argument("--check", action="store_true", help="Exit 0 if up-to-date, 1 if stale")
    group.add_argument("--diff", action="store_true", help="Show unified diff")
    args = parser.parse_args()

    generated = generate_help()

    if args.generate:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(generated)
        # Count commands in output
        cmd_count = len(re.findall(r"`/(?:heo:)?[a-z][a-z0-9-]*`", generated))
        print(f"Generated {OUTPUT_PATH} ({cmd_count} command references)")
        return

    # Read current file
    if os.path.isfile(OUTPUT_PATH):
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            current = f.read()
    else:
        current = ""

    if args.check:
        if current == generated:
            registered = get_registered_commands()
            print(f"OK: help.md is up-to-date ({len(registered)} commands)")
            sys.exit(0)
        else:
            print("DRIFT DETECTED: commands/help.md is out of sync. Run: python3 scripts/generate-help.py --generate")
            sys.exit(1)

    if args.diff:
        current_lines = current.splitlines(keepends=True)
        generated_lines = generated.splitlines(keepends=True)
        diff = difflib.unified_diff(
            current_lines,
            generated_lines,
            fromfile="commands/help.md (current)",
            tofile="commands/help.md (generated)",
        )
        diff_text = "".join(diff)
        if diff_text:
            print(diff_text)
            sys.exit(1)
        else:
            print("No differences.")
            sys.exit(0)


if __name__ == "__main__":
    main()
