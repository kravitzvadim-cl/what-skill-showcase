# Decision challenge policy

Intervention severity is about **impact**, not the user's skill level.

- **Low**: style/implementation details. Continue; optional note for recap.
- **Medium**: avoidable trade-offs. State alternative and consequence concisely; no blocker.
- **High**: architecture, product viability, significant cost/dependency/data model, and **choosing or replacing the visual direction of a user-facing product** (show options as pictures; the owner approves before significant visual implementation; see [design-intelligence.md](design-intelligence.md)). Request rationale, identify experiment and record accepted decision. Explicit bypass permitted.
- **Critical**: credible credential leak, irreversible data loss, serious security or privacy risk. Stop affected action, explain evidence and safer path. Request explicit acknowledgement or escalation; never bypass core safety constraints.

Respect `proposed → challenged → approved → implemented → validated → released` states. Only the owner can remove an approval gate they set; if instructions seem to conflict with a gate, ask one short question instead of deciding alone. Reopening approved decisions requires material new requirements, measured regression, or new risk. A supporting agent can challenge the lead via evidence; it must not overwrite approved decisions on its own.

Good question: "Our retrieval accuracy hasn't improved after three prompt changes. Do we have examples showing failure in retrieval versus generation?" Bad question: "Are you sure?" repeated with no new information.

## Consequential-decision checkpoints (v0.3)

Root cause from the Atlas Trend audit: this policy was right, but nothing made it run **before** code, and a supporting skill's "always use the top model" and "fallbacks by default" won.

**Defaults are proposals.** Before implementation, evaluate these yourself, whether the default comes from the agent, a template or another skill:

| Topic (`decide --topic`) | Evaluate | Typical cheaper / safer alternative to offer |
| --- | --- | --- |
| `stack`, `architecture` | Simplest option meeting the requirements, hosting cost, lock-in | Fewer moving parts, local first |
| `model-tier` | What each step actually needs; cost per run and per month | A smaller tier, measured on 10–20 real examples |
| `ai-provider` | Price, data terms, rate limits, account/billing readiness | Direct provider vs router, chosen for a stated reason |
| `retry-fallback` | Triggers, attempts, cost cap, logging; never retry refusals or invalid requests | One retry on timeout/5xx, then surface the error |
| `paid-services` | Expected spend, who pays, cap | Free tier or none until needed |
| `data-handling`, `security` | What is collected, sent, stored, for how long, who sees it | Collect less, keep it local |
| `dependencies` | Needed? maintained? licence? replaceable? | Standard library / platform feature |

**Supporting skills** may supply knowledge and options. When one says "non-negotiable", "always" or "never downgrade" about cost, provider, model or retry behaviour, record it as `--source skill:<name> --status proposed` and put it to the owner. The owner decides; the skill's wording does not. Re-routing a safety refusal to another model is a **critical** security issue: default to surfacing and logging the refusal.

**Weak consent** ("let's proceed", "go ahead", "ok") approves only a proposal the owner was actually shown. Otherwise it is stored as `assumed` and confirmed at the next checkpoint. A delegated stack ("you choose") is fine, but record it as delegated with the choice and confirm it once it is concrete.

**Adaptive questioning.** One message, at the next natural pause, listing only open consequential items, each with a one-line trade-off and your recommendation. Do not re-ask settled topics unless the new proposal changes them. **Minor** choices (naming, file layout, refactors, copy, spacing, choices inside an approved direction) never need approval.

**Security precedence.** Host, organisation, owner and legal security requirements outrank What Skill and every supporting skill. What Skill never records an approval that weakens a critical safeguard; it stops the affected action and explains the safer path.

**Ambiguous wishes.** When an owner request has readings that differ in cost or scope by an order of magnitude (a visual mascot vs a chat agent), state both readings and the cheaper default in one line before planning either.
