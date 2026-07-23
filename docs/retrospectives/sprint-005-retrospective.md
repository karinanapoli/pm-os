# Sprint 005 — Retrospective

> "A product is never finished. But at some point, it's ready."

---

# Objective

Reflect on Sprint 005: async generation, UX writing audit, status translation, accessibility, and PRDValidator robustness.

---

# What worked very well?

## Role-play testing as a first-time user

Walking through the app as if seeing it for the first time revealed issues that code review never would: "discovery" not translated, "Observações" label outdated, loading text too vague, tour not triggering. This is more effective than any checklist.

## Batch i18n edits

Updating all user-facing strings in a single pass (rather than one-by-one as bugs appear) ensured consistency. Changing "Score" → "Nota" everywhere at once avoided partial migration.

## Small, focused template for progress

The `generate_processing.html` template is self-contained — no changes needed to existing templates. The polling logic is inline JS, not a library dependency. This minimized risk.

---

# What could improve?

## Polling is wasteful

Polling `/generate/status/{task_id}` every 2s works but generates unnecessary HTTP traffic. Server-Sent Events (SSE) or WebSockets would be more efficient. However, polling was simpler to implement and debug.

## Still no integration tests for AI

The PRDValidator got unit tests, but the async generation flow has no automated tests. A test that submits `/generate`, polls `/status`, and verifies `/result` would catch regressions.

## French language support removed

This sprint removed a partially-implemented French locale. If the app targets EU markets, French should be restored. pt-BR + EN is sufficient for Brazil-focused use.

---

# Main Learnings

- AI products must be async-first;
- UX writing is information architecture, not copy;
- i18n bugs are invisible in the fallback language;
- Accessibility is low effort, high impact;
- Role-play testing catches issues that code review misses.

---

# Actions for Sprint 006

- SSE or WebSocket for real-time progress (replace polling);
- Integration test for async generation flow;
- Create Backlog capability (user stories from PRDs);
- Smart OKRs;
- AI Prototyping;
- Export/Import initiatives.
