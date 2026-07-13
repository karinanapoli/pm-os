# Sprint 003 — Learning

> "A Sprint 003 marcou a transição do PM OS de um projeto de experimentação para uma plataforma de AI Product Engineering."

---

# Objetivo da Sprint

O objetivo inicial da Sprint era integrar um Large Language Model (LLM) real ao PM OS, utilizando Ollama como provedor de IA.

Durante o desenvolvimento, percebemos que a simples integração de um modelo de IA expôs limitações arquiteturais importantes.

Ao invés de apenas concluir a funcionalidade, optamos por fortalecer a arquitetura da plataforma.

Essa decisão aumentou o escopo da Sprint, mas estabeleceu uma base muito mais sólida para a evolução do projeto.

---

# Principais Aprendizados

## 1. Arquitetura deve refletir o domínio

Inicialmente, o PM OS utilizava o conceito de **Feature** como unidade central do sistema.

Ao longo da Sprint percebemos que esse termo representava uma implementação, mas não o domínio do problema.

Product Managers trabalham sobre **Iniciativas**.

Uma iniciativa concentra contexto, decisões, artefatos e conhecimento ao longo de todo o seu ciclo de vida.

Essa percepção levou à criação da ADR-004 e à adoção do conceito de **Initiative** como elemento central da plataforma.

---

## 2. A arquitetura deve refletir o modelo mental do usuário

Outro aprendizado importante foi compreender que a organização interna do sistema não deve refletir apenas sua implementação.

Ela deve refletir a forma como o usuário pensa.

A antiga estrutura baseada em:

```text
features/
```

foi substituída por um Workspace orientado a Iniciativas:

```text
workspace/
└── initiatives/
```

Essa mudança tornou a plataforma mais intuitiva e preparada para colaboração.

---

## 3. AI é apenas uma dependência

Durante a integração com Ollama ficou evidente que modelos de IA não pertencem ao domínio da aplicação.

Eles são serviços externos.

A criação da camada de infraestrutura permitiu desacoplar completamente os Workflows das implementações concretas.

Hoje o domínio depende apenas de contratos.

Essa decisão permitirá adicionar novos provedores de IA sem alterar a lógica de negócio.

---

## 4. Contracts são mais importantes que implementações

Ao introduzir `typing.Protocol`, os componentes passaram a depender de contratos em vez de classes concretas.

Essa mudança reduziu o acoplamento da aplicação e facilitou testes, evolução e substituição de implementações.

Foi um dos principais aprendizados sobre Dependency Inversion durante a Sprint.

---

## 5. Workflows representam capacidades

No início do projeto os Workflows eram vistos apenas como scripts que executavam uma sequência de passos.

Ao longo da Sprint percebemos que eles representam capacidades reutilizáveis da plataforma.

Exemplos:

- Create PRD;
- Create Backlog;
- Create Roadmap;
- Executive Summary.

Todos reutilizam os mesmos componentes do Core.

Essa mudança alterou a forma como o PM OS passou a ser planejado.

---

## 6. O Bootstrap é o Composition Root

A Sprint consolidou o Bootstrap como ponto único de montagem da aplicação.

Toda criação de dependências acontece nesse componente.

Isso tornou a arquitetura mais previsível, desacoplada e preparada para futuras expansões.

---

## 7. Observabilidade faz parte da arquitetura

A introdução do Logger demonstrou que observar o comportamento do sistema é tão importante quanto implementar funcionalidades.

Os logs passaram a registrar cada etapa dos Workflows, facilitando depuração, diagnóstico e entendimento do fluxo de execução.

---

## 8. Tratar erros também é projetar a experiência do usuário

A implementação do `OllamaConnectionError` mostrou que tratamento de erros não é apenas uma preocupação técnica.

É também uma decisão de experiência do usuário.

Separar erros de infraestrutura da forma como eles são apresentados tornou a aplicação mais amigável e preparada para diferentes interfaces.

---

# Evolução da Arquitetura

Durante a Sprint o PM OS passou pelas seguintes transformações:

```text
Protótipo

↓

Aplicação

↓

Framework

↓

Plataforma
```

Essa evolução aconteceu principalmente pela reorganização do domínio e pela separação clara entre:

- domínio;
- infraestrutura;
- contratos;
- workflows;
- Workspace.

---

# Evolução da Forma de Pensar

Mais importante do que as mudanças de código foi a mudança na forma de pensar a arquitetura.

Ao longo da Sprint, deixamos de focar apenas em "fazer funcionar" e passamos a discutir questões como:

- O nome representa corretamente o domínio?
- Essa decisão facilita a evolução da plataforma?
- O modelo mental do usuário está refletido na arquitetura?
- Esse componente possui apenas uma responsabilidade?
- Essa implementação pode ser substituída no futuro?

Essas perguntas passaram a orientar as decisões do projeto.

---

# Dívidas Técnicas Identificadas

Durante a Sprint foram identificadas oportunidades de evolução que serão tratadas nas próximas iterações.

Entre elas:

- camada centralizada de configuração;
- testes de integração;
- CLI oficial do PM OS;
- Template Engine;
- Configuration Manager;
- múltiplos provedores de IA;
- métricas e telemetria;
- suporte a Vector Stores.

---

# Conclusão

A Sprint 003 representou um marco importante para o PM OS.

Mais do que integrar um modelo de IA, ela consolidou a identidade arquitetural da plataforma.

O projeto deixou de ser apenas um experimento de automação para se tornar uma base consistente para a construção de capacidades reutilizáveis voltadas ao trabalho de Product Managers.

As decisões tomadas nesta Sprint servirão como fundamento para todas as próximas evoluções do PM OS.