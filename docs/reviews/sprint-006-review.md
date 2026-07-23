# Sprint 006 Review

> "The stepper should live inside the page, not on a separate screen — progressive enhancement, not page replacement."

---

# Sprint Objective

Replace the separate `generate_processing.html` progress page with an inline stepper rendered inside `generate.html` via JS fetch + polling, while keeping full backward compatibility for non-JS fallback.

---

# Stories Delivered

## ✅ Story 1 — Inline Async Stepper

### Objective

The user should see the generation progress inside the same page, not on a separate `/generate_processing` screen. The form should disappear and a vertical stepper with 4 steps + progress bar should take its place.

### Deliverables

- `POST /generate` now checks `X-Requested-With: fetch` header — returns `{"job_id": "..."}` for JS, `generate_processing.html` for fallback;
- `generate.html` gains a hidden `<div id="genStepper">` with 4-step stepper (rendered server-side via Jinja2 loop), shown/hidden by JS;
- JS intercepts form submit → `fetch POST /generate` → polls `GET /generate/status/{job_id}` every 800ms → updates step status + progress bar + detail text;
- On completion: `fetch GET /generate/result/{job_id}?fragment=1` → injects HTML fragment inline;
- Fragment endpoint: `?fragment=1` returns `generate_result_fragment.html` partial (no `base.html` wrapper);
- Error state shows error card inline with retry link;
- `e.stopImmediatePropagation()` prevents `base.html`'s loading overlay from colliding with the stepper (script ordering issue).

---

## ✅ Story 2 — Structured Job Store

### Objective

The flat `{step, message}` job store should be upgraded to a structured `{steps: [{status, detail}]}` array so the frontend can display per-step status independently.

### Deliverables

- `_gen_tasks` entries now include `steps: [{status, detail}, ...]` (4 steps: context, draft, refine, validate);
- `_set_step(step_idx, status, detail)` helper updates both `steps[i]` AND backward-compat `step`/`message` fields;
- `GET /generate/status` returns both `steps[]` and `step`/`message` — both old and new clients work;
- Steps array initialized as all `pending`; transitions: `pending → active → done` (or `error` on failure);
- Progress bar computed: each done step = 25%, active step = +12.5%.

---

## ✅ Story 3 — Auth Bypass Session Populate

### Objective

`auth_bypass_localhost` should auto-populate `user_email` in the session so the sidebar squads section works without requiring explicit login after server restart.

### Deliverables

- `_AuthMiddleware` now sets `session["user_email"]` and `session["authenticated"]` when bypass is active;
- First user from config is used (or `"local@localhost"` if no users exist);
- Squad sidebar section renders correctly without login.

---

## ✅ Story 4 — Progress Callback in CreatePRDWorkflow

### Objective

`CreatePRDWorkflow` should expose an `on_step` callback so any caller (CLI, scripts, future UIs) can track progress without coupling to the web layer.

### Deliverables

- `on_step: Optional[Callable[[str, str, str], None]]` parameter added to `__init__`;
- `_on_step(step_id, status, detail)` helper calls callback + preserves existing `self.logger.info()` calls;
- Called at 4 key points: context loading, prompt building, AI generation, validation.

---

## ✅ Story 5 — Backward Compatibility

### Objective

All existing functionality must continue working without changes. Non-JS users, existing tests, and the old `generate_processing.html` template must remain functional.

### Deliverables

- `generate_processing.html` unchanged — still rendered when `X-Requested-With` header is not `fetch`;
- Status endpoint returns `steps` + `step`/`message` — old polling JS reads `data.step` as before;
- `GET /generate/result` without `?fragment=1` renders full page as before;
- 151 tests pass (zero regressions).

---

# Sprint Result

By the end of Sprint 006:

- **Inline stepper** — generation progress shown inside the same page, not a separate screen;
- **4-step structured progress** — each step has independent status + detail;
- **Progressive enhancement** — works with and without JavaScript;
- **No session loss** — `auth_bypass_localhost` keeps squads working across restarts;
- **`on_step` callback** — `CreatePRDWorkflow` can report progress to any caller;
- **151 tests passing** — zero regressions;
- **Zero new dependencies** — all changes use vanilla JS and existing Jinja2 infrastructure.

---

# Main Architectural Decisions

- **Progress client-side, not server-sent**: Polling (800ms interval) instead of SSE/WebSocket — simpler, no infra change, sufficient for 10–60s generation cycles;
- **Fragment endpoint instead of JSON**: `GET /generate/result?fragment=1` returns pre-rendered HTML instead of JSON — avoids duplicating Jinja2 template logic in JS;
- **Backward compat fields in job store**: `step`/`message` kept alongside `steps[]` — old polling page works without changes;
- **`stopImmediatePropagation()`**: Solves a subtle script-ordering issue where `base.html`'s submit handler fires after `generate.html`'s handler and re-shows the loading overlay.

---

# Next Sprint

- Create Backlog (user stories from PRDs);
- Smart OKRs;
- AI Prototyping;
- Security Score;
- Metrics Integration;
- Export/Import initiatives.
