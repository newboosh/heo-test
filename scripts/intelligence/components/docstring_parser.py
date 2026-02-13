"""Docstring parser for Google-style docstrings.

Parses Google-style Python docstrings to extract:
- Summary
- Description
- Arguments
- Returns
- Raises
- Examples
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class DocstringInfo:
    """Parsed docstring information."""

    summary: Optional[str] = None
    """One-line summary."""

    description: Optional[str] = None
    """Extended description."""

    args: List[Dict[str, str]] = None
    """List of argument dicts with 'name' and 'description'."""

    returns: Optional[Dict[str, str]] = None
    """Return value info with 'type' and 'description'."""

    raises: List[Dict[str, str]] = None
    """List of exception dicts with 'exception' and 'description'."""

    examples: Optional[str] = None
    """Examples section as raw text."""

    def __post_init__(self):
        """Initialize list fields."""
        if self.args is None:
            self.args = []
        if self.raises is None:
            self.raises = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return asdict(self)


class DocstringParser:
    """Parse Google-style docstrings."""

    @staticmethod
    def parse(docstring: Optional[str]) -> DocstringInfo:
        """Parse Google-style docstring.

        Args:
            docstring: Raw docstring text.

        Returns:
            Parsed DocstringInfo object.
        """
        if not docstring:
            return DocstringInfo()

        lines = docstring.split('\n')
        info = DocstringInfo()

        # Extract summary (first non-empty line)
        info.summary = lines[0].strip() if lines else None

        # Split into sections
        sections = DocstringParser._split_sections(lines)

        # Parse each section
        for section_name, section_lines in sections.items():
            if section_name == "description":
                info.description = '\n'.join(section_lines).strip()
            elif section_name == "Args":
                info.args = DocstringParser._parse_args(section_lines)
            elif section_name == "Returns":
                info.returns = DocstringParser._parse_returns(section_lines)
            elif section_name == "Raises":
                info.raises = DocstringParser._parse_raises(section_lines)
            elif section_name == "Examples":
                info.examples = '\n'.join(section_lines).strip()

        return info

    @staticmethod
    def _split_sections(lines: List[str]) -> Dict[str, List[str]]:
        """Split docstring into sections.

        Args:
            lines: Docstring lines.

        Returns:
            Dict mapping section name to lines.
        """
        sections = {}
        current_section = "description"
        current_lines = []

        section_headers = {"Args", "Returns", "Raises", "Examples", "Note", "Warning"}

        for i, line in enumerate(lines):
            # Skip first line (summary)
            if i == 0:
                continue

            stripped = line.strip()

            # Check if this is a section header (with or without trailing colon)
            header = stripped[:-1] if stripped.endswith(':') else stripped
            if header in section_headers and (i + 1 < len(lines) or i == len(lines) - 1):
                # Save current section
                if current_lines or current_section != "description":
                    sections[current_section] = current_lines
                current_section = header
                current_lines = []
            else:
                current_lines.append(line)

        # Save last section
        if current_lines or current_section != "description":
            sections[current_section] = current_lines

        return sections

    @staticmethod
    def _parse_args(lines: List[str]) -> List[Dict[str, str]]:
        """Parse Args section.

        Args:
            lines: Lines from Args section.

        Returns:
            List of arg dicts with name and description.
        """
        args = []
        current_arg = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this is an argument definition
            match = re.match(r'^(\w+)\s*(\(.*?\))?\s*:\s*(.*)', stripped)
            if match:
                if current_arg:
                    args.append(current_arg)
                current_arg = {
                    "name": match.group(1),
                    "type": match.group(2) or "",
                    "description": match.group(3).strip()
                }
            elif current_arg:
                # Continuation of description
                current_arg["description"] += " " + stripped

        if current_arg:
            args.append(current_arg)

        return args

    @staticmethod
    def _parse_returns(lines: List[str]) -> Optional[Dict[str, str]]:
        """Parse Returns section.

        Args:
            lines: Lines from Returns section.

        Returns:
            Dict with type and description.
        """
        text = ' '.join(l.strip() for l in lines if l.strip())
        if not text:
            return None

        # Try to extract type and description
        match = re.match(r'(\w+|[\w\[\],\s]+):\s*(.*)', text)
        if match:
            return {
                "type": match.group(1).strip(),
                "description": match.group(2).strip()
            }

        return {"type": "", "description": text}

    @staticmethod
    def _parse_raises(lines: List[str]) -> List[Dict[str, str]]:
        """Parse Raises section.

        Args:
            lines: Lines from Raises section.

        Returns:
            List of exception dicts.
        """
        raises = []
        current_exception = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this is an exception definition
            match = re.match(r'^\s*(\w+Error|\w+Exception|\w+):\s*(.*)', stripped)
            if match:
                # Save previous
                if current_exception:
                    raises.append(current_exception)

                current_exception = {
                    "exception": match.group(1),
                    "description": match.group(2).strip()
                }
            elif current_exception:
                # Continuation
                current_exception["description"] += " " + stripped

        if current_exception:
            raises.append(current_exception)

        return raises
