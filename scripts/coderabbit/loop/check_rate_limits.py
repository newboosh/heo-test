#!/usr/bin/env python3
"""Check GitHub API rate limits.

Usage:
    python3 scripts/coderabbit/loop/check_rate_limits.py [--json] [--threshold N]

Output:
    github_remaining: X
    github_limit: Y
    github_reset: TIMESTAMP
    coderabbit_estimate: Z (estimated based on recent activity)

Exit codes:
    0 - Rate limits OK (above threshold)
    1 - Rate limits LOW (below threshold)
    2 - Error occurred
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.utils import eprint, run_gh_command


def get_rate_limits() -> dict:
    """Get GitHub API rate limit status."""
    result = run_gh_command(["api", "rate_limit"])
    data = json.loads(result.stdout)

    core = data.get("resources", {}).get("core", {})
    graphql = data.get("resources", {}).get("graphql", {})

    # Calculate time until reset
    core_reset = core.get("reset", 0)
    graphql_reset = graphql.get("reset", 0)

    now = datetime.now().timestamp()
    core_reset_in = max(0, core_reset - now)
    graphql_reset_in = max(0, graphql_reset - now)

    # Estimate CodeRabbit interactions remaining
    # CodeRabbit uses GraphQL primarily, so base estimate on that
    graphql_remaining = graphql.get("remaining", 0)
    # Each PR check uses ~2-5 GraphQL calls, commenting uses ~1-2
    coderabbit_estimate = graphql_remaining // 5

    return {
        "github_core_remaining": core.get("remaining", 0),
        "github_core_limit": core.get("limit", 0),
        "github_core_reset": core_reset,
        "github_core_reset_in_minutes": round(core_reset_in / 60, 1),
        "github_graphql_remaining": graphql_remaining,
        "github_graphql_limit": graphql.get("limit", 0),
        "github_graphql_reset": graphql_reset,
        "github_graphql_reset_in_minutes": round(graphql_reset_in / 60, 1),
        "coderabbit_estimate": coderabbit_estimate,
        # Use the lower of core and graphql for overall status
        "github_remaining": min(core.get("remaining", 0), graphql_remaining),
    }


def main():
    parser = argparse.ArgumentParser(description="Check GitHub API rate limits")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--threshold",
        type=int,
        default=500,
        help="Warn if remaining calls below this (default: 500)",
    )

    args = parser.parse_args()

    try:
        limits = get_rate_limits()

        if args.json:
            print(json.dumps(limits, indent=2))
        else:
            print(f"github_remaining: {limits['github_remaining']}")
            print(f"github_core_remaining: {limits['github_core_remaining']}/{limits['github_core_limit']}")
            print(f"github_graphql_remaining: {limits['github_graphql_remaining']}/{limits['github_graphql_limit']}")
            print(f"coderabbit_estimate: {limits['coderabbit_estimate']}")

            if limits["github_core_reset_in_minutes"] > 0:
                print(f"core_resets_in: {limits['github_core_reset_in_minutes']} minutes")
            if limits["github_graphql_reset_in_minutes"] > 0:
                print(f"graphql_resets_in: {limits['github_graphql_reset_in_minutes']} minutes")

        # Check threshold
        if limits["github_remaining"] < args.threshold:
            if not args.json:
                eprint(f"\nWARNING: Rate limit below threshold ({args.threshold})")
                eprint("Consider pausing operations until rate limit resets")
            sys.exit(1)

        sys.exit(0)

    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
