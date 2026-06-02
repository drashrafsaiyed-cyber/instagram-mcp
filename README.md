# Instagram MCP Server

**Control your Instagram from Claude — on web, mobile, and desktop.**

One-click deploy your own Instagram MCP server and connect it to Claude web (claude.ai) or Claude Desktop. Post photos, read insights, manage comments, and reply to DMs — all by chatting with Claude.

---

## ⚡ One-Click Deploy (Free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/drashrafsaiyed-cyber/instagram-mcp)

> Free tier · No credit card · Always-on after first request

---

## What You Can Do

| Area | Tools |
|------|-------|
| **Account** | `get_account_info`, `list_recent_media`, `get_account_insights` |
| **Insights** | `get_media_insights` |
| **Publishing** | `publish_photo`, `publish_reel`, `publish_carousel` |
| **Comments** | `get_comments`, `reply_to_comment`, `hide_comment`, `delete_comment` |
| **DMs** | `list_conversations`, `get_messages`, `send_dm` |

---

## Setup (3 steps, ~10 minutes)

### Step 1 — Get your Instagram access token

1. Go to [Meta Developer Portal](https://developers.facebook.com) → create or open your app
2. Add use case: **"Manage messaging & content on Instagram"**
3. Go to **Use cases → Customize → API Setup with Instagram Login → Generate access tokens**
4. Click **Generate token** next to your Instagram account → copy it
5. Your **IG User ID** is shown below your username on that same page

> Token lasts 60 days. Refresh anytime:
> ```
> GET https://graph.instagram.com/refresh_access_token
>     ?grant_type=ig_refresh_token&access_token=YOUR_TOKEN
> ```

### Step 2 — Deploy to Render

1. Click the **Deploy to Render** button above
2. Sign up / log in with GitHub (no card needed)
3. Fill in the environment variables:
   - `META_ACCESS_TOKEN` → your token from Step 1
   - `IG_USER_ID` → your numeric Instagram account ID from Step 1
4. Click **Deploy** — done in ~2 minutes
5. Your server URL: `https://your-app-name.onrender.com/mcp`

### Step 3 — Connect to Claude

**Claude Web + Mobile (claude.ai):**
1. Settings → Integrations → Add Integration
2. Paste: `https://your-app-name.onrender.com/mcp`
3. New chat → *"Show my recent Instagram posts"* 🎉

**Claude Desktop:**
```json
{
  "mcpServers": {
    "instagram": {
      "command": "uv",
      "args": ["--directory", "/path/to/instagram-mcp", "run", "server.py"]
    }
  }
}
```

---

## Local Development

```bash
git clone https://github.com/drashrafsaiyed-cyber/instagram-mcp
cd instagram-mcp
uv sync
cp .env.example .env
# Fill .env with your token and user ID
uv run server.py
```

---

## Example Prompts

Once connected, try these in Claude:

- *"Show me my last 10 posts and their stats"*
- *"Which of my recent reels got the best reach?"*
- *"What are my account insights for this week?"*
- *"Post this image [url] with caption: Friday vibes 🌅 #..."*
- *"Show me all comments on my latest post and draft replies"*
- *"List my DMs from today and tell me which need a reply"*

---

## Important Notes

- **Images/videos must be at public URLs** — Instagram fetches from your URL. Use Cloudinary, S3, or raw GitHub URLs. Local paths won't work.
- **DMs: 24-hour window** — you can only reply to users who messaged you in the last 24 hours.
- **Publishing limit: 50 posts/24h** per account.
- **Free Render tier sleeps** after 15 min idle — first request takes ~30-50s to wake up, then it's fast.

---

## Requirements

- Instagram **Business** or **Creator** account
- Meta Developer app with **"Manage messaging & content on Instagram"** use case enabled
- Python 3.11+

---

## Tech Stack

- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api) via `graph.instagram.com`
- [uv](https://github.com/astral-sh/uv) — Python package manager

---

## License

MIT — free to use, fork, and deploy.

---

*Built with Claude Code*
