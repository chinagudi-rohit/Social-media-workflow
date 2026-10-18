import importlib.util
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from pipeline import budget, dashboard, library, metrics, production, timing, trends, uploadpost
from pipeline.config import ROOT, load_niches, load_platforms, load_yaml, niche_by_id
from pipeline.script import build_captions, validate_library

NICHES = load_niches()
ALL_NICHES = load_niches(include_inactive=True)
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
        assert validate_library(s, ALL_NICHES, PLATFORMS, library.STRUCTURES) == [], s["id"]


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
    snap["niches"]["legal-money"]["trend_boost"] = 3.0
    scored = trends.score_niches(NICHES, snap, [manifest("investing", 0)], NOW)
    by_id = {s["id"]: s for s in scored}
    assert by_id["investing"]["parts"]["recency"] < 0
    assert by_id["legal-money"]["score"] > by_id["investing"]["score"]
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
    snap["earnings_sources"] = {"facebook": "Facebook insights", "tiktok": "Logged by hand"}
    scored = trends.score_niches(NICHES, None, [], NOW)
    plan = timing.plan({**TIMING, "explore_rate": 0}, MONDAY, at(MONDAY, "07:54"))
    files = dashboard.datasets(snap, PROD, scored, NICHES, date(2026, 10, 18), plan)
    assert files["earnings_daily"] == [
        {"date": "2026-10-18", "platform": "tiktok", "usd": 3.5, "source": "Logged by hand"},
        {"date": "2026-10-18", "platform": "facebook", "usd": 2.0, "source": "Facebook insights"}]
    assert [(r["platform"], r["account"]) for r in files["platforms"]] == [
        ("youtube", "Not signed in"), ("tiktok", "Connected"), ("instagram", "Not signed in"),
        ("facebook", "Not signed in")]
    assert files["post_times"][1] == {"platform": "tiktok", "at": "2026-10-19T18:00:00-04:00",
                                      "day": "Mon Oct 19", "time": "6:00 PM EDT", "basis": "Research"}
    assert files["videos"][0]["youtube"] == "published" and files["videos"][0]["tiktok"] == "not posted"
    assert files["credits"][0]["videos_left"] == (1050 - 80) // files["credits"][0]["cost_per_video"]
    assert len(files["niches"]) == len(NICHES) and len(files["programs"]) == 4
    empty = dashboard.datasets(metrics.snapshot(date(2026, 10, 18), {}, {}, [], [], {}), PROD, scored, NICHES,
                               date(2026, 10, 18))
    assert [r["usd"] for r in empty["earnings_daily"]] == [0.0] * 4 and len(empty["platforms"]) == 4
    used = load_platforms()["targets"]
    assert "tiktok" not in used                         # owner is in India: TikTok is blocked there
    only = dashboard.datasets(snap, PROD, scored, NICHES, date(2026, 10, 18), plan, targets=used)
    assert [r["platform"] for r in only["platforms"]] == ["youtube", "instagram", "facebook"]
    assert "tiktok" not in only["videos"][0]


def test_hosted_assembler_matches_repo():
    import hashlib
    render = PROD["render"]
    digest = hashlib.sha256((ROOT / "tools" / "assemble.py").read_bytes()).hexdigest()
    assert render["assembler_url"].startswith("https://")
    assert render["assembler_sha256"] == digest, "tools/assemble.py changed: re-upload it and update config/production.yaml"


def test_local_time_for_upload_post_schedule():
    assert uploadpost.local_time("2026-10-18T22:00:00+00:00", "America/New_York") == "2026-10-18T18:00:00"
    fields = uploadpost.build_form(CAPS, "https://v.mp4", "me", ["youtube"], PLATFORMS, "r",
                                   "2026-10-18T12:30:00", timezone="America/New_York")
    assert ("timezone", "America/New_York") in fields and ("scheduled_date", "2026-10-18T12:30:00") in fields


# --- post times ----------------------------------------------------------------------

TIMING = load_yaml("timing.yaml")
NY = __import__("zoneinfo").ZoneInfo("America/New_York")
MONDAY = date(2026, 10, 19)


def at(day, hhmm):
    return datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time(), NY)


def posted(run_id, platform, when, views, age=40, status="published"):
    return {"run_id": run_id, "posts": {platform: {"status": status, "at": when.isoformat(),
                                                    "views": views, "views_age_hours": age}}}


def test_research_defaults_pick_each_platforms_best_slot():
    cfg = {**TIMING, "explore_rate": 0}
    plan = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"))
    assert {p: e["slot"] for p, e in plan.items()} == {
        p: TIMING["slots"][p]["weekday"][0] for p in timing.PLATFORMS}
    assert all(e["basis"] == ["research"] for e in plan.values())
    sunday = timing.plan(cfg, date(2026, 10, 18), at(date(2026, 10, 18), "07:54"), platforms=["tiktok"])
    assert sunday["tiktok"]["slot"] == TIMING["slots"]["tiktok"]["sunday"][0]


