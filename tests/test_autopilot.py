import importlib.util
import json
import math
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


def test_days_left_follows_the_owners_quota():
    plan = {"renews_on_day": 18, "quota": {"start": date(2026, 10, 18), "first_days": 15, "then_days": 30}}
    assert budget.days_left(date(2026, 10, 18), plan) == 15
    assert budget.days_left(date(2026, 10, 21), plan) == 12
    assert budget.days_left(date(2026, 11, 1), plan) == 1
    assert budget.days_left(date(2026, 11, 2), plan) == 30      # after the top-up: 30 days
    assert budget.days_left(date(2026, 12, 2), plan) == 30
    assert budget.days_left(date(2026, 10, 21), {"renews_on_day": 18}) == 28


def test_videos_today_paces_the_budget():
    # Plenty of budget: one a day (capped).
    assert budget.videos_today(1050, 31, 80, 30, 0, 1) == 1
    # Budget for ~half the days: every other day.
    assert budget.videos_today(560, 31, 80, 30, 1, 1) == 0
    assert budget.videos_today(560, 31, 80, 30, 2, 1) == 1
    # 14 videos over 12 days: the spare two come first, then one a day.
    assert budget.videos_today(663.8, 39.06, 80, 12, 1, 2) == 2
    assert budget.videos_today(663.8 - 2 * 39.06, 39.06, 80, 11, 0, 2) == 2
    assert budget.videos_today(663.8 - 4 * 39.06, 39.06, 80, 10, 0, 2) == 1
    # Nothing spendable above the reserve.
    assert budget.videos_today(100, 31, 80, 10, 5, 1) == 0


def test_plan_today_uses_active_tier():
    plan = budget.plan_today(PROD, 1050, date(2026, 10, 18), None)
    assert plan["tier"] == "multishot" and 18 < plan["est_cost_per_video"] < 26
    assert plan["days_left_in_window"] == 15
    assert plan["videos_today"] == 3                    # ~46 multi-shot videos in 15 days, 3 a day at most
    # The owner's 2-3 a day (2026-10-22): 546 credits over the 11 days left.
    left = budget.plan_today(PROD, 546.45, date(2026, 10, 22), 1)
    assert left["days_left_in_window"] == 11 and left["est_videos_left_this_window"] >= 22
    quality = budget.plan_today({**PROD, "tier": "quality"}, 1050, date(2026, 10, 18), None)
    assert 40 < quality["est_cost_per_video"] < 55 and quality["videos_today"] == 2
    reach = budget.plan_today({**PROD, "tier": "reach"}, 1050, date(2026, 10, 18), None)
    assert 10 < reach["est_cost_per_video"] < 14 and reach["videos_today"] == 3
    lean = budget.plan_today({**PROD, "tier": "lean"}, 1050, date(2026, 10, 18), None)
    assert 25 < lean["est_cost_per_video"] < 40 and lean["videos_today"] == 3


def test_plan_week_covers_every_day_then_adds_weekday_spares():
    # The owner's weekly batch (2026-10-26): Monday already has 3, the batch covers Tue-Sun.
    monday = date(2026, 10, 26)
    week = budget.plan_week(PROD, 417.85, monday, 7, {monday: 3})
    counts = [d["videos"] for d in week["days"]]
    assert counts[0] == 0 and all(c >= 2 for c in counts[1:]) and max(counts) == 3
    assert week["videos"] == 17 and counts[1:5] == [3, 3, 3, 3]                  # spares go to weekdays first
    # A thin balance over a 30-day window: a few videos, spaced across the week.
    thin = [d["videos"] for d in budget.plan_week(PROD, 417.85, date(2026, 11, 2), 7)["days"]]
    assert thin == [1, 0, 1, 0, 1, 0, 0]


def test_plan_today_counts_videos_already_made_today():
    # A catch-up run made 3 this morning: the scheduled run that afternoon makes none.
    assert budget.plan_today(PROD, 417.85, date(2026, 10, 26), 0, made_today=3)["videos_today"] == 0
    assert budget.plan_today(PROD, 417.85, date(2026, 10, 26), 0, made_today=1)["videos_today"] == 2


# --- production -----------------------------------------------------------------------

REACH = {**PROD, "tier": "reach"}


def test_generation_requests_reach_tier():
    s = next(x for x in SCRIPTS if x["id"] == "inv-rule-of-72")
    voice = PROD["voices"][0]
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), REACH, voice)
    assert len(g["keyframes"]) == 8 and [m["block"] for m in g["motion"]] == [1, 3, 5, 7]
    assert g["keyframes"][0]["params"]["model"] == "z_image"
    assert g["keyframe_retry"]["model"] == "seedream_5_0_flash"
    assert g["motion"][0]["params"]["resolution"] == "480p" and g["motion"][0]["params"]["duration"] == 4
    assert g["motion"][0]["params"]["medias"][0]["role"] == "start_image"
    assert PROD["prompts"]["keyframe_suffix"] in g["keyframes"][0]["params"]["prompt"]
    assert g["voice"]["params"]["prompt"].startswith(f"[{PROD['prompts']['voice_delivery']}, starts speaking immediately] ")
    assert g["voice"]["params"]["voice_id"] == voice["voice_id"]
    assert 10 < g["estimated_credits"] < 14
    assert g["motion"][0]["params"]["generate_audio"] and "No music, no speech" in g["motion"][0]["params"]["prompt"]
    lean = production.generation_requests(s, niche_by_id(s["niche_id"]), {**PROD, "tier": "lean"}, voice)
    assert 25 < lean["estimated_credits"] < 40 and lean["keyframe_retry"] is None
    assert "No music" not in lean["motion"][0]["params"]["prompt"]


def test_render_plan_and_asset_validation():
    s = next(x for x in SCRIPTS if x["id"] == "inv-rule-of-72")
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), REACH, PROD["voices"][0])
    assets = {"keyframes": {str(i): f"https://k/{i}" for i in range(1, 9)}, "motion": {"1": "https://m/1"},
              "voice": "https://v"}
    errors = production.validate_assets(assets, s, g)
    assert any("motion.3" in e for e in errors)
    assets["motion"].update({b: f"https://m/{b}" for b in ("3", "5", "7")})
    assert production.validate_assets(assets, s, g) == []
    plan = production.render_plan(s, assets, PROD["render"])
    assert "min_duration" not in plan and plan["blocks"][1]["motion_url"] is None
    assert plan["blocks"][0]["text"] == s["blocks"][0]["narration"]
    assert plan["hook_title"] == s["on_screen_hook"] and plan["shot_seconds"] == PROD["render"]["shot_seconds"]
    assert plan["audio"]["seed"] == production.render_plan(s, assets, PROD["render"])["audio"]["seed"]
    other = next(x for x in SCRIPTS if x["id"] == "pf-hsa-triple-tax")
    assert production.render_plan(other, assets, PROD["render"])["audio"]["seed"] != plan["audio"]["seed"]
    assert production.render_plan(s, assets, {**PROD["render"], "audio": None})["audio"] is None
    # The music bed comes from the niche's beds; without a library the assembler synthesizes one.
    beds = PROD["render"]["audio"]["music"]
    assert plan["audio"]["music_url"] in [b["url"] for b in beds.values() if s["niche_id"] in b["niches"]]
    assert "music" not in plan["audio"] and plan["audio"]["whoosh_url"].startswith("https://")
    bare = {k: v for k, v in PROD["render"]["audio"].items() if k != "music"}
    assert "music_url" not in production.render_plan(s, assets, {**PROD["render"], "audio": bare})["audio"]


def test_generated_bed_loops_and_lands_on_the_cut():
    np = pytest.importorskip("numpy")
    clip = np.sin(np.linspace(0, 200, assemble.SR * 2))
    looped = assemble.loop_to(clip, assemble.SR * 5, np)
    assert len(looped) == assemble.SR * 5 and np.abs(looped).max() <= 1.0001
    click = np.zeros(assemble.SR)
    click[12000:12480] = 1.0
    assert abs(assemble.peak_at(click, np) - 12240) < 300
    assert assemble.sample({}, "music_url", np, 10) is None


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
    assert assemble.kenburns("punch_left", 60, 1080, 1920, 30).startswith("zoompan=z='1.30+")


def test_numbers_and_starred_words_are_highlighted():
    gold = "&H003DB8F5"
    assert assemble.highlight("SAVES $200 A", gold) == f"SAVES {{\\c{gold}&}}$200{{\\c&H00FFFFFF&}} A"
    assert assemble.highlight("THE *MATH*.", gold) == f"THE {{\\c{gold}&}}MATH.{{\\c&H00FFFFFF&}}"
    assert assemble.highlight("*NOBODY* KNOWS 50%", "") == "NOBODY KNOWS 50%"


def test_hook_title_is_big_short_lines_over_the_opening():
    assert assemble.hook_lines("the deductible math nobody explains") == ["THE DEDUCTIBLE MATH", "NOBODY EXPLAINS"]
    doc = assemble.ass_document([(0, 1, "HI")], 1080, 1920, "F", 96, 560, hook="Same *payout*, 10x price", hook_seconds=2.6)
    hook = next(line for line in doc.splitlines() if ",Hook," in line and line.startswith("Dialogue"))
    assert hook.startswith("Dialogue: 1,0:00:00.00,0:00:02.60,Hook") and "\\N" in hook and "*" not in hook
    assert "Style: Hook,F,120," in doc
    assert ",Hook," not in assemble.ass_document([(0, 1, "HI")], 1080, 1920, "F", 96, 560)


def test_long_stills_are_cut_so_the_picture_keeps_changing():
    shots = assemble.plan_shots([(0, 6.4), (6.4, 11.74), (11.74, 13.0)], [4.04, 0, 0], shot_seconds=3.5)
    assert [(b, k) for b, _, _, k in shots] == [(0, "motion"), (0, "punch"), (1, "still"), (1, "punch"), (2, "still")]
    assert all(d <= 4.1 for _, _, d, _ in shots)
    ends = [s + d for _, s, d, _ in shots]
    assert ends[-1] == pytest.approx(13.0) and all(abs(ends[i] - shots[i + 1][1]) < 1e-6 for i in range(len(shots) - 1))


# --- Upload-Post ------------------------------------------------------------------------

CAPS = build_captions(next(x for x in SCRIPTS if x["id"] == "pf-hsa-triple-tax"),
                      niche_by_id("personal-finance"), PLATFORMS)


