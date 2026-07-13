# PM OS — Components

> "Componentes pequenos, responsabilidades claras e dependência de contratos. Essa é a base da arquitetura do PM OS."

---

# Objetivo

Este documento descreve os principais componentes do PM OS Core, suas responsabilidades e como eles colaboram para executar as capacidades da plataforma.

Cada componente possui uma única responsabilidade e se comunica através de contratos bem definidos, permitindo evolução incremental, baixo acoplamento e alta coesão.

---

# Visão Geral

O PM OS é organizado em torno de componentes especializados.

Cada componente executa apenas uma parte do fluxo de trabalho.

Nenhum componente implementa responsabilidades pertencentes a outro.

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
Infrastructure (Ollama, OpenAI...)
      │
      ▼
Markdown Writer
```

O Workflow atua apenas como orquestrador desse fluxo.

---

# Workspace

## Responsabilidade

Representar a área de trabalho do usuário.

O Workspace armazena todas as iniciativas, seus contextos, artefatos, metadados e configurações.

Estrutura atual:

```text
workspace/
└── initiatives/
    └── INT-0001-consulta-inteligente-fornecedores/
        ├── context/
        ├── artifacts/
        ├── logs/
        └── metadata.yaml
```

## Conhece

- iniciativas;
- artefatos;
- contexto;
- configurações.

## Não conhece

- IA;
- workflows;
- lógica de negócio.

---

# Initiative

## Responsabilidade

Representar a unidade central do domínio do PM OS.

Uma Initiative agrupa todo o conhecimento relacionado a uma iniciativa de produto durante seu ciclo de vida.

Pode conter:

- discovery;
- pesquisas;
- atas;
- requisitos;
- PRDs;
- roadmaps;
- RFCs;
- métricas;
- decisões.

## Entrada

Workspace.

## Saída

Objeto de domínio utilizado pelos Workflows.

## Conhece

- nome;
- localização;
- documentos associados.

## Não conhece

- IA;
- prompts;
- infraestrutura;
- interfaces.

## Princípios aplicados

- Domain-Driven Design
- Single Responsibility

---

# Initiative Repository

## Responsabilidade

Recuperar Initiatives disponíveis no Workspace.

Converte a estrutura de diretórios em objetos de domínio.

## Entrada

Workspace.

## Saída

Lista de objetos `Initiative`.

## Conhece

- estrutura do Workspace;
- localização das iniciativas.

## Não conhece

- IA;
- prompts;
- workflows;
- artefatos.

## Princípios aplicados

- Repository Pattern
- Separation of Concerns

---

# Context Builder

## Responsabilidade

Consolidar o conhecimento disponível de uma Initiative.

Seu objetivo não é apenas ler arquivos, mas construir um contexto reutilizável para qualquer workflow.

## Entrada

Objeto `Initiative`.

## Saída

Contexto consolidado.

## Conhece

- documentos da Initiative.

## Não conhece

- IA;
- prompts;
- persistência.

## Princípios aplicados

- Context Engineering
- Single Responsibility

---

# Prompt Builder

## Responsabilidade

Transformar contexto em instruções específicas para um workflow.

Responde à pergunta:

> "O que queremos que a IA faça?"

Enquanto o Context Builder responde:

> "O que a IA precisa saber?"

## Entrada

- workflow;
- contexto.

## Saída

Prompt.

## Conhece

- estrutura de cada workflow.

## Não conhece

- Workspace;
- IA;
- armazenamento.

---

# Contracts

## Responsabilidade

Definir contratos públicos entre os componentes.

O PM OS utiliza `typing.Protocol` para desacoplar o domínio das implementações concretas.

Exemplos:

- AIClientProtocol
- InitiativeRepositoryProtocol
- ContextBuilderProtocol
- MarkdownWriterProtocol
- Logger

## Princípios aplicados

- Dependency Inversion Principle
- Interface Segregation

---

# Infrastructure

## Responsabilidade

Implementar integrações com serviços externos.

O domínio nunca depende diretamente dessas implementações.

Exemplos atuais:

```text
infrastructure/
├── ai/
│   └── clients/
│       ├── FakeAIClient
│       └── OllamaClient
└── logging/
    └── ConsoleLogger
