# Guided Product Specification

## Outcome

PM Studio supports two compatible initiative experiences:

- **Quick mode** keeps the existing context → PRD → validation journey.
- **Guided mode (Beta)** adds evidence → specification → clarification →
  approval → deliverables.

Quick mode remains the default for existing and newly created initiatives.
Choosing guided mode does not remove or block direct PRD generation.

In guided mode, **Prepare from context** lets the PM select initiative sources
and ask the configured AI provider for a structured first proposal. The result
fills blank fields only: content already corrected by the PM is preserved.
Generated facts retain available source identifiers, unsupported conclusions
become hypotheses or open questions, and approval always remains a human action.

## Product model

The product specification is the living source for:

- problem and users;
- evidence and expected outcome;
- metrics, scope and requirements;
- constraints, risks and dependencies;
- hypotheses and open questions;
- acceptance criteria.

Every saved change creates a new specification version. Approval records the
accepted version, actor and timestamp. Decisions are stored independently with
their rationale.

## Derived deliverables

PRDs and backlogs record the specification version from which they were
derived. Editing the specification marks older deliverables as needing review.

The quick PRD workflow bootstraps an editable specification in the background
when the initiative does not have one yet. This lets existing users adopt the
guided experience later without repeating their work.

## Safety and compatibility

- Existing workspace folders and `prd.md` files remain valid.
- Specification state is stored under each initiative's `artifacts/`.
- Markdown exports remain portable.
- Clarifications and consistency findings are advisory, not blocking.
- Backlog generation requires explicit approval of a specification.
- External systems are not changed automatically.

## Current boundaries

The first backlog generator is deterministic and traceable. External issue
creation and governed MCP write tools remain separate actions that require
preview and explicit confirmation.
