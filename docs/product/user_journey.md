# PM Studio — User Journey

## Purpose

PM Studio transforms scattered product information into traceable context,
decisions, and deliverables. It supports Product Managers without replacing
their judgment.

## Entry points

The user can start in either mode:

- **Quick mode**: add context and generate a PRD or backlog with minimal setup;
- **Guided mode**: build and approve a structured specification before deriving
  deliverables.

Both modes use the same initiative workspace and preserve traceability.

## Current journey

### 1. Create an initiative

The initiative establishes the scope for sources, signals, decisions,
specification, PRD, backlog, and assistant history. It may belong to a personal
workspace or a squad.

### 2. Add evidence

The PM uploads Markdown, TXT, or PDF sources, links signals, and optionally uses
Product Docs or external read-only sources. Every source receives a stable ID so
generated claims can be traced back to evidence.

### 3. Build context

PM Studio previews selected sources, confidentiality, size, and destination
before an external AI provider receives content. Demo mode remains local and
deterministic.

### 4. Define the product

In guided mode, the PM reviews problem, users, evidence, outcome, metrics,
scope, requirements, risks, open questions, and acceptance criteria. Saving
creates a version; approval is an explicit human action.

### 5. Record decisions

Important decisions include rationale, owner, status, and a **revisit if**
condition. The Decision Memory exposes them across initiatives without
duplicating the source of truth.

### 6. Generate deliverables

The approved context can produce a PRD and a structured backlog. Derived
artifacts record their source version and become stale when the specification
changes.

### 7. Review and approve

Generated content remains editable. Editing sends the artifact back to review;
approval enables the final download.

### 8. Prepare a governed backlog export

For an approved backlog, the PM selects stories, chooses a target contract
(GitHub Issues, Linear, Plane, or generic), reviews the exact payload, and
confirms a portable JSON package. Preparation and confirmation are recorded in
an audit trail. External systems are not changed silently.

### 9. Create items through a write-enabled MCP connection

After package confirmation, the PM selects an MCP tool whose policy explicitly
allows confirmed writes, confirms the external action, and reviews the result
for each story. Repeating the same batch skips stories already created; failed
stories remain visible for controlled retry.

### 10. Consult the initiative assistant

The assistant answers from initiative context and conversation history. The PM
may explicitly call a discovered MCP read tool with JSON arguments. Tool output
is bounded, labeled as untrusted external data, and recorded in the history.
Write tools are never executed automatically.

### 11. Monitor traceability

The Initiative Map connects context, definition, decisions, and deliverables.
The dashboard and timeline expose attention points without replacing product
judgment.

## Next journey extension

The next safe step is normalizing external identifiers, detecting drift, and
adding target-specific retry and compensation contracts without silently
changing the source backlog.

## Experience principles

- Context is more important than prompts.
- Workflows deliver outcomes; prompts remain implementation details.
- Facts, inferences, and recommendations must remain distinguishable.
- Human approval precedes consequential actions.
- External writes require preview, authorization, audit, and recovery.
- Documentation is produced as part of the work.
- AI is replaceable; initiative knowledge remains portable.
