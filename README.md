# 📸 Instagram MCP Server

**Control your Instagram from Claude — post, analyze, reply to DMs, manage comments. All by chatting.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP%203.x-green.svg)](https://github.com/jlowin/fastmcp)
[![Deploy to Render](https://img.shields.io/badge/Deploy-Render%20Free-blue?logo=render)](https://render.com/deploy?repo=https://github.com/drashrafsaiyed-cyber/instagram-mcp)

---

<!-- Add your demo GIF here: record Claude Desktop controlling Instagram and drop the .gif below -->
> 🎬 **Demo GIF coming soon** — Claude posting a reel, reading insights, replying to comments live on screen.

---

## What You Can Do

Ask Claude in plain English. It handles the API.

```
"Show my last 10 posts and which got the most reach"
"Post this image with caption: Monday motivation 💪 #AI #Health"
"Read my DMs from today and draft replies for the questions"
"Hide all spam comments on my latest reel"
"What are my account insights for this week?"
"Which of my reels got the best watch time?"
```

---

## Use Cases

### 📊 Content Creator
- Morning briefing: *"Show yesterday's post performance — reach, saves, shares"*
- Strategy: *"Compare my last 5 reels by reach and tell me what worked"*
- Scheduling prep: *"Draft 3 caption options for this fitness post"*

### 🏥 Doctor / Professional
- Engagement: *"Reply to all comments on my last post professionally"*
- Growth tracking: *"How many followers did I gain this week?"*
- Content audit: *"List all posts from this month with their engagement rates"*

### 🛍️ Small Business
- Customer service: *"Show DMs from the last 24 hours and reply to order questions"*
- Publishing: *"Post this product photo with this caption and these hashtags"*
- Analytics: *"Which post type (reel/carousel/photo) gets me the most reach?"*

---

## Tools (14 total)

| Category | Tool | What it does |
|----------|------|-------------|
| **Account** | `get_account_info` | Followers, bio, post count |
| | `update_profile` | Update bio text and/or website URL |
| | `list_recent_media` | Last N posts with engagement stats |
| | `get_account_insights` | Reach, profile views, follower growth |
| **Insights** | `get_media_insights` | Per-post reach, saves, views, interactions |
| **Publishing** | `publish_photo` | Post a photo with caption + hashtags |
| | `publish_reel` | Post a Reel (video) |
| | `publish_carousel` | Post 2–10 images as carousel |
| **Comments** | `get_comments` | Read all comments on a post |
| | `reply_to_comment` | Reply to a comment |
| | `hide_comment` | Hide spam/unwanted comments |
| | `delete_comment` | Permanently delete a comment |
| **DMs** | `list_conversations` | List active DM threads |
| | `get_messages` | Read messages in a thread |
| | `send_dm` | Reply to a DM |

---

## Quick Start

### Option A — Claude Web + Mobile (Recommended)

**1. Deploy your server (free, 2 min):**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/drashrafsaiyed-cyber/instagram-mcp)

Fill in `META_ACCESS_TOKEN` and `IG_USER_ID` when prompted. ([How to get these ↓](#getting-your-token))

**2. Connect to Claude web:**
- [claude.ai](https://claude.ai) → Settings → Integrations → Add Integration
- Paste: `https://your-app-name.onrender.com/mcp`

**3. Done.** Open a new chat and try: *"Show my recent Instagram posts"*

---

### Option B — Claude Desktop (Local)

```bash
git clone https://github.com/drashrafsaiyed-cyber/instagram-mcp
cd instagram-mcp
uv sync
cp .env.example .env
# Fill .env with your token and user ID
uv run server.py
```

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "instagram": {
      "command": "uv",
      "args": ["--directory", "/path/to/instagram-mcp", "run", "server.py"],
      "env": {
        "META_ACCESS_TOKEN": "your_token",
        "IG_USER_ID": "your_ig_user_id",
        "ACCOUNT_NAME": "My Instagram"
      }
    }
  }
}
```

---

### Option C — Multiple Instagram Accounts (Claude Desktop)

Run the **same server folder** multiple times with different env vars. Claude sees each as a separate named MCP and never confuses them.

```json
{
  "mcpServers": {
    "instagram-personal": {
      "command": "uv",
      "args": ["--directory", "/path/to/instagram-mcp", "run", "server.py"],
      "env": {
        "META_ACCESS_TOKEN": "TOKEN_FOR_ACCOUNT_1",
        "IG_USER_ID": "IG_USER_ID_1",
        "ACCOUNT_NAME": "Personal"
      }
    },
    "instagram-business": {
      "command": "uv",
      "args": ["--directory", "/path/to/instagram-mcp", "run", "server.py"],
      "env": {
        "META_ACCESS_TOKEN": "TOKEN_FOR_ACCOUNT_2",
        "IG_USER_ID": "IG_USER_ID_2",
        "ACCOUNT_NAME": "My Business"
      }
    }
  }
}
```

Claude will show separate tools per account — *"Post this to My Business"* picks the right one automatically.

> Each account must be a **Business or Creator** Instagram account, and must be added as a tester in your Meta app → Use cases → Step 2: Generate access tokens → Add account.

---

## Getting Your Token

This server uses the **Instagram Login API** (`graph.instagram.com`) — the modern Meta approach for Instagram Business/Creator accounts.

**Step 1 — Create or open your Meta app**
1. Go to [developers.facebook.com](https://developers.facebook.com) → My Apps
2. Create a new app or open an existing one
3. Add use case: **"Manage messaging & content on Instagram"**

**Step 2 — Generate your access token**
1. Use cases → Customize → **API Setup with Instagram Login**
2. Step 2: **Generate access tokens** → click Generate next to your account
3. Copy the token → this is your `META_ACCESS_TOKEN`
4. Your numeric **IG User ID** is shown below your username on the same page

**Step 3 — Refresh before expiry (60 days)**
```bash
curl "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=YOUR_TOKEN"
```
Or just run this in your project folder:
```bash
uv run python -c "
import httpx, re
from pathlib import Path
env = Path('.env').read_text()
token = re.search(r'META_ACCESS_TOKEN=(.+)', env).group(1).strip()
r = httpx.get('https://graph.instagram.com/refresh_access_token', params={'grant_type':'ig_refresh_token','access_token':token})
new = r.json()['access_token']
Path('.env').write_text(env.replace(token, new))
print('Refreshed. Expires in:', r.json()['expires_in']//86400, 'days')
"
```

---

## Requirements

- Instagram **Business** or **Creator** account
- Meta Developer app with **"Manage messaging & content on Instagram"** use case
- Python 3.11+

> **Publishing note:** Images and videos must be at a public HTTPS URL — Instagram fetches from your URL. Use [Cloudinary](https://cloudinary.com) (free), S3, or a public GitHub raw URL. Local file paths won't work.

---

## Architecture

```
Claude (Web/Desktop)
      │  MCP protocol
      ▼
instagram-mcp server  (FastMCP 3.x, streamable-http or stdio)
      │  HTTPS REST
      ▼
graph.instagram.com   (Instagram Login API v21.0)
      │
      ▼
Your Instagram account
```

**Why `graph.instagram.com` and not `graph.facebook.com`?**
This server uses the newer Instagram Login API which issues `IGAA...` tokens and routes through `graph.instagram.com`. The older Facebook Graph API approach required a linked Facebook Page and `EAA...` tokens. The new flow is simpler — just your Instagram account, no Facebook Page needed.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Cannot parse access token` | Token expired or wrong type. Regenerate via the steps above. |
| `code 100` on insights | Invalid metric name. Metrics differ between account vs media endpoints. |
| `code 190` | Token expired. Run the refresh command. |
| Container processing failed | Video too long (>90s), wrong codec, or URL returns 404 after first fetch. |
| Empty DM list | No active 24h messaging window. Someone needs to DM you first. |
| Claude doesn't see tools | Restart Claude Desktop fully (tray icon → Quit). Check logs at `%APPDATA%\Claude\logs\`. |

---

## Contributing

PRs welcome. If you add a new tool or fix a metric name mismatch, please:
1. Test against a real Instagram account
2. Update the tool table in this README
3. Note which API permission the new tool requires

---

## License

MIT — free to use, fork, and deploy commercially.

---

*Built with [FastMCP](https://github.com/jlowin/fastmcp) · Powered by [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)*
