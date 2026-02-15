#!/usr/bin/env python3
"""
Sentinel Patterns - Shared pattern definitions for emerging issue detection.

Used by:
  - hooks/sentinel-detect.py (auto-detection hook)
  - agents/sentinel.md (consolidation agent reference)

Patterns detect code that should not ship: temporary implementations,
debug artifacts, hardcoded values, incomplete work, and disconnection
markers. Each pattern has a type, severity, and suggested action.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SentinelPattern:
    """A single detection pattern for emerging issue scanning.

    Each pattern has a set of regex markers that are compiled on init.
    Use scan_line() to check individual lines against this pattern.

    Args:
        name: Unique identifier for the pattern (e.g., "todo_marker").
        issue_type: Category — bug, debt, mock, disconnected, workaround,
            temporary, or debug.
        severity: How serious — critical, important, minor, or note.
        markers: List of regex strings to match against.
        action: Suggested remediation action.
        description: Human-readable explanation of what this pattern detects.
    """

    name: str
    issue_type: str
    severity: str
    markers: List[str]
    action: str
    description: str
    _compiled: List[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Compile regex markers into pattern objects."""
        self._compiled = []
        for marker in self.markers:
            try:
                self._compiled.append(re.compile(marker, re.IGNORECASE))
            except re.error as exc:
                import sys

                print(
                    f"sentinel: regex compile failed for {marker!r}: {exc}, using escaped literal",
                    file=sys.stderr,
                )
                self._compiled.append(re.compile(re.escape(marker), re.IGNORECASE))

    def scan_line(self, line: str, line_num: int) -> Optional[dict]:
        """Check a single line against this pattern.

        Args:
            line: The source line to scan.
            line_num: The 1-based line number in the file.

        Returns:
            A finding dict with keys (pattern, type, severity, line, matched,
            marker, action, context) if a match is found, or None.
        """
        for i, pattern in enumerate(self._compiled):
            match = pattern.search(line)
            if match:
                return {
                    "pattern": self.name,
                    "type": self.issue_type,
                    "severity": self.severity,
                    "line": line_num,
                    "matched": match.group(0),
                    "marker": self.markers[i],
                    "action": self.action,
                    "context": line.strip(),
                }
        return None


# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

