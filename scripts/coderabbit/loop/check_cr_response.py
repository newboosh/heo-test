#!/usr/bin/env python3
"""Check for CodeRabbit's response to fixes.

Usage:
    python3 scripts/coderabbit/loop/check_cr_response.py --pr PR_NUMBER

Output:
    approved - CodeRabbit approved the changes
    rejected - CodeRabbit found new issues
    pending - Still waiting for CodeRabbit response
"""

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.utils import (
    eprint,
    get_pr_for_branch,
    get_repo_info,
    gh_api_graphql,
)

# Indicators that CodeRabbit approved the fix
# Format: (phrase, weight) - higher weight = stronger signal
APPROVAL_INDICATORS = [
    ("looks good", 2),
    ("lgtm", 2),
    ("approved", 3),
    ("the fix addresses", 2),
    ("correctly implements", 2),
    ("no further changes needed", 3),
    ("no further changes required", 3),
    ("issue resolved", 3),
    ("properly fixed", 2),
    ("changes are correct", 2),
    ("well done", 1),
    ("thank you for", 1),
]

# Indicators that CodeRabbit rejected/wants more changes
# Format: (phrase, weight, context_required)
# context_required: if True, phrase must appear with negative context
REJECTION_INDICATORS = [
    ("still has issues", 3, False),
    ("still needs", 2, False),
    ("doesn't address", 3, False),
    ("does not address", 3, False),
    ("not quite right", 2, False),
    ("additional changes required", 3, False),
    ("additional changes needed", 3, False),
    ("consider instead", 1, True),  # May be a suggestion, not rejection
    ("should be changed to", 2, False),
    ("issue remains", 3, False),
    ("not fixed", 3, False),
    ("incorrect", 2, True),  # Context-dependent
    ("please update", 2, False),
    ("needs to be", 2, True),
    ("must be", 2, True),
]

# Negation words that flip meaning
NEGATION_WORDS = ["not", "no", "don't", "doesn't", "won't", "isn't", "aren't"]


def check_cr_response(pr_number: int, since_minutes: int = 15) -> str:
    """Check CodeRabbit's response status.

    Returns: 'approved', 'rejected', or 'pending'
    """
    owner, repo = get_repo_info()

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(last: 5) {
                nodes {
                  author { login }
                  body
                  createdAt
                }
              }
            }
          }
          comments(last: 20) {
            nodes {
              author { login }
              body
              createdAt
            }
          }
          reviews(last: 10) {
            nodes {
              author { login }
              state
              body
              submittedAt
            }
          }
        }
      }
    }
    """

    result = gh_api_graphql(query, {"owner": owner, "repo": repo, "pr": pr_number})
    pr_data = result["data"]["repository"]["pullRequest"]

    if not pr_data:
        raise ValueError(f"PR #{pr_number} not found in {owner}/{repo}")

    # Calculate cutoff time
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)

    # CodeRabbit bot login variants
    coderabbit_logins = {"coderabbitai", "coderabbitai[bot]", "coderabbit"}

    # Check for recent CodeRabbit activity
    recent_cr_comments = []

    # Check review threads
    for thread in pr_data.get("reviewThreads", {}).get("nodes", []):
        for comment in thread.get("comments", {}).get("nodes", []):
            author = comment.get("author", {}).get("login", "")
            if author.lower() not in coderabbit_logins:
                continue

            created_at = comment.get("createdAt", "")
            if created_at:
                comment_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if comment_time > cutoff:
                    recent_cr_comments.append({
                        "body": comment["body"],
                        "resolved": thread.get("isResolved", False),
                    })

    # Check general comments
    for comment in pr_data.get("comments", {}).get("nodes", []):
        author = comment.get("author", {}).get("login", "")
        if author.lower() not in coderabbit_logins:
            continue

        created_at = comment.get("createdAt", "")
        if created_at:
            comment_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if comment_time > cutoff:
                recent_cr_comments.append({
                    "body": comment["body"],
                    "resolved": False,
                })

    # Check reviews - track both recent and latest CodeRabbit review
    latest_cr_review = None
    latest_cr_review_time = None

    for review in pr_data.get("reviews", {}).get("nodes", []):
        author = review.get("author", {}).get("login", "")
        if author.lower() not in coderabbit_logins:
            continue

        submitted_at = review.get("submittedAt", "")
        if submitted_at:
            review_time = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))

            # Track latest CodeRabbit review regardless of cutoff
            if latest_cr_review_time is None or review_time > latest_cr_review_time:
                latest_cr_review = review
                latest_cr_review_time = review_time

            # Check if within cutoff window
            if review_time > cutoff:
                state = review.get("state", "").upper()
                if state == "APPROVED":
                    return "approved"
                elif state in ["CHANGES_REQUESTED", "REQUEST_CHANGES"]:
                    return "rejected"

    # If no recent activity, fall back to latest CodeRabbit review
    if not recent_cr_comments and latest_cr_review:
        state = latest_cr_review.get("state", "").upper()
        if state == "APPROVED":
            return "approved"
        elif state in ["CHANGES_REQUESTED", "REQUEST_CHANGES"]:
            return "rejected"

    if not recent_cr_comments:
        return "pending"

    # Analyze recent comments
    approval_score = 0
    rejection_score = 0

    for item in recent_cr_comments:
        body_lower = item["body"].lower()
        sentences = body_lower.replace(".", "\n").replace("!", "\n").split("\n")

        # If thread is resolved, lean toward approval
        if item.get("resolved"):
            approval_score += 3

        # Check for approval indicators with weights
        for phrase, weight in APPROVAL_INDICATORS:
            if phrase in body_lower:
                # Check if negated in same sentence
                negated = False
                for sentence in sentences:
                    if phrase in sentence:
                        if any(neg in sentence for neg in NEGATION_WORDS):
                            negated = True
                            break
                if not negated:
                    approval_score += weight

        # Check for rejection indicators with weights and context
        for indicator_tuple in REJECTION_INDICATORS:
            phrase, weight, context_required = indicator_tuple
            if phrase in body_lower:
                if context_required:
                    # Only count if in a clearly negative context
                    for sentence in sentences:
                        if phrase in sentence and len(sentence) > len(phrase) + 10:
                            rejection_score += weight
                            break
                else:
                    rejection_score += weight

    # Determine result with threshold
    if rejection_score >= 3 and rejection_score > approval_score:
        return "rejected"
    elif approval_score >= 3 and approval_score > rejection_score:
        return "approved"
    elif approval_score > 0 and rejection_score == 0:
        return "approved"
    else:
        return "pending"


def main():
    parser = argparse.ArgumentParser(description="Check CodeRabbit response status")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch's PR)")
    parser.add_argument(
        "--since",
        type=int,
        default=15,
        help="Check comments from last N minutes (default: 15)",
    )

    args = parser.parse_args()

    pr_number = args.pr
    if not pr_number:
        pr_number = get_pr_for_branch()
        if not pr_number:
            eprint("ERROR: No PR found for current branch")
            sys.exit(1)

    try:
        status = check_cr_response(pr_number, args.since)
        print(status)
        sys.exit(0)
    except Exception as e:
        eprint(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