```

No futuro poderão existir integrações para:

- OpenAI;
- Azure OpenAI;
- Anthropic;
- Gemini;
- Vector Stores;
- Observabilidade.

## Princípios aplicados

- Ports and Adapters
- Dependency Injection

---

# Markdown Writer

## Responsabilidade

Persistir artefatos gerados pelos workflows.

Não gera conteúdo.

Não conhece IA.

Não conhece contexto.

Sua única responsabilidade é salvar arquivos.

## Entrada

- conteúdo;
- caminho de saída.

## Saída

Arquivo Markdown.

---

# Workflow

## Responsabilidade

Representar uma capacidade da plataforma.

Cada Workflow coordena os componentes especializados para entregar um resultado de negócio.

Exemplos atuais e futuros:

- CreatePRDWorkflow
- CreateBacklogWorkflow
- CreateRoadmapWorkflow
- CreateRFCWorkflow
- ExecutiveSummaryWorkflow

O Workflow não implementa regras específicas de IA.

Ele apenas coordena os componentes necessários.

## Princípios aplicados

- Use Case Pattern
- Orchestration

---

# Logger

## Responsabilidade

Registrar os principais eventos durante a execução dos workflows.

Seu objetivo é tornar o comportamento do sistema observável.

Exemplo:

```text
Loading initiatives...
Building context...
Generating PRD...
Writing artifact...
```

## Princípios aplicados

- Observability
- Separation of Concerns

---

# Bootstrap

## Responsabilidade

Montar toda a aplicação.

O Bootstrap é o **Composition Root** do PM OS.

Toda criação de dependências acontece neste componente.

Exemplo:

```text
Workflow
    │
    ▼
AIClient (Contract)
    │
    ▼
OllamaClient
```

Graças ao Bootstrap, é possível substituir implementações sem alterar os Workflows.

## Princípios aplicados

- Composition Root
- Dependency Injection
- Inversion of Control

---

# Relação entre os Componentes

O fluxo principal da plataforma é:

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
      │
      ▼
Markdown Writer
```

O Workflow apenas coordena essa sequência.

Cada componente permanece independente.

---

# Princípios Arquiteturais

Todos os componentes seguem os seguintes princípios:

- Single Responsibility Principle
- Dependency Injection
- Dependency Inversion
- Separation of Concerns
- Context Engineering
- AI as a Dependency
- Composition Root
- Low Coupling
- High Cohesion

---

# Resumo

| Componente | Responsabilidade |
|------------|------------------|
| Workspace | Armazenar iniciativas e conhecimento |
| Initiative | Representar a unidade central do domínio |
| Initiative Repository | Recuperar iniciativas do Workspace |
| Context Builder | Consolidar conhecimento |
| Prompt Builder | Construir prompts |
| Contracts | Definir contratos públicos |
| Infrastructure | Implementar integrações externas |
| AI Client | Gerar conteúdo utilizando IA |
| Markdown Writer | Persistir artefatos |
| Workflow | Orquestrar capacidades |
| Logger | Registrar eventos da execução |
| Bootstrap | Montar a aplicação |

---

# Evolução

A arquitetura continuará evoluindo conforme novas capacidades forem adicionadas.

Os próximos componentes previstos incluem:

- Configuration Manager;
- Template Engine;
- Vector Store;
- Embedding Service;
- Metrics;
- Telemetry.

Independentemente do crescimento do projeto, o PM OS continuará seguindo os mesmos princípios:

- componentes pequenos;
- responsabilidades claras;
- domínio desacoplado da infraestrutura;
- contexto como principal ativo do sistema;
- arquitetura orientada a capacidades.