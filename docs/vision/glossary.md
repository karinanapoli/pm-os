# PM OS Glossary

This document gathers the main concepts used by PM OS.

Its goal is to create a common language among Product Managers, engineers, and contributors.

---

# AI Client

Component responsible for communicating with an Artificial Intelligence model.

Future examples:

- Ollama
- OpenAI
- Gemini
- Claude

---

# Builder

Component responsible for transforming an input into another representation.

Examples:

ContextBuilder

PromptBuilder

---

# Context

Organized set of information prepared to be sent to the AI model.

Context is not just the sum of documents.

It is an asset built by the system.

---

# Context Engineering

Discipline responsible for building high-quality context for AI models.

It is one of the pillars of PM OS.

---

# Core

Central layer of PM OS.

Contains all business logic.

Never depends on external interfaces.

---

# Domain Model

Object that represents a concept from the Product Management domain.

Example:

Feature

---

# Feature

Work unit of PM OS.

A Feature can contain documents, requirements, meeting notes, APIs, images, and any other input related to product development.

---

# MCP

Model Context Protocol.

Layer responsible for making PM OS tools available to different interfaces.

In PM OS, the MCP never contains business rules.

---

# PM OS Core

Framework core.

Where the following live:

- Repositories
- Builders
- Workflows
- AI Clients
- Writers
- Domain Models

---

# Prompt

Set of instructions sent to the AI model.

The Prompt tells the model what to do.

---

# Prompt Engineering

Techniques used to structure prompts.

In PM OS, Prompt Engineering is considered complementary to Context Engineering.

---

# Repository

Component responsible for accessing data sources.

Example:

FeatureRepository.

---

# Workflow

Organized sequence of components that execute a task.

Example:

create_prd

↓

FeatureRepository

↓

ContextBuilder

↓

PromptBuilder

↓

AIClient

↓

MarkdownWriter

---

# Workspace

Set of files used by PM OS.

Includes:

- Features
- Templates
- Skills
- Knowledge
- Configurations

The Workspace represents the main source of knowledge for the system.

---

# Writer

Component responsible for persisting results.

Example:

MarkdownWriter.
