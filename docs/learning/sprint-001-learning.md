# Sprint 001 — Fundação do PM OS Core

## Objetivo da Sprint

Criar a fundação técnica e conceitual do PM OS.

Nesta sprint, o objetivo não era ainda gerar um PRD completo com IA, mas sim construir a base do sistema: estrutura do projeto, primeiros componentes do Core e decisões arquiteturais fundamentais.

---

## O que construímos

Criamos a estrutura inicial do projeto `pm-os`, incluindo:

- `features/`
- `src/pm_os/`
- `mcp/`
- `skills/`
- `templates/`
- `knowledge/`
- `config/`
- `tests/`
- `docs/`

Também criamos os primeiros componentes do PM OS Core:

- `Feature`
- `FeatureRepository`
- `ContextBuilder`
- `PromptBuilder`
- `AIClient` fake

---

## Principal decisão da Sprint

A principal decisão foi entender que o MCP não deve ser o cérebro do sistema.

O MCP será apenas uma interface.

A lógica principal ficará no PM OS Core, escrito em Python.

Isso permite que o projeto evolua para diferentes interfaces no futuro, como:

- MCP
- CLI
- Web app
- Continue
- OpenCode
- Claude Desktop
- Cursor

---

## Pipeline criado

O pipeline inicial ficou assim:

```text
FeatureRepository
      ↓
Feature
      ↓
ContextBuilder
      ↓
PromptBuilder
      ↓
AIClient fake