#!/usr/bin/env python3
"""
Twitter/X search via twitterapi.io (NOT the official X/Twitter API).

Standalone CLI and importable module for Twitter-specific operations.
Two subcommands:
  search       - Advanced tweet search by keyword, with optional author/date filters
  user-tweets  - Get latest tweets from a specific user by handle

API docs: https://docs.twitterapi.io/

Usage:
  # Keyword search
  python3 twitter_search.py search "AI news" --since 2026-03-01 --num 5

  # Combine variants with OR to reduce API calls
  python3 twitter_search.py search '"GPT 5.4" OR "GPT-5.4"' --since 2026-03-01 --num 10

  # Filter by author (with or without keyword)
  python3 twitter_search.py search "GPT-5" --from openai --since 2026-01-01
  python3 twitter_search.py search --from elonmusk --since 2026-02-01 --num 10

  # Get a user's latest tweets
  python3 twitter_search.py user-tweets --username openai --num 1
"""

import json
import sys
import os
import argparse
from datetime import datetime, timezone
import threading

try:
    import requests
except ImportError:
    print('{"error": "requests library not installed. Run: pip3 install requests"}',
          file=sys.stderr)
    sys.exit(1)

# Base URL for all twitterapi.io endpoints
_BASE_URL = "https://api.twitterapi.io"

# Maximum results per API call (twitterapi.io returns at most 20 per page)
_API_MAX_PER_PAGE = 20


