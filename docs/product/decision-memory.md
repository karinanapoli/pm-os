# Decision Memory

## Outcome

Decision Memory makes product choices discoverable across initiatives without
moving or duplicating their source data. Decisions continue to live inside the
owning initiative specification; `/decisions` builds a workspace-scoped view.

## Recording a decision

A decision contains:

- title;
- rationale;
- author and date;
- related source identifiers when available;
- optional **revisit if** condition;
- lifecycle status.

The revisit condition should be observable. Prefer “revisit if activation stays
below 30% after two months” over “revisit if this does not work.”

## Lifecycle

- **Active**: the current decision still guides the product;
- **Revisited**: the decision has been reopened for evaluation;
- **Superseded**: another decision replaced it.

Changing status does not delete rationale or history.

## Workspace scope

The global memory lists decisions only from initiatives available in the active
personal or squad workspace. Each item links back to the initiative
specification that owns it.

## Compatibility

Existing decisions are loaded as active and receive an empty revisit condition.
No workspace migration is required.

## Current boundaries

- Review conditions are not monitored automatically.
- Decisions cannot yet link directly to signals through the global page.
- Full status-change history and superseding-decision links are future work.
- AI may help detect contradictions later, but it does not change decisions.
