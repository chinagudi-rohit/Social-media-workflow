import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from pipeline import instagram, youtube
from pipeline.config import ROOT, load_niches, load_platforms, niche_by_id
from pipeline.niches import pick_niche, recent_topics
from pipeline.runs import create_run, load_manifest, record_post
from pipeline.script import build_captions, merge_hashtags, validate

NICHES = load_niches(include_inactive=True)
PLATFORMS = load_platforms()
EXAMPLE = json.loads((ROOT / "templates" / "example_script.json").read_text())


def errors_for(**changes):
    script = copy.deepcopy(EXAMPLE)
    script.update(changes)
    return validate(script, NICHES, PLATFORMS)


# --- script validation ---------------------------------------------------------

def test_example_script_is_valid():
    assert validate(EXAMPLE, NICHES, PLATFORMS) == []


def test_unknown_niche_rejected():
    assert any("niche_id" in e for e in errors_for(niche_id="crypto-moonshots"))


def test_short_block_narration_rejected():
    blocks = copy.deepcopy(EXAMPLE["blocks"])
    blocks[1]["narration"] = "Too short."
    assert any(e.startswith("block 2: narration has 2 words") for e in errors_for(blocks=blocks))


def test_block_count_limits():
    assert any("blocks" in e for e in errors_for(blocks=EXAMPLE["blocks"][:1]))
    assert any("blocks" in e for e in errors_for(blocks=EXAMPLE["blocks"] * 4))


def test_clip_needs_one_block_but_no_narration_or_sources():
    clip = {"format": "clip", "blocks": [{"visual": "Golden-hour drone shot over a canyon road"}], "sources": []}
    assert errors_for(**clip) == []


def test_narrated_needs_a_source_url():
    assert any("source" in e for e in errors_for(sources=[{"claim": "x"}]))


def test_long_hook_and_title_rejected():
    assert any("hook" in e for e in errors_for(hook="word " * 16))
    assert any("youtube_title" in e for e in errors_for(youtube_title="x" * 101))
    assert any("running time" in e for e in errors_for(youtube_title="Index Funds in 80 Seconds"))


def test_on_screen_hook_is_short():
    assert errors_for(on_screen_hook="The *math* nobody explains") == []
    assert any("on_screen_hook" in e for e in errors_for(on_screen_hook="one"))
    assert any("on_screen_hook" in e for e in errors_for(on_screen_hook="word " * 8))


def test_hashtag_with_hash_rejected():
    assert any("hashtag" in e for e in errors_for(hashtags=["#401k"]))


# --- captions --------------------------------------------------------------------

def test_merge_hashtags_dedupes_case_insensitively_and_limits():
    assert merge_hashtags(["Money", "a"], ["money", "b", "c"], 3) == ["Money", "a", "b"]


def test_captions_respect_platform_limits():
    niche = niche_by_id(EXAMPLE["niche_id"])
    caps = build_captions(EXAMPLE, niche, PLATFORMS)

    assert set(caps) == {"instagram", "youtube", "twitter"}
    assert caps["instagram"]["caption"].startswith(EXAMPLE["captions"]["hook_line"])
    assert niche["disclaimer"] in caps["instagram"]["caption"]
    assert caps["instagram"]["caption"].count("#") == PLATFORMS["instagram"]["max_hashtags"]
    assert caps["youtube"]["title"] == EXAMPLE["youtube_title"] + " #Shorts"
    assert "https://www.irs.gov" in caps["youtube"]["description"]
    assert caps["youtube"]["description"].endswith("#Shorts")


def test_long_caption_is_truncated():
    script = copy.deepcopy(EXAMPLE)
    script["captions"]["body"] = "x" * 5000
    caps = build_captions(script, niche_by_id(script["niche_id"]), PLATFORMS)
    assert len(caps["instagram"]["caption"]) == PLATFORMS["instagram"]["caption_max"]
    assert caps["instagram"]["caption"].endswith("…")


# --- niche rotation and runs ---------------------------------------------------

NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)


def run(niche_id, days_ago, topic="t"):
    return {"niche_id": niche_id, "topic": topic, "created_at": (NOW - timedelta(days=days_ago)).isoformat()}


def test_unused_niche_comes_first_in_config_order():
    assert pick_niche(NICHES, [run(NICHES[0]["id"], 1)], NOW)["id"] == NICHES[1]["id"]


def test_weight_makes_niche_come_back_sooner():
    niches = [{"id": "a", "weight": 2}, {"id": "b", "weight": 1}]
    # a: 3 days * 2 = 6 beats b: 5 days * 1 = 5
    assert pick_niche(niches, [run("a", 3), run("b", 5)], NOW)["id"] == "a"


