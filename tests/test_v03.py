"""v0.3 unit tests plus scenario tests A (architectural challenge), B (Brain consistency), C (session recovery)."""
import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from argparse import Namespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import what_skill as w  # noqa: E402
import scenario_fixtures as fx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def out(fn, **kw):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        fn(Namespace(**kw))
    return buf.getvalue()


def cli(*argv):
    """Run the real CLI entry point; returns (exit_code, stdout)."""
    code = 0
    with contextlib.redirect_stdout(io.StringIO()) as buf, contextlib.redirect_stderr(io.StringIO()):
        try:
            w.main(list(argv))
        except SystemExit as stop:
            code = stop.code or 0
    return code, buf.getvalue()


def cfg(repo):
    return w.load_config(Path(repo))


def decide(repo, topic, status, proposal="x", source="owner", quote=""):
    return out(w.cmd_decide, repo=str(repo), topic=topic, proposal=proposal, source=source, status=status,
               quote=quote, rationale="", cost_estimate="")


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class DecisionTests(Tmp):
    def test_implementation_gate_blocks_until_cost_topics_approved(self):
        fx.init(self.repo)
        decide(self.repo, "stack", "approved", "Python script", quote="python is fine")
        code, text = cli("gate", "--repo", str(self.repo), "--implementation")
        self.assertEqual(3, code)  # no scan yet
        self.assertIn("challenge", text)
        cli("challenge", "--repo", str(self.repo), "--text", "A Python script.")
        self.assertEqual(0, cli("gate", "--repo", str(self.repo), "--implementation")[0])
        decide(self.repo, "model-tier", "proposed", "Opus everywhere", source="skill:claude-api")
        self.assertEqual(3, cli("gate", "--repo", str(self.repo), "--implementation")[0])
        # AI is now in play: provider, retry/fallback and paid services are required too.
        decide(self.repo, "model-tier", "approved", "Haiku for all steps", quote="use only Haiku")
        code, text = cli("gate", "--repo", str(self.repo), "--implementation")
        self.assertEqual(3, code)
        for topic in ("ai-provider", "retry-fallback", "paid-services"):
            self.assertIn(topic, text)
        for topic in ("ai-provider", "retry-fallback", "paid-services"):
            decide(self.repo, topic, "approved", "ok choice", quote=f"I approve the {topic} plan you showed")
        self.assertEqual(0, cli("gate", "--repo", str(self.repo), "--implementation")[0])

    def test_skill_default_is_never_recorded_as_owner_decision(self):
        fx.init(self.repo)
        with self.assertRaises(ValueError):
            decide(self.repo, "model-tier", "approved", "Opus", source="skill:claude-api")
        with self.assertRaises(ValueError):
            decide(self.repo, "model-tier", "proposed", "Opus", source="the skill")  # unknown source form
        decide(self.repo, "model-tier", "proposed", "Opus", source="skill:claude-api")
        self.assertEqual("skill:claude-api", cfg(self.repo)["decisions"]["model-tier"]["source"])

    def test_weak_consent_records_assumed_not_approved(self):
        fx.init(self.repo)
        text = decide(self.repo, "retry-fallback", "approved", "Fallback to another provider", quote="Let's proceed")
        self.assertEqual("assumed", cfg(self.repo)["decisions"]["retry-fallback"]["status"])
        self.assertIn("never shown", text)

    def test_weak_consent_approves_what_was_shown(self):
        fx.init(self.repo)
        decide(self.repo, "model-tier", "proposed", "Haiku for all steps", source="agent")
        decide(self.repo, "model-tier", "approved", "Haiku for all steps", quote="go ahead")
        self.assertEqual("approved", cfg(self.repo)["decisions"]["model-tier"]["status"])
        # ...but not a different choice than the one shown
        decide(self.repo, "ai-provider", "proposed", "OpenRouter", source="agent")
        decide(self.repo, "ai-provider", "approved", "OpenAI direct", quote="ok")
        self.assertEqual("assumed", cfg(self.repo)["decisions"]["ai-provider"]["status"])

    def test_superseded_decision_keeps_history_and_brain_line(self):
        fx.init(self.repo)
        decide(self.repo, "model-tier", "approved", "Haiku + Sonnet", quote="Haiku plus Sonnet for judging")
        decide(self.repo, "model-tier", "approved", "Haiku only", quote="use only Haiku 5.5")
        d = cfg(self.repo)["decisions"]["model-tier"]
        self.assertEqual("Haiku only", d["proposal"])
        self.assertEqual("Haiku + Sonnet", d["history"][-1]["proposal"])
        self.assertIn("supersedes: Haiku + Sonnet", (self.repo / ".project-brain/decisions.md").read_text())


