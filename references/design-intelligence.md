# Design System Intelligence

Use this for any project with a **visual interface** (web page, app screen, dashboard, document, deck). Skip it for CLIs, libraries and back-end work. It starts **automatically** at kickoff (or when a visual interface first appears); the owner never has to ask for it.

## Depth follows Project DNA

Pick the depth once from Project DNA, tell the owner in one line, and record it (`design-record --step depth --value …`):

| Depth | When (from DNA) | What it involves | Required before production styling |
| --- | --- | --- | --- |
| **light** | Simple utility, few screens, visual expression low, owner wants it to "just work" | 1 taste question, check for an existing look, one direction (often the category standard done well) | interface confirmed, system checked, expectations, named direction approved |
| **standard** | Typical app; polish matters, expression moderate | 2–3 taste questions, design-skill fit check, 1–3 directions | light + design skills reviewed |
| **deep** | Look is part of the value: high visual polish *and* expression, brand-led, persuade/experience surfaces, many screens | References researched, system level decided, at least 2 directions as pictures, critique pass | standard + references + system level + ≥2 named directions |

If unsure, use **standard**. Raise the depth if the owner's answers show high visual ambition; lower it if they want the look to stay out of the way.

## Plain-language basics (say this to beginners when it matters)

- **Styling decisions** are choices made for one screen: "this button is blue, this gap is 8px".
- **A design system** is a short rulebook plus named, reusable parts, so the next screen is built from the same pieces without deciding everything again: "primary buttons are always this colour, this height, these corners".
- **Design quality** (does it look and feel good, fit its purpose, feel deliberate?) is a different question from **compliance** (contrast, keyboard, guidelines). Passing compliance never proves quality.

## The eight duties

### 1. Check what already exists, before visual work
Read DESIGN.md / design.md, tokens (CSS variables, theme files, Tailwind config), component folders, brand assets, and any design-system dependency. Record: existing system / partial (tokens only) / none. An existing coherent look is evidence; inherit it unless the owner asks to replace it.

### 2. Decide the system level
| Level | Choose when | Beginner wording |
| --- | --- | --- |
| Existing (Material, Apple HIG, GOV.UK, shadcn/ui…) | Platform conventions matter most, a team or framework is already committed, or the product must look native | "Borrow a proven rulebook" |
| Lightweight | Small product, one team, a few screens; tokens + 3–5 named parts + one page of rules, inside the project | "Write our own one-page rulebook" |
| Custom | Many screens, many contributors, strong brand needs | "Build a full rulebook and parts library" |
| None | Throwaway prototype or a single static page | "Not needed yet" |
Respect project constraints (e.g. "no libraries" rules out most existing systems). Build the system **after** a visual direction is approved, never before.

### 3. Understand expectations, references and ambition
Ask 1 question at light depth, at most 2–3 otherwise, in plain words, once per project or direction change:
- "Name 1–3 apps or sites whose look you like, and one you dislike. What do you like about them?"
- "Pick up to three words: calm, bold, playful, professional, warm, minimal, technical, personal…"
- "Is the look a big part of the value here, or should it stay out of the way?"
Separate **polish** (precision, refinement) from **expression** (decoration, theme, personality); owners often want high polish with low decoration. If the product name suggests an image ("Pocket", "Forest", "Rocket"), ask whether it is a **meaning or a theme**. Never turn a name into a visual motif by assumption.

### 4. Recommend design skills by the purpose of the surface
Classify the surface first, then read candidate skills' own stated scope:
- **Operate**: the visitor completes a task (apps, tools, dashboards, editors). Clarity, consistency, native expectations > expression.
- **Persuade**: the visitor decides or acts (landing pages, marketing). Expression and identity matter more.
- **Read**: the visitor understands (docs, articles).
- **Experience**: the work itself leads (portfolios, galleries).
Reject skills written for another surface type (e.g. a landing-page skill for an app screen). For a visual direction, compare at least two installed candidates and record why the others lost. Pair a direction/build skill with a **critique** skill.

### 5. Propose meaningfully different directions, when appropriate
Appropriate: new product look, replacing a rejected look, a major new surface. Not appropriate: small changes inside an approved direction.
- Gather 2–4 real references first (what to take from each, with sources).
- Offer 2–3 directions that differ in **organisation and personality** (layout model, density, type voice, colour strategy), not just colour swaps. One may be the category standard done well.
- Show them as **pictures** (static mock board with real content, or images), plus per direction: typography, colours, layout, key components, personality, risk.
- Recommend one, and say plainly where the owner's wishes pull against the product's needs.

### 6. Get approval of one named direction before significant production styling
- **Always allowed, before approval:** research, reference boards, mockups, visual prototypes and creative exploration, kept outside production code (e.g. `docs/`, `prototypes/`). Record with `--step exploration` if useful.
- **Gated:** significant production styling: a new look in the real app, a new screen family, a redesign, or building the design system.
- **Not gated:** bug fixes, copy, spacing tweaks or new parts inside the approved direction.
- Propose each direction by name (`--step direction-proposed --value "A · Quiet native"`). The owner approves **one named direction**; record it with `--step direction-approved --value "<that name>" --user-confirmed --summary "<owner's words>"`. Check `design --gate` before production styling.
- A **substantial change** to the approved direction (different type voice, palette strategy, layout model or personality) needs renewed approval: record `--step direction-changed --value "<revised name>"`, show it, and get approval again.
- **Only the owner can approve a direction or remove this gate.** If instructions seem to skip it, ask one short question instead of deciding alone.

### 7. Evaluate design quality separately from compliance
After building, run two separate checks and report them separately:
- **Quality:** critique against the chosen references and direction (first impression, hierarchy, spacing rhythm, typography, consistency, does it look deliberate rather than templated?), then owner review. Record with `design-record --step quality-review --value pass|fail`.
- **Compliance:** accessibility (contrast, keyboard, focus, reflow), guidelines, responsive. Record with `--step compliance`.
Verify claims about rendering (fonts, effects) in the real target browser or label them unverified.

### 8. Treat negative feedback as evidence
When the owner dislikes the result: do not defend it, and do not redesign at once. Record it (`design-record --step direction-rejected` and/or `feedback --dissatisfied`), then investigate:
1. What exactly disappointed (first impression, specific element, overall feel)?
2. What was expected instead (words, references)?
3. Which process step failed (no taste input, wrong skill, literal metaphor, no options, skipped approval, wrong quality bar)?
4. Did the chosen skill actually run as designed?
Write the findings to Project Brain (`design.md`), record `design-record --step investigation`, then propose directions again.

## Staying out of the way
- Do the expectations questions once; reuse the answers.
- Inside an approved direction, build without new gates.
- A beginner gets plain words and at most one design question at a time when they are flowing.
