# ADR-004 — Initiative-Oriented Workspace

## Status

**Accepted**

---

# Context

PM OS was born as a set of workflows for generating product artifacts, such as PRDs.

In early versions, the Workspace organization reflected the application's processing flow, using separate directories for input, processing, and output.

Example:

```text
features/
├── 01-inbox/
├── 02-processing/
└── 03-prds/
```

Although this structure was sufficient for a prototype, it presented some limitations as the project evolved.

The main problems identified were:

- artificial separation between context and artifacts;
- difficulty locating all information related to the same initiative;
- name collision risk (`PRD.md`, `PRD-final.md`, `PRD-v2.md`);
- low scalability for new workflows (Backlog, Roadmap, RFC, Executive Summary, etc.);
- organization based on system implementation rather than the user's mental model.

During Sprint 003 we realized that PM OS is not just generating documents.

It is managing knowledge about product initiatives.

This insight changed the way the domain was modeled.

---

# Problem

The existing structure organized files by processing stage.

However, Product Managers do not work thinking about "PRD folders" or "backlog folders".

They work thinking about initiatives.

An initiative concentrates all knowledge related to a business problem:

- research;
- discovery documents;
- meeting notes;
- requirements;
- PRDs;
- backlogs;
- roadmaps;
- RFCs;
- metrics;
- decisions.

Separating these elements into different directories made navigation difficult, reduced traceability, and created unnecessary dependencies between workflows.

---

# Decision

PM OS will adopt an **Initiative-oriented Workspace**.

The initiative becomes the central unit of the domain.

Each initiative will be responsible for storing its entire lifecycle.

Adopted structure:

```text
workspace/
└── initiatives/
    └── INT-0001-smart-supplier-query/
        ├── context/
        ├── artifacts/
        ├── logs/
        └── metadata.yaml
```

Each directory has a clear responsibility:

| Directory | Responsibility |
|------------|------------------|
| `context/` | Raw knowledge of the initiative (discovery, meeting notes, research, documents, images, transcriptions, etc.) |
| `artifacts/` | Artifacts produced by PM OS workflows (PRD, Backlog, Roadmap, RFC, Executive Summary, etc.) |
| `logs/` | Initiative-specific logs and workflow executions. |
| `metadata.yaml` | Source of truth for the initiative, containing identification, status, and metadata. |

All workflows must generate their results inside the initiative's own folder.

Example:

```text
workspace/
└── initiatives/
    └── INT-0001-smart-supplier-query/
        └── artifacts/
            ├── prd.md
            ├── backlog.md
            ├── roadmap.md
            └── rfc.md
```

---

# Alternatives Considered

## Alternative 1 — Keep current structure

```text
features/
├── 01-inbox/
├── 02-processing/
└── 03-prds/
```

### Advantages

- no immediate refactoring;
- low implementation effort.

### Disadvantages

- unintuitive structure for users;
- artifacts separated from context;
- low scalability.

---

## Alternative 2 — Organize by Initiatives (**Chosen**)

```text
workspace/
└── initiatives/
```

### Advantages

- reflects the Product Manager's mental model;
- eliminates the need for global artifact directories;
- facilitates new workflows;
- increases traceability;
- reduces name collision;
- improves experience for new project users.

### Disadvantages

- requires refactoring of the current architecture;
- requires updating documentation, tests, and existing code.

---

# Consequences

From this decision forward:

- the Workspace now represents the product domain, not the internal application flow;
- new workflows must use the initiative folder as the default destination;
- the concept of `Feature` will be gradually replaced by `Initiative`;
- global artifact directories are no longer the recommended approach.

---

# Architecture Impact

This decision directly impacts the following components:

- Initiative Repository;
- Context Builder;
- Workflows;
- Markdown Writer;
- Bootstrap;
- Templates;
- Integration tests.

These components must evolve to work using the initiative-oriented structure.

---

# User Impact

This change makes PM OS more intuitive.

When opening an initiative, the user will find in a single place:

- context;
- documents;
- artifacts;
- history;
- metadata.

The architecture now reflects how Product Managers organize their work.

---

# Future Considerations

The `metadata.yaml` file should evolve to store information such as:

- identifier;
- name;
- owner;
- status;
- tags;
- executed workflows;
- generated artifacts;
- important dates.

The evolution of initiative lifecycle is also planned:

```text
Discovery
Planning
Development
Delivery
Completed
Archived
```

---

# Decision Motivation

This ADR was born during Sprint 003.

Initially, the goal was only to change where PRDs were generated.

During discussion we realized the problem was not in file generation, but in how the domain was being modeled.

By adopting an initiative-oriented architecture, PM OS ceases to be just a document generator and becomes a true **Operating System for Product Managers**.

This decision establishes a more consistent foundation for the project's evolution and reduces the need for major refactoring in the future.