SENTINEL_PATTERNS: List[SentinelPattern] = [
    # --- Temporary Code ---
    SentinelPattern(
        name="todo_marker",
        issue_type="temporary",
        severity="minor",
        markers=[
            r"\bTODO\b",
            r"\bFIXME\b",
            r"\bHACK\b",
            r"\bXXX\b",
            r"\bREMOVEME\b",
        ],
        action="Address or create a ticket before shipping",
        description="TODO/FIXME markers indicating incomplete work",
    ),
    SentinelPattern(
        name="temporary_marker",
        issue_type="temporary",
        severity="important",
        markers=[
            r"\bTEMP\b(?:ORARY)?",
            r"\bPLACEHOLDER\b",
            r"\bSTUB\b",
            r"#\s*temporary",
            r"#\s*remove\s+(before|after|this)",
        ],
        action="Replace with permanent implementation",
        description="Explicit temporary/placeholder markers",
    ),
    SentinelPattern(
        name="mock_marker",
        issue_type="mock",
        severity="important",
        markers=[
            r"\bMOCK\b(?!test|spec|_test)",
            r"\bFAKE\b(?!test|spec|_test)",
            r"\bdummy[_\s](?:data|value|response|token|key|secret)",
            r"(?<!\w)mock_(?:response|data|result|value|api)",
            r"(?<!\w)fake_(?:response|data|result|value|api)",
        ],
        action="Replace mock with real implementation",
        description="Mock/fake implementations outside test files",
    ),
    SentinelPattern(
        name="workaround_marker",
        issue_type="workaround",
        severity="important",
        markers=[
            r"\bWORKAROUND\b",
            r"#\s*workaround\s+for",
            r"#\s*hack\s+to\s+(fix|avoid|prevent|work)",
            r"#\s*this\s+is\s+a\s+(hack|workaround|temp)",
        ],
        action="Replace workaround with proper fix",
        description="Explicit workaround markers",
    ),

    # --- Debug Code ---
    SentinelPattern(
        name="debug_print",
        issue_type="debug",
        severity="minor",
        markers=[
            r"(?<!['\"\w])console\.log\(",
            r"\bprint\(\s*['\"]debug",
            r"\bprint\(\s*f?['\"](?:>>>|---|\*\*\*|DEBUG)",
            r"\bbreakpoint\(\)",
            r"\bimport\s+pdb",
            r"\bpdb\.set_trace\(\)",
            r"\bdebugger\b",
            r"\bimport\s+ipdb",
        ],
        action="Remove debug statements before shipping",
        description="Debug/logging statements meant for development",
    ),

    # --- Hardcoded Values ---
    SentinelPattern(
        name="hardcoded_url",
        issue_type="debt",
        severity="critical",
        markers=[
            r"['\"]https?://localhost[:/]",
            r"['\"]https?://127\.0\.0\.1[:/]",
            r"['\"]https?://0\.0\.0\.0[:/]",
        ],
        action="Extract URL to configuration/environment variable",
        description="Hardcoded localhost/development URLs",
    ),
    SentinelPattern(
        name="hardcoded_secret",
        issue_type="debt",
        severity="critical",
        markers=[
            r"(?:password|passwd|secret|token|api_key|apikey)\s*=\s*['\"][^'\"]{8,}['\"]",
            r"(?:PASSWORD|SECRET|TOKEN|API_KEY)\s*=\s*['\"][^'\"]{8,}['\"]",
        ],
        action="Move secret to environment variable or secrets manager",
        description="Hardcoded secrets, passwords, or API keys",
    ),
    SentinelPattern(
        name="hardcoded_config",
        issue_type="debt",
        severity="important",
        markers=[
            r"#\s*hardcoded",
            r"#\s*should\s+be\s+(configurable|an?\s+env|in\s+config)",
            r"#\s*move\s+to\s+(config|env|settings)",
        ],
        action="Extract to configuration",
        description="Values explicitly marked as needing configuration",
    ),

    # --- Incomplete Implementation ---
    SentinelPattern(
        name="not_implemented",
        issue_type="temporary",
        severity="important",
        markers=[
            r"raise\s+NotImplementedError",
            r"throw\s+new\s+Error\(['\"]not\s+implemented",
            r"pass\s+#\s*(todo|implement|fixme|stub)",
            r"return\s+None\s+#\s*(todo|implement|fixme|stub|placeholder)",
        ],
        action="Implement before shipping",
        description="Explicitly unimplemented code paths",
    ),
    SentinelPattern(
        name="skip_marker",
        issue_type="temporary",
        severity="important",
        markers=[
            r"@pytest\.mark\.skip",
            r"@pytest\.mark\.xfail",
            r"@unittest\.skip",
            r"\.skip\(\s*['\"]",
            r"#\s*test\s+disabled",
            r"#\s*skipping\s+(this\s+)?test",
        ],
        action="Enable or remove skipped tests",
        description="Disabled/skipped tests that may need attention",
    ),

    # --- Disconnection Markers ---
    SentinelPattern(
        name="unused_import",
        issue_type="disconnected",
        severity="minor",
        markers=[
            r"#\s*noqa:\s*F401",  # Explicitly suppressed unused import
            r"#\s*unused\s+import",
            r"#\s*will\s+be\s+used\s+(later|soon|by)",
        ],
        action="Connect or remove unused import",
        description="Imports marked as unused or suppressed",
    ),
    SentinelPattern(
        name="dead_code_marker",
        issue_type="disconnected",
        severity="minor",
        markers=[
            r"#\s*dead\s+code",
            r"#\s*unreachable",
            r"#\s*never\s+called",
            r"#\s*not\s+(yet\s+)?connected",
            r"#\s*wire\s+(this|up)\s+(to|later)",
        ],
        action="Connect to system or remove",
        description="Code explicitly marked as disconnected",
    ),
]


# ============================================================================
# FILE TYPE FILTERS
# ============================================================================

# Patterns to SKIP (infrastructure, test dirs, vendor, etc.)
SKIP_PATTERNS = [
    r"tests/",
    r"__tests__/",
    r"spec/",
    r"hooks/lib/",  # Skip shared sentinel library; production hooks are still scanned
    r"node_modules/",
    r"\.venv/",
    r"venv/",
    r"vendor/",
    r"\.git/",
    r"\.sentinel/",
]

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".rs", ".rb",
    ".sh", ".bash",
    ".yaml", ".yml", ".toml",
    ".html", ".jinja2",
}

