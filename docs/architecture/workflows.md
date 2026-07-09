# Workflows

## O que é um Workflow?

No PM OS, um Workflow representa um caso de uso do usuário.

Um Workflow não implementa regras específicas de IA.

Seu papel é apenas orquestrar componentes especializados.

Cada componente possui uma única responsabilidade.

O Workflow coordena essas responsabilidades para atingir um objetivo.

---

## Primeiro Workflow

Atualmente o PM OS possui um Workflow:

CreatePRDWorkflow

Fluxo:

```text
FeatureRepository
        │
        ▼
ContextBuilder
        │
        ▼
PromptBuilder
        │
        ▼
AIClient
        │
        ▼
MarkdownWriter
        │
        ▼
PRD.md
```

---

## Responsabilidades

### Workflow

Responsável por:

- controlar a ordem de execução;
- conectar os componentes;
- retornar o artefato gerado.

O Workflow não conhece detalhes internos dos componentes.

Ele depende apenas de seus contratos públicos.

---

## Princípios aplicados

- Single Responsibility
- Dependency Injection
- Dependency Inversion
- Composition over Magic
- AI is a Dependency