def test_passed_and_booked_slots_are_skipped():
    cfg = {**TIMING, "explore_rate": 0}
    late = timing.plan(cfg, MONDAY, at(MONDAY, "17:50"), platforms=["tiktok"])   # 18:00 is inside the lead time
    assert late["tiktok"]["slot"] == "20:00"
    other = posted("other", "tiktok", at(MONDAY, "18:00"), None, status="scheduled")
    second = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), [other], platforms=["tiktok"], run_id="mine")
    assert second["tiktok"]["slot"] == "15:30"                                     # 2.5 h away from 18:00
    night = timing.plan(cfg, MONDAY, at(MONDAY, "23:00"), platforms=["tiktok"])
    assert night["tiktok"]["at"].startswith("2026-10-20T18:00")                    # tomorrow's best


def test_audience_activity_moves_the_slot():
    cfg = {**TIMING, "explore_rate": 0}
    audience = {"date": "2026-10-18", "timezone": "America/New_York",
                "platforms": {"tiktok": {"mon": {"18": 20, "21": 100, "15": 30}}}}
    assert timing.validate_audience(audience) == []
    plan = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), audience=audience, platforms=["tiktok"])
    assert plan["tiktok"]["slot"] == "21:00" and "audience" in plan["tiktok"]["basis"]
    assert timing.validate_audience({"date": "x", "platforms": {"tiktok": {"funday": {"25": -1}}}})


def test_own_results_outweigh_research():
    cfg = {**TIMING, "explore_rate": 0}
    days = [MONDAY - timedelta(days=d) for d in range(1, 13)]
    history = [posted(f"a{i}", "youtube", at(d, "16:00"), 400) for i, d in enumerate(days[:6])]
    history += [posted(f"b{i}", "youtube", at(d, "19:00"), 2400) for i, d in enumerate(days[6:])]
    plan = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), history, platforms=["youtube"])
    assert plan["youtube"]["slot"] == "19:00"
    assert plan["youtube"]["basis"][-1] == "results (12 posts)"
    few = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), history[-2:], platforms=["youtube"])
    assert few["youtube"]["slot"] == "16:00"                                      # 2 posts: not enough


def test_exploration_is_stable_and_near_its_rate():
    cfg = {**TIMING, "explore_rate": 0.15}
    runs = [f"run-{i}" for i in range(400)]
    picks = [timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), platforms=["tiktok"], run_id=r)["tiktok"] for r in runs]
    share = sum(p["explore"] for p in picks) / len(picks)
    assert 0.08 < share < 0.22
    assert all(p["slot"] == ("15:30" if p["explore"] else "18:00") for p in picks)
    again = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), platforms=["tiktok"], run_id=runs[0])["tiktok"]
    assert again == picks[0]


def test_groups_platforms_by_time():
    plan = {"tiktok": {"at": "b"}, "youtube": {"at": "a"}, "facebook": {"at": "b"}}
    assert timing.groups(plan) == [("a", ["youtube"]), ("b", ["tiktok", "facebook"])]


def test_only_money_niches_are_active_and_picked():
    assert [n["id"] for n in NICHES] == ["investing", "personal-finance", "credit-debt", "insurance",
                                         "real-estate", "side-hustles", "tech-ai-tools", "legal-money"]
    assert len(ALL_NICHES) == 12 and niche_by_id("psychology")["active"] is False
    scored = trends.score_niches(NICHES, None, [], NOW)
    picks = library.pick(library.load_scripts(), scored, [], 40)
    assert len(picks) == 34 and {p["niche_id"] for p in picks} == {n["id"] for n in NICHES}


def test_metricool_args_one_network_each_with_ai_flags():
    from pipeline import metricool
    cfg = load_platforms()
    base = {"at": "2026-10-19T16:00:00-04:00", "video_url": "https://v.mp4", "title": "T #Shorts", "text": "Body",
            "tags": ["a"], "ai_disclosure_fallback": "Made with AI."}
    yt = metricool.schedule_args({**base, "platform": "youtube"}, cfg)
    info = json.loads(yt["info"])
    assert yt["blogId"] == cfg["metricool"]["brand_id"]
    assert yt["date"] == "2026-10-20T01:30:00+05:30" and info["publicationDate"]["timezone"] == "Asia/Kolkata"
    assert info["providers"] == [{"network": "youtube"}] and info["media"] == ["https://v.mp4"]
    assert info["youtubeData"]["type"] == "short" and info["youtubeData"]["isAiGeneratedContent"] is True
    assert info["youtubeData"]["madeForKids"] is False
    ig = json.loads(metricool.schedule_args({**base, "platform": "instagram"}, cfg)["info"])
    assert ig["instagramData"] == {"type": "REEL", "showReelOnFeed": True, "isAiGenerated": True}
    fb = json.loads(metricool.schedule_args({**base, "platform": "facebook"}, cfg)["info"])
    assert fb["facebookData"]["type"] == "REEL" and fb["text"].endswith("Made with AI.")
