import json
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from pipeline import hermes_ops, localdash, metrics
from pipeline.config import ROOT, load_yaml

CFG = load_yaml("hermes.yaml")
DAY = date(2026, 10, 20)


class FakeHermes:
    """Stands in for subprocess.run: answers the commands the kickoff sends and records them."""

    def __init__(self, credits=1000, ready=True, boards="default"):
        self.calls, self.credits, self.ready, self.boards, self.n = [], credits, ready, boards, 0

    def __call__(self, cmd, timeout=None):
        self.calls.append(cmd)
        ok = SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd[0] == "higgsfield":
            return SimpleNamespace(returncode=0, stdout=json.dumps({"credits": self.credits}), stderr="")
        if "mcp" in cmd and "test" in cmd:
            return SimpleNamespace(returncode=0 if self.ready else 3, stdout="", stderr="")
        if cmd[1:4] == ["kanban", "boards", "list"]:
            return SimpleNamespace(returncode=0, stdout=self.boards, stderr="")
        if "create" in cmd and "kanban" in cmd and "boards" not in cmd:
            self.n += 1
            return SimpleNamespace(returncode=0, stdout=json.dumps({"id": f"t_{self.n}"}), stderr="")
        return ok

    def creates(self):
        return [c for c in self.calls if "create" in c and "boards" not in c]

    def subs(self):
        return [c for c in self.calls if "notify-subscribe" in c]


def flag(cmd, name):
    return [cmd[i + 1] for i, c in enumerate(cmd) if c == name]


def plan(videos=1, cost=31.4):
    return {"videos_today": videos, "est_cost_per_video": cost, "tier": "lean", "balance": 1000.0,
            "days_left_in_cycle": 29}


def test_cards_chain_research_scripts_produce_publish():
    cards = hermes_ops.plan_cards(CFG, DAY, plan(1))
    assert [c["key"] for c in cards] == ["research", "scripts", "produce", "publish"]
    assert [c["parents"] for c in cards] == [[], ["research"], ["scripts"], ["produce"]]
    assert [c["assignee"] for c in cards] == ["fm-research", "fm-writer", "fm-producer", "fm-publisher"]
    assert "37.7 credits" in cards[2]["body"]  # 1 video x 31.4 + 20% for retries


def test_no_videos_means_research_then_publish_with_the_reason():
    cards = hermes_ops.plan_cards(CFG, DAY, plan(0), ["Higgsfield is not signed in"])
    assert [c["key"] for c in cards] == ["research", "publish"]
    assert cards[1]["parents"] == ["research"]
    assert "Higgsfield is not signed in" in cards[1]["body"]


def test_kickoff_creates_idempotent_cards_on_the_board_in_the_repo():
    fake = FakeHermes(credits=1000)
    cfg = {**CFG, "notify": {**CFG["notify"], "chat_id": "123456789012345678"}}
    out = hermes_ops.kickoff(DAY, cfg=cfg, run=fake, env={}, manifests=[])
    assert out["videos_today"] == 1 and out["notes"] == []
    creates = fake.creates()
    assert len(creates) == 4
    for cmd, key in zip(creates, ["research", "scripts", "produce", "publish"]):
        assert flag(cmd, "--board") == ["faceless"]
        assert flag(cmd, "--workspace") == [f"dir:{ROOT}"]
        assert flag(cmd, "--idempotency-key") == [f"fm-{DAY}-{key}"]
    assert flag(creates[2], "--parent") == ["t_2"]  # produce waits for scripts
    modes = [flag(c, "--delivery-mode")[0] for c in fake.subs()]
    assert modes == ["notify", "notify", "notify", "notify+wake"]  # the last card wakes fm-lead
    assert all(flag(c, "--notifier-profile") == ["fm-lead"] for c in fake.subs())
    # the board did not exist yet, so it was created
    assert any(c[1:4] == ["kanban", "boards", "create"] for c in fake.calls)


def test_kickoff_makes_no_videos_while_nothing_is_signed_in():
    fake = FakeHermes(credits=1000, ready=False, boards="faceless")
    out = hermes_ops.kickoff(DAY, cfg=CFG, run=fake, env={}, manifests=[])
    assert out["videos_today"] == 0
    assert len(out["notes"]) == 2
    assert [c["key"] for c in out["cards"]] == ["research", "publish"]
    assert fake.subs() == []  # no Discord channel configured yet
    assert out["notifications"] is False


