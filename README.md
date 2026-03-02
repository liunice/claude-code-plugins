# claude-code-plugins

A public plugin marketplace for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Python 3 with pip

## Installation

1. Add the marketplace and install the plugin:

```bash
/plugin marketplace add liunice/claude-code-plugins
/plugin install search-skills@liunice-plugins
```

2. Run the setup command to install Python dependencies and configure API keys:

```bash
/search-skills:setup
```

The setup will guide you to add API keys to `~/.claude/settings.json`. **At least one** search source key (Brave / Exa / Tavily / Grok) is required.

3. Restart Claude Code for hooks and environment variables to take effect.

## Plugins

| Plugin | Description |
|--------|-------------|
| [search-skills](./plugins/search-skills/) | Multi-source search (Brave + Exa + Tavily + Grok) with intelligent content extraction (trafilatura + MinerU). Replaces built-in WebSearch/WebFetch via PreToolUse hooks. |

## Credits

The [search-skills](./plugins/search-skills/) plugin is based on [openclaw-search-skills](https://github.com/blessonism/openclaw-search-skills), adapted for Claude Code's plugin architecture.

## License

MIT
