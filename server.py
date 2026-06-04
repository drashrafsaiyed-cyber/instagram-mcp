"""
Instagram MCP Server

Exposes Instagram Graph API (publishing, insights, comments, DMs) as MCP tools.
Built using the mcp-server-builder skill workflow.

Requirements:
- Instagram Business or Creator account linked to a Facebook Page
- Meta Developer app with instagram_basic, instagram_content_publish,
  instagram_manage_comments, instagram_manage_messages, pages_show_list,
  pages_read_engagement permissions
- Long-lived Page access token (60-day, refreshable)

Setup:
    uv init instagram-mcp && cd instagram-mcp
    uv add "fastmcp>=3.0" httpx python-dotenv

Create a .env file in the same directory with:
    META_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxx
    IG_USER_ID=178414xxxxxxxxxx
    PAGE_ID=104xxxxxxxxxxxxx        # optional, only needed for DMs

Test:
    npx @modelcontextprotocol/inspector uv run server.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Annotated, Literal

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import Field

# Load .env from the same directory as this script
load_dotenv(Path(__file__).parent / ".env")

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
IG_USER_ID = os.environ.get("IG_USER_ID")
# ACCOUNT_NAME labels this instance so Claude knows which account it's talking to.
# Set it per-instance: "Dr. Ashraf (Personal)", "Surgicare ICU", "Pushpam", "Anita AI"
ACCOUNT_NAME = os.environ.get("ACCOUNT_NAME", "Instagram")

if not ACCESS_TOKEN:
    print("FATAL: META_ACCESS_TOKEN env var required. Create a .env file.", file=sys.stderr)
    sys.exit(1)
if not IG_USER_ID:
    print("FATAL: IG_USER_ID env var required (your IG Business account ID).", file=sys.stderr)
    sys.exit(1)

GRAPH = "https://graph.instagram.com/v21.0"

# MCP server name = account name so Claude's tool picker shows the right label
mcp = FastMCP(ACCOUNT_NAME)


# ────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────────────────

def _client() -> httpx.Client:
    """Build an HTTP client. Access token is passed per-request as a query param
    because that's what the Graph API expects."""
    return httpx.Client(timeout=60.0)


def _check(resp: httpx.Response, context: str) -> dict:
    """Raise a helpful error if the Graph API call failed, else return JSON."""
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error", {})
            msg = err.get("message", resp.text[:300])
            code = err.get("code", resp.status_code)
            sub = err.get("error_subcode", "")
            raise ValueError(
                f"{context} failed (code {code}, subcode {sub}): {msg}. "
                f"Common causes: expired token, missing permission, or container not ready."
            )
        except ValueError:
            raise
        except Exception:
            raise ValueError(f"{context} failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


def _wait_for_container(client: httpx.Client, container_id: str, max_wait_s: int = 120) -> None:
    """Poll a media container until it's FINISHED or fail. IG requires this for video/reel."""
    start = time.time()
    while time.time() - start < max_wait_s:
        resp = client.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
        )
        data = _check(resp, "Container status check")
        status = data.get("status_code", "")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise ValueError(f"Container processing failed: {data.get('status', 'no detail')}")
        time.sleep(3)
    raise ValueError(f"Container {container_id} not ready after {max_wait_s}s. Try again or check media URL.")


# ────────────────────────────────────────────────────────────────────────────
# Tools — Account & Insights
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_account_info() -> dict:
    """Fetch basic info about the connected Instagram Business account.

    Use this first to verify the token and IG user ID are valid. Returns username,
    follower count, media count, and account type.
    """
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/me",
            params={
                "fields": "username,name,biography,followers_count,follows_count,media_count,profile_picture_url",
                "access_token": ACCESS_TOKEN,
            },
        )
        return _check(resp, "get_account_info")


@mcp.tool()
def list_recent_media(
    limit: Annotated[int, Field(ge=1, le=50, default=10, description="Max posts to return")] = 10,
) -> list[dict]:
    """List recent posts/reels from the account.

    Returns id, caption, media_type, permalink, timestamp, like_count, comments_count.
    Use the returned IDs with get_media_insights or get_comments.
    """
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/me/media",
            params={
                "fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
                "limit": limit,
                "access_token": ACCESS_TOKEN,
            },
        )
        data = _check(resp, "list_recent_media")
        return data.get("data", [])


