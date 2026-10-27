# Beginner-mode trial — run AFTER installing What Skill

**Project:** A small local Reading List application. Users can add a book/article title, mark an item as read, and filter to unread items. No login, remote APIs, external database, or deployment required for the first iteration.

## Trial protocol

1. Create an empty `reading-list-demo` repo; install What Skill as a user skill in **one** chosen agent.
2. Initialize with `--mode beginner --communication plain --challenge adaptive` and choose the host's `--agent` value.
3. Prompt the agent: "Use What Skill. I'm new to app development. I want a reading list app. Interview me one question at a time before planning." Do not pre-fill answers for the user.
4. Expect approximately 4–6 plain-language questions about user, problem, must-have, platform, and what success looks like; challenge any unclear scope without jargon.
5. Verify the agent updates Project Brain, explicitly labels assumptions, proposes minimal architecture, and recommends only skills clearly useful for the current task.
6. Close and reopen a **new agent session**. Ask: "What did we decide about data storage?" Confirm it reads Project Brain instead of guessing.
7. Tell the agent "I don't like the design." Confirm it asks a targeted diagnostic question and records the feedback without globally blacklisting a skill.
8. Record a milestone. Confirm that a completed milestone triggers a focused review rather than an unnecessary new interview.
9. If you reach a working local release and explicitly confirm it, change the lifecycle. Verify the mentor becomes quieter.

## Pass/fail criteria

- Correct lead agent and project paths, with no overwrites.
- Interview language and question depth appropriate for a beginner.
- A coherent minimum project plan and contextual skill recommendations with real source evidence.
- Reliable new-session recovery from committed Project Brain, not old chat.
- Honest distinction between automated checks and user preference; negative-feedback response is helpful.
- No autonomous external skill execution or overclaiming cross-session monitoring.

Do not report the above as passed until it has actually been exercised in a coding-agent environment. This document is a test plan, not a test report.
