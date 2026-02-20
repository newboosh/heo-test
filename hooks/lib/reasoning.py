#!/usr/bin/env python3
"""
Reasoning Context Classification - Shared library for intent-aware hooks.

Classifies the assistant's last message to determine whether code patterns
flagged by sentinel are intentional, being cleaned up, or unexplained.

Used by:
  - hooks/sentinel-detect.py        (PostToolUse — applies context to findings)
  - hooks/sentinel-task-context.py  (PreToolUse Task — captures orchestrator intent)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path


# ============================================================================
# REASONING CLASSIFICATION PATTERNS
# ============================================================================

# Agent explicitly acknowledges a code pattern as intentional / by design
INTENTIONAL_PATTERNS = [
    r"\bintentional(ly)?\b",
    r"\bby design\b",
    r"\btemporary\b.{0,40}\b(for now|until|by design|testing)\b",
    r"\bdebug\b.{0,60}\b(for now|while|investigating|tracing|diagnosing)\b",
    r"\bkeep(ing)?\b.{0,40}\b(for|while|until|during)\b.{0,40}\b(debug|investigat|diagnos|test)\b",
    r"\bplaceholder\b.{0,40}\b(will|to be)\b.{0,40}\b(replaced|implemented|removed)\b",
    r"\bstub(bing)?\b.{0,30}\b(out|first|the interface|for now)\b",
    r"\bscaffold(ing)?\b",
    r"\bleav(e|ing)\b.{0,40}\b(todo|fixme|hack|this)\b.{0,40}\b(for|until|to)\b",
    r"\bknown\b.{0,20}\b(todo|issue|limitation|debt)\b",
    r"\bnot (real|production)\b.{0,40}\bdata\b",
    r"\btest(ing)?\b.{0,20}\b(fixture|data|config)\b",
    r"\bthis is (a |the )?(test|dev|development|local)\b",
]

# Agent is actively removing / fixing patterns (suppress all findings in this edit)
CLEANUP_PATTERNS = [
    r"\bremov(e|ing)\b.{0,40}\b(debug|temp|placeholder|mock|stub|todo|fixme|hack|workaround|print)\b",
    r"\bclean(ing)?\b.{0,20}\bup\b",
    r"\b(address(ing)?|fix(ing)?)\b.{0,30}\bsentinel\b",
    r"\b(address(ing)?|resolv(e|ing))\b.{0,30}\b(todo|fixme|warning|issue)\b",
    r"\bdelet(e|ing)\b.{0,30}\b(debug|temp|unused|dead)\b",
    r"\bthis will be (removed|replaced|implemented)\b",
    r"\brefactor(ing)?\b.{0,40}\b(away|out|this|temp|hack)\b",
]

# Agent is writing legitimate output code (suppress print() warnings)
OUTPUT_CODE_PATTERNS = [
    r"\bcli (tool|script|interface|app|utility)\b",
    r"\bcommand.?line (tool|script|interface|output)\b",
    r"\buser.facing (output|message|result)\b",
    r"\bprint(ing)?\b.{0,40}\b(result|output|message|summary|report|status|progress)\b",
    r"\b(display|show(ing)?|output(ting)?)\b.{0,30}\b(to|for) the user\b",
    r"\bscript that (outputs|prints|displays)\b",
    r"\bproduces? output\b",
]

# Patterns used to extract specific acknowledged items from orchestrator messages
# (for cross-agent context propagation)
ACKNOWLEDGE_EXTRACTION_PATTERNS = [
    r"keep(?:ing)?\s+(?:the\s+)?([\w\s]+(?:debug|temp|todo|mock|print|hack|stub)[^.,;]{0,60})",
    r"(?:these?|the)\s+([\w\s]*(?:debug|temp|todo|mock|print|hack|stub)[^.,;]{0,40})\s+(?:are|is)\s+(?:intentional|temporary|by design)",
    r"(?:hardcoded?|localhost|temp(?:orary)?)[^.,;]{0,60}(?:intentional|by design|for (?:testing|dev|local))",
]


# ============================================================================
# CLASSIFICATION
# ============================================================================

def classify_reasoning(message: str) -> dict:
    """Classify assistant reasoning for intent-aware hook decisions.

    Args:
        message: The last_assistant_message string from the hook payload.

    Returns:
        Dict with keys:
            intentional (bool)  — agent acknowledged a pattern as deliberate
            cleanup (bool)      — agent is actively removing/fixing patterns
            output_code (bool)  — agent is writing legitimate output-producing code
            has_context (bool)  — any relevant context found at all
    """
    if not message:
        return {
            "intentional": False,
            "cleanup": False,
            "output_code": False,
            "has_context": False,
        }

    msg = message.lower()

    intentional = any(re.search(p, msg) for p in INTENTIONAL_PATTERNS)
    cleanup = any(re.search(p, msg) for p in CLEANUP_PATTERNS)
    output_code = any(re.search(p, msg) for p in OUTPUT_CODE_PATTERNS)

    return {
        "intentional": intentional,
        "cleanup": cleanup,
        "output_code": output_code,
        "has_context": intentional or cleanup or output_code,
    }


def extract_acknowledged_items(message: str) -> list[str]:
    """Extract specific items the orchestrator has acknowledged as intentional.

    Args:
        message: The orchestrator's last_assistant_message.

    Returns:
        List of short description strings that were acknowledged.
    """
    items = []
    msg = message.lower()
    for pattern in ACKNOWLEDGE_EXTRACTION_PATTERNS:
        for match in re.finditer(pattern, msg):
            item = (match.group(1) if match.lastindex else match.group(0)).strip()
            if item:
                items.append(item)
    return list(set(items))


# ============================================================================
# AGENT CONTEXT FILE (cross-agent propagation)
# ============================================================================

_CONTEXT_FILE = ".sentinel/agent-context.json"
_CONTEXT_TTL_SECONDS = 3600  # 1 hour


def read_agent_context(cwd: str = ".") -> dict:
    """Read cross-agent context written by sentinel-task-context hook.

    Args:
        cwd: Working directory to locate .sentinel/agent-context.json.

    Returns:
        Context dict, or empty dict if absent / expired / unreadable.
    """
    ctx_file = Path(cwd) / _CONTEXT_FILE
    if not ctx_file.exists():
        return {}
    try:
        data = json.loads(ctx_file.read_text(encoding="utf-8"))
        if time.time() > data.get("expires_at", 0):
            ctx_file.unlink(missing_ok=True)
            return {}
        return data
    except Exception:
        return {}


def write_agent_context(
    reasoning: dict,
    acknowledged: list[str],
    raw_message: str,
    cwd: str = ".",
) -> None:
    """Write orchestrator intent to .sentinel/agent-context.json.

    Merges with any existing context so multiple Task invocations accumulate.

    Args:
        reasoning:    Classification dict from classify_reasoning().
        acknowledged: Extracted acknowledged item strings.
        raw_message:  Truncated excerpt of the orchestrator message.
        cwd:          Working directory for .sentinel/ directory.
    """
    ctx_dir = Path(cwd) / ".sentinel"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    ctx_file = ctx_dir / "agent-context.json"

    # Merge with existing context
    existing: dict = {}
    if ctx_file.exists():
        try:
            existing = json.loads(ctx_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Union reasoning bools so accumulated context from multiple Task spawns is preserved
    existing_reasoning = existing.get("reasoning", {})
    merged_reasoning = {
        "intentional": reasoning.get("intentional") or existing_reasoning.get("intentional", False),
        "cleanup": reasoning.get("cleanup") or existing_reasoning.get("cleanup", False),
        "output_code": reasoning.get("output_code") or existing_reasoning.get("output_code", False),
        "has_context": reasoning.get("has_context") or existing_reasoning.get("has_context", False),
    }

    merged_acknowledged = list(set(existing.get("acknowledged", []) + acknowledged))

    now = time.time()
    ctx = {
        "reasoning": merged_reasoning,
        "acknowledged": merged_acknowledged,
        "message_excerpt": raw_message[:500],
        "written_at": now,
        "expires_at": now + _CONTEXT_TTL_SECONDS,
    }
    ctx_file.write_text(json.dumps(ctx, indent=2), encoding="utf-8")


# ============================================================================
# FINDING CONTEXT APPLICATION
# ============================================================================

def apply_context_to_findings(
    findings: list[dict],
    classification: dict,
    agent_context: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Apply reasoning context to a list of sentinel findings.

    Rules (in priority order):
      1. Finding matches an acknowledged item in agent_context → suppress
      2. classification["cleanup"] → suppress all (agent is fixing things)
      3. classification["output_code"] + print-related finding → suppress
      4. classification["intentional"] → downgrade severity one level
      5. critical finding with no context at all → mark as escalated

    Args:
        findings:       Raw finding dicts from scan_file_content().
        classification: Output of classify_reasoning().
        agent_context:  Output of read_agent_context().

    Returns:
        Tuple of (active, suppressed, escalated) finding lists.
        active     — findings to record normally (may include escalated)
        suppressed — findings intentionally silenced
        escalated  — subset of active marked for urgent attention
    """
    active: list[dict] = []
    suppressed: list[dict] = []
    escalated: list[dict] = []

    acknowledged_items = agent_context.get("acknowledged", [])

    for finding in findings:
        f = dict(finding)  # shallow copy to avoid mutating originals

        # Rule 1: acknowledged by orchestrator context
        if _is_acknowledged(f, acknowledged_items):
            f["_tag"] = "acknowledged"
            suppressed.append(f)
            continue

        # Rule 2: agent is actively cleaning up — suppress everything
        if classification.get("cleanup"):
            f["_tag"] = "cleanup-in-progress"
            suppressed.append(f)
            continue

        # Rule 3: agent is writing legitimate output code — suppress print-related findings only
        if classification.get("output_code") and "print" in f.get("pattern", "").lower():
            f["_tag"] = "output-code"
            suppressed.append(f)
            continue

        # Rule 4: agent acknowledged intentional — downgrade severity
        if classification.get("intentional"):
            downgrade = {"critical": "important", "important": "minor", "minor": "note"}
            original = f["severity"]
            f["severity"] = downgrade.get(original, original)
            f["_tag"] = f"downgraded-from-{original}"
            active.append(f)
            continue

        # Rule 5: critical finding with no reasoning context — escalate
        if not classification.get("has_context") and f["severity"] == "critical":
            f["_escalated"] = True
            escalated.append(f)
            active.append(f)
            continue

        active.append(f)

    return active, suppressed, escalated


def _is_acknowledged(finding: dict, acknowledged_items: list[str]) -> bool:
    """Check if a finding matches any orchestrator-acknowledged item."""
    if not acknowledged_items:
        return False
    finding_text = f"{finding.get('pattern', '')} {finding.get('context', '')}".lower()
    for item in acknowledged_items:
        # Match if any significant word from the acknowledged description appears
        words = [w for w in item.lower().split() if len(w) > 3]
        if words and all(w in finding_text for w in words[:3]):
            return True
    return False
