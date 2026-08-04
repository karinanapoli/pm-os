class PromptBuilder:
    def build(self, workflow_name: str, context: str, question: str = "", lang: str = "en") -> str:
        if workflow_name == "create_prd":
            return self._build_create_prd_prompt(context, lang)
        if workflow_name == "create_specification":
            return self._build_create_specification_prompt(context, lang)
        if workflow_name == "create_backlog":
            return self._build_create_backlog_prompt(context, lang)
        if workflow_name == "consult":
            if lang == "en":
                return self._build_consult_prompt_en(context, question)
            return self._build_consult_prompt(context, question)
        raise ValueError(f"Unsupported workflow: {workflow_name}")

    def _build_create_specification_prompt(self, context: str, lang: str = "en") -> str:
        fields = (
            "problem, users, evidence, outcome, metrics, scope, out_of_scope, "
            "requirements, constraints, risks, dependencies, hypotheses, "
            "open_questions, acceptance_criteria"
        )
        if lang == "pt-BR":
            return f"""
Você é uma Product Manager experiente preparando uma especificação revisável.

Analise SOMENTE o contexto fornecido e retorne um objeto JSON válido, sem texto
antes ou depois. Use exatamente estas chaves:

{fields}

Regras:

- Preserve identificadores de fonte no formato [SRC-XXXXXXXX].
- Não invente fatos, métricas, requisitos ou fontes.
- Coloque inferências em "hypotheses".
- Coloque informações ausentes ou ambíguas em "open_questions".
- Use strings Markdown; listas devem ter um item por linha.
- Deixe o campo vazio quando o contexto não sustentar uma resposta.

Contexto:

{context}
"""
        return f"""
You are an experienced Product Manager preparing a reviewable specification.

Analyze ONLY the provided context and return a valid JSON object with no text
before or after it. Use exactly these keys:

{fields}

Rules:

- Preserve source identifiers in the [SRC-XXXXXXXX] format.
- Do not invent facts, metrics, requirements, or sources.
- Put inferences in "hypotheses".
- Put missing or ambiguous information in "open_questions".
- Use Markdown strings; lists must have one item per line.
- Leave a field empty when context does not support an answer.

Context:

{context}
"""

    def _build_create_prd_prompt(self, context: str, lang: str = "en") -> str:
        if lang == "pt-BR":
            return f"""
Você é um Product Manager experiente.

Crie um PRD completo em Markdown com base no contexto abaixo.

Regras de evidência:

- Use as fontes como contexto de forma silenciosa e consolide informações
  coincidentes em uma única narrativa.
- Não cite, enumere ou repita todos os documentos consultados ao longo do PRD.
- Cite o identificador exato [SRC-XXXXXXXX] somente quando a rastreabilidade
  for relevante: dado decisivo, citação direta, requisito regulatório,
  divergência entre fontes ou decisão que precise ser auditada.
- Quando houver fontes essenciais, inclua ao final uma seção opcional
  "Referências essenciais", limitada a cinco itens. Omita a seção quando ela
  não agregar valor à leitura.
- Nunca invente uma fonte.
- Separe explicitamente "Fatos sustentados pelas fontes", "Inferências" e
  "Recomendações".
- Quando não houver evidência suficiente, registre a informação em
  "Perguntas em aberto".

O PRD deve incluir:

1. Visão Geral
2. Problema
3. Objetivos
4. Fora do escopo
5. Personas / usuários
6. Requisitos funcionais
7. Requisitos não funcionais
8. Métricas de sucesso
9. Riscos
10. Perguntas em aberto

Contexto:

{context}
"""
        return f"""
You are an experienced Product Manager.

Create a complete PRD in Markdown based on the context below.

Evidence rules:

- Use sources silently as context and consolidate matching information into a
  single narrative.
- Do not cite, enumerate, or repeat every document throughout the PRD.
- Cite an exact [SRC-XXXXXXXX] identifier only when traceability matters: a
  decisive data point, direct quote, regulatory requirement, source conflict,
  or a decision that must be audited.
- When essential sources exist, add an optional "Essential references"
  section at the end with no more than five items. Omit it when it does not
  improve comprehension.
- Never invent a source identifier.
- Explicitly separate "Source-backed facts", "Inferences", and
  "Recommendations".
- When evidence is insufficient, add the item to "Open questions".

The PRD must include:

1. Overview
2. Problem
3. Objectives
4. Out of scope
5. Personas / users
6. Functional requirements
7. Non-functional requirements
8. Success metrics
9. Risks
10. Open questions

Context:

{context}
"""

    def _build_create_backlog_prompt(self, context: str, lang: str = "en") -> str:
        if lang == "pt-BR":
            return f"""
Você é o agente "Criar Histórias de Usuário — Gerador de Backlog". Transforme
a especificação aprovada abaixo em um backlog completo na hierarquia
Iniciativa → Épico → História.

Use somente as informações fornecidas. Não invente pessoas, squads, métricas,
baselines, metas, prazos ou dependências. Quando um campo obrigatório não
estiver disponível, escreva "A definir".

Gere sempre:

1. Uma Iniciativa com objetivo de negócio, alinhamento estratégico, tabela de
   métricas (Métrica | Baseline atual | Meta | Prazo), squads envolvidos,
   horizonte temporal, checklist de épicos, fora do escopo, riscos e
   dependências macro e status.
2. Épicos coesos com iniciativa pai, responsáveis (Squad, PM, Tech Lead e
   Designer), problema, descrição, Definition of Done, métricas, estimativa
   macro P/M/G, dependências, checklist de histórias e status.
3. De 5 a 15 histórias independentes por épico, ordenadas primeiro por
   dependência e depois por prioridade. Use "User Story" como padrão e escreva
   "Como [tipo de usuário], quero [capacidade], para que [benefício]".
4. Para cada história, inclua contexto e motivação, 3 a 5 critérios de
   aceite numerados e testáveis, fora do escopo, notas de design, notas
   técnicas, prioridade P0/P1/P2, esforço P/M/G, dependências e indicação de
   spike.

Regras de qualidade:

- Uma história representa uma unidade de valor entregável, idealmente em até
  três dias de desenvolvimento.
- Não invente limites numéricos. Use números apenas quando sustentados pela
  especificação; caso contrário, escreva "A definir".
- Evite histórias técnicas puras e não transforme subtarefas internas ou QA em
  histórias separadas.
- Não duplique requisitos entre histórias ou épicos.
- Prefixe com "[SPIKE]" apenas histórias de investigação necessárias para
  resolver uma incerteza que bloqueie estimativa ou solução.
- Mantenha os nomes idênticos nas relações entre iniciativa, épicos e histórias.

Formato obrigatório dos títulos:

## Iniciativa: [Nome]
## Épico: [Nome]
### História: [Título]

Retorne APENAS o backlog em Markdown, começando por "## Iniciativa". Não
inclua introdução, explicações, comentários sobre o processo, documentos
consultados ou texto após o backlog.

Especificação aprovada:

{context}
"""
        return f"""
You are the "Create User Stories — Backlog Generator" agent. Transform the
approved specification below into a complete Initiative → Epic → Story backlog.

Use only the supplied information. Do not invent people, squads, metrics,
baselines, targets, dates, or dependencies. Write "To be defined" when a
required field is unsupported.

Always generate one Initiative with business and strategic context, measurable
success, ownership, scope, risks and status; cohesive Epics with ownership,
problem, description, Definition of Done, metrics, estimate, dependencies,
story checklist and status; and 5 to 15 independent User Stories per Epic.
Order stories by dependency and then priority. Every story must use "As a... I
want... so that...", include context, 3 to 5 numbered and testable acceptance
criteria, out of scope, design and technical notes, P0/P1/P2 priority, P/M/G
effort, dependencies, and spike indication. Prefix a necessary investigation
with "[SPIKE]". Keep each story to a deliverable unit of user or business value,
ideally no more than three development days. Do not create pure technical,
internal-task, or standalone QA stories, and do not duplicate requirements.

Required heading format:

## Initiative: [Name]
## Epic: [Name]
### Story: [Title]

Return ONLY the Markdown backlog beginning with "## Initiative". Do not add an
introduction, process commentary, consulted-document list, or trailing notes.

Approved specification:

{context}
"""

    def _build_consult_prompt(self, context: str, question: str) -> str:
        return f"""Você é um analista de documentação de produto.

Abaixo estão documentos de diversas fontes (iniciativas e/ou documentação do produto).
Cada bloco é precedido por um cabeçalho indicando a origem.

Documentos:
{context}

Com base SOMENTE nos documentos acima, responda à pergunta abaixo.
Se a informação não estiver nos documentos, diga que não encontrou.
Cite cada afirmação factual com o identificador exato [SRC-XXXXXXXX].
Separe fatos sustentados, inferências e recomendações. Nunca invente uma fonte.

Pergunta: {question}"""

    def _build_consult_prompt_en(self, context: str, question: str) -> str:
        return f"""You are a product documentation analyst.

Below are documents from various sources (initiatives and/or product documentation).
Each block is preceded by a header indicating its origin.

Documents:
{context}

Based SOLELY on the documents above, answer the question below.
If the information is not in the documents, say so.
Cite every factual claim with the exact [SRC-XXXXXXXX] identifier.
Separate source-backed facts, inferences, and recommendations. Never invent a source.

Question: {question}"""
