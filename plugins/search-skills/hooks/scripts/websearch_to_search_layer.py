#!/usr/bin/env python3
"""
PreToolUse hook: intercept WebSearch and redirect to the search-layer skill.

Reads tool_input from stdin (JSON with tool_input.query), denies the call,
and directs the AI to use the search-layer skill instead.
"""

import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data["tool_input"]
        query = tool_input["query"]
    except (KeyError, json.JSONDecodeError, EOFError) as err:
        print(f"hook-error: {err}", file=sys.stderr)
        sys.exit(1)

    if not query:
        sys.exit(0)

    reason = f"Please use the Skill tool to invoke 'search-skills:search-layer' with args: '{query}'"

    print(json.dumps({
        "systemMessage": "MANDATORY: WebSearch is disabled. You MUST immediately call the Skill tool as specified in the deny reason. Do NOT skip the search or answer from memory.",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, separators=(',', ':')))


if __name__ == "__main__":
    main()