def test_build_form_labels_ai_on_every_platform():
    fields = uploadpost.build_form(CAPS, "https://v.mp4", "me", list(uploadpost.PLATFORMS), PLATFORMS,
                                   "run-1", facebook_page_id="42")
    d = {}
    for k, v in fields:
        d.setdefault(k, []).append(v)
    assert d["platform[]"] == ["instagram", "youtube", "facebook"]
    for flag in ("is_ai_generated", "containsSyntheticMedia", "facebook_is_ai_generated"):
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
    body = uploadpost.publish(s, "KEY", [("user", "me"), ("platform[]", "youtube")], "run-1")
    _, url, kw = s.calls[0]
    assert url.endswith("/api/upload") and body["request_id"] == "run-1"
    assert kw["headers"] == {"Authorization": "Apikey KEY", "Idempotency-Key": "run-1"}
    assert ("platform[]", (None, "youtube")) in kw["files"]


def test_publish_error_raises():
    s = FakeSession(FakeResp(403, {"success": False, "message": "Facebook uploads are not available on the Free plan."}))
    with pytest.raises(uploadpost.UploadPostError, match="Free plan"):
        uploadpost.publish(s, "KEY", [], "r")


def test_platform_results_normalizes():
    body = {"status": "completed", "results": {
        "instagram": {"status": "completed", "publish_id": "p1", "fallback_to_inbox": True},
        "youtube": {"success": True, "url": "https://youtu.be/x", "video_id": "x"},
        "facebook": {"skipped": True, "status": "skipped"},
    }}
    r = uploadpost.platform_results(body)
    assert r["instagram"]["draft"] and r["instagram"]["id"] == "p1"
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
    manual = [{"date": "2026-10-18", "platform": "instagram", "amount_usd": 3.5, "source": "gifts"}]
    totals = metrics.earnings_by_platform(yt, fb, manual, date(2026, 9, 19), date(2026, 10, 18))
    assert totals == {"youtube": 1.25, "facebook": 2.0, "instagram": 3.5}
    stats = metrics.normalize_uploadpost({"instagram": {"followers": 10, "views": 500, "junk": 1},
                                          "x": {"error": "nope"}})
    assert stats == {"instagram": {"followers": 10, "views": 500}}
    videos = [{"run_id": "r1", "date": "2026-10-18", "niche": "investing", "topic": "t", "credits": 31,
               "published": True, "posts": {"youtube": {"status": "published", "url": "u"}}}]
    snap = metrics.snapshot(date(2026, 10, 18), stats, totals,
                            [{"date": "2026-10-18", "instagram": 3.5, "facebook": 2.0}], videos,
                            {"balance": 1050, "spent_30d": 31})
    assert snap["earnings_total_30d"] == 6.75
    snap["earnings_sources"] = {"facebook": "Facebook insights", "instagram": "Logged by hand"}
    scored = trends.score_niches(NICHES, None, [], NOW)
    plan = timing.plan({**TIMING, "explore_rate": 0}, MONDAY, at(MONDAY, "07:54"))
    files = dashboard.datasets(snap, PROD, scored, NICHES, date(2026, 10, 18), plan)
    assert files["earnings_daily"] == [
        {"date": "2026-10-18", "platform": "instagram", "usd": 3.5, "source": "Logged by hand"},
        {"date": "2026-10-18", "platform": "facebook", "usd": 2.0, "source": "Facebook insights"}]
    assert [(r["platform"], r["account"]) for r in files["platforms"]] == [
        ("youtube", "Not signed in"), ("instagram", "Connected"), ("facebook", "Not signed in"),
        ("twitter", "Not signed in")]
    assert files["post_times"][1] == {"platform": "instagram", "at": "2026-10-19T19:30:00-04:00",
                                      "day": "Mon Oct 19", "time": "7:30 PM EDT", "local_day": "Mon Oct 19",
                                      "local_time": "7:30 PM EDT", "basis": "Research"}
    assert "locale" not in files and "spending" not in files
    assert files["videos"][0]["youtube"] == "published" and files["videos"][0]["instagram"] == "not posted"
    assert files["credits"][0]["videos_left"] == (1050 - PROD["plan"]["reserve_credits"]) // files["credits"][0]["cost_per_video"]
    assert files["credits"][0]["runway_balance"] is None and files["credits"][0]["hero_shots_left"] is None
    # A platform with no earnings feed names its next paid step instead of "not connected".
    ladder = load_yaml("monetization.yaml")
    unpaid = dashboard.platform_rows({**snap, "earnings_sources": {}}, ["youtube", "instagram"], ladder)
    assert [r["earnings_source"] for r in unpaid] == [
        "Not earning yet · Fan funding at 500 subscribers", "Not earning yet · Gifts at 500 followers"]
    assert dashboard.platform_rows(snap, ["facebook"], ladder)[0]["earnings_source"] == "Facebook insights"
    rw = dashboard.datasets({**snap, "runway": {"plan_left": 359, "purchased": 300, "balance": 659}},
                            PROD, scored, NICHES, date(2026, 10, 18), plan)["credits"][0]
    hero = PROD["runway"]["hero_shot"]
    assert rw["runway_used"] == PROD["runway"]["plan_credits"] - 359
    assert rw["hero_shots_left"] == (659 - hero["min_balance"]) // hero["credits"]
    assert rw["music_beds"] == len(PROD["render"]["audio"]["music"])
    assert len(files["niches"]) == len(NICHES) and len(files["programs"]) == 4
    empty = dashboard.datasets(metrics.snapshot(date(2026, 10, 18), {}, {}, [], [], {}), PROD, scored, NICHES,
                               date(2026, 10, 18))
    assert [r["usd"] for r in empty["earnings_daily"]] == [0.0] * 4 and len(empty["platforms"]) == 4
    used = load_platforms()["targets"]
    only = dashboard.datasets(snap, PROD, scored, NICHES, date(2026, 10, 18), plan, targets=used)
    assert "twitter" not in used                        # X is on hold until the owner resumes it
    assert [r["platform"] for r in only["platforms"]] == ["youtube", "instagram", "facebook"]
    assert "twitter" not in only["videos"][0]


LOCALE = {"timezone": "Asia/Kolkata", "zone_label": "IST", "currency": "INR", "usd_rate": 90.0,
          "rate_date": "2026-10-19"}
LEDGER = [
    {"date": "2026-09-18", "service": "Higgsfield", "item": "Plus plan", "amount": "49.00", "currency": "USD",
     "local_amount": "", "recurring": "monthly", "source": "card alert"},
    {"date": "2026-10-18", "service": "Higgsfield", "item": "Plus plan", "amount": "49.00", "currency": "USD",
     "local_amount": "", "recurring": "monthly", "source": "card alert"},
    {"date": "2026-10-20", "service": "Runway", "item": "Standard plan", "amount": "17.70", "currency": "USD",
     "local_amount": "1746.89", "recurring": "monthly", "source": "receipt"},
    {"date": "2026-10-21", "service": "Runway", "item": "Credits", "amount": "500", "currency": "INR",
     "local_amount": "", "recurring": "one-off", "source": "receipt"},
]


def test_expenses_convert_to_the_owners_currency():
    from pipeline import expenses
    assert expenses.local_amount(LEDGER[1], LOCALE) == (4410.0, True)      # USD at usd_rate: an estimate
    assert expenses.local_amount(LEDGER[2], LOCALE) == (1746.89, False)    # the rupees actually charged
    assert expenses.local_amount(LEDGER[3], LOCALE) == (500.0, False)
    with pytest.raises(ValueError):
        expenses.local_amount({**LEDGER[1], "currency": "EUR"}, LOCALE)
    rows = expenses.rows(LEDGER, LOCALE)
    assert [r["date"] for r in rows] == ["2026-10-21", "2026-10-20", "2026-10-18", "2026-09-18"]
    assert rows[1]["billed"] == "17.70 USD" and rows[1]["amount"] == 1746.89 and not rows[1]["estimated"]
    assert len({r["key"] for r in rows}) == len(rows)


def test_spending_summary_and_dashboard_datasets():
    from pipeline import expenses
    s = expenses.summary(LEDGER, LOCALE, date(2026, 10, 21), 2.0, ["2026-10-19", "2026-10-20", "2026-09-01"])[0]
    assert s["month"] == "October 2026" and s["currency"] == "INR"
    assert s["spent_month"] == round(4410 + 1746.89 + 500, 2)
    assert s["spent_30d"] == s["spent_month"]                               # Sep 18 is outside the 30 days
    assert s["run_rate"] == round(4410 + 1746.89, 2) and s["services"] == 2  # latest monthly charge each
    assert s["videos_30d"] == 2 and s["per_video"] == round(s["spent_30d"] / 2, 2)
    assert s["earned_30d"] == 180.0 and s["net_30d"] == round(180 - s["spent_30d"], 2)
    assert s["estimated"]
    none = expenses.summary([], LOCALE, date(2026, 10, 21), 0.0, [])[0]
    assert none["spent_30d"] == 0 and none["per_video"] is None
    snap = metrics.snapshot(date(2026, 10, 21), {}, {}, [], [], {})
    plan = timing.plan({**TIMING, "explore_rate": 0}, MONDAY, at(MONDAY, "07:54"))
    files = dashboard.datasets(snap, PROD, [], NICHES, date(2026, 10, 21), plan, locale=LOCALE, ledger=LEDGER)
    assert files["locale"] == [LOCALE]
    assert len(files["expenses"]) == 4 and files["spending"][0]["run_rate"] == s["run_rate"]
    ig = files["post_times"][1]
    assert (ig["time"], ig["local_day"], ig["local_time"]) == ("7:30 PM EDT", "Tue Oct 20", "5:00 AM IST")
    assert load_yaml("dashboard.yaml")["locale"]["currency"] == "INR"


def test_expense_ledger_add_round_trips(tmp_path):
    from pipeline import expenses
    path = tmp_path / "expenses.csv"
    expenses.add(LEDGER[2], path)
    expenses.add({**LEDGER[1], "extra": "ignored"}, path)
    assert expenses.load(path) == [LEDGER[2], LEDGER[1]]
    assert expenses.load(tmp_path / "missing.csv") == []
    seeded = expenses.load()
    assert seeded and not any("claude" in r["service"].lower() or "anthropic" in r["service"].lower()
                              for r in seeded)



def test_forecast_history_merges_every_stats_file():
    from pipeline import forecast
    old = {"instagram": {"daily": [{"day": "2026-10-17", "followers": 0, "views": 10},
                                   {"day": "2026-10-18", "followers": 1, "views": 500}]}}
    new = {"instagram": {"daily": [{"day": "2026-10-18", "followers": None, "views": 565},
                                   {"day": "2026-10-19", "followers": 2, "views": 154}]},
           "youtube": {"followers": 6}}
    merged = forecast.history([old, new])
    assert merged["instagram"] == [{"day": "2026-10-17", "followers": 0, "views": 10},
                                   {"day": "2026-10-18", "followers": 1, "views": 565},   # later wins, null keeps
                                   {"day": "2026-10-19", "followers": 2, "views": 154}]
    assert "youtube" not in merged


