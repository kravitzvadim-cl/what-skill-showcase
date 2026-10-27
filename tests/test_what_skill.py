import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import what_skill as w


class WhatSkillTests(unittest.TestCase):
    def test_init_lead_agent_project_brain_and_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / "CLAUDE.md").write_text("# Preexisting rules\n", encoding="utf-8")
            (repo / ".project-brain").mkdir()
            (repo / ".project-brain/decisions.md").write_text("existing decision", encoding="utf-8")
            args = Namespace(repo=str(repo), agent="claude", mode="beginner", communication="plain", challenge="adaptive")
            with contextlib.redirect_stdout(io.StringIO()):
                w.cmd_init(args)
            self.assertIn("Preexisting rules", (repo / "CLAUDE.md").read_text())
            self.assertIn(w.MARKER_START, (repo / "CLAUDE.md").read_text())
            self.assertEqual("existing decision", (repo / ".project-brain/decisions.md").read_text())
            self.assertEqual("claude", w.load_config(repo)["lead_agent"])
            self.assertFalse((repo / "AGENTS.md").exists())
            with contextlib.redirect_stdout(io.StringIO()):
                w.cmd_doctor(Namespace(repo=str(repo)))
            with self.assertRaises(ValueError):
                w.cmd_init(args)

    def test_all_lead_agents(self):
        for agent, fname in w.LEAD_FILES.items():
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as folder:
                with contextlib.redirect_stdout(io.StringIO()):
                    w.cmd_init(Namespace(repo=folder, agent=agent, mode="expert", communication="technical", challenge="demanding"))
                self.assertIn(w.MARKER_START, (Path(folder) / fname).read_text())
                self.assertEqual("expert", w.load_config(Path(folder))["interview_mode"])

    def test_checkpoint_and_feedback_are_project_local(self):
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.redirect_stdout(io.StringIO()):
                w.cmd_init(Namespace(repo=folder, agent="codex", mode="beginner", communication="plain", challenge="adaptive"))
                w.cmd_checkpoint(Namespace(repo=folder, kind="milestone", summary="First screen complete", evidence="User reviewed"))
                w.cmd_feedback(Namespace(repo=folder, skill="sample-design", context="mobile UI", rating=2,
                                         outcome="too generic", evidence_level="reported", cause="skill-fit", feedback="needed more personality"))
            events = (Path(folder) / ".what-skill/events.jsonl").read_text().splitlines()
            feedback = [json.loads(s) for s in (Path(folder) / ".what-skill/skill-history.jsonl").read_text().splitlines()]
            self.assertEqual(2, len(events))
            self.assertFalse(feedback[0]["global_shared"])
            self.assertEqual(2, feedback[0]["rating"])

    def test_local_skill_discovery_does_not_execute_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            skill = root / "ui-layout"
            skill.mkdir()
            (skill / "SKILL.md").write_text("---\nname: ui-layout\ndescription: Responsive visual interface layout and typography.\n---\n", encoding="utf-8")
            (skill / "run-dangerous.sh").write_text("exit 99\n", encoding="utf-8")
            candidates = w.local_skills([root], "visual layout")
            self.assertEqual("ui-layout", candidates[0]["name"])
            self.assertEqual(1.0, candidates[0]["keyword_coverage"])
            self.assertEqual("bundled-code-not-reviewed", candidates[0]["safety_status"])

    def test_lifecycle_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.redirect_stdout(io.StringIO()):
                w.cmd_init(Namespace(repo=folder, agent="gemini", mode="beginner", communication="plain", challenge="adaptive"))
            args = Namespace(repo=folder, status="released", user_confirmed=False, evidence="validated deployment")
            with self.assertRaises(ValueError):
                w.cmd_lifecycle(args)
            self.assertEqual("discovery", w.load_config(Path(folder))["lifecycle"])
            args.user_confirmed = True
            with contextlib.redirect_stdout(io.StringIO()):
                w.cmd_lifecycle(args)
            self.assertEqual("released", w.load_config(Path(folder))["lifecycle"])

    def test_spec_metadata_and_skill_dir_name(self):
        root = Path(__file__).resolve().parents[1]
        meta = w.parse_skill_frontmatter(root / "SKILL.md")
        self.assertIsNotNone(meta)
        self.assertEqual(root.name, meta["name"])
        self.assertTrue(0 < len(meta["description"]) <= 1024)


if __name__ == "__main__":
    unittest.main()
