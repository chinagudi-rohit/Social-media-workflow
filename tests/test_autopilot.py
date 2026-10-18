import importlib.util
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from pipeline import budget, dashboard, library, metrics, production, trends, uploadpost
from pipeline.config import ROOT, load_niches, load_platforms, load_yaml, niche_by_id
from pipeline.script import build_captions, validate_library

NICHES = load_niches()
PLATFORMS = load_platforms()
PROD = load_yaml("production.yaml")
SCRIPTS = library.load_scripts()
NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)

spec = importlib.util.spec_from_file_location("assemble", ROOT / "tools" / "assemble.py")
assemble = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assemble)


def manifest(niche, days_ago, script_id=None, structure=None, video=True):
    return {
        "run_id": f"r-{niche}-{days_ago}-{script_id}", "niche_id": niche, "topic": "t",
        "created_at": (NOW - timedelta(days=days_ago)).isoformat(), "script_id": script_id,
        "structure": structure, "video": {"url": "https://v" if video else None}, "posts": {},
    }


# --- library ------------------------------------------------------------------------

def test_library_has_50_valid_monetizable_scripts():
    assert len(SCRIPTS) == 50
    for s in SCRIPTS:
        assert validate_library(s, NICHES, PLATFORMS, library.STRUCTURES) == [], s["id"]


def test_library_scripts_run_over_a_minute_of_speech():
    for s in SCRIPTS:
        words = sum(len(b["narration"].split()) for b in s["blocks"])
        assert words >= 155, s["id"]  # ~2.4 words/s keeps narration past 60 s


def test_pick_spreads_across_niches_and_skips_used():
    scored = [{"id": "investing", "score": 9}, {"id": "credit-debt", "score": 8}]
    used = [manifest("investing", 1, script_id="inv-25-vs-35", structure="comparison")]
    picks = library.pick(SCRIPTS, scored, used, 2)
    assert [p["niche_id"] for p in picks] == ["investing", "credit-debt"]
    assert picks[0]["id"] != "inv-25-vs-35"
    assert picks[0]["structure"] != "comparison"  # varies structure within the niche


def test_pick_fills_from_one_niche_when_others_are_empty():
    scored = [{"id": "insurance", "score": 9}]
    assert len(library.pick(SCRIPTS, scored, [], 3)) == 3


def test_stock_counts_unused():
    used = [manifest("investing", 1, script_id="inv-25-vs-35")]
    assert library.stock(SCRIPTS, used)["investing"] == 5


# --- trends -------------------------------------------------------------------------

def test_trend_template_validates_and_bad_values_fail():
    doc = trends.template(NICHES, "2026-10-18")
    assert trends.validate(doc, NICHES) == []
    doc["niches"]["investing"]["trend_boost"] = 5
    doc["niches"]["investing"]["topic_ideas"] = [{"topic": "x", "sources": []}]
    errors = trends.validate(doc, NICHES)
    assert any("trend_boost" in e for e in errors) and any("source URL" in e for e in errors)


def test_score_rewards_rpm_trend_and_penalizes_recent_posts():
    snap = trends.template(NICHES, "2026-10-18")
    snap["niches"]["history-mysteries"]["trend_boost"] = 3.0
    scored = trends.score_niches(NICHES, snap, [manifest("investing", 0)], NOW)
    by_id = {s["id"]: s for s in scored}
    assert by_id["investing"]["parts"]["recency"] < 0
    assert by_id["history-mysteries"]["score"] > by_id["investing"]["score"]
    assert scored == sorted(scored, key=lambda s: s["score"], reverse=True)


def test_load_latest_picks_newest_on_or_before(tmp_path):
    for d in ("2026-10-16", "2026-10-17", "2026-10-19"):
        (tmp_path / f"{d}.json").write_text(json.dumps({"date": d}))
    assert trends.load_latest(tmp_path, "2026-10-18")["date"] == "2026-10-17"
    assert trends.load_latest(tmp_path, "2026-10-01") is None


# --- budget -------------------------------------------------------------------------

def test_days_until_renewal():
    assert budget.days_until_renewal(date(2026, 10, 18), 18) == 31
    assert budget.days_until_renewal(date(2026, 10, 17), 18) == 1
    assert budget.days_until_renewal(date(2026, 12, 20), 18) == 29


def test_videos_today_paces_the_budget():
    # Plenty of budget: one a day (capped).
    assert budget.videos_today(1050, 31, 80, 30, 0, 1) == 1
    # Budget for ~half the days: every other day.
    assert budget.videos_today(560, 31, 80, 30, 1, 1) == 0
    assert budget.videos_today(560, 31, 80, 30, 2, 1) == 1
    # Nothing spendable above the reserve.
    assert budget.videos_today(100, 31, 80, 10, 5, 1) == 0


def test_plan_today_uses_active_tier():
    plan = budget.plan_today(PROD, 1050, date(2026, 10, 18), None)
    assert plan["tier"] == "lean" and 25 < plan["est_cost_per_video"] < 40
    assert plan["videos_today"] == 1