def test_forecast_pace_blends_history_with_the_prior():
    from pipeline import forecast
    cfg = load_yaml("forecast.yaml")
    g = cfg["growth"]
    daily = [{"day": "2026-10-17", "followers": 0, "views": None}, {"day": "2026-10-18", "followers": 1, "views": 565},
             {"day": "2026-10-19", "followers": None, "views": 154}, {"day": "2026-10-20", "followers": 9, "views": 3}]
    rows = forecast.clean(daily, date(2026, 10, 20))
    assert [r["day"] for r in rows] == ["2026-10-17", "2026-10-18", "2026-10-19"]   # today is not over yet
    assert rows[-1]["followers"] == 1                                              # carried forward
    pc = forecast.pace(rows, 1, cfg, "instagram")
    assert pc["views_per_day"] == (565 + 154) / 2 and pc["views_basis"] == "measured"
    w = 2 / (2 + g["prior_days"])                                                   # two days of views so far
    assert pc["growth_basis"] == "history" and pc["growth_measured"] == g["min"]    # 565 -> 154 a day, clamped
    assert pc["weekly_growth"] == pytest.approx(w * g["min"] + (1 - w) * g["assumed"])
    assert forecast.pace(rows[:2], 1, cfg, "instagram")["growth_basis"] == "assumed"  # one day: prior alone
    w = 1 / (1 + cfg["prior_followers"])                                            # 1 follower gained
    assert pc["followers_basis"] == "history" and pc["followers_weight"] == pytest.approx(w)
    assert pc["followers_per_1k"] == pytest.approx(w * 1000 / 719 + (1 - w) * cfg["followers_per_1k"]["instagram"])
    # Two weeks growing exactly 20% a week: the fit finds it; the prior keeps 7/21 of the say.
    weeks = [{"day": str(date(2026, 10, 1) + timedelta(days=i)), "followers": 100 + 10 * i,
              "views": 1e6 * 1.2 ** (i / 7)} for i in range(14)]
    pc = forecast.pace(weeks, 230, cfg, "youtube")
    w = 14 / (14 + g["prior_days"])
    assert pc["growth_basis"] == "history" and pc["growth_measured"] == pytest.approx(0.2, rel=1e-3)
    assert pc["growth_weight"] == pytest.approx(w) and pc["weekly_growth"] == pytest.approx(w * 0.2 + (1 - w) * g["assumed"], rel=1e-3)
    assert pc["views_per_day"] == pytest.approx(sum(r["views"] for r in weeks[-7:]) / 7)  # current pace: last 7 days
    later = sum(r["views"] for r in weeks[1:])
    fw = 130 / (130 + cfg["prior_followers"])
    assert pc["followers_per_1k"] == pytest.approx(fw * 130 / later * 1000 + (1 - fw) * cfg["followers_per_1k"]["youtube"])
    # A recent day weighs more than an old one, and the measured rate stays inside the bounds.
    assert forecast.fit_growth([{"day": "2026-10-01", "views": 100}, {"day": "2026-10-08", "views": 200}], 30) == pytest.approx(
        math.expm1(math.log(201 / 101)), rel=1e-6)
    huge = [{**d, "views": 100 if i < 7 else 1e7} for i, d in enumerate(weeks)]
    assert forecast.pace(huge, 230, cfg, "youtube")["growth_measured"] == g["max"]
    falling = [{**d, "views": 1e6 * 0.5 ** i} for i, d in enumerate(weeks)]
    assert forecast.pace(falling, 230, cfg, "youtube")["growth_measured"] == g["min"]
    # Metricool shows no views but YouTube Studio gave a total: that period sets the pace.
    studio = {"from": "2026-10-18", "to": "2026-10-19", "views": 2860, "source": "YouTube Studio"}
    yt = [{"day": "2026-10-18", "followers": 1, "views": None}, {"day": "2026-10-19", "followers": 6, "views": None}]
    pc = forecast.pace(yt, 6, cfg, "youtube", proxy_views=300, period=studio)
    assert pc["views_basis"] == "period" and pc["views_per_day"] == 1430 and pc["views_source"] == "YouTube Studio"
    assert pc["followers_measured"] == pytest.approx(5 / 1430 * 1000)
    assert forecast.pace(weeks, 230, cfg, "youtube", period=studio)["views_basis"] == "measured"  # daily views win
    # No views yet: a proxy pace, and follower history measured against it.
    yt = [{"day": "2026-10-18", "followers": 1, "views": None}, {"day": "2026-10-19", "followers": 6, "views": None}]
    pc = forecast.pace(yt, 6, cfg, "youtube", proxy_views=300)
    assert pc["views_basis"] == "proxy" and pc["followers_measured"] == pytest.approx(5 / 300 * 1000)


def test_forecast_rules_change_on_their_date_and_count_watch_minutes():
    from pipeline import forecast
    progs = load_yaml("forecast.yaml")["programs"]
    yt = progs["youtube"]
    assert forecast.rule_on(yt, date(2027, 1, 31))["views"] == 10_000_000
    assert forecast.rule_on(yt, date(2027, 2, 1))["views"] == 20_000_000
    assert forecast.views_needed(forecast.rule_on(yt, date(2026, 10, 20))) == 10_000_000 / 90
    fb = progs["facebook"]
    window = [fb["minutes"] / fb["minutes_per_view"] / fb["window_days"]] * fb["window_days"]
    assert forecast.unlocked(fb, fb["followers"], window)
    assert not forecast.unlocked(fb, fb["followers"] - 1, window)
    assert not forecast.unlocked(fb, fb["followers"], window[:-1])
    assert forecast.unlocked(progs["instagram"], 500, [])


def test_forecast_rows_order_milestones_and_scenarios():
    from pipeline import forecast
    cfg = load_yaml("forecast.yaml")
    today = date(2026, 10, 20)
    day = lambda i: str(today - timedelta(days=i))  # noqa: E731
    series = {"instagram": [{"day": day(2), "followers": 0, "views": 20_000}, {"day": day(1), "followers": 50, "views": 30_000}],
              "facebook": [{"day": day(2), "followers": 10, "views": 40_000}, {"day": day(1), "followers": 90, "views": 40_000}],
              "youtube": [{"day": day(1), "followers": 5, "views": None}]}
    rows = forecast.rows(series, {"youtube": 5, "instagram": 50, "facebook": 90}, cfg, today,
                         ["youtube", "instagram", "facebook"])
    by = {r["key"]: r for r in rows}
    assert by["meta"]["days_of_data"] == 2 and by["meta"]["prior_growth"] == cfg["growth"]["assumed"]
    assert by["pace:youtube"]["views_basis"] == "proxy" and by["pace:youtube"]["views_per_day"] == round((25_000 + 40_000) / 2)
    ig = by["pace:instagram"]
    w = 50 / (50 + cfg["prior_followers"])
    assert ig["followers_basis"] == "history" and ig["followers_measured"] == round(50 / 30, 2)
    assert ig["followers_per_1k"] == round(w * 50 / 30 + (1 - w) * cfg["followers_per_1k"]["instagram"], 2)
    assert by[f"history:instagram:{day(1)}"]["views"] == 30_000
    path = [r for r in rows if r["kind"] == "path" and r["platform"] == "instagram"]
    assert len(path) == cfg["path_days"] and path[0]["date"] == str(today + timedelta(days=1))
    assert path[-1]["views"] > path[0]["views"] > 0                                 # growing in the expected case
    fb = by["program:facebook"]
    assert fb["pays"] and not by["program:instagram"]["pays"] and fb["days"] is not None
    assert fb["days_low"] <= fb["days"] <= (fb["days_high"] or 10**9)
    assert fb["date"] == str(today + timedelta(days=fb["days"]))
    money = [by[f"usd:{u}"] for u in cfg["milestones_usd"]]
    assert money[1]["label"] == "$1,000 earned in total"
    days = [r["days"] for r in money if r["days"] is not None]
    assert days and days == sorted(days) and days[0] > fb["days"] + cfg["programs"]["facebook"]["review_days"]
    nothing = forecast.rows({}, {}, cfg, today, ["youtube"])
    assert {r["kind"]: r.get("days") for r in nothing}["program"] is None
    assert [r["views_basis"] for r in nothing if r["kind"] == "pace"] == ["no data"]


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
    sunday = timing.plan(cfg, date(2026, 10, 18), at(date(2026, 10, 18), "07:54"), platforms=["instagram"])
    assert sunday["instagram"]["slot"] == TIMING["slots"]["instagram"]["sunday"][0]


def test_passed_and_booked_slots_are_skipped():
    cfg = {**TIMING, "explore_rate": 0, "min_gap_hours_by_platform": {}}
    late = timing.plan(cfg, MONDAY, at(MONDAY, "15:50"), platforms=["youtube"])  # 16:00 is inside the lead time
    assert late["youtube"]["slot"] == "19:00"
    other = posted("other", "youtube", at(MONDAY, "16:00"), None, status="scheduled")
    second = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), [other], platforms=["youtube"], run_id="mine")
    assert second["youtube"]["slot"] == "19:00"                                    # 3 h away from 16:00
    night = timing.plan(cfg, MONDAY, at(MONDAY, "23:00"), platforms=["youtube"])
    assert night["youtube"]["at"].startswith("2026-10-20T16:00")                   # tomorrow's best


def test_full_days_push_the_post_to_the_next_free_day():
    cfg = {**TIMING, "explore_rate": 0}
    tuesday = MONDAY + timedelta(days=1)
    taken = [posted(f"r{d}{s}", "youtube", at(d, s), None, status="scheduled")
             for d in (MONDAY, tuesday) for s in TIMING["slots"]["youtube"]["weekday"]]
    plan = timing.plan(cfg, MONDAY, at(MONDAY, "23:00"), taken, platforms=["youtube"], run_id="mine")
    assert plan["youtube"]["at"].startswith("2026-10-21T16:00")                    # Wednesday's best


def test_a_weekly_batch_never_posts_past_its_last_day():
    cfg = {**TIMING, "explore_rate": 0}
    tuesday = MONDAY + timedelta(days=1)
    taken = [posted(f"r{d}{s}", "youtube", at(d, s), None, status="scheduled")
             for d in (MONDAY, tuesday) for s in TIMING["slots"]["youtube"]["weekday"]]
    plan = timing.plan(cfg, MONDAY, at(MONDAY, "00:38"), taken, platforms=["youtube", "instagram"],
                       run_id="mine", until=tuesday)
    assert plan["youtube"] is None                                                 # sits this video out
    assert plan["instagram"]["at"].startswith("2026-10-19T19:30")
    later = timing.plan(cfg, tuesday, at(MONDAY, "00:38"), platforms=["instagram"], until=tuesday)
    assert later["instagram"]["at"].startswith("2026-10-20T19:30")                 # its own posting day


