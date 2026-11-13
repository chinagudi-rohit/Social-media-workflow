"""Publish a Reel through the Instagram Graph API (container -> poll -> publish)."""

import time


class InstagramError(RuntimeError):
    pass


def _check(resp, what):
    # Never put the URL in the message: it can carry the access token.
    if resp.status_code >= 400:
        try:
            message = resp.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = resp.text[:300]
        raise InstagramError(f"{what} failed ({resp.status_code}): {message}")
    return resp.json()


def publish_reel(
    session,
    *,
    base_url,
    ig_user_id,
    token,
    video_url,
    caption,
    share_to_feed=True,
    poll_seconds=10,
    timeout_seconds=900,
    sleep=time.sleep,
):
    container = _check(
        session.post(
            f"{base_url}/{ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": "true" if share_to_feed else "false",
                "access_token": token,
            },
        ),
        "create container",
    )["id"]

    # Instagram downloads and transcodes the video before it can be published.
    waited = 0
    while True:
        status = _check(
            session.get(
                f"{base_url}/{container}",
                params={"fields": "status_code,status", "access_token": token},
            ),
            "container status",
        )
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise InstagramError(f"container {container} {code}: {status.get('status', '')}")
        if waited >= timeout_seconds:
            raise InstagramError(f"container {container} not ready after {timeout_seconds}s (last: {code})")
        sleep(poll_seconds)
        waited += poll_seconds

    media_id = _check(
        session.post(
            f"{base_url}/{ig_user_id}/media_publish",
            data={"creation_id": container, "access_token": token},
        ),
        "publish",
    )["id"]
    info = _check(
        session.get(f"{base_url}/{media_id}", params={"fields": "permalink", "access_token": token}),
        "permalink lookup",
    )
    return {"id": media_id, "url": info.get("permalink")}