class ChallengeTests(Tmp):
    def test_challenge_skips_settled_topics(self):
        fx.init(self.repo)
        decide(self.repo, "stack", "approved", "Next.js", quote="Next.js please")
        code, text = cli("challenge", "--repo", str(self.repo), "--text", "We will build it with Next.js.")
        self.assertEqual(0, code)
        self.assertEqual([], json.loads(text)["ask_owner"])

    def test_minor_choices_are_not_flagged(self):
        fx.init(self.repo)
        code, text = cli("challenge", "--repo", str(self.repo), "--text",
                         "Rename the helper to formatDate and move the button 8px to the left.")
        self.assertEqual(0, code)
        self.assertEqual([], json.loads(text)["ask_owner"])


class SpendAndLiveTests(Tmp):
    def test_live_gate_needs_logging_and_approval(self):
        fx.init(self.repo)
        r = str(self.repo)
        self.assertEqual(3, cli("gate", "--repo", r, "--live", "--approval", "S1")[0])
        self.assertEqual(3, cli("checkpoint", "--repo", r, "--kind", "pre-live", "--summary", "first run")[0])
        self.assertEqual(0, cli("checkpoint", "--repo", r, "--kind", "pre-live", "--summary", "first run",
                                "--evidence", "docs/runs/*.ndjson: inputs, outputs, cost.usd, errors")[0])
        self.assertEqual(3, cli("gate", "--repo", r, "--live", "--approval", "S1")[0])  # no approval yet
        with self.assertRaises(ValueError):
            out(w.cmd_approve_spend, repo=r, scope="5 showcase searches", cap=0.25, quote="")
        out(w.cmd_approve_spend, repo=r, scope="5 showcase searches", cap=0.25, quote="yes, up to 25 cents")
        self.assertEqual(0, cli("gate", "--repo", r, "--live", "--approval", "S1", "--expected-cost", "0.1")[0])
        self.assertEqual(3, cli("gate", "--repo", r, "--live", "--approval", "S1", "--expected-cost", "0.5")[0])

    def test_status_shows_cap_and_measured_total(self):
        fx.init(self.repo)
        r = str(self.repo)
        out(w.cmd_approve_spend, repo=r, scope="showcases", cap=0.25, quote="ok up to $0.25")
        out(w.cmd_spend, repo=r, amount=0.106, approval="S1", ref="docs/runs/a.ndjson", estimated=False, note="")
        out(w.cmd_spend, repo=r, amount=0.01, approval="S1", ref="", estimated=True, note="")
        s = json.loads(cli("status", "--repo", r)[1])["summary"]["spend"]
        self.assertAlmostEqual(0.106, s["measured_total_usd"])
        self.assertAlmostEqual(0.01, s["estimated_total_usd"])
        self.assertAlmostEqual(0.134, s["approvals"][0]["remaining_usd"])
        self.assertEqual([], s["issues"])

    def test_spend_without_approval_is_flagged_by_doctor(self):
        fx.init(self.repo)
        r = str(self.repo)
        self.assertEqual(0, cli("doctor", "--repo", r)[0])
        text = out(w.cmd_spend, repo=r, amount=0.0006, approval=None, ref="kit call", estimated=False, note="")
        self.assertIn("without a matching approval", text)
        code, report = cli("doctor", "--repo", r)
        self.assertEqual(1, code)
        self.assertIn("without a matching approval", report)

    def test_over_cap_is_flagged(self):
        fx.init(self.repo)
        r = str(self.repo)
        out(w.cmd_approve_spend, repo=r, scope="one run", cap=0.02, quote="2 cents ok")
        text = out(w.cmd_spend, repo=r, amount=0.05, approval="S1", ref="log", estimated=False, note="")
        self.assertIn("over the approved cap", text)


