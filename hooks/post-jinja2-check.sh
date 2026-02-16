#!/bin/bash
# Post-edit hook to check Jinja2 templates for security issues
# Runs after editing .html files

FILE="$1"

# Only process HTML files
if [[ ! "$FILE" == *.html ]]; then
    exit 0
fi

# Check if file exists
if [[ ! -f "$FILE" ]]; then
    exit 0
fi

issues_found=false

# Check for |safe filter usage (except with tojson)
safe_usage=$(grep -n "|safe" "$FILE" 2>/dev/null | grep -v "tojson|safe" || true)
if [[ -n "$safe_usage" ]]; then
    echo "[Hook] WARNING: |safe filter found in $FILE" >&2
    echo "$safe_usage" | head -3 >&2
    echo "[Hook] Ensure content is sanitized with bleach before |safe" >&2
    issues_found=true
fi

# Check for inline scripts without nonce
no_nonce_script=$(grep -n "<script" "$FILE" 2>/dev/null | grep -v "nonce=" | grep -v "src=" || true)
if [[ -n "$no_nonce_script" ]]; then
    echo "[Hook] WARNING: <script> without nonce in $FILE" >&2
    echo "$no_nonce_script" | head -2 >&2
    echo "[Hook] Add nonce=\"{{ csp_nonce }}\" for CSP compliance" >&2
    issues_found=true
fi

# Check for inline styles without nonce
no_nonce_style=$(grep -n "<style" "$FILE" 2>/dev/null | grep -v "nonce=" || true)
if [[ -n "$no_nonce_style" ]]; then
    echo "[Hook] WARNING: <style> without nonce in $FILE" >&2
    echo "$no_nonce_style" | head -2 >&2
    echo "[Hook] Add nonce=\"{{ csp_nonce }}\" for CSP compliance" >&2
    issues_found=true
fi

# Check for autoescape false
autoescape_off=$(grep -n "autoescape false" "$FILE" 2>/dev/null || true)
if [[ -n "$autoescape_off" ]]; then
    echo "[Hook] CRITICAL: {% autoescape false %} found in $FILE" >&2
    echo "$autoescape_off" >&2
    echo "[Hook] Never disable auto-escaping - XSS vulnerability" >&2
    issues_found=true
fi

# Check for JavaScript context with user data
js_context=$(grep -n 'var.*=.*"{{' "$FILE" 2>/dev/null | grep -v "tojson" || true)
if [[ -n "$js_context" ]]; then
    echo "[Hook] WARNING: User data in JS string context in $FILE" >&2
    echo "$js_context" | head -2 >&2
    echo "[Hook] Use |tojson filter or data attributes instead" >&2
    issues_found=true
fi

# Check for form without csrf_token
forms_without_csrf=$(grep -l "<form" "$FILE" 2>/dev/null | xargs grep -L "csrf_token" 2>/dev/null || true)
if [[ -n "$forms_without_csrf" ]]; then
    # Only warn if there's a POST form
    post_form=$(grep -n 'method.*[Pp][Oo][Ss][Tt]' "$FILE" 2>/dev/null || true)
    if [[ -n "$post_form" ]]; then
        has_csrf=$(grep "csrf_token" "$FILE" 2>/dev/null || true)
        if [[ -z "$has_csrf" ]]; then
            echo "[Hook] WARNING: POST form without csrf_token in $FILE" >&2
            echo "[Hook] Add {{ csrf_token() }} inside the form" >&2
            issues_found=true
        fi
    fi
fi

if [[ "$issues_found" = true ]]; then
    echo "[Hook] See .claude/rules/jinja2-security.md for guidelines" >&2
fi

exit 0
