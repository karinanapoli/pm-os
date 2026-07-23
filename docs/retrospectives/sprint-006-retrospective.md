# Sprint 006 — Retrospective

> "A feature is not done until the old way still works."

---

# Objective

Reflect on Sprint 006: inline async stepper, structured job store, auth bypass fix, and workflow progress callback.

---

# What worked very well?

## The fragment endpoint pattern

Adding `?fragment=1` to the result endpoint was the right call. It avoided duplicating the complex Jinja2 result template in JavaScript and kept the rendering logic in one place. The fragment template is a copy of the result block — not ideal, but pragmatic.

## Backward compat from day one

Designing the job store upgrade to keep `step`/`message` alongside `steps[]` meant the old `generate_processing.html` never broke. The fallback path was tested by simply removing JS support — it worked on the first try.

## Testing the non-JS path

Disabling JavaScript in the browser and verifying the form fell back to `generate_processing.html` caught a missing template variable. Without this test, the fallback would have thrown a 500 error.

---

# What could improve?

## Duplicated template code

`generate_result_fragment.html` is a copy of the result block from `generate.html`. If the result layout changes, both files need updating. A Jinja2 macro (`{% macro result_card(result) %}`) shared across both templates would eliminate duplication.

## Polling interval was chosen arbitrarily

The 800ms polling interval was a guess. For 10–60s generation cycles, it's fine — but formal load testing would reveal the optimal balance between responsiveness and server load.

## Still no integration test for async flow

The async generation flow (`POST /generate` → poll → `GET /result`) has no automated test. A test that mocks the AI client and verifies the full lifecycle would catch polling, step tracking, and fragment rendering regressions.

---

# Main Learnings

- Script execution order in Jinja2 extends is counterintuitive — `stopImmediatePropagation()` is the fix;
- Backward compat fields cost near-zero and prevent real bugs;
- Fragment endpoints beat client-side rendering for complex templates;
- Session cookies are invisible infrastructure — until they break features silently;
- Pull-based polling is simple and correct; push-based SSE is an optimization, not a requirement.

---

# Actions for Sprint 007

- SSE or WebSocket for real-time progress (replace polling);
- Integration test for async generation flow;
- Extract result card into a Jinja2 macro to eliminate template duplication;
- Create Backlog capability (user stories from PRDs);
- Smart OKRs;
- Export/Import initiatives.
