#!/usr/bin/env python3
"""
PreToolUse hook: intercept WebSearch and redirect to search.py.

Reads tool_input from stdin (JSON with tool_input.query), denies the call,
and provides a ready-to-use Bash command in permissionDecisionReason.
"""

import json
import os
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # If we can't parse input, allow the original tool call
        print(json.dumps({"decision": "allow"}))
        return

    tool_input = data.get("tool_input", {})
    query = tool_input.get("query", "")

    if not query:
        print(json.dumps({"decision": "allow"}))
        return

    # Build the search.py command
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    script_path = os.path.join(plugin_root, "scripts", "search-layer", "search.py")

    # Escape single quotes in query for shell safety
    safe_query = query.replace("'", "'\\''")

    # Provide the base command without --mode; the search-layer skill's Phase 1
    # intent classification guides Claude to pick the right mode and parameters.
    cmd = f"python3 '{script_path}' '{safe_query}' --num 5"

    reason = (
        f"Use the search-skills plugin instead. "
        f"Follow the search-layer skill to classify intent and choose the right "
        f"--mode (fast/deep/answer), --intent, and --freshness parameters.\n\n"
        f"Base command:\n\n"
        f"```bash\n{cmd}\n```\n\n"
        f"Available options:\n"
        f"  --mode fast|deep|answer  (default: deep)\n"
        f"  --intent factual|status|comparison|tutorial|exploratory|news|resource\n"
        f"  --freshness pd|pw|pm|py  (24h/week/month/year)\n"
        f"  --queries \"q1\" \"q2\"      (multiple sub-queries)\n"
        f"  --domain-boost d1,d2     (boost specific domains)"
    )

    print(json.dumps({
        "decision": "deny",
        "permissionDecisionReason": reason,
    }))


if __name__ == "__main__":
    main()
