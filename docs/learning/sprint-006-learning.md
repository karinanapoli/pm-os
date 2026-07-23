# Sprint 006 — Learning

> "The best UI is the one the user doesn't notice — because it was already there when they needed it."

---

# Sprint Objective

Replace the separate progress page with an inline stepper, upgrade the job store to structured steps, and fix the auth bypass so squads work without re-login.

---

# Main Learnings

## 1. Script execution order matters in Jinja2 extends

`base.html`'s `<script>` runs AFTER the child template's `<script>` because Jinja2 renders `{% block content %}` before the parent's closing script tag. This means:
- Child handlers are registered first;
- Parent handlers fire second — including the loading overlay handler;
- `e.preventDefault()` does NOT stop other handlers;
- Fix: `e.stopImmediatePropagation()` — but only after deciding to intercept.

This is not obvious from looking at the template structure. Understanding the rendered HTML output is critical.

## 2. Backward compat is a contract, not an afterthought

Keeping `step`/`message` alongside `steps[]` in the job store meant the old `generate_processing.html` polling JS continued to work without changes. The cost was trivial (2 extra dict keys); the benefit was zero risk of breaking the fallback path.

Every refactor should ask: "What else reads this data?"

## 3. Fragment endpoints are simpler than client-side rendering

The result card uses Jinja2 loops, filters (`|t`, `|markdown`, `|format`), and conditionals. Building this on the client from JSON would require either:
- Duplicating template logic in JS (fragile, out of sync);
- Shipping a template engine to the browser (heavy).

A `?fragment=1` parameter on the result endpoint returns pre-rendered HTML — the simplest possible solution.

## 4. Session cookies disappear on server restart

Starlette's `SessionMiddleware` without `max_age` creates session cookies (deleted when browser closes). Users who rely on `auth_bypass_localhost` lose their session (and their squads) on restart. The fix: auto-populate the session with a user email when bypass is active.

This is a subtle UX issue: the app "works" (no login prompt), but features silently break (squads disappear).

## 5. A fetch interceptor for CSRF is elegant but invisible

The existing `window.fetch` override in `base.html` adds `X-CSRF-Token` to every non-GET fetch. When debugging the failed stepper, the CSRF header was never suspect — and it worked correctly. Good infrastructure is infrastructure you don't think about.

---

# Architecture Evolution

```text
Sprint 005                       Sprint 006
─────────                        ─────────
Separate processing page  →      Inline stepper in generate.html
Flat {step, message}      →      Structured {steps: [{status, detail}]}
401 on restart (squads)   →      Auto-populate session on bypass
No workflow callback      →      on_step in CreatePRDWorkflow
Full page result render   →      ?fragment=1 partial
```

---

# Technical Debt Remaining

- `_gen_tasks` in-memory — lost on restart (acceptable for single-user, but should migrate to SQLite for multi-user);
- Polling at 800ms — functional but wasteful; SSE would be more efficient;
- No integration test for async generation flow (submit → poll → verify);
- Fragment template (`generate_result_fragment.html`) duplicates the result card from `generate.html` — a Jinja2 `{% include %}` or macro would eliminate duplication.

---

# Conclusion

Sprint 006 made the generation flow feel native: the stepper lives inside the page, the progress is granular per step, and every interaction works with or without JavaScript. The auth bypass fix eliminates a silent UX regression.

The platform continues to be production-ready for daily PM use, now with a smoother generation experience.