class ReconcileTests(Tmp):
    def test_reconcile_flags_completed_task_still_listed_as_blocked(self):
        fx.init(self.repo)
        (self.repo / ".project-brain/next-tasks.md").write_text("# Next\n\n- [ ] BLOCKED: export boards to PDF\n- [ ] Write the privacy note\n")
        (self.repo / ".project-brain/progress.md").write_text("# Progress\n\n- Export boards to PDF done.\n")
        kinds = [(f["kind"], f["detail"]) for f in w.reconcile(self.repo, cfg(self.repo))]
        stale = [d for k, d in kinds if k == "stale-task"]
        self.assertEqual(1, len(stale))
        self.assertIn("export boards to PDF", stale[0])

    def test_reconcile_flags_lifecycle_unchanged_after_milestone_checkpoints(self):
        fx.init(self.repo)
        fx.checkpoint(self.repo, "milestone", "M1 done")
        kinds = [f["kind"] for f in w.reconcile(self.repo, cfg(self.repo))]
        self.assertIn("lifecycle-stale", kinds)
        out(w.cmd_lifecycle, repo=str(self.repo), status="development", user_confirmed=True, evidence="")
        self.assertNotIn("lifecycle-stale", [f["kind"] for f in w.reconcile(self.repo, cfg(self.repo))])

    def test_lifecycle_change_updates_overview_and_dna(self):
        fx.init(self.repo)
        out(w.cmd_lifecycle, repo=str(self.repo), status="development", user_confirmed=True, evidence="")
        self.assertIn("Lifecycle: development", (self.repo / ".project-brain/overview.md").read_text())
        self.assertIn("**Lifecycle:** development", (self.repo / ".project-brain/project-dna.md").read_text())
        self.assertNotIn("lifecycle-conflict", [f["kind"] for f in w.reconcile(self.repo, cfg(self.repo))])

    def test_skill_gaps_are_flagged(self):
        fx.init(self.repo)
        r = str(self.repo)
        out(w.cmd_skill_use, repo=r, skill="emil-design-eng", status="recommended", stage="design", role="",
            outcome="", reason="", evidence_level="reported", evidence="")
        out(w.cmd_skill_use, repo=r, skill="animate", status="invoked", stage="build", role="", outcome="",
            reason="", evidence_level="reported", evidence="")
        fx.checkpoint(self.repo, "task-complete", "motion done", skills="animate,impeccable")
        kinds = {f["kind"] for f in w.reconcile(self.repo, cfg(self.repo))}
        self.assertTrue({"skill-not-acted", "skill-no-outcome", "skill-unrecorded"} <= kinds)
        with self.assertRaises(ValueError):
            out(w.cmd_skill_use, repo=r, skill="animate", status="completed", stage="build", role="", outcome="",
                reason="", evidence_level="reported", evidence="")
        out(w.cmd_skill_use, repo=r, skill="animate", status="completed", stage="build", role="", outcome="curves + reduced motion",
            reason="", evidence_level="verified", evidence="app/globals.css")
        self.assertNotIn("skill-no-outcome", {f["kind"] for f in w.reconcile(self.repo, cfg(self.repo))})

    def test_major_change_with_plan_requires_supersede_note(self):
        fx.init(self.repo)
        plan = self.repo / "docs/plan.md"
        plan.parent.mkdir()
        plan.write_text("# Plan\n\nPhase 2: demo page\n")
        args = ["checkpoint", "--repo", str(self.repo), "--kind", "major-change", "--summary", "Phase 2 is now the Trend Board"]
        self.assertEqual(3, cli(*args, "--plan", "docs/plan.md")[0])
        today = time.strftime("%Y-%m-%d", time.gmtime())
        plan.write_text(plan.read_text() + f"\n## Superseded\n{today}: Phase 2 is the Trend Board (decision in decisions.md).\n")
        self.assertEqual(0, cli(*args, "--plan", "docs/plan.md")[0])
        self.assertEqual(["docs/plan.md"], cfg(self.repo)["plans"])
        # A later major change without touching the plan is drift.
        old = time.time() - 3600
        os.utime(plan, (old, old))
        fx.checkpoint(self.repo, "major-change", "Dropped the demo page")
        self.assertIn("plan-drift", [f["kind"] for f in w.reconcile(self.repo, cfg(self.repo))])


