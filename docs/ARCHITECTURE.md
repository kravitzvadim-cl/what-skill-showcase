# Architecture — alpha

## What exists

```
User -> Chosen lead agent -> What Skill instructions
                               |           |
                         Project Brain  Candidate skill inventory
                               |           |
                         checkpoint     local SKILL.md inspection
                               |           |
                         evaluation      optional GitHub leads
                               \         /
                            recommendations
```

`SKILL.md` drives behavior. The Python helper initializes files, records events, inventories **local skill metadata**, and retrieves optional GitHub repo leads, but it is not an AI, orchestration runtime, or background service. The lead agent reasons about the project using that evidence and repository instructions.

## Durable data

- `.what-skill/config.json`: selected lead agent, mode, language, lifecycle, conservative permissions, and (v0.2) a `design` block with discovery/approval/evaluation state. Configs without it get safe defaults.
- `.what-skill/events.jsonl`: observed checkpoints and explicit lifecycle transitions.
- (v0.3) `config.json` also holds `decisions` (topic → proposal, status, source, owner quote, history), `required_topics`, `uses_ai`, `spend` (approvals with caps, measured/estimated entries), `observability` (pre-live logging evidence), `plans`, and `design.surfaces` (per-surface direction approvals; top-level fields stay the `main` surface). All are optional on read, so v0.2 configs work unchanged and v0.2 can still read v0.3 configs.
- `.what-skill/skill-history.jsonl`: project-local reported/verified/inferred outcome feedback.
- `.project-brain/*.md`: concise, user-reviewable project context and decisions.

Full transcripts are **off by default**; if added later they must remain out of Git unless explicitly requested with informed consent. No background cross-host transcript capture exists. The shared user installation of What Skill does not contain project-specific memory.

## Host integration boundaries

`init` adds a marked instruction block to only the chosen lead agent's file, preserving pre-existing instructions. It does not install hooks or enforce that an agent reads any particular file. Actual skill discovery and hook support vary by host/version. The selected lead agent owns orchestration; supporting agents can review but must not override approved decisions. Switching lead requires a user-approved handoff, not yet a CLI feature.

## Behavioral contract

1. At project kickoff, interview proportionally to selected mode and produce confirmed vs assumed requirements.
2. After meaningful decisions/conversations, actively update Project Brain based on accessible evidence.
3. At milestones or repeated friction, review affected project dimensions and skill suitability.
4. Recommend local or vetted external skills with evidence, clearly showing what was inspected.
5. Combine outcome evidence with user feedback, without automatically generalizing a single failure.
6. For release, request explicit confirmation; after release, reduce interruptions and avoid reopening settled issues without new evidence.
7. For visual interfaces, run design discovery (existing system, owner taste, surface-appropriate skills, directions) and get owner approval before significant visual implementation; evaluate design quality separately from compliance; investigate negative feedback before redesigning. The `design` gate is advisory data for the agent, not runtime enforcement.

## Threat model and guardrails

A third-party skill is untrusted code/instructions and may contain prompt injection or malicious install steps. Candidate retrieval must not be treated as authorization. By default only inspect text; ask approval before executing scripts, mutating security settings or sending data externally. Git repo files can leak credentials; use placeholders and redact real sensitive values. Repository instructions are not a sandbox or an execution policy. Real enforcement must come from runtime permissions and code review.

## Open limitations

- No event-driven automatic invocation; relies on agent project instructions and manual checkpoint/skill use.
- No auto conversation capture or observation of other agent sessions.
- No actual global learning aggregation; project-local feedback logs exist as data foundation.
- No verified external catalog scorer yet: `--online` returns only repository leads, not skill endorsements.
- No automated skill execution outcome attribution or verified ranking across agents.
- No automated lead handoff, formal hook templates, UI, or deployed service.

These are deliberate alpha boundaries, not hidden features.
