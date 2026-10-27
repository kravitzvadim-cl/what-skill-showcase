#!/usr/bin/env python3
"""What Skill: conservative project setup, checkpoints, decision gates and skill inventory.

Python >=3.9, standard library only. This is a helper, not an always-on daemon.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "0.3.0"
ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ".what-skill"
BRAIN_DIR = ".project-brain"
MARKER_START = "<!-- what-skill:lead-instructions:start -->"
MARKER_END = "<!-- what-skill:lead-instructions:end -->"
LEAD_FILES = {"codex": "AGENTS.md", "claude": "CLAUDE.md", "gemini": "GEMINI.md"}
MODES = ("beginner", "intermediate", "expert")
LIFECYCLES = ("discovery", "development", "pre-release", "released")
DESIGN_STEPS = ("ui-yes", "ui-no", "depth", "system-check", "system-choice", "expectations", "skills",
                "references", "exploration", "direction-proposed", "direction-approved", "direction-changed",
                "direction-rejected", "direction-superseded", "investigation", "quality-review", "compliance")
DEPTHS = ("light", "standard", "deep")
SYSTEM_CHOICES = ("existing", "lightweight", "custom", "none")
REVIEW_VALUES = ("pass", "fail")
FEEDBACK_CAUSES = ("skill-fit", "prompt", "implementation", "requirements", "process", "unknown")
CHECKPOINT_KINDS = ("kickoff", "task-complete", "major-change", "stuck", "milestone", "pre-release", "feedback",
                    "pre-implementation", "pre-live", "resume")
INVESTIGATION_QUESTIONS = [
    "What exactly disappointed you (first impression, a specific element, the overall feel)?",
    "What did you expect instead (words, example apps or sites)?",
    "Which step went wrong (no taste input, wrong skill, no options, skipped approval, wrong quality bar)?",
    "Did the chosen skill actually run as designed?",
]

# v0.3 consequential decisions
MAIN_SURFACE = "main"
SURFACE_KEYS = ("directions", "direction", "approved_direction", "investigation_pending")
DECISION_STATUSES = ("proposed", "approved", "rejected", "assumed")
AI_TOPICS = ("model-tier", "ai-provider", "retry-fallback")
DEFAULT_REQUIRED_TOPICS = ("stack",)
SKILL_USE_STATUSES = ("recommended", "invoked", "completed", "rejected", "skipped")
# Consent that only approves something the owner was actually shown.
WEAK_CONSENT = re.compile(
    r"^\s*(ok(ay)?|yes( please)?|yep|sure|fine|go( ahead| for it)?|proceed|continue|do it|ship it|lgtm|"
    r"sounds good|looks good|let'?s (go|proceed|do it|continue|start|build( it)?))[\s.!]*$", re.I)
# (topic, severity, pattern, question). Deliberately broad: a false alarm costs one line, a miss cost Atlas Trend 10x.
CHALLENGE_RULES = (
    ("security", "critical",
     r"refus\w*[^.\n]{0,80}(fallback|fall back|retry|another model|different model|second model)|"
     r"(fallback|fall back|retry|another model|different model)[^.\n]{0,80}refus\w*",
     "Re-sending a safety refusal to another model works around the provider's safety decision. "
     "Default: surface the refusal to the user and log it; never re-route it automatically."),
    ("model-tier", "high",
     r"\b(opus|gpt-?5(\.\d)?-?pro|o\d-pro|ultra|gemini[- ]?[\d.]*[- ]?pro|largest model|most capable|"
     r"top[- ]tier|flagship|frontier model)\b",
     "Top-tier model as a default. Which steps need it? Name a cheaper tier, estimate cost per run for both, "
     "and plan a small measured comparison before committing."),
    ("model-tier", "high", r"\b(always use|never downgrade|non-negotiable|must always)\b",
     "A skill or template says 'always/never'. That is the skill's default, not the owner's decision: "
     "present it as a proposal with its cost."),
    ("retry-fallback", "high", r"\b(fallbacks?|fall back|retr(y|ies|ying)|backoff|failover)\b",
     "Retry/fallback behaviour: which failures trigger it, how many attempts, which model/provider, "
     "the cost cap, and how each retry is logged. Refusals and invalid requests should not be retried."),
    ("ai-provider", "high",
     r"\b(openai|anthropic|openrouter|bedrock|vertex|azure openai|mistral|cohere|groq|together\.ai|replicate|fal)\b",
     "Which AI provider and why (price, data terms, rate limits, lock-in)? Is the owner's account/billing ready?"),
    ("paid-services", "high",
     r"(\$\s?\d|\bper (call|request|token|run|search|image)\b|\bpricing\b|\bbilling\b|\bcredits?\b|\bpaid\b|\bsubscription\b)",
     "Paid usage: expected cost per run and per month, who pays, and the spending cap the owner approves."),
    ("data-handling", "high",
     r"\b(personal data|pii|user data|retention|retain|third[- ]party|upload(ed|s)?|scrap(e|ing)|analytics|telemetry|"
     r"passwords?|cookies?|emails?)\b",
     "What data is collected, sent to third parties, stored, for how long, and who can see it?"),
    ("dependencies", "medium",
     r"\b(npm (i|install)|pip install|yarn add|pnpm add|new dependency|sdk|external service|saas|webhook)\b",
     "New dependency or external service: is it needed, maintained, licensed acceptably, and replaceable?"),
    ("stack", "high",
     r"\b(next\.?js|react native|react|vue|svelte|angular|django|rails|fastapi|flask|express|supabase|firebase|"
     r"postgres(ql)?|sqlite|mongodb|vercel|netlify|aws|docker|kubernetes)\b",
     "Stack choice: why this over the simplest option that meets the requirements? Hosting cost and lock-in?"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_time(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


class Blocked(Exception):
    """A process gate is not satisfied; exits 3 like the design gate."""


def repo_path(raw: str) -> Path:
    repo = Path(raw).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"Repository directory does not exist: {repo}")
    return repo


def safe_write(path: Path, body: str) -> bool:
    """Preserve existing project files instead of replacing user content."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return True


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps({"at": now(), **event}, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue  # one bad line must not hide the rest of the history
    return rows


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def load_config(repo: Path) -> dict[str, Any]:
    config_path = repo / CONFIG_DIR / "config.json"
    if not config_path.is_file():
        hint = ""
        for parent in repo.parents:
            if (parent / CONFIG_DIR / "config.json").is_file():
                hint = (f" A parent directory ({parent}) is initialized, but What Skill never assumes a parent"
                        " is the active project; confirm with the user.")
                break
        raise ValueError(f"Project isn't initialized: {config_path}. Run `init` first.{hint}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("lead_agent") not in LEAD_FILES:
        raise ValueError("Invalid lead_agent in project configuration")
    return config


def save_config(repo: Path, cfg: dict[str, Any]) -> None:
    (repo / CONFIG_DIR / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def default_design() -> dict[str, Any]:
    return {"has_ui": "unknown", "depth": "unset", "system_checked": False, "system_choice": "unknown",
            "expectations_captured": False, "skills_reviewed": False, "references_gathered": False,
            "explorations": 0, "directions": [], "direction": "none", "approved_direction": None,
            "investigation_pending": False, "quality_review": "not-run", "compliance": "not-run",
            "surfaces": {}}


def design_state(cfg: dict[str, Any], surface: str = MAIN_SURFACE) -> dict[str, Any]:
    """Projects created before v0.2 have no design block; v0.2 has no surfaces. Fill in safe defaults.

    The top-level direction fields are the `main` surface (v0.2 layout); other surfaces keep their own
    direction fields under `surfaces` and share discovery steps (taste, system, depth) with main.
    """
    state = {**default_design(), **cfg.get("design", {})}
    if surface != MAIN_SURFACE:
        fresh = default_design()
        state = {**state, **{k: fresh[k] for k in SURFACE_KEYS}, **state["surfaces"].get(surface, {})}
    return state


def save_design(cfg: dict[str, Any], state: dict[str, Any], surface: str) -> None:
    if surface == MAIN_SURFACE:
        cfg["design"] = state
        return
    main = {**default_design(), **cfg.get("design", {})}
    main.update({k: v for k, v in state.items() if k not in SURFACE_KEYS and k != "surfaces"})
    main["surfaces"] = {**main["surfaces"], surface: {k: state[k] for k in SURFACE_KEYS}}
    cfg["design"] = main


def approved_directions(cfg: dict[str, Any]) -> dict[str, Any]:
    main = design_state(cfg)
    found = {MAIN_SURFACE: main["approved_direction"]}
    for name in main["surfaces"]:
        found[name] = design_state(cfg, name)["approved_direction"]
    return found


def design_gate(state: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    """Return (allowed, missing, advice) for significant visual implementation, in plain words."""
    if state["has_ui"] == "no":
        return True, [], []
    missing, advice = [], []
    depth = state["depth"] if state["depth"] in DEPTHS else "standard"
    if state["depth"] not in DEPTHS:
        advice.append("Set the design depth from Project DNA (--step depth --value light|standard|deep); using standard.")
    if state["has_ui"] == "unknown":
        missing.append("Confirm whether the project has a visual interface (--step ui-yes or ui-no).")
    if not state["system_checked"]:
        missing.append("Check for an existing design system or visual style (--step system-check).")
    if not state["expectations_captured"]:
        missing.append("Ask the owner about visual expectations, references and ambition (--step expectations).")
    if state["investigation_pending"]:
        missing.append("Investigate why the last direction was rejected (--step investigation).")
    if depth in ("standard", "deep") and not state["skills_reviewed"]:
        missing.append("Recommend design skills that fit the surface type (--step skills).")
    if depth == "deep":
        if not state["references_gathered"]:
            missing.append("Research real visual references (--step references).")
        if state["system_choice"] == "unknown":
            missing.append("Decide the design-system level: existing, lightweight, custom or none (--step system-choice).")
        if len(state["directions"]) < 2:
            missing.append("Explore at least two meaningfully different directions (--step direction-proposed --value NAME).")
    elif state["system_choice"] == "unknown":
        advice.append("Decide the design-system level: existing, lightweight, custom or none (--step system-choice).")
    if state["direction"] != "approved":
        missing.append("Get the owner's approval of one named direction (--step direction-approved --value NAME --user-confirmed).")
    if state["compliance"] == "pass" and state["quality_review"] == "not-run":
        advice.append("Compliance passed, but that does not show the design is good: run a quality review.")
    return not missing, missing, advice


def lead_instructions(agent: str) -> str:
    return f"""{MARKER_START}
## What Skill — project mentor (lead: {agent}, v0.3)

This repository uses What Skill. At session start run `what_skill.py resume --repo . --agent <you>`
(or read `.what-skill/config.json` and `.project-brain/`) and continue from it: do not restart discovery
or re-ask confirmed facts. The human approves product and architectural decisions; **{agent}** is the
lead coding agent; other agents are supporting reviewers and must not overwrite approved decisions.
**Before implementing** anything that sets architecture/stack, AI model or provider, retry/fallback
behaviour, paid services, data handling/security or a significant dependency, run `challenge` on the
plan, present each consequential default (including defaults from other skills) as a proposal with its
cost, record the owner's answer with `decide`, and check `gate --implementation`. Weak consent ("go
ahead") approves only what the owner was shown. Before the first live/paid AI run, confirm every paid
path logs inputs, outputs, cost and errors (`checkpoint --kind pre-live --evidence <log path>`), get a
spend cap (`approve-spend`) and record measured cost (`spend`). Record skills actually used and their
outcome (`skill-use`). At milestones run `reconcile` and fix stale tasks, lifecycle and plans.
Visual interfaces: design discovery starts automatically at kickoff, at the depth Project DNA
suggests. Research, mockups and prototypes are always allowed; before significant production
styling run `what_skill.py design --repo . --gate [--surface NAME]` and follow
`references/design-intelligence.md`. Only the owner approves a named visual direction.
Avoid interrupting productive small tasks; after confirmed release, be quieter unless new material risk.
Never claim to observe offline conversations or other agents' private sessions.
Read the installed `what-skill/SKILL.md` when host skill discovery is unavailable.
{MARKER_END}
"""


def git_present(repo: Path) -> bool:
    return any((p / ".git").exists() for p in (repo, *repo.parents))


def cmd_init(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    config_file = repo / CONFIG_DIR / "config.json"
    if config_file.exists():
        raise ValueError(f"Already initialized; preserving {config_file}. Use `status`.")
    cfg = {
        "schema_version": 2,
        "what_skill_version": VERSION,
        "initialized_at": now(),
        "lead_agent": args.agent,
        "lifecycle": "discovery",
        "interview_mode": args.mode,
        "communication_level": args.communication,
        "challenge_intensity": args.challenge,
        "memory": {"mode": "hybrid", "store_full_transcripts": False, "share_global_lessons": False},
        "discovery": {"installed": True, "public_web": "ask_before_use", "auto_install": False},
        "release_confirmed_by_user": False,
        "design": default_design(),
        "decisions": {},
        "required_topics": list(DEFAULT_REQUIRED_TOPICS),
        "spend": {"approvals": [], "entries": []},
    }
    config_file.parent.mkdir(parents=True, exist_ok=True)
    save_config(repo, cfg)
    defaults = {
        "overview.md": f"# Project overview\n\n- Lead agent: {args.agent}\n- Lifecycle: discovery (human confirmation required to change release status)\n- Problem: To be discovered\n- Audience: To be discovered\n- MVP: To be discovered\n- Success signal: To be discovered\n- Non-goals: To be discovered\n",
        "project-dna.md": (ROOT / "templates" / "project-dna.md").read_text(encoding="utf-8"),
        "decisions.md": "# Decisions\n\nRecord confirmed decisions with date, rationale, status and evidence. Do not treat assumptions as approvals.\n",
        "progress.md": "# Progress\n\nTrack completed work, test evidence, obstacles and current milestone.\n",
        "conversation-memory.md": "# Conversation memory\n\nSummarize meaningful confirmed requirements, user feedback, points of confusion and unresolved topics. No secrets or raw transcripts.\n",
        "next-tasks.md": "# Next tasks\n\n- [ ] Run What Skill kickoff interview.\n- [ ] Confirm Project DNA and MVP.\n- [ ] If there is a visual interface: design discovery at the depth DNA suggests (see design.md).\n- [ ] Before implementation: confirm stack, AI model/provider, retry/fallback, paid services and data handling (`challenge`, `decide`, `gate --implementation`).\n- [ ] Review contextual skill recommendations.\n",
        "design.md": (ROOT / "templates" / "design.md").read_text(encoding="utf-8"),
    }
    created = []
    for filename, body in defaults.items():
        if safe_write(repo / BRAIN_DIR / filename, body):
            created.append(str(Path(BRAIN_DIR) / filename))
    for fname in ("events.jsonl", "skill-history.jsonl"):
        if safe_write(repo / CONFIG_DIR / fname, ""):
            created.append(str(Path(CONFIG_DIR) / fname))
    instruction_file = repo / LEAD_FILES[args.agent]
    content = read_text(instruction_file)
    if MARKER_START not in content:
        with instruction_file.open("a", encoding="utf-8") as fp:
            fp.write(("\n\n" if content.strip() else "") + lead_instructions(args.agent))
    append_event(repo / CONFIG_DIR / "events.jsonl", {"event": "initialized", "agent": args.agent, "version": VERSION})
    has_git = git_present(repo)
    print(json.dumps({"result": "initialized", "repo": str(repo), "lead_agent": args.agent,
                      "created_memory_files": created, "lead_instruction_file": instruction_file.name,
                      "git": "present" if has_git else "missing",
                      "advice": [] if has_git else ["No Git repository. Offer the owner `git init` now so kickoff and design "
                                                    "decisions have history (What Skill never runs it, pushes or adds remotes)."]},
                     indent=2))


# ---------- decisions, gates and spend (v0.3) ----------

def decisions_of(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("decisions", {})


def uses_ai(cfg: dict[str, Any]) -> bool:
    return bool(cfg.get("uses_ai")) or any(t in decisions_of(cfg) for t in AI_TOPICS)


def required_topics(cfg: dict[str, Any]) -> list[str]:
    topics = list(cfg.get("required_topics", DEFAULT_REQUIRED_TOPICS))
    if uses_ai(cfg):
        topics += [t for t in AI_TOPICS + ("paid-services",) if t not in topics]
    return topics


def implementation_gate(cfg: dict[str, Any]) -> tuple[bool, list[str]]:
    blockers = []
    decisions = decisions_of(cfg)
    if not cfg.get("challenged"):  # eval finding: without a scan, only `stack` was required and the gate opened too early
        blockers.append("No consequential-defaults scan yet: run `challenge --file <plan> [--file <supporting skill>]`.")
    for topic in required_topics(cfg):
        if topic not in decisions:
            blockers.append(f"{topic}: not decided. Propose it to the owner and record with `decide`.")
    for topic, d in decisions.items():
        if d["status"] in ("proposed", "assumed"):
            who = d.get("source", "agent")
            blockers.append(f"{topic}: {d['status']} ({d['proposal']!r}, source {who}); needs the owner's explicit answer.")
    return not blockers, blockers


def norm(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def cmd_decide(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    topic = args.topic.strip().casefold()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", topic):
        raise ValueError("--topic must be a short slug, e.g. model-tier, retry-fallback, stack")
    source = args.source.strip()
    if source not in ("owner", "agent", "template") and not re.fullmatch(r"skill:[\w.:/-]+", source):
        raise ValueError("--source must be owner, agent, template or skill:<name>")
    decisions = cfg.setdefault("decisions", {})
    prev = decisions.get(topic)
    proposal = (args.proposal or (prev or {}).get("proposal") or "").strip()
    if not proposal:
        raise ValueError("Describe the choice with --proposal.")
    status, quote, note = args.status, (args.quote or "").strip(), ""
    if status == "approved":
        if not quote:
            raise ValueError("Approval needs the owner's own words (--quote). A skill, template or agent default "
                             "is never an owner decision; record it as proposed.")
        shown = prev is not None and prev["status"] in ("proposed", "assumed") and norm(prev["proposal"]) == norm(proposal)
        if WEAK_CONSENT.match(quote) and not shown:
            status = "assumed"
            note = ("Weak consent for a choice the owner was never shown; stored as assumed. "
                    "Present it explicitly and confirm at the next checkpoint.")
    record = {"topic": topic, "proposal": proposal, "status": status, "source": source, "quote": quote,
              "rationale": args.rationale or "", "cost_estimate": args.cost_estimate or "", "at": now(),
              "history": ((prev or {}).get("history", []) + [{k: prev[k] for k in ("proposal", "status", "source", "quote", "at")}])
              if prev else []}
    decisions[topic] = record
    if topic in AI_TOPICS:
        cfg["uses_ai"] = True
    save_config(repo, cfg)
    append_event(repo / CONFIG_DIR / "events.jsonl", {"event": "decision", "topic": topic, "status": status,
                                                      "source": source, "proposal": proposal, "quote": quote})
    line = (f"- {record['at'][:10]} · **{topic}** · {status} · {proposal} · source: {source}"
            + (f" · owner: \"{quote}\"" if quote else "") + (f" · why: {args.rationale}" if args.rationale else "")
            + (f" · est. cost: {args.cost_estimate}" if args.cost_estimate else "")
            + (f" · supersedes: {prev['proposal']} ({prev['status']})" if prev and norm(prev['proposal']) != norm(proposal) else "")
            + "\n")
    with (repo / BRAIN_DIR / "decisions.md").open("a", encoding="utf-8") as fp:
        fp.write(line)
    print(f"Decision recorded: {topic} = {status}." + (f" {note}" if note else ""))
    allowed, blockers = implementation_gate(cfg)
    print(f"Implementation gate: {'open' if allowed else 'blocked'}.")
    for b in blockers:
        print(f"- {b}")


def scan_consequential(text: str) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for topic, severity, pattern, question in CHALLENGE_RULES:
        for m in re.finditer(pattern, text, re.I):
            entry = found.setdefault(topic, {"topic": topic, "severity": severity, "questions": [], "evidence": []})
            if question not in entry["questions"]:
                entry["questions"].append(question)
            if severity == "critical":
                entry["severity"] = "critical"
            if len(entry["evidence"]) < 3:
                start, end = max(0, m.start() - 50), min(len(text), m.end() + 50)
                entry["evidence"].append(" ".join(text[start:end].split()))
    return found


def cmd_challenge(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    if not args.file and not args.text:
        raise ValueError("Give the plan or proposal with --file PATH or --text.")
    text = "\n".join([Path(f).expanduser().read_text(encoding="utf-8") for f in args.file] + ([args.text] if args.text else []))
    findings = scan_consequential(text)
    decisions = decisions_of(cfg)
    to_ask, settled = [], []
    for topic, f in findings.items():
        d = decisions.get(topic)
        if d and d["status"] in ("approved", "rejected"):
            f["status"] = f"{d['status']}: {d['proposal']}"
            f["ask_owner"] = False  # adaptive: do not re-ask a settled decision unless the proposal changes it
            settled.append(f)
        else:
            f["status"] = d["status"] if d else "undecided"
            f["ask_owner"] = True
            to_ask.append(f)
    if args.record:
        changed = False
        for f in to_ask:
            if f["topic"] not in decisions:
                decisions[f["topic"]] = {"topic": f["topic"], "proposal": f"default from {args.source}: {f['evidence'][0]}",
                                         "status": "proposed", "source": args.source, "quote": "", "rationale": "",
                                         "cost_estimate": "", "at": now(), "history": []}
                changed = True
                if f["topic"] in AI_TOPICS:
                    cfg["uses_ai"] = True
                with (repo / BRAIN_DIR / "decisions.md").open("a", encoding="utf-8") as fp:
                    fp.write(f"- {now()[:10]} · **{f['topic']}** · proposed · default from {args.source}: "
                             f"\"{f['evidence'][0]}\" · source: {args.source} · awaiting owner\n")
        if changed:
            cfg["decisions"] = decisions
            save_config(repo, cfg)
    if any(f["topic"] in AI_TOPICS for f in findings.values()) and not cfg.get("uses_ai"):
        cfg["uses_ai"] = True
        save_config(repo, cfg)
    if not cfg.get("challenged"):
        cfg["challenged"] = True
        save_config(repo, cfg)
    order = {"critical": 0, "high": 1, "medium": 2}
    to_ask.sort(key=lambda f: order[f["severity"]])
    append_event(repo / CONFIG_DIR / "events.jsonl", {"event": "challenge", "source": args.source,
                                                      "topics": [f["topic"] for f in to_ask],
                                                      "settled": [f["topic"] for f in settled]})
    print(json.dumps({"source": args.source, "ask_owner": to_ask, "already_settled": settled,
                      "how_to_ask": ("Before any implementation: one short message listing each item as a proposal with a "
                                     "one-line trade-off and cost, your recommendation, and a cheaper alternative. "
                                     "Record answers with `decide`. Minor choices (names, layout, file structure) need no approval."),
                      "note": "Pattern scan only: it finds candidates; the agent still judges the plan as a whole."},
                     indent=2, ensure_ascii=False))
    if to_ask:
        raise SystemExit(3)


def spend_summary(cfg: dict[str, Any]) -> dict[str, Any]:
    spend = cfg.get("spend", {"approvals": [], "entries": []})
    rows, issues = [], []
    for a in spend["approvals"]:
        used = [e for e in spend["entries"] if e.get("approval") == a["id"]]
        measured = round(sum(e["amount"] for e in used if e["kind"] == "measured"), 6)
        estimated = round(sum(e["amount"] for e in used if e["kind"] == "estimated"), 6)
        total = measured + estimated
        rows.append({"id": a["id"], "scope": a["scope"], "cap_usd": a["cap"], "measured_usd": measured,
                     "estimated_usd": estimated, "remaining_usd": round(a["cap"] - total, 6)})
        if total > a["cap"] + 1e-9:
            issues.append(f"Spend on {a['id']} ({a['scope']}) is ${total:.4f}, over the approved cap ${a['cap']:.4f}.")
    ids = {a["id"] for a in spend["approvals"]}
    for e in spend["entries"]:
        if e.get("approval") not in ids:
            issues.append(f"${e['amount']:.4f} spent without a matching approval ({e.get('ref') or 'no ref'}).")
    measured_total = round(sum(e["amount"] for e in spend["entries"] if e["kind"] == "measured"), 6)
    return {"approvals": rows, "measured_total_usd": measured_total,
            "estimated_total_usd": round(sum(e["amount"] for e in spend["entries"] if e["kind"] == "estimated"), 6),
            "issues": issues}


def cmd_approve_spend(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    if not (args.quote or "").strip():
        raise ValueError("A spending approval needs the owner's own words (--quote).")
    if args.cap <= 0:
        raise ValueError("--cap must be a positive amount in USD")
    spend = cfg.setdefault("spend", {"approvals": [], "entries": []})
    approval = {"id": f"S{len(spend['approvals']) + 1}", "scope": args.scope, "cap": args.cap,
                "quote": args.quote.strip(), "at": now()}
    spend["approvals"].append(approval)
    save_config(repo, cfg)
    append_event(repo / CONFIG_DIR / "events.jsonl", {"event": "spend_approved", **approval})
    print(f"Spending approved: {approval['id']} — {args.scope}, cap ${args.cap:.4f}. Record measured cost with "
          f"`spend --approval {approval['id']}`.")
    if not cfg.get("observability"):
        print("Before running: confirm logging with `checkpoint --kind pre-live --evidence <log path>`.")


def cmd_spend(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    if args.amount < 0:
        raise ValueError("--amount cannot be negative")
    spend = cfg.setdefault("spend", {"approvals": [], "entries": []})
    entry = {"amount": args.amount, "approval": args.approval or "", "ref": args.ref or "",
             "kind": "estimated" if args.estimated else "measured", "note": args.note or "", "at": now()}
    spend["entries"].append(entry)
    save_config(repo, cfg)
    append_event(repo / CONFIG_DIR / "events.jsonl", {"event": "spend", **entry})
    summary = spend_summary(cfg)
    print(f"Recorded {entry['kind']} spend ${args.amount:.4f}. Measured total ${summary['measured_total_usd']:.4f}.")
    if not args.ref:
        print("Warning: no --ref. Point to the run log so the number can be checked later.")
    for issue in summary["issues"]:
        print(f"WARNING: {issue} Tell the owner.")


def live_gate(cfg: dict[str, Any], approval: str | None, expected: float | None) -> tuple[bool, list[str]]:
    blockers = []
    if not cfg.get("observability"):
        blockers.append("No logging evidence for live runs: confirm every paid path persists inputs, outputs, cost and "
                        "errors, then `checkpoint --kind pre-live --evidence <log path>`.")
    rows = {r["id"]: r for r in spend_summary(cfg)["approvals"]}
    if not approval:
        blockers.append("Name the owner's spending approval (--approval S#); create one with `approve-spend`.")
    elif approval not in rows:
        blockers.append(f"Unknown spending approval {approval}.")
    else:
        left = rows[approval]["remaining_usd"]
        if left <= 0 or (expected is not None and expected > left):
            blockers.append(f"Approval {approval} has ${left:.4f} left; ask the owner for more before running.")
    return not blockers, blockers


def cmd_gate(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    report: dict[str, Any] = {}
    blocked = False
    check_impl = args.implementation or not args.live
    check_live = args.live or not args.implementation
    if check_impl:
        ok, why = implementation_gate(cfg)
        report["implementation"] = {"status": "open" if ok else "blocked", "required_topics": required_topics(cfg), "blockers": why}
        blocked |= args.implementation and not ok
    if check_live:
        ok, why = live_gate(cfg, args.approval, args.expected_cost)
        report["live_ai"] = {"status": "open" if ok else "blocked", "blockers": why}
        blocked |= args.live and not ok
    report["note"] = ("Gates record evidence for the agent; they are not runtime enforcement. Higher-priority security "
                      "and host rules always win.")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if blocked:
        raise SystemExit(3)


# ---------- reconciliation and recovery (v0.3) ----------

TASK_STOP = {"blocked", "discussing", "todo", "done", "task", "tasks", "next", "add", "make", "run", "what"}


def task_lines(text: str) -> list[tuple[bool, str]]:
    """Checkbox items, plus plain bullet/numbered items (some projects write tasks as `1. [BLOCKED] ...`)."""
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$", line)
        if m:
            out.append((m.group(1).lower() == "x", m.group(2).strip()))
            continue
        m = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.*\S)\s*$", line)
        if m:
            out.append((False, m.group(1)))
    return out


def lifecycle_in(text: str) -> str | None:
    m = re.search(r"Lifecycle:\**\s*([a-z-]+)", text, re.I)
    return m.group(1).casefold() if m else None


def done_evidence(repo: Path, events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    evidence = [("progress.md", line.strip()) for line in read_text(repo / BRAIN_DIR / "progress.md").splitlines()
                if line.strip() and not line.startswith("#")]
    evidence += [(f"checkpoint {e['kind']} {e['at'][:10]}", e.get("summary", "")) for e in events
                 if e.get("event") == "checkpoint" and e.get("kind") in ("task-complete", "milestone", "kickoff", "pre-release")]
    if git_present(repo):
        try:
            log = subprocess.run(["git", "-C", str(repo), "log", "--format=%h %s", "-n", "300"],
                                 capture_output=True, text=True, timeout=5)
            evidence += [("commit", line) for line in log.stdout.splitlines()]
        except (OSError, subprocess.SubprocessError):
            pass
    return evidence


def reconcile(repo: Path, cfg: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(kind: str, detail: str, fix: str) -> None:
        findings.append({"kind": kind, "detail": detail, "proposed_fix": fix})

    events = read_jsonl(repo / CONFIG_DIR / "events.jsonl")
    checkpoints = [e for e in events if e.get("event") == "checkpoint"]

    # Lifecycle: one value everywhere, and not frozen while milestones pass.
    life = cfg.get("lifecycle")
    for name in ("overview.md", "project-dna.md"):
        written = lifecycle_in(read_text(repo / BRAIN_DIR / name))
        if written and written != life:
            add("lifecycle-conflict", f"{BRAIN_DIR}/{name} says lifecycle '{written}' but config says '{life}'.",
                f"Confirm the real stage with the owner, then `lifecycle --status <stage> --user-confirmed` (updates all three).")
    last_change = max((e["at"] for e in events if e.get("event") == "lifecycle_change"), default="")
    later = [e for e in checkpoints if e["at"] > last_change and e.get("kind") in ("milestone", "task-complete")]
    if life == "discovery" and (any(e["kind"] == "milestone" for e in later) or len(later) >= 2):
        add("lifecycle-stale", f"Lifecycle is still 'discovery' after {len(later)} milestone/task-complete checkpoints.",
            "Ask the owner whether the project is now in development; record with `lifecycle --user-confirmed`.")

    # Tasks still open (or BLOCKED/DISCUSSING) although later evidence says they are done.
    evidence = done_evidence(repo, events)
    for done, task in task_lines(read_text(repo / BRAIN_DIR / "next-tasks.md")):
        if done:
            continue
        if re.search(r"\b(done|completed|finished)\b", task, re.I):
            add("stale-task", f"Task '{task[:120]}' says it is done but is still listed.",
                "Move it to progress.md or tick it.")
            continue
        if re.search(r"\b(pending|not yet|waiting)\b", task, re.I):
            continue  # the task itself says it is still open
        want = tokens(task) - TASK_STOP
        if len(want) < 2:
            continue
        best = max(((want & tokens(line), where, line) for where, line in evidence), key=lambda b: len(b[0]), default=None)
        if best:
            shared, where, line = best
            # ponytail: keyword overlap heuristic; it proposes, the owner confirms. Upgrade path: embeddings.
            if (len(shared) >= 2 and len(shared) / len(want) > 0.5) or (len(shared) >= 4 and len(shared) / len(want) >= 0.2):
                add("stale-task", f"Open task '{task[:120]}' looks done: {where}: '{line[:120]}' (shared: {', '.join(sorted(shared))}).",
                    "Confirm, then tick it in next-tasks.md (or reword it if only part is done).")

    # Design approvals: one per surface; an approval replaced without a change or rejection may be lost.
    current = approved_directions(cfg)
    live_names = {a["name"].casefold() for a in current.values() if a}
    by_surface: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        if e.get("event") == "design":
            by_surface.setdefault(e.get("surface") or MAIN_SURFACE, []).append(e)
    for surface, rows in by_surface.items():
        live = (current.get(surface) or {}).get("name")
        for i, e in enumerate(rows):
            if e.get("step") != "direction-approved" or not e.get("value"):
                continue
            name = e["value"]
            if name.casefold() in live_names:
                continue  # still approved on some surface
            after = rows[i + 1:]
            if any(a.get("step") in ("direction-changed", "direction-rejected") or
                   (a.get("step") == "direction-superseded" and a.get("value", "").casefold() == name.casefold())
                   for a in after):
                continue  # replaced through a recorded path
            if any(a.get("step") == "direction-approved" for a in after):
                add("design-approval-overwritten",
                    f"Surface '{surface}': owner approved '{name}' ({e['at'][:10]}: {e.get('summary', '')!r}) but config now "
                    f"holds '{live}'. v0.2 kept one approval slot, so a second surface may have replaced the first.",
                    f"If '{name}' still applies, re-record it on its own surface: `design-record --surface <name> "
                    f"--step direction-proposed/--step direction-approved --value \"{name}\" --user-confirmed` "
                    f"quoting the original approval. If the owner confirms it was replaced, record "
                    f"`design-record --step direction-superseded --value \"{name}\"`.")
    for surface, approved in current.items():
        if approved and not any(e.get("step") == "direction-approved" for e in by_surface.get(surface, [])):
            add("design-approval-unlogged", f"Surface '{surface}' approval '{approved['name']}' has no event evidence.",
                "Confirm it with the owner and re-record it.")
        if design_state(cfg, surface)["investigation_pending"]:
            add("design-investigation-pending", f"Surface '{surface}': a rejected direction was never investigated.",
                "Investigate before proposing new directions.")

    # Decisions waiting for the owner.
    for topic, d in decisions_of(cfg).items():
        if d["status"] in ("assumed", "proposed"):
            add("decision-unconfirmed", f"'{topic}' is {d['status']}: {d['proposal']} (source {d.get('source')}).",
                "Present it to the owner and record their answer with `decide`.")

    # Skills: recommended and never acted on; invoked without a recorded outcome; used but never recorded.
    history = read_jsonl(repo / CONFIG_DIR / "skill-history.jsonl")
    latest: dict[str, str] = {}
    for h in history:
        if h.get("event") == "skill_use":
            latest[h["skill"]] = h["status"]
        elif h.get("event") == "skill_feedback":
            latest[h["skill"]] = "completed"
    for skill, st in latest.items():
        if st == "recommended":
            add("skill-not-acted", f"'{skill}' was recommended but never invoked, rejected or skipped.",
                "Invoke it, or record `skill-use --status skipped|rejected --reason ...`.")
        elif st == "invoked":
            add("skill-no-outcome", f"'{skill}' was invoked but no outcome was recorded.",
                "Record `skill-use --status completed --outcome ...` (what it changed, evidence).")
    mentioned = {s for e in checkpoints for s in e.get("skills", [])}
    for skill in sorted(mentioned - set(latest)):
        add("skill-unrecorded", f"Checkpoint says '{skill}' was used, but skill history has no entry.",
            f"Record `skill-use --skill {skill} --status completed --outcome ...`.")

    # Plans that went stale after later major changes.
    for plan in cfg.get("plans", []):
        path = repo / plan
        if not path.is_file():
            add("plan-missing", f"Registered plan {plan} no longer exists.", "Re-register the current plan or mark it dropped.")
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        newer = [e for e in checkpoints if e.get("kind") == "major-change" and parse_time(e["at"]) > mtime]
        if newer:
            add("plan-drift", f"{plan} is older than {len(newer)} later major change(s) (last: {newer[-1].get('summary', '')!r}).",
                "Update its phase table or add a dated '## Superseded' note.")

    for issue in spend_summary(cfg)["issues"]:
        add("spend", issue, "Tell the owner and record an approval or a correction.")
    if checkpoints and not git_present(repo):
        add("no-git", "Checkpoints exist but the project has no Git history.", "Offer the owner `git init` and a first commit.")
    return findings


def cmd_reconcile(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    findings = reconcile(repo, cfg)
    print(json.dumps({"findings": findings, "count": len(findings), "applied": False,
                      "note": "Proposals only. Confirm with the owner where facts are disputed; keep every approved "
                              "decision unless the owner supersedes it."}, indent=2, ensure_ascii=False))
    if args.strict and findings:
        raise SystemExit(3)


def overview_fields(text: str) -> dict[str, str]:
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^\s*-\s+([A-Za-z][\w /-]{1,30}):\s*(.+)$", line)
        if m and "to be discovered" not in m.group(2).casefold():
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def skill_summary(repo: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for h in read_jsonl(repo / CONFIG_DIR / "skill-history.jsonl"):
        if h.get("event") == "skill_use":
            out[h["skill"]] = {"status": h["status"], "stage": h.get("stage", ""), "outcome": h.get("outcome", "")}
        elif h.get("event") == "skill_feedback":
            out[h["skill"]] = {"status": "completed", "stage": h.get("task_context", ""), "outcome": h.get("outcome", ""),
                               "rating": h.get("rating")}
    return out


def cmd_resume(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    events = read_jsonl(repo / CONFIG_DIR / "events.jsonl")
    decisions = decisions_of(cfg)
    kickoff_done = any(e.get("kind") == "kickoff" for e in events) or bool(decisions) or \
        any(e.get("event") in ("design", "decision") for e in events)
    design = design_state(cfg)
    lead = cfg["lead_agent"]
    role = None
    if args.agent:
        role = ("lead: you orchestrate development" if args.agent == lead else
                f"supporting: {lead} is the lead. Review and advise; do not overwrite approved decisions or Project Brain "
                f"files without the lead/owner.")
    brief = {
        "project": repo.name, "repo": str(repo), "what_skill_version": cfg.get("what_skill_version", "0.2 or earlier"),
        "lead_agent": lead, "your_role": role, "lifecycle": cfg.get("lifecycle"),
        "settings": {k: cfg.get(k) for k in ("interview_mode", "communication_level", "challenge_intensity")},
        "overview": overview_fields(read_text(repo / BRAIN_DIR / "overview.md")),
        "discovery": "done: continue from Project Brain, do not restart the interview or re-ask confirmed facts"
                     if kickoff_done else "not started: run the kickoff interview",
        "approved_decisions": {t: d["proposal"] for t, d in decisions.items() if d["status"] == "approved"},
        "rejected_options": {t: d["proposal"] for t, d in decisions.items() if d["status"] == "rejected"},
        "awaiting_owner": {t: f"{d['status']}: {d['proposal']}" for t, d in decisions.items() if d["status"] in ("proposed", "assumed")},
        "implementation_gate": "open" if implementation_gate(cfg)[0] else "blocked",
        "design": {"has_ui": design["has_ui"], "approved_directions": {s: (a or {}).get("name") for s, a in approved_directions(cfg).items()}},
        "open_tasks": [t for done, t in task_lines(read_text(repo / BRAIN_DIR / "next-tasks.md")) if not done],
        "recent_checkpoints": [f"{e['at'][:16]} {e['kind']}: {e.get('summary', '')}" for e in events if e.get("event") == "checkpoint"][-5:],
        "skills": skill_summary(repo),
        "spend": spend_summary(cfg),
        "stale_or_conflicting": reconcile(repo, cfg),
        "next_step": "Tell the user in two or three lines where the project stands and the next task; fix stale items "
                     "with the owner before relying on them. Read decisions.md / progress.md for detail.",
    }
    print(json.dumps(brief, indent=2, ensure_ascii=False))


# ---------- v0.2 commands (extended) ----------

def cmd_status(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    gate_ok, _ = implementation_gate(cfg)
    summary = {"implementation_gate": "open" if gate_ok else "blocked", "spend": spend_summary(cfg),
               "approved_directions": approved_directions(cfg)}
    if getattr(args, "reconcile", False):
        summary["reconcile"] = reconcile(repo, cfg)
    print(json.dumps({"repo": str(repo), **cfg, "summary": summary}, indent=2, ensure_ascii=False))


def plan_note_is_current(text: str) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    dates = re.findall(r"(?:Superseded|Updated)\W[\s\S]{0,80}?(\d{4}-\d{2}-\d{2})", text, re.I)
    return any(d >= today for d in dates)


def cmd_checkpoint(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    evidence = (args.evidence or "").strip()
    plan = getattr(args, "plan", None)
    skills = [s.strip() for s in (getattr(args, "skills", "") or "").split(",") if s.strip()]
    if args.kind == "pre-live" and not evidence:
        raise Blocked("pre-live needs --evidence naming where runs are logged (inputs, outputs, cost, errors). "
                      "Ask: if this run fails, will we know why without re-running?")
    if plan:
        plan_file = repo / plan
        if not plan_file.is_file():
            raise ValueError(f"Plan file not found: {plan_file}")
        if args.kind == "major-change" and not plan_note_is_current(read_text(plan_file)):
            raise Blocked(f"{plan} has no dated '## Superseded' or 'Updated: YYYY-MM-DD' note for this change. "
                          "Update the plan first so it matches the approved scope.")
        rel = str(plan_file.relative_to(repo))
        cfg.setdefault("plans", [])
        if rel not in cfg["plans"]:
            cfg["plans"].append(rel)
    if args.kind == "pre-live":
        cfg["observability"] = {"evidence": evidence, "summary": args.summary, "at": now()}
    if plan or args.kind == "pre-live":
        save_config(repo, cfg)
    append_event(repo / CONFIG_DIR / "events.jsonl", {
        "event": "checkpoint", "kind": args.kind, "summary": args.summary,
        "evidence": evidence, "lifecycle": cfg["lifecycle"],
        "needs_project_brain_review": True, **({"skills": skills} if skills else {}), **({"plan": plan} if plan else {}),
    })
    print("Checkpoint recorded. Lead agent should evaluate relevant risks, skill fit and update Project Brain based on verified facts.")
    if args.kind in ("task-complete", "milestone", "pre-release"):
        print("Record each skill actually used and its outcome with `skill-use` (and owner sentiment with `feedback` if given).")
        findings = reconcile(repo, cfg)
        if findings:
            print(f"Reconcile: {len(findings)} stale or conflicting item(s):")
            for f in findings[:8]:
                print(f"- [{f['kind']}] {f['detail']}")
        if args.kind != "task-complete" and git_present(repo):
            print(f"Suggest a commit for this checkpoint: \"{args.summary}\".")
    if args.kind == "pre-implementation":
        ok, why = implementation_gate(cfg)
        print(f"Implementation gate: {'open' if ok else 'blocked'}.")
        for b in why:
            print(f"- {b}")


def cmd_skill_use(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    load_config(repo)
    if args.status == "completed" and not (args.outcome or "").strip():
        raise ValueError("A completed skill needs --outcome: what it produced or changed, and the evidence.")
    if args.status in ("rejected", "skipped") and not (args.reason or "").strip():
        raise ValueError(f"A {args.status} skill needs --reason.")
    entry = {"event": "skill_use", "skill": args.skill, "status": args.status, "stage": args.stage,
             "role": args.role or "", "outcome": args.outcome or "", "reason": args.reason or "",
             "evidence_level": args.evidence_level, "evidence": args.evidence or "", "global_shared": False}
    append_event(repo / CONFIG_DIR / "skill-history.jsonl", entry)
    print(f"Skill use recorded: {args.skill} = {args.status} ({args.stage}).")
    if args.status == "invoked":
        print("When it finishes, record the outcome: `skill-use --status completed --outcome ...`.")


def cmd_feedback(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    load_config(repo)
    dissatisfied = getattr(args, "dissatisfied", False) or (args.rating is not None and args.rating <= 2)
    entry = {
        "event": "skill_feedback", "skill": args.skill, "task_context": args.context,
        "rating": args.rating, "outcome": args.outcome,
        "evidence_level": args.evidence_level,
        "cause": args.cause,
        "user_feedback": args.feedback,
        "global_shared": False,
        "needs_investigation": dissatisfied,
    }
    append_event(repo / CONFIG_DIR / "skill-history.jsonl", entry)
    print("Project-specific feedback saved. No global learning and no installation performed.")
    if dissatisfied:
        print("The owner is dissatisfied: treat this as evidence. Investigate before changing anything:")
        for q in INVESTIGATION_QUESTIONS:
            print(f"- {q}")


def parse_skill_frontmatter(path: Path) -> dict[str, str] | None:
    """Minimal safe metadata reader; does not execute YAML or bundled scripts."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not raw.startswith("---\n"):
        return None
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", raw, re.S)
    if not match:
        return None
    meta: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            meta[key] = value.strip("\"'") if value not in ("|", ">") else ""
        elif key and line.startswith(" "):
            meta[key] = (meta[key] + " " + line.strip()).strip()
    if not meta.get("name") or not meta.get("description"):
        return None
    return meta


def tokens(text: str) -> set[str]:
    stop = {"the", "with", "and", "for", "that", "this", "your", "into", "from", "use", "when", "are", "using", "build", "project", "skill"}
    return {s for s in re.findall(r"[a-z0-9]+", text.casefold()) if len(s) > 2 and s not in stop}


def local_skills(roots: list[Path], query: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    desired = tokens(query)
    for root in roots:
        if not root.is_dir():
            continue
        # Recognize both a direct skill directory and its first-level children.
        paths = [root / "SKILL.md"] + list(root.glob("*/SKILL.md"))
        for p in paths:
            resolved = str(p.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            info = parse_skill_frontmatter(p)
            if not info:
                continue
            title = info["name"]
            matched = desired & tokens(title + " " + info["description"])
            score = len(matched) / max(1, len(desired)) if desired else 0.0
            found.append({"name": title, "description": info["description"],
                          "source": resolved, "status": "local-metadata-inspected",
                          "match_terms": sorted(matched), "keyword_coverage": round(score, 2),
                          "safety_status": "bundled-code-not-reviewed",
                          "recommendation_status": "candidate-needs-task-review"})
    return sorted(found, key=lambda c: (-c["keyword_coverage"], c["name"]))


def github_leads(query: str, limit: int) -> tuple[list[dict[str, Any]], str | None]:
    """Repository search only: never assert repository contains a suitable skill."""
    terms = query.strip() or "agent skills"
    q = urllib.parse.quote(f"{terms} agent skills in:name,description,readme")
    url = f"https://api.github.com/search/repositories?q={q}&per_page={min(limit, 10)}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"what-skill-discovery/{VERSION}"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.load(response)
    except (OSError, urllib.error.HTTPError, ValueError) as exc:
        return [], f"GitHub discovery unavailable: {type(exc).__name__}: {exc}"
    leads = []
    for row in data.get("items", [])[:limit]:
        leads.append({"repository": row.get("full_name"), "url": row.get("html_url"),
                      "repo_stars": row.get("stargazers_count"),
                      "status": "unverified-repository-lead",
                      "warning": "SKILL.md, license, code, compatibility and suitability NOT inspected; do not install automatically."})
    return leads, None


def cmd_discover(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    load_config(repo)
    roots = [repo / ".agents/skills", repo / ".claude/skills", repo / ".gemini/skills",
             Path.home() / ".agents/skills", Path.home() / ".claude/skills", Path.home() / ".gemini/skills"]
    roots += [Path(s).expanduser().resolve() for s in args.root]
    local = local_skills(roots, args.query)
    leads: list[dict[str, Any]] = []
    warning = None
    if args.online:
        leads, warning = github_leads(args.query, args.limit)
    print(json.dumps({"query": args.query, "local_candidates": local[:args.limit],
                      "github_leads": leads,
                      "coverage": "Local metadata scanned; public GitHub repo search only if --online used. No external skill verified or installed.",
                      "warning": warning}, indent=2, ensure_ascii=False))


def surface_of(args: argparse.Namespace) -> str:
    raw = (getattr(args, "surface", None) or MAIN_SURFACE).strip().casefold()
    if not re.fullmatch(r"[a-z0-9][a-z0-9 _-]*", raw):
        raise ValueError("--surface must be a short name, e.g. main, trend-board, landing")
    return raw


def cmd_design(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    surface = surface_of(args)
    state = design_state(cfg, surface)
    allowed, missing, advice = design_gate(state)
    print(json.dumps({"design": state, "surface": surface,
                      "approved_directions": approved_directions(cfg),
                      "visual_implementation": "allowed" if allowed else "blocked",
                      "exploration": "always allowed: research, references, mockups and prototypes outside production code",
                      "missing": missing, "advice": advice,
                      "note": "The gate covers significant production styling. Small changes inside the approved direction never need it."},
                     indent=2, ensure_ascii=False))
    if args.gate and not allowed:
        raise SystemExit(3)


def cmd_design_record(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    surface = surface_of(args)
    state = design_state(cfg, surface)
    step, value = args.step, (args.value or "").strip() or None
    if step in ("ui-yes", "ui-no"):
        state["has_ui"] = "yes" if step == "ui-yes" else "no"
    elif step == "depth":
        if value not in DEPTHS:
            raise ValueError(f"--value must be one of {', '.join(DEPTHS)}")
        state["depth"] = value
    elif step == "references":
        state["references_gathered"] = True
    elif step == "exploration":
        state["explorations"] += 1
    elif step == "system-check":
        state["system_checked"] = True
    elif step == "system-choice":
        if value not in SYSTEM_CHOICES:
            raise ValueError(f"--value must be one of {', '.join(SYSTEM_CHOICES)}")
        state["system_choice"] = value
    elif step == "expectations":
        state["expectations_captured"] = True
    elif step == "skills":
        state["skills_reviewed"] = True
    elif step in ("direction-proposed", "direction-changed"):
        if not value:
            raise ValueError("Name the direction with --value (e.g. \"A · Quiet native\").")
        if value.casefold() not in (d.casefold() for d in state["directions"]):
            state["directions"].append(value)
        state["direction"] = "proposed"
        if step == "direction-changed":  # a substantial change to the approved direction needs renewed approval
            state["approved_direction"] = None
    elif step == "direction-approved":
        if not args.user_confirmed:
            raise ValueError("Only the owner approves a visual direction; pass --user-confirmed only after explicit approval.")
        if state["investigation_pending"]:
            raise ValueError("The last direction was rejected and not yet investigated; record --step investigation first.")
        match = [d for d in state["directions"] if value and d.casefold() == value.casefold()]
        if state["direction"] != "proposed" or not match:
            raise ValueError("Approve one named, proposed direction: --value must match a --step direction-proposed name.")
        state["direction"] = "approved"
        state["approved_direction"] = {"name": match[0], "owner_confirmation": args.summary, "at": now()}
    elif step == "direction-rejected":
        state["direction"] = "rejected"
        state["approved_direction"] = None
        state["investigation_pending"] = True
    elif step == "direction-superseded":  # history note only: an earlier approval no longer applies
        if not value:
            raise ValueError("Name the superseded direction with --value.")
    elif step == "investigation":
        state["investigation_pending"] = False
    elif step in ("quality-review", "compliance"):
        if value not in REVIEW_VALUES:
            raise ValueError("--value must be pass or fail")
        state["quality_review" if step == "quality-review" else "compliance"] = value
    save_design(cfg, state, surface)
    save_config(repo, cfg)
    append_event(repo / CONFIG_DIR / "events.jsonl", {
        "event": "design", "step": step, "value": value or "", "summary": args.summary,
        "user_confirmed": bool(args.user_confirmed), "surface": surface,
        "needs_investigation": step == "direction-rejected"})
    allowed, missing, _ = design_gate(state)
    label = "" if surface == MAIN_SURFACE else f" for surface '{surface}'"
    print(f"Design step recorded: {step}{label}. Significant visual implementation is {'allowed' if allowed else 'blocked'}"
          f"{' (approved: ' + state['approved_direction']['name'] + ')' if allowed and state['approved_direction'] else ''}."
          " Research, mockups and prototypes are always allowed.")
    if step == "direction-rejected":
        print("Treat the rejection as evidence. Investigate before proposing anything new:")
        for q in INVESTIGATION_QUESTIONS:
            print(f"- {q}")
    for item in missing:
        print(f"Still needed: {item}")


def sync_lifecycle_text(path: Path, stage: str) -> bool:
    text = read_text(path)
    new, n = re.subn(r"(Lifecycle:\**\s*)([a-z-]+)", lambda m: m.group(1) + stage, text, count=1, flags=re.I)
    if n and new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def cmd_lifecycle(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    old = cfg["lifecycle"]
    if old == args.status:
        print(f"Already in lifecycle stage: {old}")
        return
    if not args.user_confirmed:
        raise ValueError("Lifecycle transitions require user confirmation; pass --user-confirmed only after explicit approval.")
    cfg["lifecycle"] = args.status
    cfg["release_confirmed_by_user"] = args.status == "released"
    save_config(repo, cfg)
    synced = [name for name in ("overview.md", "project-dna.md") if sync_lifecycle_text(repo / BRAIN_DIR / name, args.status)]
    append_event(repo / CONFIG_DIR / "events.jsonl", {
        "event": "lifecycle_change", "from": old, "to": args.status,
        "user_confirmed": True, "evidence": args.evidence or "", "synced_files": synced})
    print(f"Lifecycle updated {old} -> {args.status}" + (f" (also updated {', '.join(synced)})" if synced else "")
          + ". Review Project Brain for corresponding changes.")


def cmd_upgrade(args: argparse.Namespace) -> None:
    """Refresh only the marked lead-instruction block; everything else in the project stays as it is."""
    repo = repo_path(args.repo)
    cfg = load_config(repo)
    if not args.user_confirmed:
        raise ValueError("Upgrading a project's lead instructions needs the owner's approval; pass --user-confirmed after it.")
    path = repo / LEAD_FILES[cfg["lead_agent"]]
    text = read_text(path)
    block = lead_instructions(cfg["lead_agent"])
    if MARKER_START in text and MARKER_END in text:
        start, end = text.index(MARKER_START), text.index(MARKER_END) + len(MARKER_END)
        text = text[:start] + block.strip("\n") + text[end:]
    else:
        text += ("\n\n" if text.strip() else "") + block
    path.write_text(text, encoding="utf-8")
    old = cfg.get("what_skill_version", "0.2 or earlier")
    cfg["what_skill_version"] = VERSION
    cfg["schema_version"] = max(2, int(cfg.get("schema_version", 1)))
    cfg.setdefault("decisions", {})
    cfg.setdefault("required_topics", list(DEFAULT_REQUIRED_TOPICS))
    cfg.setdefault("spend", {"approvals": [], "entries": []})
    save_config(repo, cfg)
    append_event(repo / CONFIG_DIR / "events.jsonl", {"event": "upgraded", "from": old, "to": VERSION})
    print(f"Upgraded {path.name} instruction block and config from {old} to {VERSION}. Existing decisions, approvals "
          f"and Project Brain files were not changed. Run `reconcile` next.")


def cmd_doctor(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    problems, warnings = [], []
    try:
        cfg = load_config(repo)
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"healthy": False, "problems": [str(exc)]}, indent=2))
        raise SystemExit(1)
    expected = LEAD_FILES[cfg["lead_agent"]]
    text = read_text(repo / expected)
    if MARKER_START not in text or MARKER_END not in text:
        problems.append(f"Missing lead-agent instruction marker in {expected}")
    elif "what_skill.py resume" not in text:
        warnings.append(f"{expected} has the v0.2 instruction block; with the owner's approval run `upgrade --user-confirmed`.")
    for name in ("overview.md", "project-dna.md", "decisions.md", "progress.md", "conversation-memory.md", "next-tasks.md"):
        if not (repo / BRAIN_DIR / name).is_file():
            problems.append(f"Missing {BRAIN_DIR}/{name}")
    if cfg.get("lifecycle") not in LIFECYCLES:
        problems.append("Invalid lifecycle")
    if cfg.get("interview_mode") not in MODES:
        problems.append("Invalid interview mode")
    problems += spend_summary(cfg)["issues"]
    for topic, d in decisions_of(cfg).items():
        if d["status"] == "assumed":
            warnings.append(f"Decision '{topic}' is assumed, not approved.")
    if not git_present(repo) and any(e.get("event") == "checkpoint" for e in read_jsonl(repo / CONFIG_DIR / "events.jsonl")):
        warnings.append("No Git repository although checkpoints exist; offer the owner `git init`.")
    print(json.dumps({"healthy": not problems, "lead_agent": cfg["lead_agent"], "problems": problems, "warnings": warnings}, indent=2))
    if problems:
        raise SystemExit(1)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=f"What Skill {VERSION}: project-scoped mentorship helpers")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init", help="Initialize project memory + lead instructions (never overwrite existing configuration)")
    init.add_argument("--repo", required=True)
    init.add_argument("--agent", choices=tuple(LEAD_FILES), required=True)
    init.add_argument("--mode", choices=MODES, default="beginner")
    init.add_argument("--communication", choices=("plain", "balanced", "technical"), default="plain")
    init.add_argument("--challenge", choices=("light", "adaptive", "demanding"), default="adaptive")
    init.set_defaults(func=cmd_init)
    st = sub.add_parser("status", help="Configuration plus gate, spend and approval summary")
    st.add_argument("--repo", required=True)
    st.add_argument("--reconcile", action="store_true", help="Include stale/conflicting Project Brain items")
    st.set_defaults(func=cmd_status)
    doc = sub.add_parser("doctor", help="Validate project setup; flags unapproved or over-cap spend")
    doc.add_argument("--repo", required=True)
    doc.set_defaults(func=cmd_doctor)
    check = sub.add_parser("checkpoint", help="Record a milestone/event requiring agent review")
    check.add_argument("--repo", required=True)
    check.add_argument("--kind", required=True, choices=CHECKPOINT_KINDS)
    check.add_argument("--summary", required=True)
    check.add_argument("--evidence", default="", help="pre-live: where runs are logged (required)")
    check.add_argument("--plan", default=None, help="Plan file affected; major-change requires a dated Superseded/Updated note")
    check.add_argument("--skills", default="", help="Comma-separated skills actually used for this work")
    check.set_defaults(func=cmd_checkpoint)
    dec = sub.add_parser("decide", help="Record a consequential decision: proposed|approved|rejected|assumed")
    dec.add_argument("--repo", required=True)
    dec.add_argument("--topic", required=True, help="stack, architecture, model-tier, ai-provider, retry-fallback, "
                     "paid-services, data-handling, security, dependencies, ...")
    dec.add_argument("--proposal", default=None)
    dec.add_argument("--source", required=True, help="owner | agent | template | skill:<name>")
    dec.add_argument("--status", choices=DECISION_STATUSES, required=True)
    dec.add_argument("--quote", default="", help="The owner's own words; required for approved")
    dec.add_argument("--rationale", default="")
    dec.add_argument("--cost-estimate", default="")
    dec.set_defaults(func=cmd_decide)
    ch = sub.add_parser("challenge", help="Scan a plan or skill proposal for consequential defaults (exit 3 if any need the owner)")
    ch.add_argument("--repo", required=True)
    ch.add_argument("--file", action="append", default=[])
    ch.add_argument("--text", default="")
    ch.add_argument("--source", default="agent", help="Who proposed it: agent | template | skill:<name>")
    ch.add_argument("--record", action="store_true", help="Record undecided findings as proposed decisions")
    ch.set_defaults(func=cmd_challenge)
    gt = sub.add_parser("gate", help="--implementation: consequential decisions approved? --live: logging + spend approval? (exit 3 if blocked)")
    gt.add_argument("--repo", required=True)
    gt.add_argument("--implementation", action="store_true")
    gt.add_argument("--live", action="store_true")
    gt.add_argument("--approval", default=None, help="Spending approval id for --live")
    gt.add_argument("--expected-cost", type=float, default=None)
    gt.set_defaults(func=cmd_gate)
    aps = sub.add_parser("approve-spend", help="Record the owner's spending approval with a cap")
    aps.add_argument("--repo", required=True)
    aps.add_argument("--scope", required=True)
    aps.add_argument("--cap", type=float, required=True, help="USD")
    aps.add_argument("--quote", required=True)
    aps.set_defaults(func=cmd_approve_spend)
    sp = sub.add_parser("spend", help="Record measured (or estimated) spend against an approval")
    sp.add_argument("--repo", required=True)
    sp.add_argument("--amount", type=float, required=True, help="USD")
    sp.add_argument("--approval", default=None)
    sp.add_argument("--ref", default=None, help="Run log or invoice reference")
    sp.add_argument("--estimated", action="store_true", help="Not provider-measured")
    sp.add_argument("--note", default="")
    sp.set_defaults(func=cmd_spend)
    rec = sub.add_parser("reconcile", help="Read-only: find stale tasks, lifecycle conflicts, lost approvals, plan drift, skill gaps")
    rec.add_argument("--repo", required=True)
    rec.add_argument("--strict", action="store_true", help="Exit 3 when anything is found")
    rec.set_defaults(func=cmd_reconcile)
    res = sub.add_parser("resume", help="Read-only session-recovery brief for a fresh agent session")
    res.add_argument("--repo", required=True)
    res.add_argument("--agent", choices=tuple(LEAD_FILES), default=None, help="The agent running this session")
    res.set_defaults(func=cmd_resume)
    su = sub.add_parser("skill-use", help="Record that a skill was recommended, invoked, completed, rejected or skipped")
    su.add_argument("--repo", required=True)
    su.add_argument("--skill", required=True)
    su.add_argument("--status", choices=SKILL_USE_STATUSES, required=True)
    su.add_argument("--stage", required=True, help="e.g. kickoff, planning, design, build, review, release")
    su.add_argument("--role", default="")
    su.add_argument("--outcome", default="")
    su.add_argument("--reason", default="")
    su.add_argument("--evidence-level", choices=("verified", "reported", "inferred"), default="reported")
    su.add_argument("--evidence", default="")
    su.set_defaults(func=cmd_skill_use)
    up = sub.add_parser("upgrade", help="Refresh a v0.2 project's lead-instruction block (owner approval required)")
    up.add_argument("--repo", required=True)
    up.add_argument("--user-confirmed", action="store_true")
    up.set_defaults(func=cmd_upgrade)
    feed = sub.add_parser("feedback", help="Record project-local skill feedback; never global by default")
    feed.add_argument("--repo", required=True)
    feed.add_argument("--skill", required=True)
    feed.add_argument("--context", required=True)
    feed.add_argument("--rating", type=int, choices=range(1, 6))
    feed.add_argument("--outcome", required=True)
    feed.add_argument("--evidence-level", choices=("verified", "reported", "inferred"), default="reported")
    feed.add_argument("--cause", choices=FEEDBACK_CAUSES, default="unknown")
    feed.add_argument("--feedback", default="")
    feed.add_argument("--dissatisfied", action="store_true", help="Owner disliked the result; flags it for investigation")
    feed.set_defaults(func=cmd_feedback)
    stage = sub.add_parser("lifecycle", help="Explicitly confirm project lifecycle stage")
    stage.add_argument("--repo", required=True)
    stage.add_argument("--status", choices=LIFECYCLES, required=True)
    stage.add_argument("--user-confirmed", action="store_true", help="Use only after direct approval by project owner")
    stage.add_argument("--evidence", default="")
    stage.set_defaults(func=cmd_lifecycle)
    des = sub.add_parser("design", help="Show design readiness; --gate exits 3 if significant visual work isn't approved yet")
    des.add_argument("--repo", required=True)
    des.add_argument("--gate", action="store_true")
    des.add_argument("--surface", default=None, help="Surface name (default: main)")
    des.set_defaults(func=cmd_design)
    drec = sub.add_parser("design-record", help="Record a design discovery/approval/evaluation step")
    drec.add_argument("--repo", required=True)
    drec.add_argument("--step", choices=DESIGN_STEPS, required=True)
    drec.add_argument("--value", default=None, help="depth: light|standard|deep; system-choice: existing|lightweight|custom|none; "
                      "direction-*: the direction's name; reviews: pass|fail")
    drec.add_argument("--summary", required=True, help="What happened; for direction-approved, the owner's confirmation in their words")
    drec.add_argument("--user-confirmed", action="store_true", help="Only for direction-approved, after the owner's explicit approval")
    drec.add_argument("--surface", default=None, help="Surface this direction belongs to (default: main); each keeps its own approval")
    drec.set_defaults(func=cmd_design_record)
    disc = sub.add_parser("discover", help="Scan installed skill metadata; optional unverified public GitHub leads")
    disc.add_argument("--repo", required=True)
    disc.add_argument("--query", required=True)
    disc.add_argument("--root", action="append", default=[], help="Additional directory containing skill folders")
    disc.add_argument("--online", action="store_true", help="Explicitly permit public GitHub repository search")
    disc.add_argument("--limit", type=int, default=8)
    disc.set_defaults(func=cmd_discover)
    return p


def main(argv: list[str] | None = None) -> None:
    try:
        args = parser().parse_args(argv)
        args.func(args)
    except Blocked as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        raise SystemExit(3)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