class SurfaceTests(Tmp):
    def test_second_surface_approval_does_not_overwrite_first(self):
        fx.init(self.repo)
        for step in ("ui-yes", "system-check", "expectations", "skills"):
            fx.design(self.repo, step)
        fx.design(self.repo, "direction-proposed", "Build Booklet")
        fx.design(self.repo, "direction-approved", "Build Booklet", True, "Owner: Booklet")
        fx.design(self.repo, "direction-proposed", "Trend Board", surface="trend-board")
        self.assertEqual(3, cli("design", "--repo", str(self.repo), "--gate", "--surface", "trend-board")[0])
        fx.design(self.repo, "direction-approved", "Trend Board", True, "Owner: board", surface="trend-board")
        found = {k: (v or {}).get("name") for k, v in w.approved_directions(cfg(self.repo)).items()}
        self.assertEqual({"main": "Build Booklet", "trend-board": "Trend Board"}, found)
        self.assertEqual(0, cli("design", "--repo", str(self.repo), "--gate")[0])
        self.assertEqual(0, cli("design", "--repo", str(self.repo), "--gate", "--surface", "trend-board")[0])
        self.assertEqual([], [f for f in w.reconcile(self.repo, cfg(self.repo)) if f["kind"].startswith("design")])

    def test_v02_config_reads_single_direction_as_main_surface(self):
        fx.init(self.repo)
        p = self.repo / ".what-skill/config.json"
        c = json.loads(p.read_text())
        c["design"].pop("surfaces")
        c["design"]["approved_direction"] = {"name": "A", "owner_confirmation": "yes A", "at": "2026-10-01T00:00:00+00:00"}
        p.write_text(json.dumps(c))
        self.assertEqual({"main": "A"}, {k: v["name"] for k, v in w.approved_directions(cfg(self.repo)).items()})


class GitAndUpgradeTests(Tmp):
    def test_init_reports_missing_git_without_creating_it(self):
        report = json.loads(out(w.cmd_init, repo=str(self.repo), agent="claude", mode="beginner",
                                communication="plain", challenge="adaptive"))
        if not w.git_present(self.repo):  # temp dirs are normally outside any repo
            self.assertEqual("missing", report["git"])
            self.assertTrue(report["advice"])
        self.assertFalse((self.repo / ".git").exists())

    def test_doctor_warns_when_no_git_and_checkpoints_exist(self):
        fx.init(self.repo)
        fx.checkpoint(self.repo, "milestone", "m1")
        report = json.loads(cli("doctor", "--repo", str(self.repo))[1])
        if not w.git_present(self.repo):
            self.assertTrue(any("git init" in x for x in report["warnings"]))

    def test_upgrade_replaces_only_the_marked_block(self):
        (self.repo / "CLAUDE.md").write_text("# Mine\nkeep me\n")
        fx.init(self.repo)
        p = self.repo / "CLAUDE.md"
        text = p.read_text()
        start, end = text.index(w.MARKER_START), text.index(w.MARKER_END) + len(w.MARKER_END)
        p.write_text(text[:start] + w.MARKER_START + "\nold v0.2 block\n" + w.MARKER_END + text[end:] + "\nafter\n")
        self.assertTrue(any("v0.2 instruction block" in x for x in json.loads(cli("doctor", "--repo", str(self.repo))[1])["warnings"]))
        with self.assertRaises(ValueError):
            out(w.cmd_upgrade, repo=str(self.repo), user_confirmed=False)
        out(w.cmd_upgrade, repo=str(self.repo), user_confirmed=True)
        new = p.read_text()
        self.assertIn("keep me", new)
        self.assertIn("after", new)
        self.assertNotIn("old v0.2 block", new)
        self.assertEqual(1, new.count(w.MARKER_START))
        self.assertIn("what_skill.py resume", new)

    def test_parent_project_is_never_assumed(self):
        fx.init(self.repo)
        child = self.repo / "packages/app"
        child.mkdir(parents=True)
        with self.assertRaises(ValueError) as err:
            w.load_config(child)
        self.assertIn("never assumes a parent", str(err.exception))


