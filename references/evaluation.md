# Hybrid skill performance evaluation

Assess a recommendation **after a meaningful task or milestone**, or immediately when the user dislikes the result. Compare intended outcome versus observed outcome. Tests passing do not imply good visual quality; nice-looking output does not imply secure code. For visual work, report **design quality** (critique against references and direction, then owner review) separately from **compliance** (accessibility, guidelines); a compliance pass is never presented as a quality result.

Evidence levels:
- `verified`: instrumented test, measured metric, reviewed artifact or traceable user acceptance.
- `reported`: user's subjective experience or second-hand account.
- `inferred`: agent hypothesis, explicitly marked as such.

Use project context before drawing conclusions. Ask focused diagnostics: what disappointed you, what outcome was expected, was the prompt adequate, and was the skill executed? One bad application is not a permanent global ban. If the skill did not actually run, label this as recommendation quality feedback, not execution performance.

Negative feedback is evidence: record it (`feedback --dissatisfied`, or `design-record --step direction-rejected` for a rejected look), investigate before changing anything, and write what was learned to Project Brain.

Capture skill source/ref, task, context, expected value, evidence, user satisfaction (optional 1–5), failure causes `skill-fit|prompt|implementation|requirements|process|unknown`, and next experiment. In global learning share only user-approved, non-sensitive generalized patterns; no raw project names, secrets, prompts, screenshots or transcripts.

Minimize interruptions. Record objective evidence silently where available, request user review after consequential artifacts, and don't ask on every minor code edit.

## Observability before live AI runs (v0.3)

Before the first live or paid run, check that **every** paid code path (including small helper endpoints) persists inputs, outputs, model, cost and errors in an evaluable form, and that each known top risk has a measurable signal in those logs. Ask: "If this run fails, will we know why without re-running?" Record `checkpoint --kind pre-live --evidence <log location>`; repeat it when a new paid path is added. Keep the logs the conclusions rely on, or record where they live if they are git-ignored.

Spending: the owner sets a cap in their words (`approve-spend`); check `gate --live --approval S#` before running; record provider-measured cost (`spend --ref <log>`), marking estimates as `--estimated`. Report measured totals against the cap; never invent a cost that the provider did not report.

## Evidence validity

Before citing a screenshot, log or test as evidence, open it and confirm it shows what you claim (size, content, not blank, not mid-animation). Prefer an independent reviewer with no shared context for "is this done" judgements on visual or consequential work, and record the reviewer's outcome with `skill-use`.
