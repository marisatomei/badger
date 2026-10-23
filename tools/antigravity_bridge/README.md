# Antigravity Badge Bridge

Desktop bridge and lifecycle hooks connecting Google Antigravity to the Badgeware hardware badge.

## Quickstart

### 1. Pair with your Badge
When the badge is showing the 8-digit PIN (press Up on the badge):

```sh
python antigravity_bridge.py pair <PIN> --host <BADGE_IP>
```

Saves pairing credentials to `~/.gemini/antigravity_badge.json`.

### 2. Stream Live Sessions

**Option A: Transcript Watcher**
```sh
python antigravity_bridge.py watch
```

**Option B: Lifecycle Hooks**
Copy [`hooks.json`](./hooks.json) to `.agents/hooks.json` or `~/.gemini/config/hooks.json`.

### 3. Manual Testing CLI

```sh
# Query connection
python antigravity_bridge.py status

# Push states
python antigravity_bridge.py state working
python antigravity_bridge.py state attention
python antigravity_bridge.py state complete
python antigravity_bridge.py state idle

# Push agent indicators and usage
python antigravity_bridge.py agents "antigravity=w,linter=a"
python antigravity_bridge.py usage "Tokens: 14k|Turns: 3"
```
