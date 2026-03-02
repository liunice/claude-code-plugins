#!/usr/bin/env python3
"""
PreToolUse hook: intercept WebFetch and redirect to content_extract.py.

Reads tool_input from stdin (JSON with tool_input.url), denies the call,
and provides a ready-to-use Bash command in permissionDecisionReason.
"""

import json
import os
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"decision": "allow"}))
        return

    tool_input = data.get("tool_input", {})
    url = tool_input.get("url", "")

    if not url:
        print(json.dumps({"decision": "allow"}))
        return

    # Build the content_extract.py command
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    script_path = os.path.join(plugin_root, "scripts", "content-extract", "content_extract.py")

    # Escape single quotes in URL for shell safety
    safe_url = url.replace("'", "'\\''")

    cmd = f"python3 '{script_path}' --url '{safe_url}'"

    reason = (
        f"Use the search-skills plugin instead. Run this command:\n\n"
        f"```bash\n{cmd}\n```\n\n"
        f"The script extracts content using trafilatura (fast probe), "
        f"with automatic MinerU fallback for anti-crawl sites and PDFs. "
        f"Returns JSON with title, content, content_length, and method used."
    )

    print(json.dumps({
        "decision": "deny",
        "permissionDecisionReason": reason,
    }))


if __name__ == "__main__":
    main()
