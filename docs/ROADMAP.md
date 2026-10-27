# Roadmap and acceptance gates

## v0.1 — portable foundation (this release)

- [x] Agent Skills-compatible root `SKILL.md` and focused reference files.
- [x] Codex/Claude/Gemini lead-agent selection and additive instruction setup.
- [x] Isolated Project Brain scaffold and user-adjustable interview/language/challenge config.
- [x] Checkpoint/skill feedback records and explicit release confirmation command.
- [x] Local skill metadata discovery; optional explicitly requested, unverified public GitHub repo leads.
- [x] Standard-library unit tests; CI workflow.
- [ ] Real use inside Codex, Claude Code and Gemini with each host version (not yet tested).

## v0.2 — Design System Intelligence (from the Pocket Tasks trial)

- [x] `references/design-intelligence.md`: existing-system check, system level, owner taste/references, surface-appropriate design skills, directions, approval gate, quality vs compliance, negative-feedback investigation.
- [x] `design` / `design-record` helper commands; `.project-brain/design.md` template; split visual polish/expression in Project DNA.
- [x] `feedback --dissatisfied` and `cause=process`; additive, backward-compatible config.
- [x] Exploration always allowed; adaptive depth (light/standard/deep) from Project DNA; approval names one direction with the owner's confirmation; substantial change needs renewed approval.
- [x] Tests: design discovery and approval happen before visual implementation.
- [ ] Verify in a fresh project that the agent asks taste questions and shows directions before building UI.

## v0.2.x — first real beginner trial (continued)

- [ ] Install user skill in chosen agent and verify discovery.
- [ ] Run beginner interview on a simple small project; capture only 4–6 useful questions.
- [ ] Verify Project DNA, selective skill recommendation and persistent memory after a new session.
- [ ] Verify approved decision survives session restart and existing repo files are preserved.
- [ ] Collect explicit user feedback and refine instructions.

## v0.3 — reliable mentorship (from the Atlas Trend audit)

- [x] Consequential-decision checkpoints: `challenge`, `decide` (owner quote, weak consent → assumed, skill source), `gate --implementation`.
- [x] Live-AI observability (`checkpoint --kind pre-live`), spend approvals vs measured spend (`approve-spend`, `spend`, `gate --live`, doctor flags).
- [x] Project Brain reconciliation (`reconcile`), lifecycle sync, per-surface design approvals, plan-drift checkpoint, Git offer.
- [x] Recorded skill usage and outcomes (`skill-use`, `checkpoint --skills`); lifecycle skill map.
- [x] Session recovery (`resume`) and `upgrade` for v0.2 projects.
- [x] Scenario tests A/B/C plus fresh-session behavioural evals (see docs/V0.3-EVALS.md).
- [ ] Verify on a real new project end to end (not only fixtures), across a real session boundary and a second host.

## v0.4 — host-native checkpoints

- [ ] Investigate, document and test supported safe hooks per host (opt-in, no destructive injection).
- [ ] Add idempotent resume/compaction checkpoint helpers.
- [ ] Add formal user-approved lead-agent handoff protocol.
- [ ] Add safe migration and doctor repair assistance.

## v0.4 — trusted discovery and evidence

- [ ] Verified `SKILL.md` discovery from public catalogs with provenance and freshness.
- [ ] Security/compatibility review of external candidate instructions and scripts.
- [ ] Context-specific ranking with transparent weights and uncertainty labels.
- [ ] Human-verified feedback attribution and opt-in sanitized global lessons.

## Release criteria before declaring production quality

1. Three host compatibility smoke tests in live installations.
2. Memory continuity verified across two sessions without chat persistence.
3. No overwriting of existing lead instructions; no project memory cross-contamination.
4. Critical risk challenges and post-release quiet mode behave as designed.
5. Discovered external skills never installed/executed without approval.
