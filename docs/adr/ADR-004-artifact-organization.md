# ADR-004 — Workspace Orientado a Iniciativas

## Status

**Aceita**

---

# Contexto

O PM OS nasceu como um conjunto de workflows para geração de artefatos de produto, como PRDs.

Nas primeiras versões, a organização do Workspace refletia o fluxo de processamento da aplicação, utilizando diretórios separados para entrada, processamento e saída.

Exemplo:

```text
features/
├── 01-inbox/
├── 02-processing/
└── 03-prds/
```

Embora essa estrutura fosse suficiente para um protótipo, ela apresentava algumas limitações à medida que o projeto evoluiu.

Os principais problemas identificados foram:

- separação artificial entre contexto e artefatos;
- dificuldade para localizar todas as informações relacionadas a uma mesma iniciativa;
- risco de colisão de nomes (`PRD.md`, `PRD-final.md`, `PRD-v2.md`);
- baixa escalabilidade para novos workflows (Backlog, Roadmap, RFC, Executive Summary, etc.);
- organização baseada na implementação do sistema e não no modelo mental do usuário.

Durante a Sprint 003 percebemos que o PM OS não está apenas gerando documentos.

Ele está gerenciando conhecimento sobre iniciativas de produto.

Essa percepção mudou a forma como o domínio passou a ser modelado.

---

# Problema

A estrutura existente organizava arquivos por etapa do processamento.

Entretanto, Product Managers não trabalham pensando em "pastas de PRD" ou "pastas de backlog".

Eles trabalham pensando em iniciativas.

Uma iniciativa concentra todo o conhecimento relacionado a um problema de negócio:

- pesquisas;
- documentos de discovery;
- atas;
- requisitos;
- PRDs;
- backlogs;
- roadmaps;
- RFCs;
- métricas;
- decisões.

Separar esses elementos em diferentes diretórios dificultava a navegação, reduzia a rastreabilidade e criava dependências desnecessárias entre workflows.

---

# Decisão

O PM OS passará a utilizar um **Workspace orientado a Iniciativas**.

A iniciativa passa a ser a unidade central do domínio.

Cada iniciativa será responsável por armazenar todo o seu ciclo de vida.

Estrutura adotada:

```text
workspace/
└── initiatives/
    └── INT-0001-consulta-inteligente-fornecedores/
        ├── context/
        ├── artifacts/
        ├── logs/
        └── metadata.yaml
```

Cada diretório possui uma responsabilidade clara:

| Diretório | Responsabilidade |
|------------|------------------|
| `context/` | Conhecimento bruto da iniciativa (discovery, atas, pesquisas, documentos, imagens, transcrições, etc.) |
| `artifacts/` | Artefatos produzidos pelos workflows do PM OS (PRD, Backlog, Roadmap, RFC, Executive Summary, etc.) |
| `logs/` | Logs específicos da iniciativa e execuções dos workflows. |
| `metadata.yaml` | Fonte de verdade da iniciativa, contendo identificação, status e metadados. |

Todos os workflows deverão gerar seus resultados dentro da pasta da própria iniciativa.

Exemplo:

```text
workspace/
└── initiatives/
    └── INT-0001-consulta-inteligente-fornecedores/
        └── artifacts/
            ├── prd.md
            ├── backlog.md
            ├── roadmap.md
            └── rfc.md
```

---

# Alternativas Consideradas

## Alternativa 1 — Manter a estrutura atual

```text
features/
├── 01-inbox/
├── 02-processing/
└── 03-prds/
```

### Vantagens

- nenhuma refatoração imediata;
- baixo esforço de implementação.

### Desvantagens

- estrutura pouco intuitiva para usuários;
- artefatos separados do contexto;
- baixa escalabilidade.

---

## Alternativa 2 — Organizar por Iniciativas (**Escolhida**)

```text
workspace/
└── initiatives/
```

### Vantagens

- reflete o modelo mental do Product Manager;
- elimina a necessidade de diretórios globais para artefatos;
- facilita novos workflows;
- aumenta a rastreabilidade;
- reduz colisão de nomes;
- melhora a experiência para novos usuários do projeto.

### Desvantagens

- exige refatoração da arquitetura atual;
- requer atualização de documentação, testes e código existente.

---

# Consequências

A partir desta decisão:

- o Workspace passa a representar o domínio do produto, e não o fluxo interno da aplicação;
- novos workflows deverão utilizar a pasta da iniciativa como destino padrão;
- o conceito de `Feature` será gradualmente substituído por `Initiative`;
- os diretórios globais de artefatos deixam de ser a abordagem recomendada.

---

# Impacto na Arquitetura

Esta decisão impacta diretamente os seguintes componentes:

- Initiative Repository;
- Context Builder;
- Workflows;
- Markdown Writer;
- Bootstrap;
- Templates;
- Testes de integração.

Esses componentes deverão evoluir para trabalhar utilizando a estrutura orientada a iniciativas.

---

# Impacto para o Usuário

Esta mudança torna o PM OS mais intuitivo.

Ao abrir uma iniciativa, o usuário encontrará em um único lugar:

- contexto;
- documentos;
- artefatos;
- histórico;
- metadados.

A arquitetura passa a refletir a forma como Product Managers organizam seu trabalho.

---

# Considerações Futuras

O arquivo `metadata.yaml` deverá evoluir para armazenar informações como:

- identificador;
- nome;
- responsável;
- status;
- tags;
- workflows executados;
- artefatos gerados;
- datas importantes.

Também está prevista a evolução do ciclo de vida das iniciativas:

```text
Discovery
Planejamento
Desenvolvimento
Entrega
Concluída
Arquivada
```

---

# Motivação da Decisão

Esta ADR nasceu durante a Sprint 003.

Inicialmente, o objetivo era apenas alterar o local onde os PRDs eram gerados.

Durante a discussão percebemos que o problema não estava na geração dos arquivos, mas na forma como o domínio estava sendo modelado.

Ao adotar uma arquitetura orientada a iniciativas, o PM OS deixa de ser apenas um gerador de documentos e passa a representar um verdadeiro **Operating System para Product Managers**.

Essa decisão estabelece uma base mais consistente para a evolução do projeto e reduz a necessidade de grandes refatorações no futuro.