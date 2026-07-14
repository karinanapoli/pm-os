# PM Studio Principles

The principles below guide all architectural and product decisions in PM Studio.

When in doubt between two solutions, these principles shall prevail.

---

# 1. Context > Prompt

We always prioritize the quality of context over the quality of the prompt.

Prompts guide models.

Context determines response quality.

---

# 2. Workflows > Prompts

Never build features based solely on prompts.

Every prompt must be part of a workflow.

---

# 3. AI is a Dependency

AI is a dependency of the system.

Never the center of the architecture.

PM Studio must remain organized even if the model is replaced.

---

# 4. Core First

Every business rule must stay in the PM Studio Core.

Interfaces never implement domain logic.

---

# 5. Low Coupling

Components should depend only on what they really need to know.

Changes in one component should not impact the rest of the system.

---

# 6. High Cohesion

Each component has only one responsibility.

If a component starts doing too many things, it should be split.

---

# 7. Composition over Magic

We prefer small specialized components working together.

We avoid giant components that do "everything".

---

# 8. Learn by Building

Each PM Studio component should teach some concept.

The project is also a learning tool.

---

# 9. Open Source by Design

Every decision must consider clarity, simplicity, and ease of contribution.

The project must be accessible to new contributors.

---

# 10. Security by Design

Security is not a step in the workflow.

It is part of the architecture.

Whenever possible, security principles must be present from the start of development.

---

# 11. Document Decisions

Every important architectural decision must be recorded through an ADR.

Code changes.

Decisions remain.

---

# 12. Small Iterations

PM Studio evolves through small sprints.

Each sprint must deliver value.

Each sprint must leave the project better than it was before.
