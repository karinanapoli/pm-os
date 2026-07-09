# PM OS — Components

## Objetivo

Este documento descreve os principais componentes do PM OS Core, suas responsabilidades e como eles colaboram para executar os workflows da plataforma.

Cada componente possui uma única responsabilidade.

A comunicação entre eles acontece através de contratos bem definidos, reduzindo acoplamento e facilitando a evolução da arquitetura.

---

# Visão Geral

O PM OS Core é composto por pequenos componentes especializados.

Nenhum componente conhece a implementação interna dos demais.

Cada Workflow apenas orquestra esses componentes.

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
```

---

# Feature

## Responsabilidade

Representa uma iniciativa de produto dentro do PM OS.

Uma Feature é a unidade central de trabalho do sistema.

Ela agrupa todos os materiais relacionados a uma iniciativa.

Exemplos:

- atas de reunião;
- documentos de discovery;
- RFCs;
- diagramas;
- requisitos;
- APIs;
- imagens;
- decisões técnicas.

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
- workflows;
- MCP;
- interfaces de usuário.

---

# FeatureRepository

## Responsabilidade

Encontrar Features disponíveis no Workspace.

Converte a estrutura de diretórios em objetos de domínio.

## Entrada

Workspace.

## Saída

Lista de objetos `Feature`.

## Conhece

- estrutura do Workspace;
- arquivos disponíveis.

## Não conhece

- IA;
- prompts;
- contexto;
- artefatos.

## Padrão aplicado

Repository Pattern.

Todo acesso ao Workspace acontece por meio deste componente.

---

# ContextBuilder

## Responsabilidade

Construir contexto consolidado para uma iniciativa.

O objetivo não é simplesmente ler arquivos.

O objetivo é transformar conhecimento disperso em um contexto reutilizável.

## Entrada

Objeto `Feature`.

## Saída

Contexto consolidado.

## Conhece

- documentos da iniciativa;
- conteúdo dos arquivos.

## Não conhece

- modelo de IA;
- prompts;
- artefatos finais.

## Princípio aplicado

Context Engineering.

Contexto é tratado como um ativo do sistema.

---

# PromptBuilder

## Responsabilidade

Transformar contexto em instruções para um Workflow específico.

O PromptBuilder responde:

> "O que queremos que o modelo faça?"

Enquanto o ContextBuilder responde:

> "O que o modelo precisa saber?"

## Entrada

- nome do workflow;
- contexto.

## Saída

Prompt.

## Conhece

- estrutura esperada de cada Workflow.

## Não conhece

- Workspace;
- IA;
- persistência.

---

# AIClient

## Responsabilidade

Comunicar-se com um modelo de IA.

O restante do Core não conhece implementações específicas.

Nesta Sprint utilizamos um Fake AI Client.

No futuro poderão existir implementações para:

- Ollama
- OpenAI
- Gemini
- Claude
- modelos internos

## Entrada

Prompt.

## Saída

Texto gerado.

## Princípio aplicado

AI is a Dependency.

O Core depende apenas do contrato do cliente de IA.

---

# MarkdownWriter

## Responsabilidade

Persistir artefatos Markdown no Workspace.

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

Representar um caso de uso do usuário.

Workflows não implementam regras específicas de IA.

Eles apenas coordenam componentes especializados.

Cada Workflow representa uma ação de negócio.

Exemplos futuros:

- CreatePRDWorkflow
- CreateBacklogWorkflow
- CreateRFCWorkflow
- ExecutiveSummaryWorkflow

## Exemplo

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
```

---

# Bootstrap

## Responsabilidade

Montar a aplicação.

O Bootstrap é o Composition Root do PM OS.

Toda criação de dependências acontece neste componente.

Graças ao Bootstrap, é possível trocar implementações sem alterar os Workflows.

Exemplo:

```text
Hoje

Workflow
    ↓
Fake AI Client

Amanhã

Workflow
    ↓
Ollama Client
```

Nenhum Workflow precisa ser alterado.

---

# Protocols

## Responsabilidade

Definir contratos públicos entre os componentes.

Os Workflows dependem de Protocols e não de implementações concretas.

Exemplo:

```python
AIClientProtocol
```

e não

```python
AIClient
```

Isso reduz acoplamento e facilita testes, evolução e substituição de implementações.

## Princípio aplicado

Dependency Inversion Principle (DIP).

---

# Relação entre os componentes

Cada componente possui uma única responsabilidade.

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
```

O Workflow coordena esse fluxo.

Os componentes não conhecem uns aos outros.

---

# Princípios Arquiteturais

Os componentes do PM OS seguem os seguintes princípios:

- Single Responsibility Principle
- Dependency Injection
- Dependency Inversion
- Composition over Magic
- Context Engineering
- AI is a Dependency
- Low Coupling
- High Cohesion

---

# Resumo

| Componente | Responsabilidade |
|------------|------------------|
| Feature | Representar uma iniciativa de produto |
| FeatureRepository | Localizar iniciativas no Workspace |
| ContextBuilder | Consolidar conhecimento |
| PromptBuilder | Construir prompts para Workflows |
| AIClient | Conversar com modelos de IA |
| MarkdownWriter | Persistir artefatos |
| Workflow | Orquestrar casos de uso |
| Bootstrap | Montar a aplicação |
| Protocols | Definir contratos públicos |

---

# Evolução

À medida que o PM OS evoluir, novos componentes poderão ser adicionados ao Core.

Entretanto, os princípios fundamentais permanecem:

- componentes pequenos;
- responsabilidades claras;
- baixo acoplamento;
- alta coesão;
- dependência de contratos;
- contexto como ativo do sistema.