def test_upload_post_keys_count_as_a_publisher():
    fake = FakeHermes(ready=False)
    ready = hermes_ops.readiness(CFG, fake, {"UPLOADPOST_API_KEY": "k", "UPLOADPOST_USER": "u"})
    assert ready["publisher"] and not ready["metricool"]


def test_dry_run_creates_nothing():
    fake = FakeHermes()
    out = hermes_ops.kickoff(DAY, balance=500, dry_run=True, cfg=CFG, run=fake, env={}, manifests=[])
    assert fake.creates() == [] and "task_ids" not in out
    assert not any(c[0] == "higgsfield" for c in fake.calls)  # balance was given


def test_kickoff_message_names_what_needs_the_owner():
    msg = hermes_ops.kickoff_message({"date": "2026-10-20", "videos_today": 0, "est_cost_per_video": 31.4,
                                      "balance": 50.0, "notes": ["no publisher is signed in"],
                                      "cards": [{"key": "research"}], "task_ids": {"research": "t_1"},
                                      "notifications": False}, "faceless")
    assert msg.startswith("Faceless kickoff Tue Oct 20 ET: 0 videos today")
    assert "Needs you: no publisher is signed in" in msg
    assert "route-discord.sh" in msg


def test_on_demand_approve_creates_produce_then_publish():
    fake = FakeHermes(boards="faceless")
    ids = hermes_ops.approve_video("t_w", 32, post=True, day=DAY, cfg=CFG, run=fake)
    produce, publish = fake.creates()
    assert flag(produce, "--parent") == ["t_w"] and flag(publish, "--parent") == [ids["produce"]]
    assert "38.4" in flag(produce, "--body")[0]  # 32 credits + 20%


# --- Metricool numbers for the dashboard ------------------------------------------------

def test_external_metrics_validate_and_load(tmp_path):
    doc = {"date": "2026-10-20", "source": "metricool",
           "platforms": {"tiktok": {"followers": 120, "views": 5300}},
           "youtube_revenue": [{"day": "2026-10-19", "estimatedRevenue": 0.42}]}
    assert metrics.validate_external(doc) == []
    (tmp_path / "2026-10-19.json").write_text(json.dumps(doc))
    assert metrics.load_external(DAY, directory=tmp_path)["platforms"]["tiktok"]["views"] == 5300
    assert metrics.load_external(DAY + timedelta(days=5), directory=tmp_path) is None


def test_external_metrics_reject_guesses():
    bad = {"date": "d", "source": "metricool", "platforms": {"tiktok": {"views": "about 5k"}, "myspace": {}}}
    errors = metrics.validate_external(bad)
    assert any("tiktok" in e for e in errors) and any("myspace" in e for e in errors)


# --- local dashboard --------------------------------------------------------------------

def test_page_wraps_the_dashboard_for_hermes():
    page = localdash.render_page("tok123")
    assert '"token": "tok123"' in page and "earnings_daily" in page
    assert "Connect Metricool to Claude" not in page
    assert "window.dash" in page and "cdnjs.cloudflare.com/ajax/libs/d3/7.9.0" in page


@pytest.fixture
def server():
    launched = []
    status = SimpleNamespace(get=lambda: {"higgsfield": True, "metricool": False}, invalidate=lambda: None)
    handler = localdash.make_handler("tok", CFG, status, launch=lambda cmd, **kw: launched.append(cmd))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", launched
    httpd.shutdown()


def post(url, headers):
    req = urllib.request.Request(url, method="POST", headers=headers, data=b"")
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code


def test_connect_needs_the_page_token(server):
    base, launched = server
    assert post(f"{base}/api/connect/metricool", {}) == 403
    assert post(f"{base}/api/connect/metricool", {"X-FM-Token": "tok", "Origin": "https://evil.example"}) == 403
    assert post(f"{base}/api/connect/metricool", {"X-FM-Token": "tok"}) == 202
    assert launched == [["hermes", "-p", "fm-publisher", "mcp", "login", "metricool"]]
    assert post(f"{base}/api/connect/anything", {"X-FM-Token": "tok"}) == 404


def test_only_dashboard_datasets_are_served(server):
    base, _ = server
    assert urllib.request.urlopen(f"{base}/data/credits.json").status == 200
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(f"{base}/data/..%2F..%2F.env.json")
    assert json.load(urllib.request.urlopen(f"{base}/api/status")) == {"higgsfield": True, "metricool": False}
