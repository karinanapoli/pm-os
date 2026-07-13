# Sprint 003 — Learning

> "Sprint 003 marked the transition of PM OS from an experimentation project to an AI Product Engineering platform."

---

# Sprint Objective

The initial objective of the Sprint was to integrate a real Large Language Model (LLM) into PM OS, using Ollama as the AI provider.

During development, we realized that simply integrating an AI model exposed important architectural limitations.

Instead of just completing the functionality, we chose to strengthen the platform's architecture.

This decision increased the Sprint scope but established a much more solid foundation for the project's evolution.

---

# Main Learnings

## 1. Architecture must reflect the domain

Initially, PM OS used the concept of **Feature** as the central unit of the system.

Throughout the Sprint we realized that this term represented an implementation, but not the problem domain.

Product Managers work on **Initiatives**.

An initiative concentrates context, decisions, artifacts, and knowledge throughout its entire lifecycle.

This insight led to the creation of ADR-004 and the adoption of **Initiative** as the central element of the platform.

---

## 2. Architecture must reflect the user's mental model

Another important learning was understanding that the internal organization of the system should not only reflect its implementation.

It should reflect how the user thinks.

The old structure based on:

```text
features/
```

was replaced by an initiative-oriented Workspace:

```text
workspace/
└── initiatives/
```

This change made the platform more intuitive and ready for collaboration.

---

## 3. AI is just a dependency

During the integration with Ollama, it became evident that AI models do not belong to the application domain.

They are external services.

The creation of the infrastructure layer allowed completely decoupling Workflows from concrete implementations.

Today the domain depends only on contracts.

This decision will allow adding new AI providers without changing business logic.

---

## 4. Contracts are more important than implementations

By introducing `typing.Protocol`, components started depending on contracts instead of concrete classes.

This change reduced application coupling and facilitated testing, evolution, and replacement of implementations.

It was one of the main learnings about Dependency Inversion during the Sprint.

---

## 5. Workflows represent capabilities

At the beginning of the project, Workflows were seen only as scripts that executed a sequence of steps.

Throughout the Sprint we realized they represent reusable platform capabilities.

Examples:

- Create PRD;
- Create Backlog;
- Create Roadmap;
- Executive Summary.

All reuse the same Core components.

This change altered how PM OS started being planned.

---

## 6. Bootstrap is the Composition Root

The Sprint consolidated Bootstrap as the single point of application assembly.

All dependency creation happens in this component.

This made the architecture more predictable, decoupled, and ready for future expansions.

---

## 7. Observability is part of the architecture

The introduction of the Logger demonstrated that observing system behavior is as important as implementing features.

Logs now record each stage of Workflows, facilitating debugging, diagnosis, and understanding of the execution flow.

---

## 8. Error handling is also designing user experience

The implementation of `OllamaConnectionError` showed that error handling is not just a technical concern.

It is also a user experience decision.

Separating infrastructure errors from how they are presented made the application more user-friendly and ready for different interfaces.

---

# Architecture Evolution

During the Sprint, PM OS went through the following transformations:

```text
Prototype

↓

Application

↓

Framework

↓

Platform
```

This evolution happened mainly through domain reorganization and the clear separation between:

- domain;
- infrastructure;
- contracts;
- workflows;
- Workspace.

---

# Evolution of Thinking

More important than code changes was the change in how we think about architecture.

Throughout the Sprint, we stopped focusing only on "making it work" and started discussing questions like:

- Does the name correctly represent the domain?
- Does this decision facilitate platform evolution?
- Is the user's mental model reflected in the architecture?
- Does this component have only one responsibility?
- Can this implementation be replaced in the future?

These questions started guiding project decisions.

---

# Technical Debt Identified

During the Sprint, opportunities for evolution were identified that will be addressed in future iterations.

Among them:

- centralized configuration layer;
- integration tests;
- official PM OS CLI;
- Template Engine;
- Configuration Manager;
- multiple AI providers;
- metrics and telemetry;
- Vector Store support.

---

# Conclusion

Sprint 003 represented an important milestone for PM OS.

More than integrating an AI model, it consolidated the architectural identity of the platform.

The project ceased to be just an automation experiment and became a consistent foundation for building reusable capabilities for Product Managers.

The decisions made in this Sprint will serve as the foundation for all future evolutions of PM OS.
