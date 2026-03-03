#!/usr/bin/env python3
"""
PreToolUse hook: intercept WebFetch and redirect to the content-extract skill.

Reads tool_input from stdin (JSON with tool_input.url), denies the call,
and directs the AI to use the content-extract skill instead.
"""

import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
        url = data["tool_input"]["url"]
    except (KeyError, json.JSONDecodeError, EOFError) as err:
        print(f"hook-error: {err}", file=sys.stderr)
        sys.exit(1)

    if not url:
        sys.exit(0)

    reason = f"Please use the Skill tool to invoke 'search-skills:content-extract' with args: '{url}'"

    print(json.dumps({
        "systemMessage": "MANDATORY: WebFetch is disabled. You MUST immediately call the Skill tool as specified in the deny reason. Do NOT skip the extraction or use other methods.",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, separators=(',', ':')))


if __name__ == "__main__":
    main()
