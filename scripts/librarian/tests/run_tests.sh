#!/usr/bin/env bash
# Test runner for the catalog + librarian system
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Catalog + Librarian Test Suite ==="
echo ""

# Step 1: Run catalog unit tests
echo "Step 1: Running catalog unit tests..."
python3 -m pytest scripts/catalog/tests/ -v --tb=short
echo ""

# Step 2: Run librarian unit tests
echo "Step 2: Running librarian unit tests..."
python3 -m pytest scripts/librarian/tests/ -v --tb=short
echo ""

echo "=== All Tests Passed ==="