def test_audience_activity_moves_the_slot():
    cfg = {**TIMING, "explore_rate": 0}
    audience = {"date": "2026-10-18", "timezone": "America/New_York",
                "platforms": {"youtube": {"mon": {"16": 20, "21": 100, "15": 30}}}}
    assert timing.validate_audience(audience) == []
    plan = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), audience=audience, platforms=["youtube"])
    assert plan["youtube"]["slot"] == "21:00" and "audience" in plan["youtube"]["basis"]
    assert timing.validate_audience({"date": "x", "platforms": {"youtube": {"funday": {"25": -1}}}})
    assert timing.validate_audience({"date": "2026-10-18", "timezone": "UTC",
                                     "platforms": {"tiktok": {"mon": {"9": 1}}}}) == ["unknown platform 'tiktok'"]


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
    picks = [timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), platforms=["youtube"], run_id=r)["youtube"] for r in runs]
    share = sum(p["explore"] for p in picks) / len(picks)
    assert 0.08 < share < 0.22
    assert all(p["slot"] == ("19:00" if p["explore"] else "16:00") for p in picks)
    again = timing.plan(cfg, MONDAY, at(MONDAY, "07:54"), platforms=["youtube"], run_id=runs[0])["youtube"]
    assert again == picks[0]


def test_groups_platforms_by_time():
    plan = {"instagram": {"at": "b"}, "youtube": {"at": "a"}, "facebook": {"at": "b"}}
    assert timing.groups(plan) == [("a", ["youtube"]), ("b", ["instagram", "facebook"])]


def test_reach_phase_favors_reach_niches_and_learns_from_results():
    from pipeline import insights
    from pipeline.config import strategy_weights
    assert len(NICHES) == 12                                   # Worth Knowing covers every niche
    prod = load_yaml("production.yaml")
    assert prod["strategy"]["phase"] == "reach"
    reach = {s["id"]: s for s in trends.score_niches(NICHES, None, [], NOW, strategy_weights(prod))}
    revenue_cfg = {**prod, "strategy": {**prod["strategy"], "phase": "revenue"}}
    revenue = {s["id"]: s for s in trends.score_niches(NICHES, None, [], NOW, strategy_weights(revenue_cfg))}
    assert reach["how-its-made"]["score"] > reach["investing"]["score"]
    assert all(s["parts"]["rpm"] == 0 for s in reach.values())     # ad-revenue tier ignored until paid
    assert revenue["investing"]["score"] > revenue["how-its-made"]["score"]

    def posted(niche, i, views, hours=60.0):
        at = (NOW - timedelta(hours=hours + i)).isoformat()
        return {"run_id": f"{niche}-{i}", "niche_id": niche, "created_at": at, "structure": "story", "voice": "Juno",
                "video": {"duration_seconds": 56}, "posts": {"youtube": {"status": "published", "at": at,
                "views": views, "views_age_hours": hours, "avg_view_seconds": 30, "likes": 5}}}
    history = [posted("psychology", i, 4000) for i in range(4)] + [posted("investing", i, 400) for i in range(4)]
    lifts, count = insights.niche_results(history)
    assert lifts["psychology"] > 0 > lifts["investing"] and count == {"psychology": 4, "investing": 4}
    learned = {s["id"]: s for s in trends.score_niches(NICHES, None, history, NOW + timedelta(days=5),
                                                       strategy_weights(prod))}
    assert learned["psychology"]["parts"]["results"] > 0 > learned["investing"]["parts"]["results"]
    assert learned["history-mysteries"]["parts"]["explore"] > learned["psychology"]["parts"]["explore"]
    summary = insights.summarize(insights.video_rows(history))
    best = [r for r in summary if r["dimension"] == "niche"][0]
    assert best["value"] == "psychology" and best["retention"] == round(30 / 56, 3)
    assert insights.summarize(insights.video_rows(history[:2])) == []   # too few videos to judge


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


def test_x_post_fits_280_with_disclosure_and_metricool_args():
    from pipeline import metricool
    from pipeline.script import x_post
    script = next(x for x in SCRIPTS if x["id"] == "pf-hsa-triple-tax")
    caps = CAPS["twitter"]["text"]
    assert len(caps) <= 280 and "Made with AI." in caps and caps.startswith(script["captions"]["hook_line"])
    long = x_post("H" * 240, "Body sentence that is long. Second.", "#a #b", 280)
    assert long == "H" * 240 + "\n\nMade with AI.\n\n#a #b"           # body dropped to fit
    assert len(x_post("H" * 400, "B.", "#a", 280)) <= 280
    args = metricool.schedule_args({"platform": "twitter", "at": "2026-10-19T09:00:00-04:00", "video_url": "v",
                                    "text": caps, "ai_disclosure_fallback": "Made with AI."}, PLATFORMS)
    info = json.loads(args["info"])
    assert info["providers"] == [{"network": "twitter"}] and info["twitterData"] == {"tags": []}
    assert info["text"] == caps


def test_milestones_announce_each_step_once_and_show_next():
    from pipeline import milestones
    ladder = load_yaml("monetization.yaml")
    stats = {"instagram": {"followers": 620}, "twitter": {"followers": 40, "views_90d": 600_000}}
    new, upcoming = milestones.check(ladder, stats)
    reached = {(s["platform"], s["at"]) for s in new}
    assert ("instagram", 500) in reached and ("instagram", 1000) not in reached
    assert ("twitter", 500000) in reached and ("twitter", 500) not in reached
    assert upcoming["instagram"]["at"] == 1000 and upcoming["instagram"]["to_go"] == 380
    again, _ = milestones.check(ladder, stats, [milestones.key(s["platform"], s) for s in new])
    assert again == []


# --- reach experiment ---------------------------------------------------------------------

def test_experiment_arms_stay_balanced_and_mixed():
    from pipeline import experiment
    variables = load_yaml("experiment.yaml")["variables"]
    arms = experiment.assign(variables, 12, seed="t")
    for name, values in variables.items():
        counts = [sum(a[name] == v for a in arms) for v in values]
        assert max(counts) == min(counts), (name, counts)                 # balanced every 6 videos
    binary = [n for n, v in variables.items() if len(v) == 2]
    for a_name in binary:                                                  # no two-value pair in lockstep
        for b_name in binary:
            if a_name < b_name:
                same = sum(variables[a_name].index(x[a_name]) == variables[b_name].index(x[b_name]) for x in arms)
                assert 2 <= same <= 10, (a_name, b_name, same)
    assert experiment.assign(variables, 4, start=8, seed="t") == arms[8:12]  # day two continues


def test_experiment_ingest_matches_posts_and_reports():
    from pipeline import experiment
    now = datetime(2026, 10, 19, 22, tzinfo=timezone.utc)
    m = lambda rid, arms, yt, ig: {
        "run_id": rid, "topic": rid, "experiment": {"id": "t", "arms": arms},
        "video": {"duration_seconds": 30, "credits_spent": 10},
        "posts": {"youtube": {"at": "2026-10-19T12:00:00+00:00", "url": f"https://www.youtube.com/shorts/{yt}"},
                  "instagram": {"at": "2026-10-19T12:00:00+00:00", "url": f"https://www.instagram.com/reel/{ig}/"}}}
    runs = [m("a", {"length": "short"}, "AAAAAA1", "ig1"), m("b", {"length": "standard"}, "BBBBBB2", "ig2")]
    yt = experiment.parse_rows("youtube", {"rows": [["AAAAAA1", "2026-10-19", "900", "21", "40", "3", "5", "300", "t"],
                                                     ["BBBBBB2", "2026-10-19", "100", "9", "2", "0", "0", "10", "t"]]})
    ig = experiment.parse_rows("instagram", {"rows": [["https://www.instagram.com/reel/ig1/", "x", "50", "8", "1", "0",
                                                       "0", "40", "1", "30", "60"]]})
    for platform, stats in (("youtube", yt), ("instagram", ig)):
        for run_id, fields in experiment.merge(runs, platform, stats, now):
            next(r for r in runs if r["run_id"] == run_id)["posts"][platform].update(fields)
    assert runs[0]["posts"]["youtube"]["views"] == 900 and runs[0]["posts"]["youtube"]["views_age_hours"] == 10.0
    assert runs[0]["posts"]["instagram"]["views"] == 50 and "views" not in runs[1]["posts"]["instagram"]
    rep = experiment.report(runs, {"id": "t", "variables": {"length": ["short", "standard"]}})
    assert rep["videos"] == 2 and rep["credits_spent"] == 20 and rep["best"][0]["run_id"] == "a"
    short = next(r for r in rep["by_variable"] if r["value"] == "short")
    assert short["median_views"] == 950 and short["median_youtube_retention"] == 0.7 and short["lift"] > 0
    assert experiment.post_key("facebook", "https://facebook.com/reel/1778923520024339") == "1778923520024339"
    # A row with no views (YouTube lagging in Metricool) leaves stats recorded another way alone.
    blank = experiment.parse_rows("youtube", {"rows": [["AAAAAA1", "2026-10-19", None, None, None, None, None, None, "t"]]})
    assert experiment.merge(runs, "youtube", blank, now + timedelta(hours=5)) == []
    # Nor does a lower count than the post already has (Metricool lags Meta's own numbers).
    assert experiment.merge(runs, "instagram", ig, now + timedelta(hours=5)) != []
    runs[0]["posts"]["instagram"]["views"] = 80
    assert experiment.merge(runs, "instagram", ig, now + timedelta(hours=5)) == []


def test_hashtag_arm_replaces_or_drops_tags():
    s = next(x for x in SCRIPTS if x["id"] == "inv-rule-of-72")
    none = build_captions(s, niche_by_id(s["niche_id"]), PLATFORMS, hashtags=[])
    assert "#" not in none["instagram"]["caption"] and "#" not in none["youtube"]["description"]
    assert "#Shorts" not in none["youtube"]["title"]
    broad = build_captions(s, niche_by_id(s["niche_id"]), PLATFORMS, hashtags=["facts", "money", "learn", "x", "y", "z"])
    assert broad["youtube"]["description"].count("#") == PLATFORMS["youtube"]["max_hashtags"]
    assert broad["instagram"]["caption"].endswith("#facts #money #learn #x #y")


