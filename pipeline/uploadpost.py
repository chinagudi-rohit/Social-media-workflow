"""Publish to TikTok, Instagram, YouTube and Facebook in one call through Upload-Post.

Docs: https://docs.upload-post.com/api/upload-video (POST /api/upload, multipart form,
`Authorization: Apikey <key>`). The video is passed as a public URL (the Higgsfield-hosted
file), the upload runs asynchronously, and GET /api/uploadposts/status reports per-platform
results. Every platform gets its AI-generated label set.
"""

API = "https://api.upload-post.com/api"
PLATFORMS = ("tiktok", "instagram", "youtube", "facebook")


STATES = {"completed": "published", "success": "published", "pending": "processing", "queued": "processing",
          "in_progress": "processing"}


class UploadPostError(RuntimeError):
    pass


def _check(resp, what):
    try:
        body = resp.json()
    except ValueError:
        body = {"message": resp.text[:300]}
    if resp.status_code >= 400 or body.get("success") is False:
        msg = body.get("message") or body.get("error") or str(body)[:300]
        raise UploadPostError(f"{what} failed ({resp.status_code}): {msg}")
    return body


def build_form(captions, video_url, user, platforms, cfg, request_id, scheduled_date=None, facebook_page_id=None,
               timezone=None):
    """Multipart fields as (name, value) pairs, ready for requests' `files=`."""
    yt, tt, ig = captions["youtube"], captions["tiktok"], captions["instagram"]
    fields = [
        ("user", user),
        ("video", video_url),
        ("title", yt["title"]),
        ("request_id", request_id),
        ("external_id", request_id),
        ("async_upload", "true"),
        ("is_ai_generated", "true"),
    ]
    fields += [("platform[]", p) for p in platforms]
    if "tiktok" in platforms:
        fields += [
            ("tiktok_title", tt["description"]),
            ("is_aigc", "true"),
            ("post_mode", "MEDIA_UPLOAD" if cfg["tiktok"].get("mode") == "UPLOAD_TO_DRAFT" else "DIRECT_POST"),
        ]
    if "instagram" in platforms:
        fields += [
            ("instagram_title", ig["caption"]),
            ("media_type", "REELS"),
            ("share_to_feed", str(cfg["instagram"]["share_to_feed"]).lower()),
        ]
    if "youtube" in platforms:
        fields += [
            ("youtube_title", yt["title"]),
            ("youtube_description", yt["description"]),
            ("categoryId", str(cfg["youtube"]["category_id"])),
            ("privacyStatus", cfg["youtube"]["privacy"]),
            ("containsSyntheticMedia", "true"),
            ("selfDeclaredMadeForKids", str(cfg["youtube"]["made_for_kids"]).lower()),
        ]
        fields += [("tags[]", t) for t in yt["tags"]]
    if "facebook" in platforms:
        if not facebook_page_id:
            raise UploadPostError("facebook needs a page id (UPLOADPOST_FACEBOOK_PAGE_ID)")
        fields += [
            ("facebook_page_id", facebook_page_id),
            ("facebook_media_type", "REELS"),
            ("facebook_title", yt["title"]),
            ("facebook_description", ig["caption"]),
            ("facebook_is_ai_generated", "true"),
        ]
    if scheduled_date:
        fields.append(("scheduled_date", scheduled_date))
        if timezone:
            fields.append(("timezone", timezone))
    return fields


def local_time(at_iso, tz_name):
    """An ISO time with offset as the wall-clock time Upload-Post's `scheduled_date` takes."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.fromisoformat(at_iso).astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%dT%H:%M:%S")


def publish(session, api_key, fields, request_id):
    resp = session.post(
        f"{API}/upload",
        headers={"Authorization": f"Apikey {api_key}", "Idempotency-Key": request_id},
        files=[(k, (None, v)) for k, v in fields],
        timeout=120,
    )
    return _check(resp, "upload")


def status(session, api_key, request_id=None, job_id=None):
    params = {"request_id": request_id} if request_id else {"job_id": job_id}
    resp = session.get(f"{API}/uploadposts/status", headers={"Authorization": f"Apikey {api_key}"},
                       params=params, timeout=60)
    return _check(resp, "status")


def platform_results(status_body):
    """Normalize a status response to {platform: {status, url, id, error}}."""
    raw = status_body.get("results") or status_body.get("platforms") or {}
    if isinstance(raw, list):
        raw = {r.get("platform"): r for r in raw if r.get("platform")}
    out = {}
    for platform, r in raw.items():
        state = r.get("status") or ("completed" if r.get("success") else "failed")
        if r.get("skipped"):
            state = "skipped"
        out[platform] = {
            "status": STATES.get(state, state),
            "url": r.get("url"),
            "id": r.get("post_id") or r.get("video_id") or r.get("publish_id") or r.get("container_id"),
            "error": r.get("error"),
            "draft": bool(r.get("fallback_to_inbox")),
        }
    return out


def analytics(session, api_key, profile, platforms, facebook_page_id=None):
    params = {"platforms": ",".join(platforms)}
    if facebook_page_id and "facebook" in platforms:
        params["page_id"] = facebook_page_id
    resp = session.get(f"{API}/analytics/{profile}", headers={"Authorization": f"Apikey {api_key}"},
                       params=params, timeout=60)
    return _check(resp, "analytics")
