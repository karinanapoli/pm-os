# PM Studio — Architecture and Performance Audit

Date: 2026-07-24

## Outcome

The hardening cycle is complete. PM Studio now has focused application
services around its highest-risk workflows, persistent and scoped generation
jobs, bounded external integration concurrency, and a stronger automated
quality baseline.

## Verified baseline

- 288 automated tests passing before this documentation update.
- 81.76% measured Python statement coverage.
- CI runs on Python 3.9, 3.11 and 3.13.
- CI coverage floor increased from 76% to 80%.
- 61 Python modules and 37 test modules.
- No broken installed dependencies reported by `pip check`.
- Critical Ruff rules and whitespace validation passing.

`src/pm_os/web/app.py` has 2,104 physical lines. Coverage reports count
approximately 1,108 executable statements in that module; these metrics are
different and should not be presented interchangeably.

## Improvements delivered

### Architecture

- PRD validation and persistence moved to a dedicated service.
- Generation job lifecycle separated from PRD generation behavior.
- PRD generation and product consultation extracted from HTTP routes.
- Initiative lifecycle and Product Docs operations centralized.
- Configuration updates made transactional and persistence optimized.

### Performance and reliability

- Generation jobs persist across restarts and are isolated by user and squad.
- Completed jobs expire after a conservative retention period.
- MCP contexts are fetched concurrently with a maximum of four workers.
- Invalid AI validation responses do not replace trustworthy reports.
- External HTTP destinations and redirects remain protected against SSRF.

### Security and trust

- Session, account token, squad authorization and public URL protections were
  strengthened during the cycle.
- Context sources have stable identifiers and generated output exposes citation
  verification results.
- Upload operations validate filename, extension and size within their service.

## Accepted boundaries

These are not release blockers for the current local/self-hosted product:

- `app.py` remains a large HTTP composition root. Further extraction should
  organize routes by capability, without moving business logic back into them.
- Background work uses an in-process thread pool. Multiple application
  instances would require a shared queue and worker model.
- SQLite is appropriate for the current deployment model. Distributed scale
  would require a shared transactional database.
- Broad exception handlers remain at selected interface and integration
  boundaries; structured error telemetry should precede aggressive narrowing.

## Recommended next product step

Pause infrastructure-only refactoring and deliver **Create Backlog** as the next
end-to-end PM capability. Reuse the existing context, source selection,
generation job, citation and validation services. Track latency, provider
errors, citation coverage and user completion rate from the beginning.
