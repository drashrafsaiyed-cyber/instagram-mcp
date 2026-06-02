# Instagram MCP Server

An MCP server that lets Claude publish, analyze, and engage on your Instagram Business account via the Meta Graph API.

## What it does

**14 tools across four areas:**

| Area | Tools |
|------|-------|
| Account | `get_account_info`, `list_recent_media`, `get_account_insights` |
| Publishing | `publish_photo`, `publish_reel`, `publish_carousel` |
| Insights | `get_media_insights` |
| Comments | `get_comments`, `reply_to_comment`, `hide_comment`, `delete_comment` |
| DMs | `list_conversations`, `get_messages`, `send_dm` |

## Prerequisites

1. **Instagram Business or Creator account** linked to a Facebook Page ✅ (you confirmed)
2. **Meta Developer app** ✅ (you confirmed) — needs these products added:
   - Instagram Graph API
   - Facebook Login (for token generation)
   - (Optional, for DMs) Messenger
3. **Permissions/Scopes** on your access token:
   - `instagram_basic`
   - `instagram_content_publish`
   - `instagram_manage_comments`
   - `instagram_manage_messages` (for DMs)
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_metadata`
4. **A way to host images/videos publicly** for publishing — Instagram fetches media from your URL. Use S3, Cloudinary, imgur, or a public GitHub raw URL.

## Setup (PowerShell, Windows)

```powershell
# 1. Create the project folder
cd "C:\Users\Ashraf Saiyed\mcp-servers"
mkdir instagram-mcp
cd instagram-mcp

# 2. Initialize with uv
uv init .
uv add "fastmcp>=3.0" httpx python-dotenv

# 3. Drop server.py and .env.example into this folder (from this artifact)

# 4. Create your real .env
Copy-Item .env.example .env
notepad .env    # fill in the three values
```

## Getting your tokens & IDs

### Step 1: Get a User Access Token

1. Go to **Meta Graph API Explorer**: https://developers.facebook.com/tools/explorer/
2. Select your app from the top-right dropdown
3. Click **"Generate Access Token"**, then add these permissions one by one:
   - `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `instagram_manage_messages`, `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata`
4. Click **Generate** → log in → approve.

### Step 2: Find your Page ID and IG User ID

In the Graph API Explorer, run:

```
GET  me/accounts
```

This lists your Pages. Copy the `id` of your target Page → that's your `PAGE_ID`.

Then run (replace `{PAGE_ID}`):

```
GET  {PAGE_ID}?fields=instagram_business_account
```

The returned `instagram_business_account.id` is your `IG_USER_ID`.

### Step 3: Get a long-lived Page token

The token from Step 1 is a User token, valid ~1 hour. Convert to a long-lived (60-day) Page token:

```
GET  oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={YOUR_APP_ID}
     &client_secret={YOUR_APP_SECRET}
     &fb_exchange_token={SHORT_LIVED_USER_TOKEN}
```

Then get the Page token:

```
GET  {PAGE_ID}?fields=access_token&access_token={LONG_LIVED_USER_TOKEN}
```

Use this Page `access_token` as `META_ACCESS_TOKEN` in your `.env`. **Page tokens do not expire** as long as you periodically refresh the underlying User token.

## Test before wiring to Claude

```powershell
# From the instagram-mcp folder
npx @modelcontextprotocol/inspector uv run server.py
```

This opens a browser UI. Try calling `get_account_info` first — if your username comes back, your token is good. Then try `list_recent_media`. **Don't try publishing before you've verified read calls work.**

## Wire into Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` and add this under `mcpServers` (alongside your existing `github-writer`):

```json
{
  "mcpServers": {
    "github-writer": {
      "command": "uv",
      "args": ["--directory", "C:\\Users\\Ashraf Saiyed\\mcp-servers\\github-writer-mcp", "run", "server.py"]
    },
    "instagram": {
      "command": "uv",
      "args": ["--directory", "C:\\Users\\Ashraf Saiyed\\mcp-servers\\instagram-mcp", "run", "server.py"]
    }
  }
}
```

**Fully quit Claude Desktop** (right-click the system tray icon → Quit, not just close the window) and reopen.

## Important caveats

- **Media URLs must be PUBLIC.** Instagram fetches from your URL. `localhost`, signed S3 URLs, and Drive links won't work. Use Cloudinary or commit images to a public GitHub repo and use the raw URL.
- **DMs have a 24-hour window.** You can only DM users who messaged you within the last 24 hours. Cold outreach via DM is not possible (and would get you banned anyway).
- **Publishing rate limit: 50 posts/24h** per account.
- **Reels: max 90 seconds, max 1GB, MP4 H.264 + AAC.** Vertical 9:16 recommended.
- **Carousels: 2-10 images**, all must be public URLs.
- **Token refresh:** Page tokens don't expire, but if you change your password or revoke the User token, the Page token dies too. Regenerate via the steps above when that happens.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `code 190, subcode 463` | Token expired. Regenerate. |
| `code 100` on publish | Image URL not accessible to Meta. Check it loads in incognito. |
| `code 10, subcode 2207024` | Missing `instagram_content_publish` permission. |
| `Container processing failed` | Video too long, wrong codec, or URL 404s after first fetch. |
| DM tool errors | `PAGE_ID` not set, or you haven't subscribed your page to messaging webhooks. |
| Claude doesn't see the tools | Fully quit + reopen Claude Desktop. Check `%APPDATA%\Claude\logs\mcp*.log`. |

## What you can ask Claude now

- "Show me my last 10 posts and their like counts"
- "Which of my recent reels got the best reach?"
- "Post this photo with the caption: 'Friday vibes 🌅' and these hashtags: #..."
- "List unanswered comments from the last 24 hours and draft replies"
- "Summarize my DMs from today and tell me which ones need a personal reply"
