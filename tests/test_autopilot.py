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
    assert plan["tier"] == "quality" and 35 < plan["est_cost_per_video"] < 45
    assert plan["videos_today"] == 1                    # ~24 shot-list videos fit in the cycle
    reach = budget.plan_today({**PROD, "tier": "reach"}, 1050, date(2026, 10, 18), None)
    assert 10 < reach["est_cost_per_video"] < 14 and reach["videos_today"] == 2
    lean = budget.plan_today({**PROD, "tier": "lean"}, 1050, date(2026, 10, 18), None)
    assert 25 < lean["est_cost_per_video"] < 40 and lean["videos_today"] == 1


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
    assert "No written text" in g["keyframes"][0]["params"]["prompt"]
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
    assert files["credits"][0]["videos_left"] == (1050 - 80) // files["credits"][0]["cost_per_video"]
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
    cfg = {**TIMING, "explore_rate": 0}
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

    def posted(niche, i, views, hours=40.0):
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
    assert g["motion"][0]["params"]["prompt"].startswith(example["blocks"][0]["shots"][0]["action"])
    # Subject first, hook styling on the opening frame only; motion prompts carry no style.
    first, second = (example["blocks"][0]["shots"][k]["visual"] for k in (0, 1))
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
    assert k["after"] == "1.1" and k["params"]["model"] == tier["keyframe"]["ref"]["model"]
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
