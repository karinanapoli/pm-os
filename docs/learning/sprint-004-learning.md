# Sprint 004 — Learning

> "A tool only becomes a platform when it supports the full workflow, not just one task."

---

# Sprint Objective

Evolve PM Studio from a documentation tool into a complete Product Manager workspace by adding multi-provider AI, authentication, product docs, roadmap, and actionable validation.

---

# Main Learnings

## 1. Products are used daily, tools are used occasionally

PM Studio started as a PRD generator — something you open once per initiative. To become a daily workspace, it needed to cover the full PM workflow: planning, documentation, validation, research, and governance.

The timeline/roadmap feature is the visual representation of this vision — showing users not just what the tool does today, but where it's going.

---

## 2. Authentication must be invisible to the primary user

Adding auth to a local-first tool is risky — if you lock yourself out, the tool becomes unusable.

The localhost bypass solved this: anyone on the machine itself never needs credentials. Only remote access requires login. This makes auth safe to enable without fear of getting stuck.

---

## 3. Multi-provider AI is relatively cheap to add when architecture is right

Because Sprint 003 had already abstracted AI behind a Protocol, adding OpenAI and Anthropic was straightforward — each new provider was just a class implementing `generate(prompt) -> str`.

The real effort was in the UI (provider selector, API key fields, conditional form display) and config persistence, not in the AI integration itself.

This validated the architectural decision from Sprint 003.

---

## 4. Validation is only useful if it prescribes next steps

The original validation showed scores and issues — informative but not actionable.

Adding `rationale` (why this score) and `action_items` (what to do next) transformed validation from a report into a checklist. Users can now check off actions as they complete them, turning validation into an execution tool.

---

## 5. Version history builds trust

Knowing that every PRD generation saves the previous version gives users confidence to iterate. They can experiment without fear of losing work.

The same applies to validation reports — versioning both together means a user can always trace back what changed between iterations.

---

## 6. Sidebar labels are information architecture

Renaming "Discovery" → "Overview", "Consult" → "Q&A", and restructuring sections into Overview / Create / Workspace / System made the sidebar match how PMs think about their work: first see the big picture, then create something, then work with existing content, then manage settings.

The old "Discovery" label was ambiguous — it meant nothing specific to a new user.

---

## 7. Documentation naming matters for discoverability

Renaming "Product Documentation" to "Supplementary Documentation" made the purpose clearer: this is extra context that supplements initiative-specific docs. The old name implied it was the primary documentation source, which caused confusion.

---

## 8. A roadmap inside the product builds confidence

The `/timeline` page serves two purposes:
- Shows users what exists today;
- Shows them what's coming — building anticipation and trust that the product is actively evolving.

The spoiler section adds a human touch, hinting at future capabilities without over-promising.

---

# Architecture Evolution

Sprint 004 added the following layers to the platform:

```text
Sprint 003                       Sprint 004
─────────                        ─────────
Ollama only    →    Ollama + OpenAI + Anthropic
No auth        →    Optional auth with login page
No product docs →   Product Documentation Hub
No roadmap     →    Interactive Timeline page
Basic validation →  Validation with diff + actions
No versioning  →    PRD + validation version history
```

---

# Technical Debt Identified

- No database — everything is file-based, which won't scale for multi-user;
- No user management — current auth is single-password shared access;
- No audit trail — who generated what is not tracked;
- No tests for the new AI clients (OpenAI, Anthropic) — they require real API keys;
- Login page is hardcoded in English (acceptable since language preference isn't known pre-auth);
- Session secret is hardcoded in dev (`pm-studio-dev-secret`).

---

# Conclusion

Sprint 004 transformed PM Studio into a platform that Product Managers can use daily.

The addition of multiple AI providers, authentication, product docs, roadmap, and actionable validation moved the tool beyond "PRD generator" into "PM workspace."

The architectural foundation from Sprint 003 proved flexible enough to absorb these new capabilities without structural changes — validating the investment in clean architecture.
