# Host adaptation and authority

The user chooses one lead coding agent per project. What Skill adapts to the lead agent's native instructions and capability limits. Durable truth lives in the project repository, **not** in a proprietary session or a separate agent's instructions. Authority: user > lead agent coordination > supporting agent suggestions.

Codex: use `AGENTS.md` for session-start and checkpoint expectations. User-level skill convention: `~/.agents/skills/what-skill`; test actual recognition in the installed Codex version. Do not imply `AGENTS.md` guarantees a background process.

Claude Code: use `CLAUDE.md` and `~/.claude/skills/what-skill`; optional supported hooks can improve session/checkpoint coverage, but should be added only after reviewing current docs and obtaining consent. Do not silently overwrite existing hooks.

Gemini CLI: use `GEMINI.md` and `~/.gemini/skills/what-skill` (some versions also support `.agents/skills` alias). Confirm commands with actual local version before assuming behavior.

`init` only appends a small, marked block to the selected lead's instructions. Other agents should **read and respect** `.what-skill/config.json` and Project Brain if they are asked to review the repo; do not inject lead authority into their instructions.

Lead transfer requires explicit user request. Summarize approved decisions, current progress, outstanding risks and open tasks; change config and host instruction blocks only with permission. Old host instructions should not remain active as independent leadership rules; cleanup is a follow-up action.

Native agent tools and hooks vary by host and version. A repository instruction is **guidance**, not enforceable always-on execution. Report any missing coverage honestly. No silent automatic cross-provider session capture.