@mcp.tool()
def get_media_insights(
    media_id: Annotated[str, Field(description="The media ID from list_recent_media")],
) -> dict:
    """Get performance metrics for a single post/reel.

    Returns reach, impressions, saved, video_views (if video), and engagement.
    Different media types return different metrics — reels have plays, photos don't.
    """
    # Metric set depends on media type, but Graph API will return what's available.
    # Using a broad set; API ignores unsupported ones for the given type.
    metrics = "reach,saved,likes,comments,shares,total_interactions,views"
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/{media_id}/insights",
            params={"metric": metrics, "access_token": ACCESS_TOKEN},
        )
        data = _check(resp, "get_media_insights")
        # Flatten for readability
        result = {}
        for item in data.get("data", []):
            name = item.get("name")
            values = item.get("values", [{}])
            result[name] = values[0].get("value") if values else None
        return result


@mcp.tool()
def get_account_insights(
    period: Annotated[
        Literal["day", "week", "days_28"],
        Field(default="day", description="Reporting period"),
    ] = "day",
) -> dict:
    """Get account-level insights (reach, impressions, profile views, follower growth).

    Use 'day' for last 24h, 'week' for 7 days, 'days_28' for monthly trends.
    Useful for content strategy decisions.
    """
    metrics = "reach,profile_views,follower_count,website_clicks,accounts_engaged,total_interactions"
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/me/insights",
            params={"metric": metrics, "period": period, "access_token": ACCESS_TOKEN},
        )
        data = _check(resp, "get_account_insights")
        result = {}
        for item in data.get("data", []):
            name = item.get("name")
            values = item.get("values", [])
            result[name] = values[-1].get("value") if values else None
        return result


@mcp.tool()
def update_profile(
    biography: Annotated[
        str | None,
        Field(default=None, max_length=150, description="New bio text. Max 150 characters. Pass None to leave unchanged."),
    ] = None,
    website: Annotated[
        str | None,
        Field(default=None, description="New website URL (must start with http:// or https://). Pass None to leave unchanged."),
    ] = None,
) -> dict:
    """Update your Instagram Business profile bio and/or website URL.

    THIS IS A WRITE OPERATION. At least one of biography or website must be provided.
    Changes are live immediately on your public profile.

    Required permission: instagram_business_manage_profile
    (Add this in your Meta app → Use cases → Permissions and features if missing.)
    """
    if biography is None and website is None:
        raise ValueError("Provide at least one field to update: biography or website.")

    params: dict = {"access_token": ACCESS_TOKEN}
    if biography is not None:
        params["biography"] = biography
    if website is not None:
        params["website"] = website

    with _client() as client:
        resp = client.post(
            f"{GRAPH}/me",
            params=params,
        )
        result = _check(resp, "update_profile")
        # Fetch current profile to confirm what changed
        verify = client.get(
            f"{GRAPH}/me",
            params={"fields": "username,biography,website", "access_token": ACCESS_TOKEN},
        )
        current = verify.json() if verify.status_code == 200 else {}
        return {
            "success": result.get("success", True),
            "updated_fields": {k: v for k, v in params.items() if k != "access_token"},
            "current_profile": current,
        }


# ────────────────────────────────────────────────────────────────────────────
# Tools — Publishing
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def publish_photo(
    image_url: Annotated[str, Field(description="PUBLIC https URL of the image. Must be JPEG, < 8MB, accessible without auth.")],
    caption: Annotated[str, Field(default="", max_length=2200, description="Caption with hashtags. Max 30 hashtags.")] = "",
) -> dict:
    """Publish a single photo to the Instagram feed.

    THIS IS A WRITE OPERATION. The image URL must be publicly accessible — Instagram fetches
    it from your URL. Local file paths won't work; upload to S3/Cloudinary/imgur first.
    Returns the published post ID and permalink.
    """
    with _client() as client:
        # Step 1: create container
        resp = client.post(
            f"{GRAPH}/me/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": ACCESS_TOKEN,
            },
        )
        container = _check(resp, "publish_photo (create container)")
        container_id = container["id"]

        # Photos don't usually need polling, but check briefly
        _wait_for_container(client, container_id, max_wait_s=30)

        # Step 2: publish
        resp = client.post(
            f"{GRAPH}/me/media_publish",
            params={"creation_id": container_id, "access_token": ACCESS_TOKEN},
        )
        published = _check(resp, "publish_photo (publish)")
        post_id = published["id"]

        # Fetch permalink
        resp = client.get(
            f"{GRAPH}/{post_id}",
            params={"fields": "permalink", "access_token": ACCESS_TOKEN},
        )
        info = _check(resp, "publish_photo (get permalink)")
        return {"post_id": post_id, "permalink": info.get("permalink", "")}


