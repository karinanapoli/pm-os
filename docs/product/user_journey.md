# Jornada do Usuário

## Status

Draft

---

# Objetivo

Este documento descreve como um Product Manager utiliza o PM OS desde o momento em que surge uma nova iniciativa até a geração de todos os artefatos do projeto.

Este documento não descreve a implementação técnica.

Ele descreve a experiência que queremos proporcionar.

Todas as decisões de arquitetura devem respeitar esta jornada.

---

# A Filosofia do PM OS

O PM OS não existe para gerar PRDs.

O PM OS existe para transformar conhecimento disperso em contexto reutilizável.

Documentos são apenas uma consequência.

O verdadeiro ativo é o contexto.

---

# O problema atual

Hoje um Product Manager sai de uma reunião com informações espalhadas em diversos lugares.

Por exemplo:

- anotações pessoais;
- gravação da reunião;
- transcrição;
- conversa no Slack;
- documentos técnicos;
- RFCs;
- diagramas;
- Figma;
- Jira;
- e-mails;
- apresentações.

Antes mesmo de começar a escrever um PRD, o PM precisa gastar horas consolidando todas essas informações.

O maior problema não é escrever documentos.

O maior problema é organizar conhecimento.

---

# Nossa hipótese

Acreditamos que Product Managers não precisam de um gerador de prompts.

Eles precisam de um sistema capaz de organizar conhecimento, construir contexto e reutilizar esse contexto durante todo o ciclo de vida de uma iniciativa.

---

# A jornada do usuário

## Etapa 1 — Surge uma nova iniciativa

Tudo começa quando uma nova iniciativa aparece.

Exemplos:

- Novo Dashboard de Segurança
- IA para Atendimento
- Marketplace B2B
- Sistema de MFA
- Integração com PIX

Nesse momento o usuário ainda não pensa em escrever um PRD.

Ele apenas sabe que uma nova iniciativa começou.

---

## Etapa 2 — Criar um Workspace da iniciativa

O PM cria um Workspace para essa iniciativa.

Exemplo:

```text
features/

    dashboard-seguranca/
```

Esse Workspace passa a ser o local onde todo o conhecimento será armazenado.

Ainda não existe contexto.

Ainda não existe PRD.

Existe apenas uma iniciativa.

---

## Etapa 3 — Adicionar materiais

O usuário simplesmente adiciona tudo o que possui sobre aquela iniciativa.

Exemplos:

```text
meeting.mp3

transcricao.md

notas.md

figma.pdf

arquitetura.png

jira.md

rfc.md

slack.md

email.md

pesquisa.pdf
```

O PM não precisa decidir o que é importante.

Ele apenas adiciona os materiais.

---

## Etapa 4 — Construção do contexto

O PM OS analisa todos os materiais disponíveis.

Ele identifica:

- objetivos;
- problemas;
- decisões;
- stakeholders;
- requisitos;
- restrições;
- riscos;
- documentos relacionados;
- conhecimento já existente.

Ao final dessa etapa o sistema cria um contexto consolidado.

Esse contexto passa a ser a fonte oficial de conhecimento da iniciativa.

Não é um prompt.

É um ativo do sistema.

---

## Etapa 5 — Executar Workflows

Com o contexto consolidado, qualquer workflow pode ser executado.

Exemplos:

- Criar PRD
- Criar RFC
- Criar Backlog
- Criar Roadmap
- Criar Executive Summary
- Criar Security Review
- Criar AI Review
- Criar Release Notes

Todos os workflows reutilizam exatamente o mesmo contexto.

O usuário não precisa explicar novamente a iniciativa.

---

## Etapa 6 — Revisão

O PM revisa o artefato gerado.

Pode:

- editar;
- complementar;
- aprovar;
- rejeitar;
- solicitar uma nova versão.

O objetivo não é substituir o Product Manager.

O objetivo é acelerar a construção de artefatos de alta qualidade.

---

## Etapa 7 — Evolução contínua

Conforme a iniciativa evolui, novos materiais podem ser adicionados ao Workspace.

Por exemplo:

- novas reuniões;
- novos RFCs;
- novas decisões;
- novos diagramas;
- novos requisitos.

O contexto é atualizado continuamente.

Os próximos artefatos sempre utilizam a versão mais recente desse conhecimento.

---

# O papel do Contexto

O contexto é o principal ativo do PM OS.

Ele representa todo o conhecimento consolidado sobre uma iniciativa.

Os workflows apenas consomem esse contexto.

Os prompts apenas orientam o modelo.

O contexto determina a qualidade da resposta.

---

# O papel dos Workflows

Os workflows representam ações que um Product Manager deseja executar.

Exemplos:

- Criar PRD
- Criar Backlog
- Criar RFC
- Criar Story Map
- Criar Plano de Release

Cada workflow utiliza o mesmo contexto, mas produz artefatos diferentes.

---

# O papel da IA

A IA não é o produto.

Ela é apenas uma dependência do sistema.

O PM OS continua responsável por:

- organizar conhecimento;
- construir contexto;
- definir prompts;
- orquestrar workflows;
- gerar artefatos.

O modelo de IA é apenas o mecanismo responsável pela geração do texto.

---

# Experiência desejada

No futuro, a experiência ideal será simples.

O usuário poderá escrever algo como:

> "Crie um PRD para esta iniciativa."

Ou:

> "Atualize o backlog com base na última reunião."

Ou:

> "Gere um resumo executivo para a diretoria."

O PM OS será responsável por encontrar o contexto correto, consolidar as informações necessárias e executar o workflow apropriado.

O usuário não precisará se preocupar com prompts, modelos ou engenharia de contexto.

---

# Princípios reforçados

Esta jornada reforça alguns dos princípios fundamentais do PM OS:

- Contexto é mais importante que prompts.
- O conhecimento pertence à iniciativa.
- Workflows representam objetivos de negócio.
- A IA é uma dependência, não o produto.
- O PM continua sendo responsável pelas decisões.
- O PM OS acelera a produção de artefatos sem substituir o pensamento crítico.