# --- production -----------------------------------------------------------------------

def test_generation_requests_lean_tier():
    s = next(x for x in SCRIPTS if x["id"] == "inv-rule-of-72")
    voice = PROD["voices"][0]
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), PROD, voice)
    assert len(g["keyframes"]) == 8 and [m["block"] for m in g["motion"]] == [1, 3, 5, 7]
    assert g["motion"][0]["params"]["medias"][0]["role"] == "start_image"
    assert "No written text" in g["keyframes"][0]["params"]["prompt"]
    assert g["voice"]["params"]["voice_id"] == voice["voice_id"]
    assert 25 < g["estimated_credits"] < 40


def test_render_plan_and_asset_validation():
    s = next(x for x in SCRIPTS if x["id"] == "inv-rule-of-72")
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), PROD, PROD["voices"][0])
    assets = {"keyframes": {str(i): f"https://k/{i}" for i in range(1, 9)}, "motion": {"1": "https://m/1"},
              "voice": "https://v"}
    errors = production.validate_assets(assets, s, g)
    assert any("motion.3" in e for e in errors)
    assets["motion"].update({b: f"https://m/{b}" for b in ("3", "5", "7")})
    assert production.validate_assets(assets, s, g) == []
    plan = production.render_plan(s, assets, PROD["render"])
    assert plan["min_duration"] > 60 and plan["blocks"][1]["motion_url"] is None
    assert plan["blocks"][0]["text"] == s["blocks"][0]["narration"]


# --- assembler helpers ----------------------------------------------------------------

def test_block_windows_follow_transcript():
    word_times = [i * 0.5 for i in range(20)]
    w = assemble.block_windows([5, 5, 10], word_times, 12.0)
    assert w[0][0] == 0 and w[-1][1] == 12.0
    assert w[0][1] == pytest.approx(2.5) and w[1][1] == pytest.approx(5.0)


def test_caption_chunks_merge_split_tokens():
    words = [(0, .3, "up"), (.3, .5, "to"), (.5, .8, "$9"), (.8, 1.0, ",000."), (1.0, 1.3, "tax"), (1.3, 1.6, "-free")]
    assert [c[2] for c in assemble.caption_chunks(words)] == ["UP TO $9,000", "TAX-FREE"]


def test_ass_document_and_duration():
    doc = assemble.ass_document([(0, 1, "HELLO")], 1080, 1920, "Montserrat ExtraBold", 96, 560)
    assert "Style: Cap,Montserrat ExtraBold,96" in doc and "HELLO" in doc
    assert assemble.final_duration(58.0, 1.2, 62) == 62 and assemble.final_duration(70, 1.2, 62) == 71.2
    assert assemble.kenburns("pan_up", 90, 1080, 1920, 30).startswith("zoompan=")


# --- Upload-Post ------------------------------------------------------------------------

CAPS = build_captions(next(x for x in SCRIPTS if x["id"] == "pf-hsa-triple-tax"),
                      niche_by_id("personal-finance"), PLATFORMS)


def test_build_form_labels_ai_on_every_platform():
    fields = uploadpost.build_form(CAPS, "https://v.mp4", "me", list(uploadpost.PLATFORMS), PLATFORMS,
                                   "run-1", facebook_page_id="42")
    d = {}
    for k, v in fields:
        d.setdefault(k, []).append(v)
    assert d["platform[]"] == ["tiktok", "instagram", "youtube", "facebook"]
    for flag in ("is_aigc", "is_ai_generated", "containsSyntheticMedia", "facebook_is_ai_generated"):
        assert d[flag] == ["true"]
    assert d["video"] == ["https://v.mp4"] and d["facebook_page_id"] == ["42"]
    assert d["instagram_title"][0].startswith(CAPS["instagram"]["caption"][:20])


def test_build_form_requires_facebook_page():
    with pytest.raises(uploadpost.UploadPostError):
        uploadpost.build_form(CAPS, "https://v.mp4", "me", ["facebook"], PLATFORMS, "run-1")


class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.text = status, body or {}, json.dumps(body or {})

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        return self.responses.pop(0)

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw))
        return self.responses.pop(0)


def test_publish_sends_idempotency_key_and_multipart():
    s = FakeSession(FakeResp(body={"success": True, "request_id": "run-1"}))
    body = uploadpost.publish(s, "KEY", [("user", "me"), ("platform[]", "tiktok")], "run-1")
    _, url, kw = s.calls[0]
    assert url.endswith("/api/upload") and body["request_id"] == "run-1"
    assert kw["headers"] == {"Authorization": "Apikey KEY", "Idempotency-Key": "run-1"}
    assert ("platform[]", (None, "tiktok")) in kw["files"]


def test_publish_error_raises():
    s = FakeSession(FakeResp(403, {"success": False, "message": "TikTok uploads are not available on the Free plan."}))
    with pytest.raises(uploadpost.UploadPostError, match="Free plan"):
        uploadpost.publish(s, "KEY", [], "r")