@mcp.tool()
def publish_reel(
    video_url: Annotated[str, Field(description="PUBLIC https URL of an MP4 video. Must be < 1GB, < 90 seconds, accessible without auth.")],
    caption: Annotated[str, Field(default="", max_length=2200, description="Caption with hashtags")] = "",
    share_to_feed: Annotated[bool, Field(default=True, description="Also show in main feed grid")] = True,
) -> dict:
    """Publish a Reel to Instagram.

    THIS IS A WRITE OPERATION. Video URL must be publicly accessible. Reel processing takes
    30-60s on Instagram's side — this tool waits. Returns post ID and permalink.
    """
    with _client() as client:
        # Step 1: create reel container
        resp = client.post(
            f"{GRAPH}/me/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": share_to_feed,
                "access_token": ACCESS_TOKEN,
            },
        )
        container = _check(resp, "publish_reel (create container)")
        container_id = container["id"]

        # Reels need polling — video processing
        _wait_for_container(client, container_id, max_wait_s=180)

        # Step 2: publish
        resp = client.post(
            f"{GRAPH}/me/media_publish",
            params={"creation_id": container_id, "access_token": ACCESS_TOKEN},
        )
        published = _check(resp, "publish_reel (publish)")
        post_id = published["id"]

        resp = client.get(
            f"{GRAPH}/{post_id}",
            params={"fields": "permalink", "access_token": ACCESS_TOKEN},
        )
        info = _check(resp, "publish_reel (get permalink)")
        return {"post_id": post_id, "permalink": info.get("permalink", "")}


@mcp.tool()
def publish_carousel(
    image_urls: Annotated[list[str], Field(min_length=2, max_length=10, description="2-10 PUBLIC image URLs. Must all be accessible JPEGs.")],
    caption: Annotated[str, Field(default="", max_length=2200, description="Caption applied to the whole carousel")] = "",
) -> dict:
    """Publish a carousel (multi-image) post. Accepts 2-10 images.

    THIS IS A WRITE OPERATION. Each image must be publicly accessible. Creates a child
    container per image, then a carousel container, then publishes. Slow — expect 30-60s.
    """
    with _client() as client:
        # Step 1: create child containers
        children: list[str] = []
        for url in image_urls:
            resp = client.post(
                f"{GRAPH}/me/media",
                params={
                    "image_url": url,
                    "is_carousel_item": True,
                    "access_token": ACCESS_TOKEN,
                },
            )
            child = _check(resp, f"publish_carousel (create child for {url[:50]})")
            children.append(child["id"])

        # Step 2: create carousel container
        resp = client.post(
            f"{GRAPH}/me/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
                "access_token": ACCESS_TOKEN,
            },
        )
        container = _check(resp, "publish_carousel (create carousel container)")
        container_id = container["id"]

        _wait_for_container(client, container_id, max_wait_s=60)

        # Step 3: publish
        resp = client.post(
            f"{GRAPH}/me/media_publish",
            params={"creation_id": container_id, "access_token": ACCESS_TOKEN},
        )
        published = _check(resp, "publish_carousel (publish)")
        post_id = published["id"]

        resp = client.get(
            f"{GRAPH}/{post_id}",
            params={"fields": "permalink", "access_token": ACCESS_TOKEN},
        )
        info = _check(resp, "publish_carousel (get permalink)")
        return {"post_id": post_id, "permalink": info.get("permalink", ""), "image_count": len(image_urls)}


# ────────────────────────────────────────────────────────────────────────────
# Tools — Comments
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_comments(
    media_id: Annotated[str, Field(description="Media ID from list_recent_media")],
    limit: Annotated[int, Field(ge=1, le=50, default=20, description="Max comments to return")] = 20,
) -> list[dict]:
    """List comments on a post.

    Returns id, text, username, timestamp, like_count, and replies (if any). Use the
    comment IDs with reply_to_comment, hide_comment, or delete_comment.
    """
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/{media_id}/comments",
            params={
                "fields": "id,text,username,timestamp,like_count,replies",
                "limit": limit,
                "access_token": ACCESS_TOKEN,
            },
        )
        data = _check(resp, "get_comments")
        return data.get("data", [])


