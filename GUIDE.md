# What Skill

**A persistent, project-aware mentor and skill advisor for coding agents.**

What Skill starts with a project idea and helps you define a good product, challenge assumptions, choose useful agent skills, record decisions, and revisit recommendations as the project changes. It adapts its language and pressure to your experience, project friction and lifecycle. It is meant to support **Codex, Claude Code or Gemini CLI**, with **one chosen lead agent** per repository.

> **Status: v0.3 / alpha.** v0.3 adds consequential-decision checkpoints (`challenge`, `decide`, `gate --implementation`), live-AI observability and spend tracking (`checkpoint --kind pre-live`, `approve-spend`, `spend`, `gate --live`), Project Brain reconciliation (`reconcile`), session recovery (`resume`), recorded skill usage (`skill-use`), per-surface design approvals (`--surface`) and `upgrade` for v0.2 projects. v0.2 projects keep working unchanged.
>
> **v0.2 status (kept for history):** v0.2 adds Design System Intelligence for projects with a visual interface (see below). This package provides a real portable `SKILL.md`, project-memory scaffold, native lead-agent instruction setup, checkpoint logs, a local skill metadata inventory, and optional **unverified** GitHub repository leads. Full automatic conversation capture, catalog verification, proactive event hooks, global evidence aggregation and independent multi-agent reviews are **planned, not implemented**. No daemon or background monitoring is included.

## Install as a user-level skill

The public showcase source is `https://github.com/kravitzvadim-cl/what-skill-showcase-showcase`. This repository is public and available. You can replace the URL with a local clone path while developing.

### Codex (macOS/Linux)

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/kravitzvadim-cl/what-skill-showcase-showcase.git ~/.agents/skills/what-skill
```

Restart/reload your agent if the new skill is not discovered. Ask: **"Use what-skill to plan this project"**. You can also explicitly request the skill by name in environments that support it.

### Claude Code

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/kravitzvadim-cl/what-skill-showcase-showcase.git ~/.claude/skills/what-skill
```

If already cloned for Codex, you can link the same source instead of cloning again:

```bash
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/what-skill ~/.claude/skills/what-skill
```

### Gemini CLI

```bash
mkdir -p ~/.gemini/skills
git clone https://github.com/kravitzvadim-cl/what-skill-showcase-showcase.git ~/.gemini/skills/what-skill
```

Gemini CLI also supports skill linking/discovery in some versions; verify using `/skills list`. These installation conventions can evolve with your installed host version.

**Avoid cloning onto an existing folder.** Update an existing clone with `git -C <installation-path> pull --ff-only`, after reviewing changes. Do not automatically trust later upstream updates.

## Initialize one project

Start with a real repository (the sample below chooses Codex as its lead):

```bash
python3 ~/.agents/skills/what-skill/scripts/what_skill.py init \
  --repo /absolute/path/to/my-project \
  --agent codex \
  --mode beginner \
  --communication plain \
  --challenge adaptive
```

For Claude and Gemini, point to the installed script in the relevant skills folder and use `--agent claude` or `--agent gemini`.

This creates `.what-skill/config.json`, initial `.project-brain/` documents and an additive What Skill block in the **lead agent's** `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`. Existing repository files are preserved. Once a repository is initialized, simply ask your lead agent to resume the What Skill interview or review the current milestone. The project files carry knowledge across sessions; the skill's copy is shared behavior, not shared project memory.

### Inspect state and checkpoints

From the skill directory:

```bash
python3 scripts/what_skill.py status --repo /path/to/my-project
python3 scripts/what_skill.py doctor --repo /path/to/my-project
python3 scripts/what_skill.py checkpoint --repo /path/to/my-project \
  --kind milestone --summary "First usable screen completed" \
  --evidence "Manually tested on a phone"
```

A checkpoint records an event. It does **not** autonomously summon your agent; ask the active agent to handle it or connect a supported host hook in a later integration.

### Find candidate skills

```bash
python3 scripts/what_skill.py discover --repo /path/to/my-project \
  --query "visual UI typography"
```

Opt in to public GitHub *repository leads* with `--online` (requires network access). These results are **not verified skills**. A coding agent must inspect the actual `SKILL.md` and safety implications before recommending or installing them.

### Record feedback

```bash
python3 scripts/what_skill.py feedback --repo /path/to/my-project \
  --skill example-ui-skill --context "mobile dashboard layout" \
  --rating 2 --outcome "Looks generic" \
  --evidence-level reported --cause skill-fit \
  --feedback "Doesn't fit the intended visual direction"
```