def test_footage_blocks_skip_generation_and_carry_credit():
    from pipeline.script import validate
    s = json.loads(json.dumps(next(x for x in SCRIPTS if x["id"] == "sc-voyager-1")))
    nasa = {"source": "nasa", "url": "https://images-assets.nasa.gov/video/x/x~orig.mp4", "start": 4,
            "license": "public-domain", "credit": "NASA/JPL-Caltech"}
    s["blocks"][1]["footage"] = nasa
    s["blocks"][3]["footage"] = {**nasa, "credit": "NASA"}
    assert validate(s, ALL_NICHES, PLATFORMS, require_shots=False) == []
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), {**PROD, "tier": "standard"}, PROD["voices"][0])
    assert [k["block"] for k in g["keyframes"]] == [1, 3, 5, 6, 7, 8]
    assert [m["block"] for m in g["motion"]] == [1, 3, 5, 6, 7, 8]
    assets = {"keyframes": {str(k["block"]): "https://k" for k in g["keyframes"]},
              "motion": {str(m["block"]): "https://m" for m in g["motion"]}, "voice": "https://v"}
    assert production.validate_assets(assets, s, g) == []
    plan = production.render_plan(s, assets, PROD["render"])
    assert plan["blocks"][1] == {"text": s["blocks"][1]["narration"], "image_url": None, "motion_url": nasa["url"],
                                 "footage": True, "clip_start": 4.0, "clip_fit": "blur"}
    caps = build_captions(s, niche_by_id(s["niche_id"]), PLATFORMS)
    assert "Footage: NASA/JPL-Caltech; NASA." in caps["youtube"]["description"]
    bad = json.loads(json.dumps(s))
    bad["blocks"][2]["footage"] = {**nasa, "url": "https://www.youtube.com/watch?v=abc", "license": "cc-by-nc"}
    bad["blocks"][4]["footage"] = bad["blocks"][5]["footage"] = nasa
    errs = validate(bad, ALL_NICHES, PLATFORMS, require_shots=False)
    assert any("never YouTube" in e for e in errs) and any("licence" in e for e in errs)
    assert any("at most 50%" in e for e in errs)
    assert production.generation_requests({**s, "motion_blocks": "all"}, niche_by_id(s["niche_id"]), PROD,
                                          PROD["voices"][0])["motion"][-1]["block"] == 8


def test_footage_shots_cut_the_film():
    shots = assemble.plan_shots([(0, 6.4), (6.4, 14.0)], [4.0, 0], 3.5, footage={1})
    assert [s[3] for s in shots] == ["motion", "punch", "footage", "footage", "footage"]
    assert all(d <= 3.5 for _, _, d, k in shots if k == "footage")
    assert assemble.footage_filter("blur", 1080, 1920, 30)[0] == "-filter_complex"


def test_shot_units_follow_their_words_and_stretch_clips():
    blocks = [{"text": "one two three four five six", "shots": [{"words": 4, "motion_url": "a"}, {"words": 2, "overlay": "X"}]},
              {"text": "seven eight", "image_url": "k", "motion_url": None}]
    us = assemble.units(blocks)
    assert [u["block"] for u in us] == [0, 0, 1] and [u["shot"] for u in us] == [True, True, False]
    assert [round(u["words"], 2) for u in us] == [4.0, 2.0, 2]
    # Shot words that do not add up to the block's words are scaled to them.
    odd = assemble.units([{"text": "a b c d e f", "shots": [{"words": 1}, {"words": 2}]}])
    assert [u["words"] for u in odd] == [2.0, 4.0]
    # A shot whose words run a little longer than its clip plays the clip slower instead of
    # ending on a still; too much longer falls back to a still for the rest.
    shots = assemble.plan_shots([(0, 5.5), (5.5, 14.0)], [4.0, 4.0], 3.5, stretch={0, 1})
    assert shots[0] == (0, 0, 5.5, "motion")
    assert [s[3] for s in shots[1:]] == ["motion", "punch", "still"]
    assert "setpts=1.3750*PTS" in assemble.motion_vf(1080, 1920, 30, 5.5 / 4.0)
    # With a cap, no picture holds past it: the clip plays, then a closer angle takes the rest.
    capped = assemble.plan_shots([(0, 5.94), (5.94, 15.0)], [6.0, 6.0], 3.5, stretch={0, 1}, max_shot=4.8)
    assert capped[0] == (0, 0, 4.54, "motion") and capped[1] == (0, 4.54, 1.4, "punch")
    assert [s[3] for s in capped[2:]] == ["motion", "punch", "still"] and max(s[2] for s in capped) <= 4.8
    assert assemble.plan_shots([(0, 4.5)], [6.0], 3.5, stretch={0}, max_shot=4.8) == [(0, 0, 4.5, "motion")]
    assert "setpts" not in assemble.motion_vf(1080, 1920, 30) and "flags=lanczos" in assemble.motion_vf(1080, 1920, 30)


def test_labels_wait_for_the_hook_and_render_in_a_box():
    ev = assemble.overlay_events([(0.0, 3.0, "A"), (3.2, 6.0, "4 = VISA"), (6.0, 6.5, "TOO SHORT"), (6.5, 9, None)], 2.6)
    assert ev == [(3.32, 6.0, "4 = VISA")]
    doc = assemble.ass_document([(0, 1, "HI")], 1080, 1920, "F", 84, 520, overlays=ev)
    assert "Style: Label," in doc and ",Label,," in doc and "VISA" in doc
    assert "-maxrate" in assemble.FINAL_VIDEO and "-crf" in assemble.encode_args(30)


def test_shot_lists_validate_and_plan_one_picture_per_shot():
    from pipeline.script import validate
    example = json.loads((ROOT / "templates" / "example_script.json").read_text())
    assert validate(example, ALL_NICHES, PLATFORMS) == []
    no_shots = json.loads(json.dumps(example))
    del no_shots["blocks"][1]["shots"]
    assert any("needs a 'shots' list" in e for e in validate(no_shots, ALL_NICHES, PLATFORMS))
    assert validate(no_shots, ALL_NICHES, PLATFORMS, require_shots=False) == []
    bad = json.loads(json.dumps(example))
    bad["blocks"][0]["shots"][0].pop("action")
    bad["blocks"][0]["shots"][1]["words"] = 3
    bad["blocks"][2]["shots"][0]["overlay"] = "A LABEL FAR TOO LONG TO READ AT A GLANCE"
    errs = validate(bad, ALL_NICHES, PLATFORMS)
    assert any("'action' is required" in e for e in errs) and any("'words' must be" in e for e in errs)
    assert any("overlay must be a short label" in e for e in errs)
    stills = json.loads(json.dumps(example))
    for b in stills["blocks"]:
        b["shots"][0]["still"] = True
    assert any("shots are stills" in e for e in validate(stills, ALL_NICHES, PLATFORMS))

    prod = {**PROD, "tier": "quality"}
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), prod, PROD["voices"][0])
    sids = ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3"]
    assert [k["shot"] for k in g["keyframes"]] == sids and [m["shot"] for m in g["motion"]] == sids
    tier = PROD["tiers"]["quality"]
    assert g["keyframes"][0]["params"]["model"] == tier["keyframe"]["hook"]["model"]
    assert g["keyframes"][1]["params"]["model"] == tier["keyframe"]["model"]
    assert g["motion"][0]["params"]["medias"][0]["value"] == "<keyframe job_id for shot 1.1>"
    bracket = PROD["prompts"]["camera_moves"][example["blocks"][0]["shots"][0]["camera"]]["bracket"]
    assert g["motion"][0]["params"]["prompt"].startswith(f"{bracket} {example['blocks'][0]['shots'][0]['action']}")
    # Subject first, hook styling on the opening frame only; motion prompts carry no style.
    first, second = (f"{sh['framing']}: {sh['visual']}" for sh in example["blocks"][0]["shots"][:2])
    assert g["keyframes"][0]["params"]["prompt"].startswith(first) and PROD["prompts"]["hook_suffix"] in g["keyframes"][0]["params"]["prompt"]
    assert g["keyframes"][1]["params"]["prompt"].startswith(second) and PROD["prompts"]["hook_suffix"] not in g["keyframes"][1]["params"]["prompt"]
    assert PROD["prompts"]["motion_hook_suffix"] in g["motion"][0]["params"]["prompt"]
    assert PROD["prompts"]["motion_hook_suffix"] not in g["motion"][1]["params"]["prompt"]
    assert example["visual_style"] not in g["motion"][1]["params"]["prompt"]
    assert g["motion_retry"]["model"] == tier["motion"]["retry"]["model"]
    assets = {"keyframes": {s: f"https://k/{s}" for s in sids}, "motion": {s: f"https://m/{s}" for s in sids},
              "voice": "https://v"}
    assert production.validate_assets(assets, example, g) == []
    assert production.validate_assets({**assets, "motion": {}}, example, g)[0].startswith("motion.1.1")
    # A recurring character: the shot is drawn from the earlier shot's frame.
    again = json.loads(json.dumps(example))
    again["blocks"][2]["shots"][1]["ref"] = "1.1"
    assert validate(again, ALL_NICHES, PLATFORMS) == []
    k = production.generation_requests(again, niche_by_id(again["niche_id"]), prod, PROD["voices"][0])["keyframes"][7]
    assert k["after"] == ["1.1"] and k["params"]["model"] == tier["keyframe"]["ref"]["model"]
    assert k["params"]["medias"] == [{"role": "image_references", "value": "<keyframe job_id for shot 1.1>"}]
    again["blocks"][0]["shots"][0]["ref"] = "2.1"
    assert any("ref must name an earlier shot" in e for e in validate(again, ALL_NICHES, PLATFORMS))
    plan = production.render_plan(example, assets, PROD["render"])
    b2 = plan["blocks"][1]
    assert [s["motion_url"] for s in b2["shots"]] == ["https://m/2.1", "https://m/2.2", "https://m/2.3"]
    assert b2["shots"][1]["overlay"] == example["blocks"][1]["shots"][1]["overlay"]
    assert assemble.units(plan["blocks"])[3]["motion_url"] == "https://m/2.1"


def test_captions_take_the_scripts_spelling():
    heard = [(0.0, 0.3, "destroying"), (0.3, 0.5, "its"), (0.5, 0.8, "weak"), (0.8, 1.2, "farms:"),
             (1.2, 1.6, "In"), (1.6, 2.0, "1932,"), (2.0, 2.2, "a"), (2.2, 2.5, "dog.")]
    script = "destroying its wheat farms: In nineteen thirty-two, a dog."
    out = assemble.align_words(heard, script)
    assert [w[2] for w in out] == ["destroying", "its", "wheat", "farms:", "In", "1932,", "a", "dog."]
    assert out[2][:2] == (0.5, 0.8)                               # timings stay the voice's
    assert assemble.align_words(heard, "") == heard


# --- owner exports, formats, comment prompts --------------------------------------------