@mcp.tool()
def reply_to_comment(
    comment_id: Annotated[str, Field(description="Comment ID from get_comments")],
    message: Annotated[str, Field(min_length=1, max_length=2200, description="Reply text")],
) -> dict:
    """Reply to a comment on a post.

    THIS IS A WRITE OPERATION. The reply will be threaded under the original comment and
    publicly visible. Returns the reply's comment ID.
    """
    with _client() as client:
        resp = client.post(
            f"{GRAPH}/{comment_id}/replies",
            params={"message": message, "access_token": ACCESS_TOKEN},
        )
        data = _check(resp, "reply_to_comment")
        return {"reply_id": data.get("id"), "in_reply_to": comment_id}


@mcp.tool()
def hide_comment(
    comment_id: Annotated[str, Field(description="Comment ID from get_comments")],
    hide: Annotated[bool, Field(default=True, description="True to hide, False to unhide")] = True,
) -> dict:
    """Hide or unhide a comment. Hidden comments are invisible to others but not deleted.

    THIS IS A WRITE OPERATION. Useful for spam/troll comments you'd rather not fully delete.
    """
    with _client() as client:
        resp = client.post(
            f"{GRAPH}/{comment_id}",
            params={"hide": str(hide).lower(), "access_token": ACCESS_TOKEN},
        )
        _check(resp, "hide_comment")
        return {"comment_id": comment_id, "hidden": hide}


@mcp.tool()
def delete_comment(
    comment_id: Annotated[str, Field(description="Comment ID from get_comments")],
) -> dict:
    """Permanently delete a comment.

    THIS IS A WRITE/DESTRUCTIVE OPERATION. Cannot be undone. Prefer hide_comment unless the
    comment is clearly spam, abuse, or violating your community standards.
    """
    with _client() as client:
        resp = client.delete(
            f"{GRAPH}/{comment_id}",
            params={"access_token": ACCESS_TOKEN},
        )
        _check(resp, "delete_comment")
        return {"comment_id": comment_id, "deleted": True}


# ────────────────────────────────────────────────────────────────────────────
# Tools — Direct Messages
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_conversations(
    limit: Annotated[int, Field(ge=1, le=50, default=20, description="Max conversations to return")] = 20,
) -> list[dict]:
    """List recent DM conversations on the Instagram account.

    Returns conversation IDs and participants. Use conversation IDs with get_messages.
    Only conversations from the last ~24h messaging window will be actionable for sending.
    """
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/me/conversations",
            params={
                "platform": "instagram",
                "fields": "id,participants,updated_time,message_count",
                "limit": limit,
                "access_token": ACCESS_TOKEN,
            },
        )
        data = _check(resp, "list_conversations")
        return data.get("data", [])


@mcp.tool()
def get_messages(
    conversation_id: Annotated[str, Field(description="Conversation ID from list_conversations")],
    limit: Annotated[int, Field(ge=1, le=25, default=10, description="Max messages to return")] = 10,
) -> list[dict]:
    """Read messages from a DM conversation.

    Returns message id, text content, sender, and timestamp. Use the sender's IGSID with
    send_dm to reply.
    """
    with _client() as client:
        resp = client.get(
            f"{GRAPH}/{conversation_id}",
            params={
                "fields": f"messages.limit({limit}){{id,message,from,created_time}}",
                "access_token": ACCESS_TOKEN,
            },
        )
        data = _check(resp, "get_messages")
        return data.get("messages", {}).get("data", [])


@mcp.tool()
def send_dm(
    recipient_igsid: Annotated[str, Field(description="Recipient's Instagram-scoped ID (IGSID) from get_messages 'from' field")],
    message: Annotated[str, Field(min_length=1, max_length=1000, description="Message text to send")],
) -> dict:
    """Send a DM reply to a user.

    THIS IS A WRITE OPERATION. IMPORTANT: Instagram enforces a 24-hour messaging window —
    you can only DM users who have messaged you within the last 24 hours, unless using
    a message tag (not supported in this tool). Cold DMs will fail and may trigger rate limits.
    """
    with _client() as client:
        resp = client.post(
            f"{GRAPH}/me/messages",
            json={
                "recipient": {"id": recipient_igsid},
                "message": {"text": message},
            },
            params={"access_token": ACCESS_TOKEN},
        )
        data = _check(resp, "send_dm")
        return {"message_id": data.get("message_id"), "recipient": recipient_igsid}


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        port = int(os.environ.get("PORT", 8000))
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run()