class ScenarioA_ArchitecturalChallenge(Tmp):
    """A supporting skill proposes an expensive model and a refusal-retrying fallback."""

    def test_skill_defaults_are_identified_challenged_and_block_implementation(self):
        repo = fx.scenario_a(self.repo / "a")
        skill = repo / ".claude/skills/ai-pipeline-builder/SKILL.md"
        self.assertEqual(3, cli("gate", "--repo", str(repo), "--implementation")[0])  # never scanned: not open yet
        code, text = cli("challenge", "--repo", str(repo), "--file", str(skill), "--source", "skill:ai-pipeline-builder", "--record")
        self.assertEqual(3, code)
        report = json.loads(text)
        asks = {f["topic"]: f for f in report["ask_owner"]}
        self.assertEqual("security", report["ask_owner"][0]["topic"])  # critical first
        self.assertEqual("critical", asks["security"]["severity"])
        self.assertIn("refus", " ".join(asks["security"]["evidence"]).lower())
        for topic in ("model-tier", "retry-fallback", "ai-provider"):
            self.assertIn(topic, asks)
        self.assertTrue(any("cheaper tier" in q for q in asks["model-tier"]["questions"]))
        self.assertNotIn("stack", asks)  # already approved: not re-asked
        decisions = cfg(repo)["decisions"]
        self.assertEqual("proposed", decisions["model-tier"]["status"])
        self.assertEqual("skill:ai-pipeline-builder", decisions["model-tier"]["source"])
        code, gate_text = cli("gate", "--repo", str(repo), "--implementation")
        self.assertEqual(3, code)
        self.assertIn("model-tier", gate_text)
        # Owner's "Let's proceed" does not approve the skill default they were shown only as a different text.
        decide(repo, "model-tier", "approved", "Opus for every step", quote="Let's proceed")
        self.assertEqual("assumed", cfg(repo)["decisions"]["model-tier"]["status"])
        self.assertEqual(3, cli("gate", "--repo", str(repo), "--implementation")[0])
        # Explicit owner answers open the gate.
        decide(repo, "model-tier", "approved", "Haiku for summaries; measure on 20 headlines first", quote="Haiku, measure first")
        decide(repo, "retry-fallback", "approved", "One retry on timeout/5xx; surface refusals; no cross-provider fallback", quote="no fallback")
        decide(repo, "security", "approved", "Refusals are shown and logged, never re-routed", quote="agreed")
        decide(repo, "ai-provider", "approved", "Anthropic direct", quote="Anthropic direct")
        decide(repo, "paid-services", "approved", "~$1/month cap", quote="max a dollar a month")
        self.assertEqual(0, cli("gate", "--repo", str(repo), "--implementation")[0])
        self.assertIn("source: skill:ai-pipeline-builder", (repo / ".project-brain/decisions.md").read_text())


class ScenarioB_BrainConsistency(Tmp):
    """Outdated tasks, conflicting lifecycle and two design approvals in a v0.2-shaped project."""

    def test_inconsistencies_are_detected_without_losing_valid_decisions(self):
        repo = fx.scenario_b(self.repo / "b")
        before_cfg = (repo / ".what-skill/config.json").read_text()
        before_decisions = (repo / ".project-brain/decisions.md").read_text()
        code, text = cli("reconcile", "--repo", str(repo), "--strict")
        self.assertEqual(3, code)
        findings = json.loads(text)["findings"]
        by_kind = {}
        for f in findings:
            by_kind.setdefault(f["kind"], []).append(f["detail"])
        stale = " ".join(by_kind.get("stale-task", []))
        self.assertIn("export boards to PDF", stale)
        self.assertIn("password gate", stale)
        self.assertNotIn("judge agreement", stale)  # genuinely open work is not flagged
        self.assertIn("lifecycle-conflict", by_kind)  # overview says development, config says discovery
        self.assertIn("lifecycle-stale", by_kind)
        self.assertIn("Build Booklet", " ".join(by_kind["design-approval-overwritten"]))
        self.assertIn("skill-not-acted", by_kind)  # emil-design-eng recommended, never used
        self.assertIn("skill-unrecorded", by_kind)  # writing-plans / impeccable used, not in history
        # Nothing was changed by reconciling.
        self.assertEqual(before_cfg, (repo / ".what-skill/config.json").read_text())
        self.assertEqual(before_decisions, (repo / ".project-brain/decisions.md").read_text())
        # Both approvals survive: the live one in config, the earlier one in events and in the finding.
        self.assertEqual("Trend Board", cfg(repo)["design"]["approved_direction"]["name"])
        approvals = [json.loads(l) for l in (repo / ".what-skill/events.jsonl").read_text().splitlines()
                     if '"direction-approved"' in l]
        self.assertEqual(["Build Booklet", "Trend Board"], [a["value"] for a in approvals])
        # Resolving the finding the proposed way restores both as separate surfaces.
        fx.design(repo, "direction-proposed", "Build Booklet", surface="app")
        fx.design(repo, "direction-approved", "Build Booklet", True, "Owner: Build Booklet, definitely (re-recorded)", surface="app")
        kinds = {f["kind"] for f in w.reconcile(repo, cfg(repo))}
        self.assertNotIn("design-approval-overwritten", kinds)
        found = {k: (v or {}).get("name") for k, v in w.approved_directions(cfg(repo)).items()}
        self.assertEqual({"main": "Trend Board", "app": "Build Booklet"}, found)

    def test_superseded_resolution_path(self):
        repo = fx.scenario_b(self.repo / "b2")
        fx.design(repo, "direction-superseded", "Build Booklet", summary="Owner: the board replaced the booklet")
        self.assertNotIn("design-approval-overwritten", {f["kind"] for f in w.reconcile(repo, cfg(repo))})
        self.assertEqual(0, cli("design", "--repo", str(repo), "--gate")[0])  # live approval untouched

    def test_v03_reads_v02_project_without_writing(self):
        repo = fx.scenario_b(self.repo / "b3")
        before = (repo / ".what-skill/config.json").read_text()
        for cmd in (("status",), ("resume",), ("design",), ("gate",), ("doctor",)):
            cli(*cmd, "--repo", str(repo))
        self.assertEqual(before, (repo / ".what-skill/config.json").read_text())


