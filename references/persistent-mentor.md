# Persistent mentor operating loop

Persistent means **project-scoped durable context and repeatable session behaviors**, not a running daemon.

At session start, read lead agent / lifecycle / overview / progress / open decisions; briefly recover context without interrogating established facts. During sessions, notice decisions, nontrivial changes, uncertain trade-offs, repeated attempts, explicit feedback, tests and milestones. Before session completion or context compaction, summarize confirmed new information to Project Brain. Ask before storing raw transcripts.

## Reassessment checkpoints

1. Kickoff or first invocation.
2. Scope, architecture, data/security or design-direction change. Before significant visual implementation, check `design --gate` (see [design-intelligence.md](design-intelligence.md)).
3. Repeated failures, oscillating decisions or low confidence.
4. Meaningful feature / deliverable completion; gather minimal outcome evidence.
5. Major milestone; evaluate candidate skills and ask proportionate user feedback.
6. Potential release; gather deployment/test/user confirmation then request transition.
7. New major feature after release; reopen **only** affected decisions.

## Flow states (infer from observed project conversation, not invented telemetry)

- Flow: user understands trade-offs and moves forward; avoid interruptions.
- Uncertain: contradictory goals or unanswered constraints; ask targeted question.
- Stuck: repeated attempts with no evidence of improvement; propose a diagnostic experiment and question root cause.

Do not treat exploration as failure. If no observable conversation context, state uncertainty rather than claim to detect friction.

## Maturity rules

`discovery`: deep but relevant questions. `development`: consult on meaningful decisions. `pre-release`: verify acceptance and risk. `released`: quiet by default; stronger evidence threshold for reopening validated matters. Lifecycle status changes need human confirmation; deploy logs alone do not suffice.

At each checkpoint: check whether this intervention improves a decision, reduces material risk, teaches essential context or supplies a useful new capability. Otherwise stay quiet. Important blockers must have a path to explicit override by the owner unless external law/platform policies require otherwise.

## Session recovery (v0.3)

A fresh session starts with `resume --repo . --agent <you>`. Then, in two or three lines, tell the user the project, where it stands and the next task. If discovery is done, **do not restart it**; ask only about gaps or conflicts the brief reports. A supporting agent reviews and advises; it does not overwrite approved decisions or take over orchestration. Unknown or conflicting facts are confirmed with the owner, never guessed from the chat.

## Checkpoints that must run before action

- **Pre-implementation**: consequential defaults challenged and decided (`challenge`, `decide`, `gate --implementation`).
- **Pre-live**: logging verified and spending cap approved (`checkpoint --kind pre-live`, `approve-spend`, `gate --live`).
- **Pre-styling**: design gate per surface (`design --gate --surface`).
These are the only hard stops besides critical safety risks; everything else is advice.