# ---------------------------------------------------------------------------
# Query counter for cross-call rate limiting (used when called from search.py)
# ---------------------------------------------------------------------------
def _check_quota(query_counter: dict) -> bool:
    """Check and consume quota. Returns True if allowed, False if exhausted."""
    if query_counter is None:
        return True
    with query_counter["lock"]:
        if query_counter["used"] >= query_counter["limit"]:
            print(f"[twitter] skipped: quota reached ({query_counter['limit']} queries)",
                  file=sys.stderr)
            return False
        query_counter["used"] += 1
        return True


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def _api_get(endpoint: str, api_key: str, params: dict, timeout: int = 30) -> dict:
    """Make a GET request to twitterapi.io and return parsed JSON."""
    r = requests.get(
        f"{_BASE_URL}{endpoint}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        params=params,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def _parse_tweet(tweet: dict) -> dict:
    """Normalize a tweet object into the standard result format."""
    author = tweet.get("author", {})
    username = author.get("userName", "")
    display_name = author.get("name", username)

    tweet_id = tweet.get("id", "")
    url = f"https://x.com/{username}/status/{tweet_id}" if username and tweet_id else ""
    if not url:
        return None

    # Parse creation date (Twitter format: "Mon Jan 01 00:00:00 +0000 2026")
    created_at = tweet.get("createdAt", "")
    published_date = ""
    if created_at:
        try:
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            published_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            published_date = created_at

    return {
        "title": f"@{username} ({display_name})",
        "url": url,
        "snippet": tweet.get("text", ""),
        "published_date": published_date,
        "source": "twitter",
    }


# ---------------------------------------------------------------------------
# Core functions (importable)
# ---------------------------------------------------------------------------
def tweet_search(query: str | None, api_key: str, *,
                 author: str = None,
                 since: str = None,
                 until: str = None,
                 query_type: str = "Latest",
                 num: int = 5,
                 timeout: int = 30,
                 query_counter: dict = None) -> list:
    """Advanced tweet search by keyword with optional filters.

    Args:
        query: Search keywords.
        api_key: twitterapi.io API key.
        author: Filter by author handle (without @).
        since: Start date, YYYY-MM-DD format.
        until: End date, YYYY-MM-DD format.
        query_type: "Latest" or "Top".
        num: Max results to return (API returns up to _API_MAX_PER_PAGE (20) per page).
        timeout: HTTP request timeout in seconds.
        query_counter: Thread-safe rate limiter dict from search.py.

    Returns:
        list of normalized tweet result dicts.
    """
    if not _check_quota(query_counter):
        return []

    try:
        # Build query string with operators
        parts = [query] if query else []
        if author:
            parts.append(f"from:{author}")
        if since:
            parts.append(f"since:{since}")
        if until:
            parts.append(f"until:{until}")

        data = _api_get("/twitter/tweet/advanced_search", api_key, {
            "query": " ".join(parts),
            "queryType": query_type,
        }, timeout=timeout)

        capped = min(num, _API_MAX_PER_PAGE)
        results = []
        for tweet in data.get("tweets", [])[:capped]:
            parsed = _parse_tweet(tweet)
            if parsed:
                results.append(parsed)
        return results
    except Exception as e:
        print(f"[twitter:search] error: {e}", file=sys.stderr)
        return []


def user_tweets(username: str, api_key: str, *,
                num: int = 5,
                include_replies: bool = False,
                timeout: int = 30,
                query_counter: dict = None) -> list:
    """Get latest tweets from a specific user.

    Args:
        username: Twitter handle (without @).
        api_key: twitterapi.io API key.
        num: Max results to return (API returns up to _API_MAX_PER_PAGE (20) per page).
        include_replies: Whether to include replies.
        timeout: HTTP request timeout in seconds.
        query_counter: Thread-safe rate limiter dict from search.py.

    Returns:
        list of normalized tweet result dicts.
    """
    if not _check_quota(query_counter):
        return []

    try:
        params = {"userName": username}
        if include_replies:
            params["includeReplies"] = "true"

        data = _api_get("/twitter/user/last_tweets", api_key, params, timeout=timeout)

        # This endpoint wraps tweets under a "data" key
        tweets_data = data.get("data", data)
        capped = min(num, _API_MAX_PER_PAGE)
        results = []
        for tweet in tweets_data.get("tweets", [])[:capped]:
            parsed = _parse_tweet(tweet)
            if parsed:
                results.append(parsed)
        return results
    except Exception as e:
        print(f"[twitter:user-tweets] error: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Twitter/X search via twitterapi.io (NOT the official X/Twitter API)")
    sub = ap.add_subparsers(dest="action", required=True)

    # --- search ---
    sp_search = sub.add_parser("search", help="Advanced tweet search by keyword")
    sp_search.add_argument("query", nargs="?", default=None,
                           help="Search keywords (optional if --from is specified)")
    sp_search.add_argument("--from", dest="author", default=None,
                           help="Filter by author handle (without @)")
    sp_search.add_argument("--since", default=None,
                           help="Start date (YYYY-MM-DD)")
    sp_search.add_argument("--until", default=None,
                           help="End date (YYYY-MM-DD)")
    sp_search.add_argument("--query-type", choices=["Latest", "Top"], default="Latest",
                           help="Sort order (default: Latest)")
    sp_search.add_argument("--num", type=int, default=5,
                           help=f"Max results (default: 5, API max: {_API_MAX_PER_PAGE} per page)")

    # --- user-tweets ---
    sp_user = sub.add_parser("user-tweets", help="Get latest tweets from a user")
    sp_user.add_argument("--username", required=True,
                         help="Twitter handle (without @)")
    sp_user.add_argument("--include-replies", action="store_true",
                         help="Include replies (default: exclude)")
    sp_user.add_argument("--num", type=int, default=5,
                         help=f"Max results (default: 5, API max: {_API_MAX_PER_PAGE} per page)")

    args = ap.parse_args()

    api_key = os.environ.get("TWITTER_API_KEY")
    if not api_key:
        print(json.dumps({
            "error": "TWITTER_API_KEY not configured. Get your key at https://twitterapi.io"
        }), file=sys.stderr)
        sys.exit(1)

    if args.action == "search":
        if not args.query and not args.author:
            ap.error("search requires at least a query or --from")
        results = tweet_search(
            args.query, api_key,
            author=args.author,
            since=args.since,
            until=args.until,
            query_type=args.query_type,
            num=args.num,
        )
        output = {
            "action": "search",
            "query": args.query,
            "filters": {
                "author": args.author,
                "since": args.since,
                "until": args.until,
                "query_type": args.query_type,
            },
            "count": len(results),
            "results": results,
        }

    elif args.action == "user-tweets":
        results = user_tweets(
            args.username, api_key,
            num=args.num,
            include_replies=args.include_replies,
        )
        output = {
            "action": "user-tweets",
            "username": args.username,
            "count": len(results),
            "results": results,
        }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