def test_owner_export_rows_match_their_posts(tmp_path):
    from pipeline import imports
    csv_file = tmp_path / "owner.csv"
    csv_file.write_text(
        "platform,title,published,views,reach,avg_view_seconds,likes,comments,shares,saves,follows\n"
        "youtube,Why You Hear Your Name in a Crowd,2026-10-19,263,,,,0,,,\n"
        'facebook,"What If the Sun Disap",2026-10-19 03:00,"1,244",229,7,2,0,0,0,0\n'
        "facebook,Why Credit Cards Have 16 Di,2026-10-19 05:00,137,108,9,0,0,0,1,0\n"
        "facebook,Could a Falling Penny Kill You?,2026-10-20 19:01,0,0,0,0,0,0,0,0\n"
        "instagram,Something we never posted,2026-10-19 03:00,5,,,,,,,\n", encoding="utf-8")
    rows = imports.read(csv_file)
    assert rows[0]["fields"] == {"views": 263, "comments": 0}            # blank cells stay out
    assert rows[1]["fields"]["views"] == 1244 and rows[2]["fields"]["saves"] == 1

    def run(rid, platform, at, **post):
        return {"run_id": rid, "posts": {platform: {"at": at, "status": "scheduled", **post}}}
    manifests = [
        run("crowd", "youtube", "2026-10-18T15:30:00-04:00"),             # 01:00 IST on the 19th
        run("party", "youtube", "2026-10-19T07:30:00-04:00"),             # same IST day, near title
        run("sun", "facebook", "2026-10-18T17:30:00-04:00"),
        run("credit", "facebook", "2026-10-18T19:30:00-04:00"),           # 2 h after sun
        run("penny", "facebook", "2026-10-21T09:30:00-04:00"),            # not out yet when read
        run("sun-ig", "instagram", "2026-10-18T17:30:00-04:00"),
    ]
    titles = {"crowd": "Why You Hear Your Name in a Crowd", "party": "Why You Hear Your Name at a Party",
              "sun": "What If the Sun Disappeared?", "credit": "Why Credit Cards Have 16 Digits",
              "penny": "Could a Falling Penny Kill You?", "sun-ig": "What if the Sun vanished right now"}
    now = datetime(2026, 10, 20, 14, tzinfo=timezone.utc)
    matched, unmatched = imports.match(rows, manifests, titles, "Asia/Kolkata", now)
    assert [(r, p) for r, p, _ in matched] == [("crowd", "youtube"), ("sun", "facebook"), ("credit", "facebook")]
    assert [r["title"] for r, _ in unmatched] == ["Could a Falling Penny Kill You?", "Something we never posted"]

    post = manifests[2]["posts"]["facebook"]
    fields = imports.record(post, rows[1]["fields"], now, "data/imports/owner.csv")
    assert fields["status"] == "published" and fields["views_age_hours"] == 40.5
    assert fields["stats_source"] == "data/imports/owner.csv" and fields["reach"] == 229
    assert imports.record({**post, "stats_at": "2026-10-20T15:00:00+00:00"}, rows[1]["fields"], now, "x") is None


def test_insights_group_by_format_and_finer_length():
    from pipeline import insights
    assert insights.format_of({"experiment": {"arms": {"format": "what-if"}}, "hook_type": "myth-bust"}) == "what-if"
    assert insights.format_of({"hook_type": "story teaser"}) == "micro-story"
    assert insights.format_of({"hook_type": "new-thing"}) == "new-thing" and insights.format_of({}) is None
    assert [insights.length_bucket(s) for s in (23, 36, 50, 67)] == ["under 30 s", "30-45 s", "45-60 s", "over 60 s"]
    at = (NOW - timedelta(hours=60)).isoformat()
    m = {"run_id": "r", "niche_id": "science-space", "hook_type": "what-if", "video": {"duration_seconds": 36},
         "posts": {"youtube": {"at": at, "views": 1000, "views_age_hours": 60, "avg_view_seconds": 12}}}
    young = {**m, "posts": {"youtube": {**m["posts"]["youtube"], "views": 0, "views_age_hours": 16}}}
    assert insights.video_rows([young]) == []          # too young to judge (YouTube decides late)
    row = insights.video_rows([m])[0]
    assert row["format"] == "what-if" and row["length"] == "30-45 s" and "format" in insights.DIMENSIONS
    assert dashboard.insight_rows(insights.summarize([row] * 3), NICHES)[1]["dimension"] == "Format"


def test_proven_niches_outrank_untested_ones_in_reach_phase():
    from pipeline.config import strategy_weights
    prod = load_yaml("production.yaml")

    def posted(niche, i, views, hours=60.0):
        at = (NOW - timedelta(hours=hours + i)).isoformat()
        return {"run_id": f"{niche}-{i}", "niche_id": niche, "created_at": at, "video": {"duration_seconds": 36},
                "posts": {"youtube": {"status": "published", "at": at, "views": views, "views_age_hours": hours}}}
    history = [posted("science-space", i, 4000) for i in range(4)] + [posted("investing", i, 400) for i in range(4)]
    # Research hypes an untested money niche: the channel's own winner still leads.
    snap = {"niches": {"personal-finance": {"trend_boost": 2.5}, "science-space": {"trend_boost": 1.0}}}
    ranked = {s["id"]: s for s in trends.score_niches(NICHES, snap, history, NOW + timedelta(days=5),
                                                      strategy_weights(prod))}
    assert ranked["science-space"]["score"] > ranked["personal-finance"]["score"]


def test_comment_prompt_goes_out_as_first_comment_on_meta():
    from pipeline import metricool
    from pipeline.script import validate
    script = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    niche = niche_by_id(script["niche_id"])
    caps = build_captions(script, niche, PLATFORMS)
    assert caps["instagram"]["first_comment"] == script["captions"]["comment_prompt"]
    base = {"at": "2026-10-19T16:00:00-04:00", "video_url": "https://v.mp4", "title": "T", "text": "Body",
            "ai_disclosure_fallback": "Made with AI.", "first_comment": "Guess?"}
    for platform in ("instagram", "facebook"):
        info = json.loads(metricool.schedule_args({**base, "platform": platform}, PLATFORMS)["info"])
        assert info["firstCommentText"] == "Guess?"
    plain = {k: v for k, v in base.items() if k != "first_comment"}
    assert json.loads(metricool.schedule_args({**plain, "platform": "youtube", "tags": []}, PLATFORMS)["info"])[
        "firstCommentText"] == ""
    bad = {**script, "captions": {**script["captions"], "comment_prompt": "Not a question."}}
    assert any("comment_prompt" in e for e in validate(bad, NICHES, PLATFORMS))


def test_shelved_runs_read_shelved_not_missed():
    snap = {"videos": [{"run_id": "a", "date": "2026-10-15", "niche": "n", "topic": "t", "posts": {},
                        "shelved": "test clip"},
                       {"run_id": "b", "date": "2026-10-16", "niche": "n", "topic": "t",
                        "posts": {"youtube": {"status": "published"}}}]}
    rows = {r["run_id"]: r for r in dashboard.video_rows(snap, ["youtube", "instagram"])}
    assert rows["a"]["youtube"] == rows["a"]["instagram"] == "shelved"
    assert rows["b"]["youtube"] == "published" and rows["b"]["instagram"] == "not posted"


def test_shots_carry_timed_beats_camera_cast_and_framing():
    from pipeline.script import validate
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    s = json.loads(json.dumps(example))
    s["cast"]["Mia"] = "a 30-year-old woman, short black bob, mustard-yellow raincoat, round red glasses"
    shot = s["blocks"][0]["shots"][0]
    shot.update(framing="Extreme close-up, low angle", cast=["Mia"], camera="crash zoom",
                beats=["her eyes snap open", "she grabs the letter and tears it open", "her jaw drops"])
    shot.pop("action")
    s["blocks"][0]["shots"][1]["framing"] = "Wide shot, overhead"
    assert validate(s, ALL_NICHES, PLATFORMS) == []
    prod = {**PROD, "tier": "quality"}
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), prod, PROD["voices"][0])
    key, motion = g["keyframes"][0]["params"]["prompt"], g["motion"][0]["params"]["prompt"]
    assert key.startswith("Extreme close-up, low angle: " + shot["visual"].rstrip(". "))
    assert "Characters: Mia: a 30-year-old woman" in key and "Mia" not in motion   # the frame already shows her
    move = PROD["prompts"]["camera_moves"]["crash zoom"]
    # Beats chain with "then"; Hailuo's bracket command opens the prompt.
    assert motion.startswith(f"{move['bracket']} Her eyes snap open, then she grabs the letter and tears it open, "
                             "then her jaw drops. ")
    assert f"Camera: {move['words']}." in motion and "Stylized 3D animation." in motion
    window = PROD["prompts"]["beat_window"]
    timed = production.motion_text(shot, {**PROD["prompts"], "beat_style": "timed"}, "seedance_2_0_mini")
    assert timed.startswith(f"0-{window / 3:g} s: her eyes snap open. ") and f"{2 * window / 3:g}-{window:g} s: her jaw drops." in timed
    plain = production.motion_text({**shot, "camera": "crash zoom"}, PROD["prompts"], "seedance_2_0_mini")
    assert move["bracket"] not in plain and move["words"] in plain
    # Broken fields are named.
    bad = json.loads(json.dumps(s))
    b0 = bad["blocks"][0]["shots"]
    b0[0].update(camera="dutch spin", cast=["Max"], beats=["only one"])
    b0[1]["framing"] = "Extreme close-up, low angle"
    errs = validate(bad, ALL_NICHES, PLATFORMS)
    assert any("camera must be one of" in e for e in errs) and any("cast Max" in e for e in errs)
    assert any("'beats' must be 2-3" in e for e in errs) and any("share the framing" in e for e in errs)


def test_shot_sound_cues_come_from_the_sound_sheet(tmp_path, monkeypatch):
    import wave
    import numpy as np
    from pipeline.script import validate
    sheet = PROD["render"]["audio"]["sfx"]
    assert production.sound_cue(sheet, "ding") == {"url": sheet["url"], "start": 2 * sheet["slot_seconds"],
                                                    "seconds": sheet["slot_seconds"]}
    assert production.sound_cue(sheet, "kazoo") is None and production.sound_cue(sheet, None) is None
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    example["blocks"][0]["shots"][0]["sfx"] = "thud"
    assert validate(example, ALL_NICHES, PLATFORMS) == []
    shots = [sid for i, b in enumerate(example["blocks"], 1) for sid in production.shot_ids(i, b)]
    assets = {"keyframes": {s: f"https://k/{s}" for s in shots}, "motion": {}, "voice": "https://v"}
    plan = production.render_plan(example, assets, PROD["render"])
    assert plan["blocks"][0]["shots"][0]["sfx"]["start"] == sheet["names"].index("thud") * sheet["slot_seconds"]
    assert plan["blocks"][0]["shots"][2]["sfx"] is None and "sfx" not in plan["audio"]
    example["blocks"][0]["shots"][0]["sfx"] = "kazoo"
    assert any("sfx must be one of" in e for e in validate(example, ALL_NICHES, PLATFORMS))

    # The assembler plays the slot on the shot's first frame instead of that cut's whoosh.
    sr = assemble.SR
    t = np.arange(int(0.5 * sr)) / sr
    tone = np.concatenate([np.zeros(int(0.5 * sr)), 0.8 * np.sin(2 * np.pi * 1000 * t) * np.exp(-t * 4)])
    path = tmp_path / "sheet.wav"
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((tone * 32767).astype(np.int16).tobytes())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "work").mkdir()
    cfg = {"music_db": None, "sfx_db": -19, "native_db": None}
    cue = {"url": path.as_uri(), "start": 0.5, "seconds": 0.5}
    bed_path = assemble.audio_bed(4.0, [1.0, 2.0], [], cfg, 1, [(2.0, cue)])
    assert assemble.audio_bed.used["cues"] == 1
    with wave.open(bed_path) as f:
        bed = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(float)
    n = int(0.35 * sr)
    probe = np.exp(2j * np.pi * 1000 * np.arange(n) / sr)    # phase-free 1 kHz detector
    tone_at = lambda s0: abs(bed[int(s0 * sr): int(s0 * sr) + n] @ probe) / n  # noqa: E731
    assert tone_at(1.95) > 100        # the 1 kHz cue is there at 2.0 s
    assert tone_at(0.95) < 20         # 1.0 s got the plain whoosh


