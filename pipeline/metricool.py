"""Ready-to-send arguments for Metricool's `createScheduledPost` connector tool.

The autopilot calls the tool itself (it is an MCP connector, not an HTTP API this CLI can
reach); this module only builds the arguments, one post per network, so every run sends
the same shape: the video as media, the network's own options, and its AI-content flag.
Facebook Reels have no AI flag in Metricool, so the disclosure line goes in the text.
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo


def network_data(platform, post, cfg):
    yt, ig = cfg["youtube"], cfg["instagram"]
    if platform == "youtube":
        return {"youtubeData": {
            "title": post["title"], "type": "short", "privacy": yt["privacy"], "tags": post.get("tags", []),
            "category": cfg["metricool"]["youtube_category"], "madeForKids": yt["made_for_kids"],
            "isAiGeneratedContent": bool(yt["contains_synthetic_media"]),
        }}
    if platform == "instagram":
        return {"instagramData": {"type": "REEL", "showReelOnFeed": ig["share_to_feed"], "isAiGenerated": True}}
    if platform == "facebook":
        return {"facebookData": {"type": "REEL", "title": post["title"]}}
    if platform == "twitter":
        return {"twitterData": {"tags": []}}
    raise ValueError(f"unknown platform: {platform}")


def schedule_args(post, cfg):
    """{blogId, date, info} for createScheduledPost, in the Metricool brand's timezone."""
    mc = cfg["metricool"]
    at = datetime.fromisoformat(post["at"]).astimezone(ZoneInfo(mc["brand_timezone"]))
    text = post["text"]
    if post["platform"] == "facebook":
        text = f"{text}\n\n{post['ai_disclosure_fallback']}"
    info = {
        "autoPublish": True, "draft": False, "descendants": [], "firstCommentText": post.get("first_comment") or "",
        "hasNotReadNotes": False,
        "media": [post["video_url"]], "mediaAltText": [], "shortener": False, "smartLinkData": {"ids": []},
        "providers": [{"network": post["platform"]}],
        "publicationDate": {"dateTime": at.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": mc["brand_timezone"]},
        "text": text,
        **network_data(post["platform"], post, cfg),
    }
    return {"blogId": str(mc["brand_id"]), "date": at.isoformat(timespec="seconds"), "info": json.dumps(info)}
