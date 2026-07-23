# ADR-005 — Structured and traceable context sources

## Status

Accepted.

## Context

AI-generated product documents can sound authoritative even when a statement is not
supported by the supplied context. Product Managers also need to understand which
information may leave their environment before generation.

## Decision

Every context document is represented as a `ContextSource` with:

- a stable source ID;
- name and type;
- author and modification date when available;
- confidentiality classification;
- content size and estimated token count.

The context sent to a model contains explicit source boundaries. Prompts require
citations in the form `[SRC-XXXXXXXX]` for factual claims and require facts,
inferences, recommendations, and unanswered questions to remain distinguishable.

The generation screen previews document count, estimated size, confidentiality
levels, and whether the configured provider is local or external.

## Consequences

- Generated content can be reviewed against its evidence.
- Users see privacy signals before submitting a generation request.
- Existing initiatives remain compatible because plain document lists are still
  supported.
- Token counts are estimates and provider billing may differ.
