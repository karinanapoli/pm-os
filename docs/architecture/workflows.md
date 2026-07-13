# PM OS — Workflows

> "Workflows represent platform capabilities. They orchestrate specialized components to transform knowledge into product artifacts."

---

# Objective

This document describes how PM OS Workflows are structured and how they use the platform's components to execute a business capability.

In PM OS, a Workflow represents a complete user use case.

Its role is to coordinate specialized components, keeping the domain decoupled from infrastructure.

---

# What is a Workflow?

A Workflow represents a **capability** of the platform.

Each capability delivers a specific business result.

Examples:

- Create PRD
- Create Backlog
- Create Roadmap
- Create RFC
- Executive Summary
- AI Review
- Security Review

All Workflows share the same architecture.

They differ only by the objective they execute.

---

# Responsibilities

A Workflow is responsible for:

- initiating capability execution;
- coordinating Core components;
- controlling execution order;
- returning the produced artifact.

The Workflow **does not**:

- implement AI rules;
- directly access the Workspace;
- build prompts;
- save files;
- know concrete implementations.

Its only responsibility is to orchestrate specialized components.

---

# Execution Flow

The standard Workflow flow is:

```text
Workspace
      │
      ▼
Initiative Repository
      │
      ▼
Context Builder
      │
      ▼
Prompt Builder
      │
      ▼
AI Client (Contract)
      │
      ▼
Infrastructure
(Ollama, OpenAI...)
      │
      ▼
Markdown Writer
      │
      ▼
Artifact
```

Each component executes only one responsibility.

---

# Current Example

Currently PM OS has one implemented capability:

```text
CreatePRDWorkflow
```

Its flow is:

```text
Initiative Repository
        │
        ▼
Context Builder
        │
        ▼
Prompt Builder
        │
        ▼
AI Client
        │
        ▼
Markdown Writer
        │
        ▼
workspace/
    initiatives/
        INT-0001/
            artifacts/
                prd.md
```

---

# General Structure

All Workflows follow the same structure.

```python
Workflow

↓

Repository

↓

Context Builder

↓

Prompt Builder

↓

AI Client

↓

Writer
```

This organization ensures consistency across all platform capabilities.

---

# Components Used

| Component | Responsibility |
|------------|------------------|
| Initiative Repository | Retrieve the Initiative from Workspace |
| Context Builder | Consolidate knowledge |
| Prompt Builder | Build the appropriate prompt for the Workflow |
| AI Client | Generate content using AI |
| Markdown Writer | Persist the produced artifact |

---

# Dependency Injection

All components are received by the Workflow through dependency injection.

Example:

```python
CreatePRDWorkflow(
    initiative_repository=...,
    context_builder=...,
    prompt_builder=...,
    ai_client=...,
    markdown_writer=...,
    logger=...
)
```

This approach allows replacing implementations without changing the Workflow.

---

# Observability

Workflows log the main execution events using the Logger.

Example:

```text
Loading initiatives...
Building context...
Building prompt...
Generating content...
Writing artifact...
Workflow completed.
```

These logs facilitate diagnosis, debugging, and execution tracking.

---

# Error Handling

Workflows do not handle technical infrastructure details.

Specific errors are encapsulated by specialized components, such as `OllamaClient`.

The input interface (CLI, MCP, or API) is responsible for transforming these errors into appropriate user messages.

This separation keeps Workflows focused only on capability orchestration.

---

# Applied Principles

All Workflows follow these principles:

- Single Responsibility Principle
- Dependency Injection
- Dependency Inversion
- Separation of Concerns
- AI as a Dependency
- Composition Root
- Context Engineering

---

# Evolution

The next planned Workflows will reuse exactly the same architecture.

Among them:

- Create Backlog
- Create Roadmap
- Create RFC
- Executive Summary
- AI Review
- Security Review

Adding a new capability should require only creating a new Workflow and its specific templates, reusing existing components.

---

# Summary

In PM OS, a Workflow represents a reusable platform capability.

It does not implement specific AI rules nor know infrastructure details.

Its role is only to coordinate specialized components to transform organized knowledge into product artifacts, keeping the architecture simple, modular, and ready for continuous evolution.