Feedback stays in the project; it isn't automatically transferred to other repositories. Don't include secrets or personal information in commit-tracked logs.

### Change lifecycle only with confirmation

```bash
python3 scripts/what_skill.py lifecycle --repo /path/to/my-project \
  --status released --user-confirmed --evidence "Owner confirmed live deployment"
```

The flag records that the human *already confirmed* the change; it isn't permission for an agent to self-approve. Released projects get quieter guidance while new high-impact features can reopen relevant questions.

### Design discovery and approval (visual interfaces)

```bash
python3 scripts/what_skill.py design --repo /path/to/my-project            # what's done, what's missing
python3 scripts/what_skill.py design-record --repo /path/to/my-project \
  --step expectations --summary "Likes Things 3 and Linear; wants calm and professional"
python3 scripts/what_skill.py design-record --repo /path/to/my-project \
  --step direction-approved --value "A · Quiet native" --user-confirmed --summary "Owner: go with A"
python3 scripts/what_skill.py design --repo /path/to/my-project --gate     # exit 3 = not ready for big visual work
```

Steps: `ui-yes|ui-no`, `depth --value light|standard|deep`, `system-check`, `system-choice --value existing|lightweight|custom|none`, `expectations`, `skills`, `references`, `exploration`, `direction-proposed --value NAME`, `direction-approved --value NAME --user-confirmed`, `direction-changed --value NAME`, `direction-rejected`, `investigation`, `quality-review --value pass|fail`, `compliance --value pass|fail`. Research, mockups and prototypes are always allowed. The gate covers significant production styling and opens when the steps required at the chosen depth are done and the owner has approved one **named** direction (stored with their confirmation). A substantial change (`direction-changed`) needs renewed approval. A rejected direction must be investigated before a new one can be approved. Small changes inside an approved direction don't need the gate. Like every helper, this records evidence for the agent; it is not runtime enforcement.

### v0.3: decisions, live runs, memory and recovery

```bash
W=scripts/what_skill.py; R=/path/to/my-project
python3 $W resume --repo $R --agent claude                     # fresh session: where are we?
python3 $W challenge --repo $R --file plan.md --source agent   # exit 3 = consequential items need the owner
python3 $W decide --repo $R --topic model-tier --proposal "Haiku for all steps" \
  --source owner --status approved --quote "use only Haiku"
python3 $W gate --repo $R --implementation                     # exit 3 until stack/AI/cost topics are approved
python3 $W checkpoint --repo $R --kind pre-live --summary "first run" --evidence "docs/runs/*.ndjson"
python3 $W approve-spend --repo $R --scope "5 test searches" --cap 0.25 --quote "up to 25 cents"
python3 $W gate --repo $R --live --approval S1
python3 $W spend --repo $R --amount 0.106 --approval S1 --ref docs/runs/x.ndjson
python3 $W skill-use --repo $R --skill animate --status completed --stage build --outcome "curves + reduced motion"
python3 $W reconcile --repo $R                                 # read-only: stale tasks, lifecycle, approvals, plans
python3 $W upgrade --repo $R --user-confirmed                  # v0.2 project: refresh the instruction block only
```

## Source files

```text
what-skill/
├── SKILL.md                   # Main portable skill
├── references/               # Detailed policies, read on demand
├── templates/                # Structured project artifacts
├── scripts/what_skill.py     # Conservative Python helper
├── tests/                    # Unit tests (stdlib)
├── docs/                     # Architecture, limitations, trial plan
└── .github/workflows/        # CI validation
```

## Key principles

- **Project scoped:** one project's decisions and conversation summaries never merge into another.
- **Lead-agent aware:** human is final authority; Codex/Claude/Gemini can lead; peers advise.
- **Evidence over hype:** judge skills by current project fit, not only Github stars.
- **Challenge with judgment:** ask more when the user is stuck, less when in flow; after release, intervene sparingly.
- **Accessible language:** communication simplicity and depth of questioning are independent.
- **User control:** never install or execute untrusted third-party skill code without inspection and approval.
- **Transparency:** local inventory is not a verified endorsement; no automatic cross-session/cross-provider transcript access.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 scripts/what_skill.py --help
```

## Roadmap and trial

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md). After installation, follow [docs/BEGINNER-TRIAL.md](docs/BEGINNER-TRIAL.md) for a small **Reading List** sample project. The trial is **not claimed as executed** by this repository.

## Licensing

MIT; see [LICENSE](LICENSE).

## References

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex skill catalog](https://github.com/openai/skills)
- [Claude Code skills documentation](https://code.claude.com/docs/en/skills)
- [Gemini CLI skills documentation](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md)
