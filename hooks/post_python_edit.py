#!/usr/bin/env python3
"""
PostToolUse Hook - Automatic Testing After Python Edits

This hook runs automatically after Edit/Write operations on Python files in the modules/ directory.
It performs basic validation to catch syntax errors early.

Hook Event: PostToolUse
Trigger: After Edit/Write tools complete
Scope: Python files in modules/ directory only
"""

import json
import sys
import os
import subprocess
from pathlib import Path


def should_validate(tool_name: str, file_path: str) -> bool:
    """Check if this file should be validated"""
    # Only validate Edit/Write operations
    if tool_name not in ["Edit", "Write"]:
        return False

    # Only validate Python files in modules/
    if not file_path:
        return False

    # Normalize path
    if file_path.startswith("//workspace/"):
        file_path = file_path.replace("//workspace/", "")
    elif file_path.startswith("/workspace/"):
        file_path = file_path.replace("/workspace/", "")

    # Check if it's a Python file in modules/
    if ".trees/claude-config/" in file_path:
        file_path = file_path.split(".trees/claude-config/")[-1]

    return file_path.startswith("modules/") and file_path.endswith(".py")


def validate_python_syntax(file_path: str) -> dict:
    """Validate Python file syntax"""
    try:
        # Run Python syntax check
        result = subprocess.run(
            ["python", "-m", "py_compile", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            return {"valid": True, "message": f"✅ Syntax valid: {file_path}"}
        else:
            return {
                "valid": False,
                "message": f"❌ Syntax error in {file_path}:\n{result.stderr}",
            }

    except subprocess.TimeoutExpired:
        return {"valid": False, "message": f"⏱️ Timeout while validating {file_path}"}
    except Exception as e:
        return {"valid": False, "message": f"⚠️ Validation error: {e}"}


def main():
    """Hook entry point"""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
        cwd = hook_input.get("cwd", "")

        # Check if we should validate this file
        if not should_validate(tool_name, file_path):
            # Not a Python file in modules/ - allow without validation
            print(json.dumps({}))
            sys.exit(0)

        # Get full path for validation
        full_path = (
            os.path.join(cwd, file_path)
            if cwd and not file_path.startswith("/")
            else file_path
        )

        # Validate syntax
        validation_result = validate_python_syntax(full_path)

        # Prepare response
        response = {}

        if not validation_result["valid"]:
            # Syntax error found - provide feedback
            response = {"hookSpecificOutput": {"message": validation_result["message"]}}
        else:
            # Valid - no output needed
            response = {}

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # On error, allow the operation but log
        error_response = {
            "hookSpecificOutput": {"message": f"⚠️ Post-edit validation hook error: {e}"}
        }
        print(json.dumps(error_response))
        sys.exit(0)


if __name__ == "__main__":
    main()