def test_shot_counters_validate_plan_and_script():
    from pipeline.script import validate
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    shot = example["blocks"][1]["shots"][0]
    shot.pop("overlay", None)
    shot["counter"] = {"to": 480000, "prefix": "$"}
    assert validate(example, ALL_NICHES, PLATFORMS) == []
    shots = [sid for i, b in enumerate(example["blocks"], 1) for sid in production.shot_ids(i, b)]
    assets = {"keyframes": {s: f"https://k/{s}" for s in shots}, "motion": {}, "voice": "https://v"}
    plan = production.render_plan(example, assets, PROD["render"])
    assert plan["blocks"][1]["shots"][0]["counter"] == {"to": 480000, "prefix": "$"}
    assert plan["effectcraft"]["sha256"] == PROD["render"]["effectcraft"]["sha256"]
    for bad, msg in (({"from": 5}, "needs a number 'to'"), ({"to": 5, "from": 5}, "other than 'to'"),
                     ({"to": 9, "suffix": "percent"}, "suffix"), ({"to": 9, "decimals": 3}, "decimals")):
        shot["counter"] = bad
        assert any(msg in e for e in validate(example, ALL_NICHES, PLATFORMS)), bad
    shot.update(counter={"to": 9}, overlay="9 TIMES")
    assert any("not both" in e for e in validate(example, ALL_NICHES, PLATFORMS))

    # The EffectCraft script counts in the caption gold, with grouping and the prefix.
    jsx = assemble.counter_jsx({"to": 1234.5, "from": 0, "prefix": "$", "suffix": "/yr", "decimals": 1},
                               3.0, 1080, 1920, 30, "Montserrat-ExtraBold", (0.96, 0.72, 0.24), "/w/c.ecproj")
    assert "addComp('Counter', 1080, 1920, 1, 3.000, 30)" in jsx
    assert "linear(time, 0.1, 2.1, 0.0, 1234.5)" in jsx and "toFixed(1)" in jsx
    assert '\\"$\\" + p.join(' in jsx and '\\"/yr\\"' in jsx and "\\\\B(?=" in jsx
    assert "doc.fillColor = [0.960, 0.720, 0.240]" in jsx and 'new File("/w/c.ecproj")' in jsx


def test_object_shots_get_no_face_and_outfit_line():
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    prod = {**PROD, "tier": "quality"}
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), prod, PROD["voices"][0])
    by_shot = {m["shot"]: m["params"]["prompt"] for m in g["motion"]}
    assert PROD["prompts"]["motion_suffix"] in by_shot["1.1"]            # Sam is in it
    assert "face" not in by_shot["1.2"] and PROD["prompts"]["motion_object_suffix"] in by_shot["1.2"]


def test_youtube_keeps_its_own_wider_gap():
    cfg = {**load_yaml("timing.yaml"), "explore_rate": 0}
    tz = timing.ZoneInfo(cfg["timezone"])
    day = date(2026, 10, 21)
    now = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    taken = {"run_id": "a", "posts": {p: {"at": "2026-10-21T16:00:00-04:00", "status": "scheduled"}
                                      for p in ("youtube", "instagram")}}
    got = timing.plan(cfg, day, now, [taken], platforms=("youtube", "instagram"), run_id="b")
    yt = datetime.fromisoformat(got["youtube"]["at"])
    ig = datetime.fromisoformat(got["instagram"]["at"])
    busy = datetime(2026, 10, 21, 16, 0, tzinfo=tz)
    assert abs(yt - busy) >= timedelta(hours=6) and abs(ig - busy) >= timedelta(hours=2)
    assert got["youtube"]["at"].startswith("2026-10-21T10:00")       # same day, 6 h before


def test_prompts_keep_studio_names_brackets_and_copies_of_copies_out():
    from pipeline.script import validate
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    bad = json.loads(json.dumps(example))
    bad["visual_style"] += ", Pixar-quality characters"
    bad["blocks"][1]["shots"][0]["beats"][0] = "a kid runs past the jars"
    bad["blocks"][0]["narration"] = "[excited] " + bad["blocks"][0]["narration"]
    bad["delivery"] = "[shouting]"
    errs = validate(bad, ALL_NICHES, PLATFORMS)
    assert any("may not name Pixar, kid" in e for e in errs) and any("narration has brackets" in e for e in errs)
    assert any(e.startswith("delivery must be") for e in errs)
    # A shot brought back from a shot that was itself brought back is drawn from the master.
    s = json.loads(json.dumps(example))
    s["blocks"][1]["shots"][2]["ref"] = "1.1"
    s["blocks"][2]["shots"][2]["ref"] = "2.3"
    s["delivery"] = "hushed, suspenseful storyteller"
    assert validate(s, ALL_NICHES, PLATFORMS) == []
    g = production.generation_requests(s, niche_by_id(s["niche_id"]), {**PROD, "tier": "quality"}, PROD["voices"][0])
    last = next(k for k in g["keyframes"] if k["shot"] == "3.3")
    assert last["after"] == ["1.1"] and last["params"]["prompt"].startswith(
        PROD["prompts"]["ref_prefixes"]["character"].format(name="the character", n=1))
    assert g["voice"]["params"]["prompt"].startswith("[hushed, suspenseful storyteller, starts speaking immediately] ")
    assert g["motion_retry"]["prompt_suffix"] == PROD["prompts"]["motion_model_suffix"]["seedance_2_0_mini"]
    assert production.motion_style_tag("Photorealistic cinematic film still", PROD["prompts"]) == \
        PROD["prompts"]["motion_style_tags"]["photoreal"]


def test_style_key_trial_puts_one_look_frame_in_front_of_every_keyframe():
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    example["blocks"][2]["shots"][2]["ref"] = "1.1"
    prod = {**PROD, "tier": "quality"}
    plain = production.generation_requests(example, niche_by_id(example["niche_id"]), prod, PROD["voices"][0])
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), prod, PROD["voices"][0],
                                       style_key=True)
    key, frames = g["keyframes"][0], g["keyframes"][1:]
    cfg = PROD["tiers"]["quality"]["keyframe"]["style_key"]
    assert g["style_key"] and not plain["style_key"] and key["shot"] == production.STYLE_KEY
    assert key["params"]["prompt"].startswith(PROD["prompts"]["style_key_prompt"] + " " + example["through_line"])
    assert all(f["params"]["model"] == cfg["model"] and f["params"]["prompt"].startswith(PROD["prompts"]["style_ref_prefix"])
               for f in frames)
    assert all(f["params"]["medias"][0]["value"] == "<keyframe job_id for shot key>" for f in frames)
    back = next(f for f in frames if f["shot"] == "3.3")
    assert back["after"] == ["key", "1.1"] and [m["value"] for m in back["params"]["medias"]] == \
        ["<keyframe job_id for shot key>", "<keyframe job_id for shot 1.1>"]
    assert "from image 2 exactly" in back["params"]["prompt"]
    assert PROD["prompts"]["hook_suffix"] in frames[0]["params"]["prompt"]
    assert 2 < g["estimated_credits"] - plain["estimated_credits"] < 5      # about +0.35 a frame on Seedream
    assert [m["params"]["medias"][0]["value"] for m in g["motion"]][:1] == ["<keyframe job_id for shot 1.1>"]


def test_asset_lock_copies_each_character_object_and_place_from_its_first_frame():
    from pipeline.script import validate
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    example["world"] = "a bright modern office in 2026, soft morning daylight"
    example["props"] = {"Jar": "a tall clear glass jar with a brass lid"}
    example["places"] = {"Desk": "Sam's white office desk by a big window, a green plant"}
    b = example["blocks"]
    b[0]["shots"][0]["place"] = "Desk"
    b[1]["shots"][1]["props"] = ["Jar"]
    b[1]["shots"][2]["props"] = ["Jar"]
    b[2]["shots"][2]["place"] = "Desk"
    assert validate(example, ALL_NICHES, PLATFORMS) == []
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), {**PROD, "tier": "quality"},
                                       PROD["voices"][0], style_key=True)
    by = {k["shot"]: k for k in g["keyframes"]}
    assert by["1.1"]["after"] == ["key"] and "Place: Desk: Sam's white office desk" in by["1.1"]["params"]["prompt"]
    assert "World: a bright modern office in 2026, soft morning daylight." in by["1.2"]["params"]["prompt"]
    assert by["2.2"]["after"] == ["key"]                                  # the jar's first frame
    assert by["2.3"]["after"] == ["key", "1.1", "2.2"]                    # Sam from 1.1, the jar from 2.2
    jar = PROD["prompts"]["ref_prefixes"]["object"].format(name="Jar", n=3)
    assert jar in by["2.3"]["params"]["prompt"] and "Props: Jar: a tall clear glass jar" in by["2.3"]["params"]["prompt"]
    assert by["3.3"]["after"] == ["key", "1.1"]                           # Sam and the desk both first drawn in 1.1
    assert "World: a bright modern office" in g["keyframes"][0]["params"]["prompt"]   # the style key too
    assert PROD["prompts"]["motion_hook_suffix"] in g["motion"][0]["params"]["prompt"]
    bad = json.loads(json.dumps(example))
    bad["blocks"][0]["shots"][1]["props"] = ["Car"]
    bad["blocks"][0]["shots"][2]["place"] = "Moon"
    errs = validate(bad, ALL_NICHES, PLATFORMS)
    assert any("props Car" in e for e in errs) and any("place 'Moon'" in e for e in errs)


# --- the H3 tier: one multi-shot clip per block --------------------------------------

