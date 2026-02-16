#!/usr/bin/env python3
"""Post a reply to a PR review thread.

Usage:
    python3 scripts/coderabbit/loop/post_reply.py --thread THREAD_ID --body "Reply text"

Note: This posts a reply without resolving the thread. Let CodeRabbit verify and resolve.
The thread ID is globally unique, so no PR number is needed.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coderabbit.utils import (
    eprint,
    gh_api_graphql,
)


def post_reply(thread_id: str, body: str) -> bool:
    """Post a reply to a review thread.

    Args:
        thread_id: The globally unique GraphQL thread ID
        body: The reply text
    """
    # GraphQL mutation to add a comment to a review thread
    mutation = """
    mutation($threadId: ID!, $body: String!) {
      addPullRequestReviewThreadReply(input: {
        pullRequestReviewThreadId: $threadId,
        body: $body
      }) {
        comment {
          id
          body
          createdAt
        }
      }
    }
    """

    try:
        result = gh_api_graphql(mutation, {"threadId": thread_id, "body": body})

        comment = result.get("data", {}).get("addPullRequestReviewThreadReply", {}).get("comment")
        if comment:
            print(f"Reply posted successfully")
            print(f"  Comment ID: {comment['id']}")
            return True
        else:
            eprint("Failed to post reply - no comment returned")
            return False

    except Exception as e:
        eprint(f"Failed to post reply: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post a reply to a PR review thread")
    parser.add_argument("--thread", required=True, help="Thread ID (GraphQL node ID)")
    parser.add_argument("--body", required=True, help="Reply body")

    args = parser.parse_args()

    success = post_reply(args.thread, args.body)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
