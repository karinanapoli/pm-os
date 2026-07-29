# Initiative Map

## Outcome

The Initiative Map explains how product context becomes a delivery. It provides
a read-only, traceable view organized into three stages:

1. **Context**: related signals and initiative source documents;
2. **Definition**: guided specification and recorded decisions;
3. **Deliverables**: specification export, requirements document, backlog, and
   validation.

## Source of truth

The map does not copy or migrate data. It derives its state from:

- Signal Repository relationships;
- Initiative context sources;
- Product Specification state;
- Decisions owned by the specification;
- Files and artifact metadata under the initiative.

Each node links to the existing journey where that information is managed.

## Artifact status

An artifact is shown as ready when its current file exists. Otherwise, it is
shown as pending. Freshness and specification-version traceability continue to
be handled by the guided deliverables workflow.

## Safety and compatibility

- The map performs no writes.
- Existing initiatives require no migration.
- Personal and squad scope follows the initiative and signal repositories.
- Missing context is displayed as an empty state rather than inferred by AI.

## Current boundaries

- Relationships are presented as a structured flow, not an interactive graph.
- Signal sources uploaded in the Signal Center are represented through their
  confirmed signals; initiative context files are listed directly.
- Cross-initiative relationships remain in Signal and Decision Memory views.