# Patterns that are OK in test files (won't flag mock/fake in tests)
TEST_FILE_PATTERNS = [
    r"test_",
    r"_test\.",
    r"\.test\.",
    r"\.spec\.",
    r"conftest\.py",
    r"fixtures",
]


def is_test_file(filepath: str) -> bool:
    """Check if a file is a test file where mocks and fakes are expected.

    Args:
        filepath: Relative or absolute path to the file.

    Returns:
        True if the file matches test file naming patterns.
    """
    return any(re.search(p, filepath) for p in TEST_FILE_PATTERNS)


def should_skip_file(filepath: str) -> bool:
    """Check if a file should be skipped entirely from sentinel scanning.

    Args:
        filepath: Relative or absolute path to the file.

    Returns:
        True if the file is in a directory that should not be scanned
        (tests, vendor, hooks infrastructure, .sentinel itself, etc.).
    """
    return any(re.search(p, filepath) for p in SKIP_PATTERNS)


def is_scannable(filepath: str) -> bool:
    """Check if a file has a scannable extension.

    Args:
        filepath: Relative or absolute path to the file.

    Returns:
        True if the file extension is in SCANNABLE_EXTENSIONS.
    """
    return Path(filepath).suffix.lower() in SCANNABLE_EXTENSIONS


def scan_file_content(
    filepath: str,
    content: str,
    changed_lines: Optional[set] = None,
) -> List[dict]:
    """Scan file content for sentinel patterns.

    When changed_lines is provided, only lines in that set are scanned.
    This enables diff-scoped detection where only newly written or modified
    lines are flagged, avoiding false positives from pre-existing issues.

    Args:
        filepath: Path to the file (for context and filtering).
        content: File content to scan.
        changed_lines: Optional set of 1-based line numbers to restrict
            scanning to. If None, all lines are scanned.

    Returns:
        List of finding dicts with pattern, type, severity, line, etc.
    """
    if should_skip_file(filepath):
        return []

    if not is_scannable(filepath):
        return []

    test_file = is_test_file(filepath)
    findings = []

    for line_num, line in enumerate(content.splitlines(), start=1):
        # If diff-scoped, skip lines that weren't changed
        if changed_lines is not None and line_num not in changed_lines:
            continue

        # Skip empty lines and very short lines
        if len(line.strip()) < 3:
            continue

        # Skip divider comments (e.g., "# ---", "# ===") but keep actionable markers
        stripped = line.strip()
        if stripped.startswith("#") and re.match(r'^#\s*[-=_*#/\\]+$', stripped):
            continue

        for pattern in SENTINEL_PATTERNS:
            # Skip mock/fake patterns in test files
            if test_file and pattern.issue_type == "mock":
                continue

            finding = pattern.scan_line(line, line_num)
            if finding:
                finding["file"] = filepath
                findings.append(finding)

    return findings


def format_finding_md(finding: dict) -> str:
    """Format a single finding as a markdown list item.

    Args:
        finding: A finding dict as returned by SentinelPattern.scan_line(),
            with keys: file, line, type, severity, pattern, context, action.

    Returns:
        A markdown-formatted string like
        ``- [!!] **type** `file:line` — pattern: `context` -> action``.
    """
    severity_icon = {
        "critical": "!!!",
        "important": "!!",
        "minor": "!",
        "note": "~",
    }
    icon = severity_icon.get(finding["severity"], "?")
    return (
        f"- [{icon}] **{finding['type']}** `{finding['file']}:{finding['line']}` — "
        f"{finding['pattern']}: `{finding['context'][:80]}` "
        f"→ {finding['action']}"
    )


if __name__ == "__main__":
    # Self-test: scan a sample
    sample = '''
    # TODO: fix this later
    password = "hunter2"
    print(">>> DEBUG: checking value")
    raise NotImplementedError
    # WORKAROUND for upstream bug
    mock_response = {"status": "ok"}
    '''
    results = scan_file_content("sample.py", sample)
    for r in results:
        print(format_finding_md(r))