class ScenarioC_SessionRecovery(Tmp):
    """A fresh session reads the project from disk only."""

    def test_resume_brief_recovers_project_without_restarting_discovery(self):
        repo = fx.scenario_c(self.repo / "invoice-nudge")
        code, text = cli("resume", "--repo", str(repo), "--agent", "codex")
        self.assertEqual(0, code)
        b = json.loads(text)
        self.assertEqual("invoice-nudge", b["project"])
        self.assertEqual("claude", b["lead_agent"])
        self.assertTrue(b["your_role"].startswith("supporting"))
        self.assertEqual("development", b["lifecycle"])
        self.assertIn("Freelancers", b["overview"]["Problem"])
        self.assertTrue(b["discovery"].startswith("done"))
        self.assertEqual("Haiku for drafting reminder emails", b["approved_decisions"]["model-tier"])
        self.assertIn("never retry refusals", b["approved_decisions"]["retry-fallback"])
        self.assertIn("paid-services", b["awaiting_owner"])
        self.assertEqual("blocked", b["implementation_gate"])
        self.assertEqual("Ledger · calm table", b["design"]["approved_directions"]["main"])
        self.assertEqual(["Weekly reminder email (needs Postmark decision)", "Accessibility pass on the invoice table"], b["open_tasks"])
        self.assertEqual("completed", b["skills"]["superpowers:writing-plans"]["status"])
        self.assertIn("skill-no-outcome", [f["kind"] for f in b["stale_or_conflicting"]])
        lead = json.loads(cli("resume", "--repo", str(repo), "--agent", "claude")[1])
        self.assertTrue(lead["your_role"].startswith("lead"))

    def test_fresh_project_says_discovery_not_started(self):
        fx.init(self.repo)
        b = json.loads(cli("resume", "--repo", str(self.repo))[1])
        self.assertTrue(b["discovery"].startswith("not started"))


class InstructionWiringTests(unittest.TestCase):
    def test_skill_md_wires_v03_duties(self):
        skill = (ROOT / "SKILL.md").read_text()
        for needle in ("Defaults are proposals", "challenge", "decide", "gate --implementation", "pre-live",
                       "approve-spend", "reconcile", "resume", "skill-use", "--surface"):
            self.assertIn(needle, skill, needle)
        policy = (ROOT / "references/decision-challenges.md").read_text()
        for needle in ("Supporting skills", "Weak consent", "security", "Minor"):
            self.assertIn(needle, policy, needle)

    def test_lead_block_mentions_v03_checkpoints(self):
        block = w.lead_instructions("claude")
        for needle in ("resume", "challenge", "gate --implementation", "pre-live", "skill-use", "reconcile", "design --repo . --gate"):
            self.assertIn(needle, block)


if __name__ == "__main__":
    unittest.main()
