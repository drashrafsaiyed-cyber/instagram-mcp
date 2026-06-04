# Upgrade Roadmap — Unlock 100% Control (Facebook Login API)

The current server uses the **Instagram Login API** (`graph.instagram.com`, `IGAA…` tokens).
It is simple to set up (just an Instagram account) but supports only a subset of features.

To unlock **ads, post deletion, likes/engagement, events, and full hashtag search**, the
server must use the **Facebook Login API** (`graph.facebook.com`, `EAA…` tokens), which is
the full Instagram Graph API.

> ⚠️ **One feature is impossible on ANY API:** editing bio / name / profile picture / website.
> Meta blocks profile writes on every Instagram API for spam prevention. No tool can do it.
> `update_profile` will never work — keep it documented as unsupported.

---

## Feature unlock comparison

| Feature | Instagram Login (now) | Facebook Login (upgrade) |
|---|:---:|:---:|
| Account info, insights | ✅ | ✅ |
| Publish photo / reel / carousel | ✅ | ✅ |
| Read + reply comments | ✅ | ✅ |
| Hide / delete comments | ✅ | ✅ |
| DMs (read/send) | ✅ | ✅ |
| **Like media / comments** | ❌ | ✅ |
| **Delete posts** | ❌ | ✅ |
| **Upcoming events** | ❌ | ✅ |
| **Ads (create/insights)** | ❌ | ✅ |
| Hashtag search | partial | ✅ full |
| Edit bio/profile | ❌ | ❌ (impossible everywhere) |

---

## Step 1 — Meta setup (per Instagram account)

For EACH account (personal, Surgicare, Pushpam, Anita AI):

1. Instagram app → Settings → switch account to **Business** (not Creator — Business links to Pages).
2. Create a **Facebook Page** (or use an existing one) and **link it** to the Instagram account:
   Instagram → Settings → Account → Sharing to other apps → Facebook → connect Page.
3. In the Meta app, switch the use case to **"API setup with Facebook login"** (the panel we currently skip).
4. In Graph API Explorer:
   - Choose **Facebook Login** (not Instagram Login)
   - Add permissions: `instagram_basic`, `instagram_content_publish`,
     `instagram_manage_comments`, `instagram_manage_insights`, `instagram_manage_messages`,
     `instagram_manage_engagement`, `instagram_manage_contents`,
     `instagram_manage_upcoming_events`, `pages_show_list`, `pages_read_engagement`,
     `pages_manage_metadata`, `business_management`
     (+ `ads_management`, `ads_read` if the account runs ads)
   - Generate token → this is an `EAA…` token
5. Exchange for a long-lived (60-day) token:
   ```
   GET https://graph.facebook.com/oauth/access_token
       ?grant_type=fb_exchange_token
       &client_id={APP_ID}
       &client_secret={APP_SECRET}
       &fb_exchange_token={SHORT_EAA_TOKEN}
   ```
6. Find the IG User ID via the linked Page:
   ```
   GET https://graph.facebook.com/v21.0/me/accounts                → get PAGE_ID
   GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account
   ```

---

## Step 2 — Code changes in `server.py`

### a) Base URL + endpoint pattern
- Change `GRAPH = "https://graph.instagram.com/v21.0"` → `https://graph.facebook.com/v21.0`
- Replace `/me/...` with `/{IG_USER_ID}/...` for account-level calls
  (Facebook Login flow addresses the IG account by its numeric ID, not `/me`).
- DMs: use the linked Page — `/{PAGE_ID}/conversations` and `/{PAGE_ID}/messages`,
  and re-add `messaging_type: "RESPONSE"` for the Messenger Platform.

### b) Re-add PAGE_ID env var (needed for DMs + ads discovery)
```python
PAGE_ID = os.environ.get("PAGE_ID")
```

### c) Recommended: dual-mode flag (best for open source)
Let users pick their setup without forking:
```python
API_FLOW = os.environ.get("API_FLOW", "instagram_login")  # or "facebook_login"
if API_FLOW == "facebook_login":
    GRAPH = "https://graph.facebook.com/v21.0"
    BASE = f"/{IG_USER_ID}"        # address account by ID
else:
    GRAPH = "https://graph.instagram.com/v21.0"
    BASE = "/me"                   # address account by /me
```
Then build endpoints as `f"{GRAPH}{BASE}/media"` etc. Tools that only exist on Facebook
Login (likes, delete_post, events, ads) should raise a clear error when `API_FLOW` is
`instagram_login`, telling the user to switch flows.

### d) Ads tools
Ads use `graph.facebook.com/{ad_account_id}/insights` and `/me/adaccounts`. These only
work with a Facebook Login token that has `ads_management`/`ads_read` AND a role on the
ad account. Keep them gated behind `API_FLOW == "facebook_login"`.

---

## Step 3 — Multi-account (already supported)

The `ACCOUNT_NAME` env var + named MCP instances (see README "Option C") already handle
running one server per account. Each account just needs its own `EAA…` token, `IG_USER_ID`,
and `PAGE_ID` in its instance config.

---

## Step 4 — Testing order after upgrade

1. `get_account_info` → confirm token + IG_USER_ID valid
2. `like_media` on one of your own posts → confirms engagement scope
3. `delete_post` on a throwaway post → confirms contents scope
4. `get_ad_accounts` → confirms ads scope (only if account has an ad account)
5. `create_event` → confirms events scope

---

*Bio editing remains impossible. Everything else reaches 100% on the Facebook Login flow.*
