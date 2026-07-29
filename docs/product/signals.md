# Product Signals

## Outcome

The Signal Center turns scattered product evidence into reusable context.
A signal can represent customer feedback, research, support information,
commercial insight, a metric, competitor movement, or an internal hypothesis.

A document is treated as a **source**, not as a signal by itself. PM Studio
prepares editable suggestions from the source and stores only the signals that
the Product Manager explicitly confirms.

## User journey

1. Open **Signals** from the workspace navigation.
2. Log a signal manually or add a document source.
3. For a source, choose local preparation or explicitly enable the configured
   AI provider.
4. Review each proposed title, description, theme, source type, and evidence
   strength.
5. Optionally relate the signal to one or more initiatives.
6. Confirm each useful signal individually.

Supported source formats are PDF, Markdown, and TXT, up to 10 MB.

## Evidence strength

Evidence strength is descriptive rather than an automated truth score:

- **Early indication**: useful observation that needs corroboration;
- **Moderate**: repeated or supported evidence;
- **Strong**: clear, well-supported evidence.

The PM can always correct the suggested strength before saving.

## Storage and traceability

Signals are stored as YAML under `workspace/signals/`. Uploaded source files and
their metadata live under `workspace/signals/sources/`. A confirmed signal keeps
the source identifier and filename so the original evidence can be reopened.

Personal and squad scopes are isolated. The same file uploaded in different
scopes produces separate source records.

## Privacy and AI behavior

Local preparation is the default and does not send the document to an external
AI. Selecting **Analyze with the configured AI** sends the extracted text to
the provider selected in Settings. If that provider fails or returns an invalid
structure, PM Studio falls back to local preparation.

No suggested signal is saved automatically. The user must review and confirm
each item.

## Current boundaries

- DOCX, CSV, and spreadsheets are not yet supported as signal sources.
- Source extraction is synchronous.
- A signal can relate to initiatives, but it is not yet included
  automatically in PRD generation context.
- Cross-signal clustering and weekly synthesis are future capabilities.
