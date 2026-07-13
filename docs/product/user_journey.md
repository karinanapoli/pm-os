# User Journey

## Status

Draft

---

# Objective

This document describes how a Product Manager uses PM OS from the moment a new initiative emerges to the generation of all project artifacts.

This document does not describe the technical implementation.

It describes the experience we want to provide.

All architecture decisions must respect this journey.

---

# The PM OS Philosophy

PM OS does not exist to generate PRDs.

PM OS exists to transform scattered knowledge into reusable context.

Documents are just a consequence.

The real asset is the context.

---

# The Current Problem

Today a Product Manager leaves a meeting with information scattered across multiple places.

For example:

- personal notes;
- meeting recording;
- transcription;
- Slack conversation;
- technical documents;
- RFCs;
- diagrams;
- Figma;
- Jira;
- emails;
- presentations.

Even before starting to write a PRD, the PM needs to spend hours consolidating all this information.

The biggest problem is not writing documents.

The biggest problem is organizing knowledge.

---

# Our Hypothesis

We believe Product Managers do not need a prompt generator.

They need a system capable of organizing knowledge, building context, and reusing that context throughout the entire lifecycle of an initiative.

---

# The User Journey

## Stage 1 — A new initiative emerges

It all starts when a new initiative appears.

Examples:

- New Security Dashboard
- AI for Customer Support
- B2B Marketplace
- MFA System
- PIX Integration

At this point, the user is not yet thinking about writing a PRD.

They just know a new initiative has begun.

---

## Stage 2 — Create an initiative Workspace

The PM creates a Workspace for this initiative.

Example:

```text
features/

    dashboard-seguranca/
```

This Workspace becomes the place where all knowledge will be stored.

There is no context yet.

There is no PRD yet.

There is only an initiative.

---

## Stage 3 — Add materials

The user simply adds everything they have about that initiative.

Examples:

```text
meeting.mp3

transcription.md

notes.md

figma.pdf

architecture.png

jira.md

rfc.md

slack.md

email.md

research.pdf
```

The PM does not need to decide what is important.

They just add the materials.

---

## Stage 4 — Context building

PM OS analyzes all available materials.

It identifies:

- objectives;
- problems;
- decisions;
- stakeholders;
- requirements;
- constraints;
- risks;
- related documents;
- existing knowledge.

At the end of this stage, the system creates a consolidated context.

This context becomes the official source of knowledge for the initiative.

It is not a prompt.

It is a system asset.

---

## Stage 5 — Execute Workflows

With the consolidated context, any workflow can be executed.

Examples:

- Create PRD
- Validate PRD
- Create RFC
- Create Backlog
- Create Roadmap
- Create Executive Summary
- Create Security Review
- Create AI Review
- Create Release Notes

All workflows reuse exactly the same context.

The user does not need to explain the initiative again.

---

## Stage 5.5 — Automatic Quality Validation

Right after generating a PRD, the system **automatically validates its quality**.

No extra command needed.

The validation evaluates:

- **Metrics** — Are they specific, measurable, and time-bound?
- **Risks** — Do they have mitigation plans?
- **Scope** — Is it well-defined? Any contradictions?
- **Requirements** — Are they clear and testable?
- **Structure** — Are all required sections present?
- **Coherence** — Does the PRD tell a consistent story?

The result is a **validation report** saved alongside the PRD:

```text
artifacts/
├── prd.md
└── prd-validation.md
```

The PM sees a summary right in the terminal:

```
PRD quality score: 6.0/10
  ⚠ Metrics: 4.0 — not SMART
  ⚠ Risks: 5.0 — missing mitigation
  ✅ Scope: 8.0
```

This stage turns quality from subjective opinion into an **observable metric**.
The PM knows where to focus before even reading the full document.

---

## Stage 6 — Review

The PM opens the validation report first.

They see exactly which sections need attention:

- Low metric score → refine success criteria.
- Low risk score → add mitigation plans.
- Scope contradiction → fix before socializing.

Then they review the PRD itself with the report as a guide.

They can:

- edit;
- complement;
- approve;
- reject;
- request a new version.

The goal is not to replace the Product Manager.

The goal is to accelerate the construction of high-quality artifacts.

---

## Stage 7 — Continuous evolution

As the initiative evolves, new materials can be added to the Workspace.

For example:

- new meetings;
- new RFCs;
- new decisions;
- new diagrams;
- new requirements.

The context is continuously updated.

Future artifacts always use the most recent version of this knowledge.

---

# The Role of Context

Context is the main asset of PM OS.

It represents all consolidated knowledge about an initiative.

Workflows only consume this context.

Prompts only guide the model.

Context determines the quality of the response.

---

# The Role of Workflows

Workflows represent actions a Product Manager wants to execute.

Examples:

- Create PRD
- Create Backlog
- Create RFC
- Create Story Map
- Create Release Plan

Each workflow uses the same context but produces different artifacts.

---

# The Role of AI

AI is not the product.

It is just a system dependency.

PM OS remains responsible for:

- organizing knowledge;
- building context;
- defining prompts;
- orchestrating workflows;
- generating artifacts.

The AI model is just the mechanism responsible for text generation.

---

# Desired Experience

In the future, the ideal experience will be simple.

The user could write something like:

> "Create a PRD for this initiative."

The system generates the PRD and **automatically validates its quality**, showing the score.

The user could also ask:

> "Validate the PRD for INT-0001."

To get a fresh quality report on demand.

Or:

> "Update the backlog based on the last meeting."

Or:

> "Generate an executive summary for the board."

Or:

> "What's the quality status of all my initiatives?"

And the Workspace Scanner would reply with scores for every PRD.

PM OS will be responsible for finding the correct context, consolidating the necessary information, and executing the appropriate workflow.

The user will not need to worry about prompts, models, or context engineering.

---

# Reinforced Principles

This journey reinforces some of the fundamental principles of PM OS:

- Context is more important than prompts.
- Knowledge belongs to the initiative.
- Workflows represent business objectives.
- AI is a dependency, not the product.
- The PM remains responsible for decisions.
- PM OS accelerates artifact production without replacing critical thinking.
- **Quality is not subjective** — every artifact gets a validation score.
- **Validation is automatic** — the system checks quality so the PM doesn't have to.
