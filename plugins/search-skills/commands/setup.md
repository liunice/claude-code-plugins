---
description: Configure search-skills plugin — install Python dependencies and set up API keys
---

# search-skills Setup

Configure Python dependencies and API keys for the search-skills plugin.

## Step 1: Check Python Dependencies

Run the following command to check if required Python packages are installed:

```bash
python3 -c "
missing = []
for pkg in ['requests', 'trafilatura', 'bs4', 'lxml']:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print('MISSING: ' + ','.join(missing))
else:
    print('OK')
"
```

If output is `OK`, skip to Step 2.

If output starts with `MISSING:`, ask the user:

Use AskUserQuestion:

- question: "Some Python dependencies are missing. Install them now?"
- header: "Dependencies"
- options:
  - label: "Yes, install now"
    description: "Run pip3 install for missing packages"
  - label: "No, skip"
    description: "I'll install them manually later"

If user selects "Yes, install now":

```bash
pip3 install requests trafilatura beautifulsoup4 lxml
```

Report whether installation succeeded or failed.

If user selects "No, skip":
- Tell them to run `pip3 install requests trafilatura beautifulsoup4 lxml` manually
- Continue to Step 2

## Step 2: Check API Key Status

Run the following command to check which search source API keys are configured:

```bash
python3 -c "
import os
keys = {
    'BRAVE_API_KEY': os.environ.get('BRAVE_API_KEY', ''),
    'EXA_API_KEY': os.environ.get('EXA_API_KEY', ''),
    'TAVILY_API_KEY': os.environ.get('TAVILY_API_KEY', ''),
    'GROK_API_KEY': os.environ.get('GROK_API_KEY', ''),
    'TWITTER_API_KEY': os.environ.get('TWITTER_API_KEY', ''),
    'MINERU_TOKEN': os.environ.get('MINERU_TOKEN', ''),
}
configured = [k for k, v in keys.items() if v]
missing = [k for k, v in keys.items() if not v]
print('CONFIGURED: ' + (','.join(configured) if configured else 'none'))
print('MISSING: ' + (','.join(missing) if missing else 'none'))
search_keys = [k for k in ['BRAVE_API_KEY', 'EXA_API_KEY', 'TAVILY_API_KEY', 'GROK_API_KEY', 'TWITTER_API_KEY'] if os.environ.get(k)]
print('SEARCH_READY: ' + ('yes' if search_keys else 'no'))
"
```

Report the status clearly:
- Which API keys are already configured
- Which are missing
- Whether at least one search source is ready (required for the plugin to work)

## Step 3: Guide API Key Configuration

If `SEARCH_READY` is `no`, tell the user:

```
At least one search source API key is required.
Add your key(s) to ~/.claude/settings.json under the "env" field:

{
  "env": {
    "BRAVE_API_KEY": "your-key",
    "EXA_API_KEY": "your-key",
    "TAVILY_API_KEY": "your-key",
    "GROK_API_KEY": "your-key",
    "TWITTER_API_KEY": "your-key"
  }
}

Where to get keys:
- Brave:   https://brave.com/search/api/  (free tier available, card required)
- Exa:     https://exa.ai
- Tavily:  https://tavily.com
- Grok:    https://docs.x.ai/docs/overview  (OpenAI-compatible API)
- Twitter: https://twitterapi.io  (NOT the official X/Twitter API; opt-in source, paid)

Optional settings (only add if needed):
- GROK_API_URL:    Custom endpoint (default: https://api.x.ai/v1)
- GROK_MODEL:      Custom model (default: grok-4.20-beta)
- GROK_TIMEOUT:    Grok request timeout in seconds (default: 120)
- SEARCH_TIMEOUT:  Brave/Exa/Tavily request timeout in seconds (default: 30)
- MINERU_TOKEN:    https://mineru.net/apiManage/token (for anti-crawl / PDF extraction)

After editing settings.json, restart Claude Code for changes to take effect.
```

If `SEARCH_READY` is `yes`, tell the user their configuration looks good.

For any missing optional keys (like `MINERU_TOKEN`), mention they can be added later if needed.

## Step 4: Confirm Setup

Tell the user:

```
Setup complete!

IMPORTANT: If you added new environment variables to ~/.claude/settings.json,
restart Claude Code for changes to take effect.

The plugin will intercept WebSearch and WebFetch calls automatically.
Run /search-skills:setup again anytime to check your configuration.
```
