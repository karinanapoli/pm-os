# PM OS — Workflows

> "Workflows representam capacidades da plataforma. Eles orquestram componentes especializados para transformar conhecimento em artefatos de produto."

---

# Objetivo

Este documento descreve como os Workflows do PM OS são estruturados e como eles utilizam os componentes da plataforma para executar uma capacidade de negócio.

No PM OS, um Workflow representa um caso de uso completo do usuário.

Seu papel é coordenar componentes especializados, mantendo o domínio desacoplado da infraestrutura.

---

# O que é um Workflow?

Um Workflow representa uma **capacidade** da plataforma.

Cada capacidade entrega um resultado de negócio específico.

Exemplos:

- Create PRD
- Create Backlog
- Create Roadmap
- Create RFC
- Executive Summary
- AI Review
- Security Review

Todos os Workflows compartilham a mesma arquitetura.

Eles diferem apenas pelo objetivo que executam.

---

# Responsabilidades

Um Workflow é responsável por:

- iniciar a execução da capacidade;
- coordenar os componentes do Core;
- controlar a ordem de execução;
- retornar o artefato produzido.

O Workflow **não**:

- implementa regras de IA;
- acessa diretamente o Workspace;
- constrói prompts;
- salva arquivos;
- conhece implementações concretas.

Sua única responsabilidade é orquestrar componentes especializados.

---

# Fluxo de Execução

O fluxo padrão de um Workflow é:

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

Cada componente executa apenas uma responsabilidade.

---

# Exemplo Atual

Atualmente o PM OS possui uma capability implementada:

```text
CreatePRDWorkflow
```

Seu fluxo é:

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

# Estrutura Geral

Todos os Workflows seguem a mesma estrutura.

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

Essa organização garante consistência entre todas as capacidades da plataforma.

---

# Componentes Utilizados

| Componente | Responsabilidade |
|------------|------------------|
| Initiative Repository | Recuperar a Initiative do Workspace |
| Context Builder | Consolidar conhecimento |
| Prompt Builder | Construir o prompt adequado ao Workflow |
| AI Client | Gerar conteúdo utilizando IA |
| Markdown Writer | Persistir o artefato produzido |

---

# Dependency Injection

Todos os componentes são recebidos pelo Workflow através de injeção de dependências.

Exemplo:

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

Essa abordagem permite substituir implementações sem alterar o Workflow.

---

# Observabilidade

Os Workflows registram os principais eventos da execução utilizando o Logger.

Exemplo:

```text
Loading initiatives...
Building context...
Building prompt...
Generating content...
Writing artifact...
Workflow completed.
```

Esses logs facilitam diagnóstico, depuração e acompanhamento da execução.

---

# Tratamento de Erros

Os Workflows não tratam detalhes técnicos de infraestrutura.

Erros específicos são encapsulados por componentes especializados, como o `OllamaClient`.

A interface de entrada (CLI, MCP ou API) é responsável por transformar esses erros em mensagens adequadas para o usuário.

Essa separação mantém os Workflows focados apenas na orquestração da capacidade.

---

# Princípios Aplicados

Todos os Workflows seguem os seguintes princípios:

- Single Responsibility Principle
- Dependency Injection
- Dependency Inversion
- Separation of Concerns
- AI as a Dependency
- Composition Root
- Context Engineering

---

# Evolução

Os próximos Workflows planejados reutilizarão exatamente a mesma arquitetura.

Entre eles:

- Create Backlog
- Create Roadmap
- Create RFC
- Executive Summary
- AI Review
- Security Review

A adição de uma nova capacidade deverá exigir apenas a criação de um novo Workflow e seus templates específicos, reutilizando os componentes existentes.

---

# Resumo

No PM OS, um Workflow representa uma capacidade reutilizável da plataforma.

Ele não implementa regras específicas de IA nem conhece detalhes da infraestrutura.

Seu papel é apenas coordenar componentes especializados para transformar conhecimento organizado em artefatos de produto, mantendo a arquitetura simples, modular e preparada para evolução contínua.