def h3_example():
    example = json.loads((ROOT / "templates" / "example_script.json").read_text(encoding="utf-8"))
    example["props"] = {"Jar": "a tall clear glass jar with a brass lid"}
    b = example["blocks"]
    b[1]["shots"][1]["props"] = ["Jar"]
    b[1]["shots"][2]["props"] = ["Jar"]
    return example


def test_trial_tier_runs_the_owner_test_then_returns_to_the_tier():
    trial = PROD["trial_tier"]
    assert trial["name"] in PROD["tiers"]
    assert production.trial_tier(PROD, []) == trial["name"]
    done = [{"run_id": "a", "tier": trial["name"]}] * trial["videos"]
    assert production.trial_tier(PROD, done) == PROD["tier"]
    assert production.trial_tier(PROD, done[:1], run_id="a") == (trial["name"] if trial["videos"] == 1 else PROD["tier"])
    assert production.trial_tier({**PROD, "trial_tier": None}, []) == PROD["tier"]


def test_h3_plan_draws_a_roster_then_one_multishot_clip_per_block():
    example = h3_example()
    cfg = PROD["tiers"]["h3"]
    assert cfg["motion"]["params"]["resolution"] == "480p"                 # the owner's rule
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), PROD, PROD["voices"][0],
                                       tier_name="h3")
    assert g["tier"] == "h3" and g["multishot"] and g["style_key"]
    key, roster = g["keyframes"][0], g["keyframes"][1:]
    assert key["shot"] == production.STYLE_KEY and "after" not in key
    assert [r["shot"] for r in roster] == [production.asset_key(k, n) for k, n, _ in production.roster(
        example, [s for b in example["blocks"] for s in production.shots_of(b)])]
    assert all(r["after"] == ["key"] and r["params"]["model"] == cfg["keyframe"]["model"] for r in roster)
    assert {r["shot"]: r["params"]["aspect_ratio"] for r in roster}["object:Jar"] == "1:1"
    assert all(r["params"]["aspect_ratio"] == "2:3" for r in roster if r["shot"].startswith("character:"))
    blocks = [b for b in example["blocks"] if not b.get("footage")]
    assert len(g["motion"]) == len(blocks)
    for m, b in zip(g["motion"], blocks):
        p = m["params"]
        assert p["model"] == "minimax_h3_max" and p["duration"] == m["seconds"] and 5 <= m["seconds"] <= 15
        assert m["credits"] == m["seconds"] * cfg["motion"]["credits_per_second"]
        assert [s[0] for s in m["spans"]] == production.shot_ids(m["block"], b)
        assert m["spans"][0][1] == 0.0 and abs(m["spans"][-1][1] + m["spans"][-1][2] - m["seconds"]) < 0.05
        assert len(p["medias"]) <= cfg["motion"]["max_references"] and m["after"]
        assert p["prompt"].count("HARD CUT.") == len(b["shots"]) - 1 and "SHOT 1 — 0.0s to" in p["prompt"]
        assert "@Image1 = " in p["prompt"] and "no voice, no narration, no music" in p["prompt"]
    jar = g["motion"][1]
    assert "object:Jar" in jar["after"] and "OBJECT Jar: a tall clear glass jar" in jar["params"]["prompt"]
    assert PROD["prompts"]["multishot"]["hook"] in g["motion"][0]["params"]["prompt"]
    assert PROD["prompts"]["multishot"]["hook"] not in g["motion"][1]["params"]["prompt"]
    words = len(" ".join(b["narration"] for b in example["blocks"]).split())
    assert g["estimated_credits"] == round(sum(k["credits"] for k in g["keyframes"]) + sum(m["credits"] for m in g["motion"])
                                           + words / 100 * cfg["voice"]["credits_per_100_words"], 2)


def test_h3_references_go_place_characters_objects_and_cap_at_seven():
    example = h3_example()
    example["places"] = {"Desk": "a white office desk by a big window"}
    example["props"].update({f"P{k}": f"object number {k}" for k in range(8)})
    shot = example["blocks"][0]["shots"][0]
    shot["props"] = [f"P{k}" for k in range(8)]
    shot["place"] = "Desk"
    m = production.generation_requests(example, niche_by_id(example["niche_id"]), PROD, PROD["voices"][0],
                                       tier_name="h3")["motion"][0]
    assert len(m["after"]) == 7 and m["after"][0] == "place:Desk" and m["after"][1].startswith("character:")


def test_clip_timing_fits_the_narration_within_the_model_range():
    motion = PROD["tiers"]["h3"]["motion"]
    short = {"narration": "Three words here.", "shots": [{"visual": "a"}, {"visual": "b"}]}
    assert production.clip_timing(short, motion) == (5, [(0.0, 2.5), (2.5, 2.5)])
    long = {"narration": " ".join(["word"] * 60), "shots": [{"visual": "a", "words": 2}, {"visual": "b", "words": 1}]}
    seconds, spans = production.clip_timing(long, motion)
    assert seconds == 15 and spans == [(0.0, 10.0), (10.0, 5.0)]
    mid = {"narration": " ".join(["word"] * 21), "visual": "x"}
    assert production.clip_timing(mid, motion)[0] == round(21 / 2.8 + 0.5)
    seedance = PROD["tiers"]["multishot"]["motion"]
    assert production.clip_timing(mid, seedance)[0] == round(21 / 2.8)                   # no pad: billed by the second
    assert production.clip_timing(short, seedance)[0] == 4


def test_h3_render_plan_points_each_shot_at_its_stretch_of_the_block_clip():
    example = h3_example()
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), PROD, PROD["voices"][0],
                                       tier_name="h3")
    assets = {"keyframes": {k["shot"]: f"https://k/{k['shot']}" for k in g["keyframes"]},
              "motion": {m["shot"]: f"https://m/{m['shot']}" for m in g["motion"]}, "voice": "https://v"}
    assert production.validate_assets(assets, example, g) == []
    assert production.validate_assets({**assets, "motion": {}}, example, g)
    plan = production.render_plan(example, assets, PROD["render"], g)
    first = plan["blocks"][0]["shots"]
    assert all(s["motion_url"] == "https://m/1" and s["image_url"] is None for s in first)
    assert [(s["clip_start"], s["clip_len"]) for s in first] == [(t0, n) for _, t0, n in g["motion"][0]["spans"]]


def test_h3_budget_prices_clip_seconds():
    h3 = PROD["tiers"]["h3"]
    cost = budget.video_cost(h3, 105, 7, 41)
    assert cost == round(7 * 0.5 + 41 * 1.5 + 105 / 100 * 1.8, 2)
    assert budget.video_cost(h3, 112, 7) == round(7 * 0.5 + 112 / 2.8 * 1.5 + 112 / 100 * 1.8, 2)
    q = PROD["tiers"]["quality"]
    assert budget.video_cost(q, 105, 11) == round(11 * q["keyframe"]["credits"] + 11 * q["motion"]["credits"] + 1.89, 2)


def test_assembler_moves_planned_cuts_onto_the_clip_real_cuts():
    assert assemble.snap_cuts([2.5, 5.5], [2.625, 5.708]) == [2.625, 5.708]
    assert assemble.snap_cuts([2.5, 5.5], []) == [2.5, 5.5]
    assert assemble.snap_cuts([2.5, 5.5], [0.4, 7.9]) == [2.5, 5.5]               # too far: kept as planned
    assert assemble.snap_cuts([2.5, 2.8], [2.6]) == [2.6, 3.1]                    # one cut used once, order kept
    assert assemble.clip_spans([0.0, 2.5, 5.5], 8.0, [2.625, 5.708]) == [(0.0, 2.625), (2.625, 3.083), (5.708, 2.292)]
    assert assemble.clip_spans([0.0], 6.0, [3.0]) == [(0.0, 6.0)]


def test_every_video_is_made_at_480p():
    """The owner's rule (2026-10-22): the active tier and any trial tier generate at 480p."""
    for name in {PROD["tier"], (PROD.get("trial_tier") or {}).get("name") or PROD["tier"]}:
        motion = PROD["tiers"][name]["motion"]
        assert motion["params"]["resolution"] == "480p", name
        assert (motion.get("retry") or {}).get("params", {}).get("resolution", "480p") == "480p", name


def test_seedance_multishot_orders_shots_and_keeps_the_clip_rate():
    example = h3_example()
    g = production.generation_requests(example, niche_by_id(example["niche_id"]), PROD, PROD["voices"][0])
    assert g["tier"] == "multishot" and g["multishot"]
    m = g["motion"][1]
    p = m["params"]
    assert p["model"] == "seedance_2_0_mini" and p["bitrate_mode"] == "high" and p["generate_audio"] is True
    assert "Shot 1, " in p["prompt"] and "Cut to:" in p["prompt"] and "HARD CUT." not in p["prompt"]
    assert p["prompt"].endswith(PROD["prompts"]["motion_model_suffix"]["seedance_2_0_mini"])
    assert m["credits"] == m["seconds"] * 0.5 and 10 < g["estimated_credits"] < 30
    assets = {"keyframes": {}, "motion": {x["shot"]: f"https://m/{x['shot']}" for x in g["motion"]}, "voice": "https://v"}
    assert production.render_plan(example, assets, PROD["render"], g)["fps"] == "source"
    assert production.render_plan(example, assets, PROD["render"])["fps"] == PROD["render"]["fps"]


def test_assembler_follows_the_real_cuts_near_the_plan():
    # Seedance's cuts land a second or so from the plan; a stray detection far away is ignored.
    assert assemble.clip_spans([0.0, 3.5, 6.0], 8.0, [2.625, 5.708]) == [(0.0, 2.625), (2.625, 3.083), (5.708, 2.292)]
    # One cut missing: the found one is used where it is near, the plan elsewhere.
    assert assemble.clip_spans([0.0, 2.5, 5.5], 8.0, [5.6]) == [(0.0, 2.5), (2.5, 3.1), (5.6, 2.4)]
    assert assemble.clip_spans([0.0, 2.5, 4.7], 8.0, [0.958, 1.75]) == [(0.0, 1.75), (1.75, 2.95), (4.7, 3.3)]


def test_untested_niche_borrows_its_family_results():
    niches = [{"id": "a", "family": "money"}, {"id": "b", "family": "money"}, {"id": "c", "family": "money"},
              {"id": "d"}]
    assert trends.family_lifts(niches, {"a": -0.4, "b": -0.2}) == {"money": pytest.approx(-0.3)}
    w = {**PROD["strategy"]["phases"]["reach"]}
    scored = {s["id"]: s for s in trends.score_niches(NICHES, None, [], NOW, w)}
    assert all(s["parts"]["results"] == 0.0 for s in scored.values())           # no results, nothing borrowed
    assert w["family_share"] > 0 and {n.get("family") for n in NICHES} >= {"money", "curiosity"}
