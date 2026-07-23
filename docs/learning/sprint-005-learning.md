# Sprint 005 — Learning

> "UX is not about how things look. It's about how things work when they break — and what the user sees while waiting."

---

# Sprint Objective

Polish the Sprint 004 foundation: eliminate blocking issues, fix l10n gaps, and make the experience accessible and consistent.

---

# Main Learnings

## 1. Async is not optional for AI products

When AI generation takes 5–7 minutes, synchronous requests are not just a performance issue — they're a reliability issue. A single slow model call blocks the entire uvicorn worker. Other users (or the same user in another tab) cannot access the app.

The fix was straightforward: `ThreadPoolExecutor` + progress polling. The effort was small; the impact was large.

## 2. Users don't read error messages — they read error messages that mention things they don't know

"Ollama may be offline" means nothing to a user who doesn't know what Ollama is. "Check your connection or try again" is universally actionable.

The same applies to "Score" vs "Nota" — in pt-BR, "Score" is an anglicism that adds friction. "Nota" is instantly understood.

## 3. The hardest i18n bugs are invisible in English

`{{ init.status|t }}` passing "discovery" as a translation key worked fine in English (the fallback returned the key itself). Only switching to pt-BR revealed the bug. The fix required both adding keys and changing the lookup pattern — a subtle but critical distinction.

## 4. A progress bar is a lie — but a useful one

The 4-step progress bar doesn't track actual model progress (no AI exposes that). It's a fixed timeline animation that advances when each phase completes. But it gives the user the confidence that something is happening, reducing perceived wait time.

## 5. Accessibility features are invisible when working — and painful when missing

The skip-link is never seen by mouse users. The `aria-live` regions are never heard by sighted users. But the absence of these features blocks keyboard-only and screen reader users entirely. The implementation cost was minimal; the cost of not having them is exclusion.

---

# Architecture Evolution

```text
Sprint 004                       Sprint 005
─────────                        ─────────
Sync generation  →    Async ThreadPoolExecutor + polling
No progress bar  →    4-step visible progress bar
Raw status       →    ("status." + status)|t prefix
Long skip-link   →    transform: translateY() full-width
Manual tour      →    Auto-trigger on register
Hardcoded text   →    All strings i18n
PRDValidator fragile →  Retry + fix_json + flatten + ensure_list
```

---

# Technical Debt Remaining

- `_gen_tasks` in-memory — lost on restart, acceptável for single-user;
- No progress tracking for model internals — only phase-based;
- Login page still hardcoded in English (needs session-based lang detection);
- AI clients still have no integration tests (require real API keys).

---

# Conclusion

Sprint 005 addressed the practical pain points of a real user session: slow generation, confusing labels, missing translation, and blocking behavior.

The platform is now production-ready for daily PM use — not because it has more features, but because the existing features work without surprises.