def test_recent_topics_newest_first():
    manifests = [run("a", 5, "old"), run("a", 1, "new"), run("b", 0, "other")]
    assert recent_topics(manifests, "a") == ["new", "old"]


def test_create_run_and_record_post(tmp_path):
    run_dir = create_run("pets", "Grapes are toxic to dogs!", runs_dir=tmp_path, today="2026-10-15")
    assert run_dir.name == "2026-10-15-pets-grapes-are-toxic-to-dogs"
    assert create_run("pets", "Grapes are toxic to dogs!", runs_dir=tmp_path, today="2026-10-15").name.endswith("-2")

    record_post(run_dir, "youtube", status="published", id="abc")
    assert load_manifest(run_dir)["status"] == "published"            # every post so far is live
    record_post(run_dir, "instagram", status="published", id="1")
    record_post(run_dir, "twitter", status="scheduled", id="2")
    assert load_manifest(run_dir)["status"] == "partially_published"
    record_post(run_dir, "twitter", status="published")
    record_post(run_dir, "facebook", status="scheduled", at="2026-10-15T12:30:00-04:00", error="x")
    record_post(run_dir, "facebook", status="published", error=None)
    fb = load_manifest(run_dir)["posts"]["facebook"]
    assert fb["at"] == "2026-10-15T12:30:00-04:00" and "error" not in fb   # merged, None removes
    assert load_manifest(run_dir)["status"] == "published"


# --- publishers ------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, body=None, headers=None):
        self.status_code, self._body, self.headers = status_code, body or {}, headers or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def _next(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kw):
        return self._next("GET", url, **kw)

    def post(self, url, **kw):
        return self._next("POST", url, **kw)

    def put(self, url, **kw):
        return self._next("PUT", url, **kw)


IG_ARGS = dict(base_url="https://graph.test/v1", ig_user_id="42", token="SECRET", video_url="https://v/x.mp4", caption="hi")


def test_instagram_publish_polls_until_finished():
    session = FakeSession([
        FakeResponse(body={"id": "c1"}),
        FakeResponse(body={"status_code": "IN_PROGRESS"}),
        FakeResponse(body={"status_code": "FINISHED"}),
        FakeResponse(body={"id": "m1"}),
        FakeResponse(body={"permalink": "https://instagram.com/reel/m1"}),
    ])
    sleeps = []
    result = instagram.publish_reel(session, **IG_ARGS, sleep=sleeps.append)

    assert result == {"id": "m1", "url": "https://instagram.com/reel/m1"}
    assert session.calls[0][2]["data"]["media_type"] == "REELS"
    assert session.calls[3][1] == "https://graph.test/v1/42/media_publish"
    assert session.calls[3][2]["data"]["creation_id"] == "c1"
    assert sleeps == [10]


def test_instagram_container_error_raises():
    session = FakeSession([FakeResponse(body={"id": "c1"}), FakeResponse(body={"status_code": "ERROR", "status": "bad codec"})])
    with pytest.raises(instagram.InstagramError, match="bad codec"):
        instagram.publish_reel(session, **IG_ARGS, sleep=lambda s: None)


def test_instagram_api_error_hides_token():
    session = FakeSession([FakeResponse(400, {"error": {"message": "Invalid video_url"}})])
    with pytest.raises(instagram.InstagramError) as e:
        instagram.publish_reel(session, **IG_ARGS)
    assert "Invalid video_url" in str(e.value) and "SECRET" not in str(e.value)


def test_youtube_upload(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0" * 1234)
    caps = build_captions(EXAMPLE, niche_by_id(EXAMPLE["niche_id"]), PLATFORMS)["youtube"]
    metadata = youtube.build_metadata(caps, PLATFORMS["youtube"])
    session = FakeSession([
        FakeResponse(body={"access_token": "tok"}),
        FakeResponse(headers={"Location": "https://upload.test/session"}),
        FakeResponse(body={"id": "yt123"}),
    ])

    token = youtube.access_token(session, "id", "secret", "refresh")
    result = youtube.upload(session, token, video, metadata)

    assert result == {"id": "yt123", "url": "https://www.youtube.com/shorts/yt123"}
    init = session.calls[1][2]
    assert init["headers"]["X-Upload-Content-Length"] == "1234"
    assert init["json"]["status"]["containsSyntheticMedia"] is True
    assert init["json"]["status"]["selfDeclaredMadeForKids"] is False
    assert session.calls[2][1] == "https://upload.test/session"


def test_youtube_error_message():
    session = FakeSession([FakeResponse(403, {"error": {"message": "quotaExceeded"}})])
    with pytest.raises(youtube.YouTubeError, match="quotaExceeded"):
        youtube.access_token(session, "id", "secret", "refresh")