def test_platform_results_normalizes():
    body = {"status": "completed", "results": {
        "tiktok": {"status": "completed", "publish_id": "p1", "fallback_to_inbox": True},
        "youtube": {"success": True, "url": "https://youtu.be/x", "video_id": "x"},
        "facebook": {"skipped": True, "status": "skipped"},
    }}
    r = uploadpost.platform_results(body)
    assert r["tiktok"]["draft"] and r["tiktok"]["id"] == "p1"
    assert r["youtube"] == {"status": "published", "url": "https://youtu.be/x", "id": "x", "error": None, "draft": False}
    assert r["facebook"]["status"] == "skipped"


# --- metrics ------------------------------------------------------------------------------

def test_youtube_revenue_parses_rows():
    s = FakeSession(FakeResp(body={"columnHeaders": [{"name": "day"}, {"name": "views"}, {"name": "estimatedRevenue"}],
                                   "rows": [["2026-10-17", 1000, 0.42]]}))
    rows = metrics.youtube_revenue(s, "tok", date(2026, 10, 1), date(2026, 10, 17))
    assert rows == [{"day": "2026-10-17", "views": 1000, "estimatedRevenue": 0.42}]
    assert s.calls[0][2]["params"]["ids"] == "channel==MINE"


def test_facebook_earnings_parses_values():
    s = FakeSession(FakeResp(body={"data": [{"values": [
        {"end_time": "2026-10-17T07:00:00+0000", "value": {"amount": 1.5}},
        {"end_time": "2026-10-18T07:00:00+0000", "value": 2}]}]}))
    rows = metrics.facebook_earnings(s, "https://g/v23.0", "42", "tok", date(2026, 10, 17), date(2026, 10, 18))
    assert rows == [{"day": "2026-10-17", "earnings": 1.5}, {"day": "2026-10-18", "earnings": 2.0}]


def test_earnings_rollup_and_dashboard_rows():
    yt = [{"day": "2026-10-17", "estimatedRevenue": 1.25}, {"day": "2026-09-01", "estimatedRevenue": 9}]
    fb = [{"day": "2026-10-18", "earnings": 2.0}]
    manual = [{"date": "2026-10-18", "platform": "tiktok", "amount_usd": 3.5, "source": "creator_rewards"}]
    totals = metrics.earnings_by_platform(yt, fb, manual, date(2026, 9, 19), date(2026, 10, 18))
    assert totals == {"youtube": 1.25, "facebook": 2.0, "tiktok": 3.5}
    stats = metrics.normalize_uploadpost({"tiktok": {"followers": 10, "views": 500, "junk": 1},
                                          "x": {"error": "nope"}})
    assert stats == {"tiktok": {"followers": 10, "views": 500}}
    videos = [{"run_id": "r1", "date": "2026-10-18", "niche": "investing", "topic": "t", "credits": 31,
               "published": True, "posts": {"youtube": {"status": "published", "url": "u"}}}]
    snap = metrics.snapshot(date(2026, 10, 18), stats, totals,
                            [{"date": "2026-10-18", "tiktok": 3.5, "facebook": 2.0}], videos,
                            {"balance": 1050, "spent_30d": 31})
    assert snap["earnings_total_30d"] == 6.75
    scored = trends.score_niches(NICHES, None, [], NOW)
    files = dashboard.datasets(snap, PROD, scored, NICHES, date(2026, 10, 18))
    assert files["earnings_daily"] == [{"date": "2026-10-18", "platform": "tiktok", "usd": 3.5},
                                       {"date": "2026-10-18", "platform": "facebook", "usd": 2.0}]
    assert [r["platform"] for r in files["platforms"]] == ["youtube", "tiktok", "facebook"]
    assert files["videos"][0]["youtube"] == "published" and files["videos"][0]["tiktok"] == "not posted"
    assert files["credits"][0]["videos_left"] == (1050 - 80) // files["credits"][0]["cost_per_video"]
    assert len(files["niches"]) == len(NICHES) and len(files["programs"]) == 4


def test_hosted_assembler_matches_repo():
    import hashlib
    render = PROD["render"]
    digest = hashlib.sha256((ROOT / "tools" / "assemble.py").read_bytes()).hexdigest()
    assert render["assembler_url"].startswith("https://")
    assert render["assembler_sha256"] == digest, "tools/assemble.py changed: re-upload it and update config/production.yaml"


def test_auto_schedule_targets_today_or_now():
    morning = datetime(2026, 10, 18, 11, 0, tzinfo=timezone.utc)   # 07:00 in New York
    assert uploadpost.auto_schedule(morning, "12:30", "America/New_York") == "2026-10-18T12:30:00"
    evening = datetime(2026, 10, 18, 22, 0, tzinfo=timezone.utc)
    assert uploadpost.auto_schedule(evening, "12:30", "America/New_York") is None
    fields = uploadpost.build_form(CAPS, "https://v.mp4", "me", ["youtube"], PLATFORMS, "r",
                                   "2026-10-18T12:30:00", timezone="America/New_York")
    assert ("timezone", "America/New_York") in fields and ("scheduled_date", "2026-10-18T12:30:00") in fields
