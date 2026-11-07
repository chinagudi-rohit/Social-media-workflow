"""Upload a vertical video to YouTube as a Short via the Data API v3 resumable upload."""

import os

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeError(RuntimeError):
    pass


def _check(resp, what):
    if resp.status_code >= 400:
        try:
            message = resp.json()["error"]
            message = message.get("message", message) if isinstance(message, dict) else message
        except (ValueError, KeyError):
            message = resp.text[:300]
        raise YouTubeError(f"{what} failed ({resp.status_code}): {message}")
    return resp


def access_token(session, client_id, client_secret, refresh_token):
    resp = session.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    return _check(resp, "token refresh").json()["access_token"]


def build_metadata(captions, yt_config):
    return {
        "snippet": {
            "title": captions["title"],
            "description": captions["description"],
            "tags": captions["tags"],
            "categoryId": yt_config["category_id"],
        },
        "status": {
            "privacyStatus": yt_config["privacy"],
            "selfDeclaredMadeForKids": yt_config["made_for_kids"],
            "containsSyntheticMedia": yt_config["contains_synthetic_media"],
        },
    }


def upload(session, token, video_path, metadata):
    size = os.path.getsize(video_path)
    init = _check(
        session.post(
            UPLOAD_URL,
            params={"uploadType": "resumable", "part": "snippet,status"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(size),
            },
            json=metadata,
        ),
        "upload init",
    )
    location = init.headers.get("Location")
    if not location:
        raise YouTubeError("upload init returned no upload URL")
    with open(video_path, "rb") as f:
        resp = session.put(
            location,
            data=f,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"},
        )
    video = _check(resp, "upload").json()
    return {"id": video["id"], "url": f"https://www.youtube.com/shorts/{video['id']}"}
