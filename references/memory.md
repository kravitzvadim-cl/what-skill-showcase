# Project memory and global learning

The repository `.project-brain/` is the durable **project** knowledge source. Store concise summaries and decisions, not indiscriminate chat logs. A user-level skill installation stores **behavior** only, never one project's brain. Optional global reusable lessons are outside repos and require opt-in.

Project files:
- `overview.md`: purpose, audience, non-goals, lead agent, lifecycle.
- `project-dna.md`: requirements and priority dimensions; distinguish confirmed and inferred.
- `decisions.md`: user-approved decisions, rationale, date, status, supersession evidence.
- `progress.md`: completed work, verification, obstacles.
- `conversation-memory.md`: useful conversational decisions, preferences, feedback and open threads (not verbatim transcripts).
- `next-tasks.md`: prioritized actionable work.
- `design.md` (visual projects): design-system level, owner taste and references, directions, evaluations, design feedback.
- `.what-skill/events.jsonl`: audit-friendly checkpoint/feedback events; avoid sensitive content.

Before writing: verify active repository, check existing decisions and duplicates, do not change another project's file, prefer small edits, redact or exclude secrets, credentials and personal data, and confirm a disputed fact. Do not infer undocumented history. If transcripts are requested, save them outside Git by default and require explicit consent and a secure location; never implicitly archive full sessions.

Global reusable learnings: opt-in only; use `~/.what-skill/` (private local), add generalized observations without code/content from another project, clearly label reports versus verified results. No automatic cross-project transfer. Allow a user to inspect and reset global entries independently.

Lead agent orchestrates writing and integration. Other agents can propose updates but should not fight over files. Context compaction and sessions may omit content; acknowledge coverage gaps honestly. Git is not a safe secret store.

## Reconciliation, not append-only (v0.3)

Run `reconcile` at session start, task completion, milestones and scope changes (milestone checkpoints print it automatically). It proposes, never applies: open tasks that later progress, checkpoints or commits show as done; lifecycle values that differ between config, `overview.md` and `project-dna.md`, or a lifecycle frozen while milestones pass; design approvals replaced without a recorded change (v0.2 kept one approval slot); decisions still `proposed`/`assumed`; skills recommended but never acted on, invoked without an outcome, or used without a record; plans older than later major changes; unapproved or over-cap spend; missing Git. Fix confirmed items in place (tick or reword tasks, `lifecycle --user-confirmed`, re-record an approval on its own `--surface`, or `design-record --step direction-superseded`). Never delete a valid approved decision to make files agree; when two records conflict, ask the owner which is current.

Lifecycle has one value: `lifecycle --user-confirmed` updates config, `overview.md` and `project-dna.md` together.
