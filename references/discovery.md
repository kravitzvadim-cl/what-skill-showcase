# Discovery protocol

## Interview design

Start with one sentence reflecting the idea, one strongest ambiguity, and a direct question. Each answer should update the working hypothesis. Ask only questions that can change scope, a critical decision, the next experiment or skill choice. Do not run a rigid quiz. Suggested depths:

| Mode | Target | Aim |
| --- | --- | --- |
| beginner | 4–6 | problem, audience, desired outcome, must-have, constraints, simple success check; plus one taste question if there is a visual interface |
| intermediate | 10–15 | above plus alternatives, edge cases, workflows, data, operational risks, validation |
| expert | 20–30+ | above plus assumptions, failure modes, observability, security, economics, scalability, reversibility |

The question count is a ceiling guideline, not a demand for filler. Ask one question at a time by default. If important information is already in project memory, do not ask it again. Even in beginner mode, surface material security or reliability risks; **simplify language, never lower safety standards**.

## Independent personalization

- `communication_level=plain`: everyday words, tiny examples, explain necessary jargon.
- `balanced`: concise technical terms with one-line clarification when useful.
- `technical`: precise engineering vocabulary, compact trade-offs and evidence.
- `challenge_intensity=light`: only essential challenge/questions.
- `adaptive`: increase scrutiny when confusion/risks recur, lower it during flow.
- `demanding`: examine assumptions and request evidence on consequential decisions, but do not interrupt trivial implementation.

Never infer intelligence from technical vocabulary. Offer to adjust wording after explicit confusion; don't silently relabel the user.

## Project DNA dimensions

Capture a **priority** of `low/medium/high/unknown` with reasoning and evidence for: visual polish, visual expression, content, UX, functionality, AI, data, security, privacy, reliability, integrations, platform constraints, delivery effort. Also capture audience, job-to-be-done, constraints, success signals, non-goals, risks, confirmed decisions, hypotheses, unresolved questions and current lifecycle. Distinguish priorities from objectively measured outcomes.

## Visual interfaces

If the product has a screen, ask one plain taste question during kickoff (liked/disliked apps or sites, a few words for the feel) and record the answer as owner evidence. Never fill in a visual priority by guessing, and never turn the product name into a theme without asking. Full protocol: [design-intelligence.md](design-intelligence.md).

## Decision checkpoint

After sufficient answers, show a short proposed problem statement, user, MVP, exclusions, major risks and success check. Invite correction. Don't write speculative decisions as "approved" before user confirmation. If user wants immediate build, record assumptions explicitly and proceed with a bounded slice.

## Setup without forms; confirm inferences (v0.3)

Setup uses stated defaults plus a one-line override ("I'll use beginner, plain, adaptive and claude as lead unless you say otherwise"); do not open with a multi-question form. When the owner answers only some questions, list the inferred answers by name ("I took 'demo for recruiters' to mean no folders; tell me if not") and record them as assumptions.
