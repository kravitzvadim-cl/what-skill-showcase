import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import what_skill as w

ROOT = Path(__file__).resolve().parents[1]


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        fn(*args)
    return out.getvalue()


def init(folder, agent="claude"):
    quiet(w.cmd_init, Namespace(repo=folder, agent=agent, mode="beginner", communication="plain", challenge="adaptive"))


def record(folder, step, value=None, confirmed=False, summary="test"):
    if value is None and step.startswith("direction-") and step != "direction-rejected":
        value = "A"  # most tests use a single direction named "A"
    return quiet(w.cmd_design_record, Namespace(repo=folder, step=step, value=value, summary=summary, user_confirmed=confirmed))


def gate(folder):
    """Return the parsed status; raises SystemExit(3) when blocked."""
    out = quiet(w.cmd_design, Namespace(repo=folder, gate=True))
    return json.loads(out)


def status(folder):
    return json.loads(quiet(w.cmd_design, Namespace(repo=folder, gate=False)))


class DesignGateTests(unittest.TestCase):
    def test_new_project_blocks_visual_implementation_until_discovery(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            with self.assertRaises(SystemExit) as stop:
                gate(folder)
            self.assertEqual(3, stop.exception.code)
            missing = " ".join(status(folder)["missing"])
            for needed in ("visual interface", "existing design system", "expectations", "approval"):
                self.assertIn(needed, missing)

    def test_discovery_alone_is_not_enough_owner_must_approve(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            for step in ("ui-yes", "system-check", "expectations", "skills", "direction-proposed"):
                record(folder, step)
            self.assertEqual("blocked", status(folder)["visual_implementation"])
            with self.assertRaises(ValueError):  # agent cannot self-approve
                record(folder, "direction-approved")
            self.assertEqual("blocked", status(folder)["visual_implementation"])
            record(folder, "direction-approved", confirmed=True)
            self.assertEqual("allowed", gate(folder)["visual_implementation"])

    def test_approval_requires_a_proposed_direction(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            with self.assertRaises(ValueError):
                record(folder, "direction-approved", confirmed=True)

    def test_approval_without_expectations_still_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            for step in ("ui-yes", "system-check", "direction-proposed"):
                record(folder, step)
            record(folder, "direction-approved", confirmed=True)
            result = status(folder)
            self.assertEqual("blocked", result["visual_implementation"])
            self.assertTrue(any("expectations" in m for m in result["missing"]))

    def test_rejection_closes_gate_and_requires_investigation(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            for step in ("ui-yes", "system-check", "expectations", "skills", "direction-proposed"):
                record(folder, step)
            record(folder, "direction-approved", confirmed=True)
            out = record(folder, "direction-rejected", summary="Owner: looks generic")
            self.assertIn("Investigate", out)
            self.assertEqual("blocked", status(folder)["visual_implementation"])
            record(folder, "direction-proposed")
            with self.assertRaises(ValueError):  # no redesign approval before investigating
                record(folder, "direction-approved", confirmed=True)
            record(folder, "investigation", summary="No taste input; literal metaphor")
            record(folder, "direction-approved", confirmed=True)
            self.assertEqual("allowed", status(folder)["visual_implementation"])
            events = [json.loads(l) for l in (Path(folder) / ".what-skill/events.jsonl").read_text().splitlines()]
            self.assertTrue(any(e.get("step") == "direction-rejected" and e["needs_investigation"] for e in events))

    def test_non_visual_project_is_never_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "ui-no")
            self.assertEqual("allowed", gate(folder)["visual_implementation"])

    def test_quality_is_tracked_separately_from_compliance(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "compliance", value="pass")
            result = status(folder)
            self.assertEqual("pass", result["design"]["compliance"])
            self.assertEqual("not-run", result["design"]["quality_review"])
            self.assertTrue(any("quality review" in a for a in result["advice"]))
            record(folder, "quality-review", value="fail")
            self.assertEqual("fail", status(folder)["design"]["quality_review"])
            with self.assertRaises(ValueError):
                record(folder, "quality-review", value="great")

    def test_system_choice_values(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "system-choice", value="lightweight")
            self.assertEqual("lightweight", status(folder)["design"]["system_choice"])
            with self.assertRaises(ValueError):
                record(folder, "system-choice", value="material-ish")


class ExplorationTests(unittest.TestCase):
    def test_research_and_mockups_are_allowed_while_production_styling_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "ui-yes")
            record(folder, "references", summary="Things 3, Linear")
            out = record(folder, "exploration", summary="Three static mockups in docs/design-directions/")
            self.assertIn("always allowed", out)
            result = status(folder)
            self.assertEqual("blocked", result["visual_implementation"])  # exploring never opens the gate
            self.assertIn("always allowed", result["exploration"])
            self.assertEqual(1, result["design"]["explorations"])
            for name in ("A", "B", "C"):
                record(folder, "direction-proposed", value=name)  # proposing before approval is fine
            self.assertEqual(["A", "B", "C"], status(folder)["design"]["directions"])
            with self.assertRaises(SystemExit):
                gate(folder)


class AdaptiveDepthTests(unittest.TestCase):
    BASE = ("ui-yes", "system-check", "expectations")

    def test_light_depth_needs_only_the_essentials(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "depth", value="light")
            for step in self.BASE + ("direction-proposed",):
                record(folder, step)
            record(folder, "direction-approved", confirmed=True)
            self.assertEqual("allowed", gate(folder)["visual_implementation"])  # no skills/references needed

    def test_standard_depth_also_needs_skill_review(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "depth", value="standard")
            for step in self.BASE + ("direction-proposed",):
                record(folder, step)
            record(folder, "direction-approved", confirmed=True)
            self.assertTrue(any("design skills" in m for m in status(folder)["missing"]))
            record(folder, "skills")
            self.assertEqual("allowed", gate(folder)["visual_implementation"])

    def test_deep_depth_needs_references_system_level_and_two_directions(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            record(folder, "depth", value="deep")
            for step in self.BASE + ("skills", "direction-proposed"):
                record(folder, step)
            record(folder, "direction-approved", confirmed=True)
            missing = " ".join(status(folder)["missing"])
            for needed in ("references", "design-system level", "two meaningfully different directions"):
                self.assertIn(needed, missing)
            record(folder, "references")
            record(folder, "system-choice", value="lightweight")
            record(folder, "direction-proposed", value="B")
            record(folder, "direction-approved", value="B", confirmed=True)
            self.assertEqual("allowed", gate(folder)["visual_implementation"])

    def test_unset_depth_defaults_to_standard_and_advises(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            result = status(folder)
            self.assertTrue(any("depth" in a for a in result["advice"]))
            self.assertTrue(any("design skills" in m for m in result["missing"]))
            with self.assertRaises(ValueError):
                record(folder, "depth", value="medium")


class NamedApprovalTests(unittest.TestCase):
    def ready(self, folder):
        init(folder)
        record(folder, "depth", value="light")
        for step in ("ui-yes", "system-check", "expectations"):
            record(folder, step)
        record(folder, "direction-proposed", value="A · Quiet native")
        record(folder, "direction-proposed", value="B · Keyboard-first")

    def test_approval_stores_the_named_direction_and_owner_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            self.ready(folder)
            record(folder, "direction-approved", value="a · quiet native", confirmed=True, summary="Owner: go with A")
            approved = status(folder)["design"]["approved_direction"]
            self.assertEqual("A · Quiet native", approved["name"])
            self.assertEqual("Owner: go with A", approved["owner_confirmation"])
            self.assertTrue(approved["at"])
            events = [json.loads(l) for l in (Path(folder) / ".what-skill/events.jsonl").read_text().splitlines()]
            last = [e for e in events if e.get("step") == "direction-approved"][-1]
            self.assertTrue(last["user_confirmed"])
            self.assertEqual("a · quiet native", last["value"])

    def test_approval_must_name_a_proposed_direction(self):
        with tempfile.TemporaryDirectory() as folder:
            self.ready(folder)
            with self.assertRaises(ValueError):
                record(folder, "direction-approved", value="C · Daily page", confirmed=True)
            with self.assertRaises(ValueError):
                quiet(w.cmd_design_record, Namespace(repo=folder, step="direction-approved", value=None,
                                                     summary="yes", user_confirmed=True))
            with self.assertRaises(ValueError):
                quiet(w.cmd_design_record, Namespace(repo=folder, step="direction-proposed", value=None,
                                                     summary="unnamed", user_confirmed=False))

    def test_substantial_change_requires_renewed_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            self.ready(folder)
            record(folder, "direction-approved", value="A · Quiet native", confirmed=True)
            self.assertEqual("allowed", gate(folder)["visual_implementation"])
            record(folder, "direction-changed", value="A2 · Quiet native, dark sidebar", summary="New layout model")
            result = status(folder)
            self.assertEqual("blocked", result["visual_implementation"])
            self.assertIsNone(result["design"]["approved_direction"])
            with self.assertRaises(ValueError):
                record(folder, "direction-approved", value="A2 · Quiet native, dark sidebar")  # still needs the owner
            record(folder, "direction-approved", value="A2 · Quiet native, dark sidebar", confirmed=True)
            self.assertEqual("A2 · Quiet native, dark sidebar", gate(folder)["design"]["approved_direction"]["name"])

    def test_kickoff_tasks_include_design_discovery_automatically(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            self.assertIn("design discovery", (Path(folder) / ".project-brain/next-tasks.md").read_text())
            self.assertIn("starts **automatically** at kickoff", (ROOT / "references/design-intelligence.md").read_text())
            self.assertIn("automatically", (ROOT / "SKILL.md").read_text())


class DissatisfactionTests(unittest.TestCase):
    def test_low_rating_or_flag_marks_feedback_for_investigation(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder, agent="codex")
            out = quiet(w.cmd_feedback, Namespace(repo=folder, skill="frontend-design", context="app screen", rating=1,
                                                  outcome="looks generic", evidence_level="reported", cause="process",
                                                  feedback="", dissatisfied=False))
            self.assertIn("Investigate", out)
            quiet(w.cmd_feedback, Namespace(repo=folder, skill="x", context="y", rating=None, outcome="z",
                                            evidence_level="reported", cause="unknown", feedback="", dissatisfied=True))
            quiet(w.cmd_feedback, Namespace(repo=folder, skill="x", context="y", rating=5, outcome="z",
                                            evidence_level="reported", cause="unknown", feedback=""))  # v0.1-style args
            rows = [json.loads(l) for l in (Path(folder) / ".what-skill/skill-history.jsonl").read_text().splitlines()]
            self.assertEqual([True, True, False], [r["needs_investigation"] for r in rows])

    def test_cli_accepts_process_cause_and_dissatisfied_flag(self):
        args = w.parser().parse_args(["feedback", "--repo", ".", "--skill", "s", "--context", "c",
                                      "--outcome", "o", "--cause", "process", "--dissatisfied"])
        self.assertTrue(args.dissatisfied)
        self.assertEqual("process", args.cause)


class CompatibilityAndWiringTests(unittest.TestCase):
    def test_v01_project_without_design_block_still_works(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            cfg_path = Path(folder) / ".what-skill/config.json"
            cfg = json.loads(cfg_path.read_text())
            cfg.pop("design")  # what a v0.1 project looks like
            cfg_path.write_text(json.dumps(cfg))
            (Path(folder) / ".project-brain/design.md").unlink()
            quiet(w.cmd_doctor, Namespace(repo=folder))  # stays healthy
            quiet(w.cmd_checkpoint, Namespace(repo=folder, kind="milestone", summary="s", evidence=""))
            self.assertEqual("unknown", status(folder)["design"]["has_ui"])
            record(folder, "ui-no")
            self.assertEqual("no", json.loads(cfg_path.read_text())["design"]["has_ui"])

    def test_init_creates_design_brain_and_gate_instruction(self):
        with tempfile.TemporaryDirectory() as folder:
            init(folder)
            self.assertTrue((Path(folder) / ".project-brain/design.md").is_file())
            self.assertIn("design --repo . --gate", (Path(folder) / "CLAUDE.md").read_text())
            dna = (Path(folder) / ".project-brain/project-dna.md").read_text()
            self.assertIn("Visual polish", dna)
            self.assertIn("Visual expression", dna)

    def test_init_never_overwrites_existing_design_file(self):
        with tempfile.TemporaryDirectory() as folder:
            brain = Path(folder) / ".project-brain"
            brain.mkdir()
            (brain / "design.md").write_text("owner's own design notes", encoding="utf-8")
            init(folder)
            self.assertEqual("owner's own design notes", (brain / "design.md").read_text())

    def test_skill_instructions_wire_design_intelligence(self):
        skill = (ROOT / "SKILL.md").read_text()
        guide = (ROOT / "references/design-intelligence.md").read_text()
        self.assertIn("references/design-intelligence.md", skill)
        self.assertIn("design --gate", skill)
        for duty in ("Check what already exists", "Decide the system level", "expectations, references and ambition",
                     "purpose of the surface", "meaningfully different directions", "approval of one named direction",
                     "quality separately from compliance", "negative feedback as evidence"):
            self.assertIn(duty, guide)
        for ref in ("discovery.md", "decision-challenges.md", "skill-discovery.md", "evaluation.md", "persistent-mentor.md"):
            self.assertIn("design", (ROOT / "references" / ref).read_text().lower(), ref)


if __name__ == "__main__":
    unittest.main()
