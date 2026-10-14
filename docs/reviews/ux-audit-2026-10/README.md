# PM Studio — Avaliação com usuários sintéticos + auditoria de UI (out/2026)

> **Escopo:** novidades das PRs #54–#58 (Cursor/MCP + OAuth, Especificação guiada a partir de PRD, Dados e insights consolidados, ferramentas externas na visão geral, edição de iniciativa + repositório vinculado, refinamentos de backlog baseados em código).
> **Método:** app rodando localmente (`main` @ `104a9d3`, idioma pt-BR, provedor Demo/Ollama), 20 telas capturadas com Playwright em desktop (1440×900) e 6 em mobile (390×844), estilos computados extraídos do DOM e varredura estática de `templates/`, `style.css` e `i18n.py`.
> **Atenção:** os usuários abaixo são **sintéticos**. As falas e notas são hipóteses derivadas do que a UI de fato mostra — servem para priorizar e roteirizar testes com PMs reais, não para substituí-los.

Capturas em [`screens/`](screens/).

---

## 1. Resumo executivo

| # | Achado | Severidade | Onde |
|---|--------|-----------|------|
| 1 | **Título da iniciativa quebra letra por letra no mobile** — 5 botões no `topbar_actions` sem `flex-wrap` espremem o `h1` (`overflow-wrap: anywhere`) | 🔴 Crítico | `initiative_detail.html:5`, `style.css:3268` |
| 2 | **Status “discovery” sem tradução (regressão do P4/P14)** — templates usam `init.status\|t` em vez de `("status." ~ init.status)\|t` | 🟠 Alto | `dashboard.html:151`, `initiative_detail.html:96` |
| 3 | **Sinais contraditórios de modelo** — sidebar mostra “Ollama · llama3.2:1b” enquanto `/generate` e Especificação usam “Demo” | 🟠 Alto | `base.html` (model-badge) vs `generate.html` |
| 4 | **Controles nativos sem estilo** destoando do tema escuro: botão “Sair”, “Conectar” (Planilhas), `input type=file` (“Choose Files”, em inglês), radios azuis do SO, `select` branco | 🟠 Alto | `base.html`, `initiative_data.html`, `initiative_detail.html`, `initiative_specification.html` |
| 5 | **Excesso de CTAs para o mesmo destino** — “Gerar PRD” aparece 3× na Especificação e 3× na Visão geral (topbar, card “Criar um PRD”, bloco PRD) | 🟠 Alto | Especificação, Visão geral |
| 6 | **Relatório de validação em inglês** dentro da UI em pt-BR (“PRD Validation Report”, “Overall Score”, “Section Breakdown”) | 🟡 Médio | Visão geral → Relatório de Validação |
| 7 | **Vocabulário inconsistente** — “Score de Validação/Segurança” (decisão registrada era “Nota”), nav “Roadmap” vs rota `/timeline`, `h1` com slug `INT-0001-smart-supplier-query` em vez do nome, separadores “·” e “—” misturados | 🟡 Médio | Abas da iniciativa, `validate`, `map` |
| 8 | **Pluralização quebrada** — “1 arquivos”, “1 validações”, “1 versões anteriores”, “1 fontes disponíveis”, “1 itens” | 🟡 Médio | vários |
| 9 | **“Score de segurança 0.0/10 — Crítico”** exibido sem análise executada; gera alarme falso | 🟡 Médio | Visão geral |
| 10 | **Sistema de ícones híbrido** — 45 glifos distintos misturando Unicode geométrico (◈◇◆✦⌁) e emoji coloridos (📄📁👤⚡🚀); ◈ usado para Dashboard *e* Roadmap | 🟡 Médio | sidebar + cards |
| 11 | **Escala tipográfica sem tokens** — 32 tamanhos de fonte distintos (incl. 9, 10.5, 11.5, 12.5, 13.5, 15.5 px) e pesos 400/500/600/650/700/800 | 🟡 Médio | `style.css` + inline |
| 12 | **Fonte documentada ≠ fonte real** — AGENTS.md diz Inter; `--font` é a pilha do sistema; “JetBrains Mono” é referenciada mas nunca carregada | 🔵 Baixo | `style.css:59,3383` |

**O que está funcionando bem:** a narrativa “Próxima ação → O que você quer produzir agora?” é clara; o card de exemplo com selo **EXEMPLO** em Dados ensina sem mentir; o aviso âmbar do modo Demo em `/generate` é honesto e acionável; a semântica de cor (violeta = sistema, ciano = IA, âmbar = reversível, coral = permanente) está consistente; contraste de texto passa AA em todos os pares checados (ver §5.4).

---

## 2. Usuários sintéticos

Cinco perfis cobrindo o público-alvo (PMs) e quem orbita o fluxo das novidades. Notas de 1 a 5 são estimativas de percepção para a tarefa indicada.

### 2.1 Marina Duarte — PM Pleno, fintech B2B (persona primária)
- **Contexto:** 4 anos de produto, squad de 6 devs, vive entre Notion, Jira e planilhas. Usa ChatGPT no dia a dia mas desconfia de “PRD gerado”.
- **JTBD:** *Quando recebo um pedido vago de stakeholder, quero transformar o que já tenho em uma especificação defensável, para não começar a discovery do zero.*
- **Tarefa avaliada:** Especificação guiada a partir do PRD existente.
- **Jornada observada:**
  1. Abre a iniciativa → entende o card “O que você quer produzir agora?” (bom).
  2. Vai em *Especificação*: o stepper mostra “1. Dados” como **concluído** (verde) embora a aba Dados exiba 0 insights — “concluído o quê?”.
  3. Escolhe “PRD atual da iniciativa” — os radios aparecem no azul padrão do SO, fora da identidade.
  4. Vê três botões que geram PRD (“Gerar PRD agora”, “Gerar PRD” no card Entregáveis e o da Visão geral) e fica em dúvida sobre qual sobrescreve o atual.
- **Fala provável:** “Gostei de poder partir do PRD que eu já tinha. Mas aqui tem botão de gerar PRD pra todo lado — se eu clicar no errado, perco minha versão?”
- **Nota (clareza da tarefa):** 3/5 · **Confiança no resultado:** 3/5

### 2.2 Lucas Ferreira — APM em primeiro emprego (persona de onboarding)
- **Contexto:** recém-saído de bootcamp, instala tudo local com Ollama, acessa muito pelo celular no transporte.
- **JTBD:** *Quando estou aprendendo, quero que a ferramenta me diga o próximo passo, para entregar algo apresentável ao meu líder.*
- **Tarefa avaliada:** abrir uma iniciativa no celular e entender o status.
- **Jornada observada:**
  1. Dashboard mobile: seletor de workspace quebra “+ Criar Squad / Entrar em Squad” em 5 linhas.
  2. Abre a iniciativa: **o título vira uma coluna de letras** (`p / pl / ie / r / Q…`) ocupando a tela inteira — bloqueante.
  3. Vê o badge “discovery” em inglês e “Score de segurança 0.0/10 Crítico” — acha que fez algo errado.
- **Fala provável:** “Achei que o app tinha quebrado. E por que minha iniciativa está ‘crítica’ se eu nem mexi em segurança?”
- **Nota (clareza):** 1/5 no mobile · 4/5 no desktop

### 2.3 Helena Prado — Head de Produto, scale-up (persona de governança)
- **Contexto:** lidera 5 PMs em squads; quer padronização, rastreabilidade de decisão e previsibilidade.
- **JTBD:** *Quando reviso o trabalho do time, quero ver decisões, aprovações e qualidade de cada especificação num só lugar, para dar feedback sem reuniões extras.*
- **Tarefa avaliada:** revisar Visão geral + Especificação + Aprovação.
- **Jornada observada:**
  1. Gosta do painel “Qualidade da especificação” (Fontes / Hipóteses / Perguntas / Decisões).
  2. Estranha a mistura de vocabulário: “Nota Média” no Dashboard, “Score de Validação” na iniciativa.
  3. Relatório de validação inteiro em inglês: “não dá pra mandar esse print para a diretoria”.
  4. Botão “Aprovar versão” com aparência de desabilitado, mas sem texto explicando o pré-requisito.
- **Fala provável:** “A estrutura é a que eu queria. Falta acabamento para eu adotar como padrão do time.”
- **Nota (adoção pelo time):** 3/5

### 2.4 Diego Nakamura — Tech Lead que usa Cursor (persona da integração)
- **Contexto:** pareia com a PM; vive no Cursor; liga para contexto de produto dentro do editor e para backlog que reflita o código real.
- **JTBD:** *Quando pego uma história, quero consultar o PRD e as decisões direto do editor, para não alternar entre ferramentas.*
- **Tarefa avaliada:** “Usar IA no Cursor, VS Code ou outro agente” + repositório vinculado + refinamento de backlog.
- **Jornada observada:**
  1. Card na Visão geral é claro e tem chips “Cursor” / “VS Code ou outra” (bom).
  2. Na Especificação o mesmo conteúdo aparece como bloco lateral “Continuar em uma ferramenta externa” — o h2 lateral (20px) é **maior** que o título do card principal (14px), invertendo a hierarquia.
  3. O ícone `⌁` (ELECTRIC ARROW) não comunica “ferramenta externa/conexão”.
- **Fala provável:** “O fluxo de conexão é ok. Só não entendi por que o app me empurra pro Cursor em três telas diferentes.”
- **Nota (descobribilidade):** 4/5 · **Clareza visual:** 3/5

### 2.5 Ana Beatriz Lima — Product Ops / pesquisadora, baixa visão (persona de acessibilidade)
- **Contexto:** consolida dados de planilhas e automações; usa zoom de 150% e leitor de tela ocasionalmente.
- **JTBD:** *Quando chegam dados novos, quero conectá-los a iniciativas e ver o que mudou, para alimentar decisões de produto.*
- **Tarefa avaliada:** aba *Dados e insights*.
- **Jornada observada:**
  1. KPI “MCPs saudáveis 0/0” — jargão técnico para quem é de Ops.
  2. Botão “Conectar” das Planilhas é um botão nativo branco; “Registrar” é um link sublinhado; “+ Registrar automação existente” é texto roxo — **três estilos para a mesma intenção** na mesma lista.
  3. Em média **15 elementos de texto abaixo de 12px por tela** (pico de 28 em Dados e 29 no Mapa); badges “Beta” em 10px.
- **Fala provável:** “Com zoom dá pra usar, mas metade das legendas vira ruído. E eu não sei o que é MCP.”
- **Nota (acessibilidade percebida):** 2/5

### 2.6 Síntese entre personas

| Tema | Marina | Lucas | Helena | Diego | Ana |
|------|:-:|:-:|:-:|:-:|:-:|
| Muitos CTAs / caminhos duplicados | ● | | ● | ● | |
| Vocabulário (Nota vs Score, inglês, jargão) | | ● | ● | | ● |
| Mobile | | ● | | | |
| Controles fora da identidade visual | ● | | | | ● |
| Hierarquia tipográfica | | | ● | ● | ● |

---

## 3. Revisão por tela (novidades)

### Visão geral da iniciativa — `screens/desktop-initiative.png`
- ✅ Card “Próxima ação” com 5 caminhos é a melhor tela do produto.
- ⚠️ Topbar com 5 botões de pesos diferentes (secundário, Beta, ciano, secundário, âmbar). “Gerar PRD” em ciano compete com “Gerar nova versão” no bloco PRD. Sugestão: manter 1 primária contextual + menu “⋯”.
- ⚠️ Grade de 5 cards deixa o último órfão; usar 3+2 ou destacar o “Cursor” como banner full-width.
- ⚠️ Histórico de PRDs lista um item chamado **“validation”** — parece um arquivo de validação vazando para a lista de versões.
- ⚠️ `input type=file` nativo (“Choose Files / No file chosen”, em inglês) e botão “Upload” em inglês.

### Especificação — `screens/desktop-specification.png`
- ✅ Escolha de fonte (Dados / PRD atual / Enviar PRD pronto) é clara e resolve a dor do “começar do zero”.
- ⚠️ Stepper marca “1. Dados” como concluído sem dados reais.
- ⚠️ Hero com 4 colunas (texto, radios, select, contador, botão) — no desktop o botão “Gerar rascunho” fica a ~900px do texto que o explica. Sugestão: empilhar em 2 linhas.
- ⚠️ Coluna lateral com 5 cards cujos títulos (20px) são maiores que o título do formulário principal (14px).

### Dados e insights — `screens/desktop-data.png`
- ✅ Card de demonstração com selo EXEMPLO + empty state com ação.
- ⚠️ Empty states em layout de 3 colunas (título | descrição | ação) quebram a leitura; título em 16px bold compete com o título do card.
- ⚠️ Ícones de fonte: 🟩 (▦ verde), ⚡ emoji, ≡ — três linguagens visuais na mesma lista.

### Gerar PRD — `screens/desktop-generate.png`
- ✅ Aviso do modo Demo é exemplar.
- ⚠️ Caixa “Privacidade e tamanho estimado” usa 16px enquanto a vizinha “Contexto” usa 13px.
- ⚠️ Botão “Gerar e validar PRD” desabilitado em ciano escurecido parece apenas “apagado”; adicionar texto de motivo (“Selecione uma iniciativa”).

### Mobile — `screens/mobile-grid.png`
- 🔴 Visão geral ilegível (título vertical).
- ⚠️ Abas da iniciativa e do stepper cortam sem indicação de rolagem (sem fade/seta).
- ⚠️ Abas de Configurações (“Geral / Modelos de IA / Fontes externas / Extensões”) quebram em 2 linhas e a última sai da tela.

---

## 4. Análise de ícones

**Inventário (templates + i18n + tour.js):** 45 símbolos distintos. Os mais usados: ← (17), ✓ (15), ⚠ (13), ✕ (12), → (9), ✦ (7), 📄 (7), ◇ (6), ◆ (5), 🚀 (5).

| Problema | Exemplos | Impacto |
|----------|----------|---------|
| Duas famílias misturadas | geométricos monocromáticos (◈ ◇ ◆ ✦ ⌁ ▫) + emoji coloridos (📄 📁 👤 ⚡ 🚀 🎉 🔮 🧩) | Emoji herdam cor/estilo do SO (Apple ≠ Windows ≠ Linux); a sidebar fica com 📄 colorido entre glifos lilás |
| Metáfora fraca ou ambígua | ◇ = Gerar PRD, ◆ = Perguntar à base, ✦ = Configurações *e* Explorar com IA, ⌁ = ferramenta externa, ▫ = Arquivados | Usuário não aprende o ícone; ✦ significa “IA” e “sistema” ao mesmo tempo, contrariando a regra violeta/ciano |
| Duplicidade | ◈ para Dashboard e Roadmap | Navegação por reconhecimento falha |
| Peso óptico desigual | ▫ e + quase invisíveis; ◆ e 📄 pesados | Sidebar parece desalinhada |
| Ícones sem rótulo acessível | `nav-icon` sem `aria-hidden="true"` → leitores de tela anunciam “losango branco contendo losango preto pequeno, Dashboard” | Ruído para Ana (2.5) |

**Recomendação:** adotar um único set de ícones em SVG de traço (ex.: Lucide, MIT, 1.75px, 16/20px), servido como sprite local para não depender de CDN (coerente com uso offline/Ollama). Mapeamento sugerido:

| Item | Hoje | Proposto (Lucide) |
|------|------|-------------------|
| Dashboard | ◈ | `layout-dashboard` |
| Nova iniciativa | + | `plus-circle` |
| Gerar PRD | ◇ | `file-text` |
| Perguntar à base | ◆ | `message-circle-question` |
| Arquivados | ▫ | `archive` |
| Roadmap | ◈ | `map` / `gantt-chart` |
| Base de conhecimento | 📄 | `library` |
| Configurações | ✦ | `settings` |
| IA (qualquer ação) | ✦ | `sparkles` (sempre ciano) |
| Ferramenta externa / Cursor | ⌁ | `plug` |
| Planilhas / Automações / Arquivos | ▦ ⚡ ≡ | `sheet` / `workflow` / `files` |
| Editar | ✎ | `pencil` |
| Baixar | ⬇ | `download` |
| Arquivar (âmbar) / Excluir (coral) | 🗄 / ✕ | `archive` / `trash-2` |

Todos com `aria-hidden="true"` quando acompanhados de texto.

---

## 5. Análise de componentes

### 5.1 Botões
Variantes em uso: `btn-primary` (56), `btn-ghost` (45), `btn-secondary` (36), `btn-ai` (16), `btn-coral` (7), `btn-amber` (2), `btn-sm` (123). O sistema é bom; os problemas são de **aplicação**:
- Botões **fora do sistema**: “Sair” (sidebar), “Conectar” (Planilhas) e o `input type=file` renderizam como controles nativos claros.
- Links e botões alternam para a mesma intenção (“Registrar” sublinhado vs “Conectar” botão vs “+ Registrar automação” texto).
- Hierarquia: regra sugerida — **no máximo 1 primária (violeta) ou 1 IA (ciano) por região**; demais em `ghost`/`secondary`.

### 5.2 Formulários
- Radios e `select` da Especificação usam aparência do SO (azul/branco). Estilizar com `accent-color: var(--primary)` e `color-scheme: dark` em `:root` resolve a maior parte com 2 linhas de CSS.
- `input type=file`: envolver em `label.btn btn-secondary` com texto i18n (“Escolher arquivos”) e nome do arquivo ao lado.

### 5.3 Badges, tags e estados
- “Beta” (`spec-beta`, 10px) aparece em 4 lugares; ok, mas em 10px fica ilegível com zoom baixo — usar 11px + `letter-spacing`.
- Badge de status usa a chave crua → “discovery” (achado #2).
- Card de KPI “Score de segurança 0.0/10 · Crítico” deveria ter estado vazio (“Ainda não avaliado → Avaliar”) em vez de nota zero.

### 5.4 Cores e contraste (WCAG 2.x)
| Par | Contraste | Resultado |
|-----|-----------|-----------|
| `--text-muted` #8b88ad sobre card #14111f | 5.51:1 | AA ✓ |
| `--text-secondary` #9895b8 sobre bg #0f0d1e | 6.68:1 | AA ✓ |
| `--primary-light` #a996f5 sobre card | 7.41:1 | AAA ✓ |
| texto branco sobre `--primary` #6e56d9 | 5.26:1 | AA ✓ |
| texto #04252c sobre `--ai` #22b8d9 | 8.14:1 | AAA ✓ |

Ponto de atenção: o `btn-ai` usa texto escuro (correto); qualquer novo botão ciano com texto branco cairia para 2.35:1.

### 5.5 Dívida de estilo inline
`style="…"` por template: `config.html` 48, `generate.html` 37, `initiative_detail.html` 36, `validate.html` 30, `initiative_new.html` 30. Em runtime, Configurações renderiza **85** elementos com estilo inline. É a principal causa das inconsistências (o bug do mobile nasce de um `display:flex` inline sem `flex-wrap`). Sugestão: extrair `.topbar-actions`, `.workspace-badge`, `.sidebar-user` para `style.css`.

---

## 6. Análise de fontes

| Aspecto | Situação atual | Recomendação |
|---------|----------------|--------------|
| Família | `--font: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui` — renderiza San Francisco no Mac, Segoe no Windows, outra coisa no Linux. AGENTS.md promete **Inter** | Decidir: (a) empacotar **Inter Variable** em `static/fonts/` (woff2, ~300 KB, funciona offline) e colocar como primeira da pilha; ou (b) atualizar a documentação para “pilha do sistema” |
| Mono | `--font-mono` ok; `style.css:3383` força `"JetBrains Mono"` sem carregá-la → cai em outra fonte; versão da sidebar (`PM Studio v0.2.0`) em mono destoa | Usar `var(--font-mono)` em todo lugar; versão na sidebar em `--font` 11px |
| Escala | **32 tamanhos distintos** (mais usados: 13px ×120, 12px ×86, 14px ×65, 11px ×55, 10px ×37; além de 9, 10.5, 11.5, 12.5, 13.5, 15.5…) | Escala de 7 tokens: `--fs-xs 11` · `--fs-sm 12` · `--fs-base 13` · `--fs-md 14` · `--fs-lg 16` · `--fs-xl 26` · `--fs-2xl 32`; nada abaixo de 11px |
| Pesos | 400, 500, 600 (×70), **650**, 700 (×41), 800 (×14) | 400 texto · 500 UI · 600 títulos · 700 números/KPIs. 650 e 800 só se a fonte variável for adotada |
| Hierarquia | `page-title` 26px com gradiente → ok. Títulos de card 14px; títulos de card lateral (Especificação) 20px; empty-state 16px bold | `h2` de card = `--fs-md/600` em todo lugar; laterais nunca maiores que o principal |
| Texto pequeno | média de 15 elementos < 12px por tela; pico 29 (Mapa) | Legendas/hints em 12px; eyebrow (“PRÓXIMO PASSO RECOMENDADO”) pode ficar 11px uppercase com tracking |
| Título com gradiente | `-webkit-text-fill-color: transparent` → em `forced-colors`/alto contraste o título some | Adicionar `@media (forced-colors: active) { .page-title { -webkit-text-fill-color: CanvasText; background: none; } }` |

---

## 7. Plano priorizado

| Prioridade | Item | Esforço | Personas beneficiadas |
|-----------|------|---------|----------------------|
| P0 | Corrigir topbar mobile (`flex-wrap: wrap` em `.topbar-actions`, `h1` com `min-width: 0` e quebra por palavra; colapsar ações em menu “⋯” < 720px) | P | Lucas |
| P0 | Restaurar tradução de status (`"status." ~ status`) + teste de regressão | P | Lucas, Helena |
| P1 | Unificar indicador de modelo (sidebar reflete o provedor efetivo, incluindo Demo) | P | Marina, Lucas |
| P1 | `color-scheme: dark` + `accent-color` + estilizar Sair/Conectar/file input | P | Ana, Marina |
| P1 | Reduzir CTAs “Gerar PRD” para 1 por tela e deixar claro quando cria nova versão | M | Marina, Helena |
| P1 | Estado “não avaliado” para Score de segurança; “Score” → “Nota” | P | Lucas, Helena |
| P2 | i18n do relatório de validação + pluralização (`ngettext`-like helper no filtro `t`) | M | Helena |
| P2 | Set de ícones SVG único com `aria-hidden` | M | todos |
| P2 | Tokens de tipografia + migrar estilos inline dos 5 templates mais afetados | G | Ana, Diego |
| P3 | Fonte Inter empacotada (ou atualizar AGENTS.md) | P | — |

---

## 8. Próximo passo de pesquisa (com pessoas reais)

Roteiro de 30 min, 5 PMs (1 por persona), tarefas:
1. “Transforme o PRD atual desta iniciativa em especificação e aprove uma versão.” — mede confusão entre CTAs (§2.1).
2. “No celular, descubra em que fase está a iniciativa X.” — valida a correção P0 (§2.2).
3. “Conecte esta iniciativa ao seu editor.” — mede descobribilidade do Cursor (§2.4).
4. “Registre uma evidência vinda de uma planilha.” — testa a lista de fontes em Dados (§2.5).

Métricas: taxa de sucesso, tempo na tarefa, SEQ (1–7) por tarefa e SUS ao final. Comparar com as notas sintéticas acima para calibrar o método.

---

## 9. Status das correções (mesma PR)

Todas as correções foram verificadas no app rodando (capturas `*-after.png` em [`screens/`](screens/)) e cobertas por testes de regressão em `tests/test_web_e2e.py::TestSyntheticUserUIFindings`.

| # | Achado | Status | Como foi resolvido |
|---|--------|--------|--------------------|
| 1 | Título quebrando letra por letra no mobile | ✅ Corrigido | `.topbar` e `.topbar-actions` com `flex-wrap`; título com `min-width: 0` e quebra por palavra; no mobile as ações vão para a linha de baixo |
| 2 | Status “discovery” sem tradução | ✅ Corrigido | Chaves `status.*` restauradas e templates usando `"status." ~ status` |
| 3 | Modelo contraditório (Ollama × Demo) | ✅ Corrigido | Rótulo único `model_label` calculado no `_ctx`; ponto âmbar quando o provedor é Demo |
| 4 | Controles nativos fora do tema | ✅ Corrigido | `color-scheme: dark` + `accent-color`; “Sair” e “Conectar/Registrar” como `btn` (`btn-xs`); seletor de arquivos com botão e texto traduzidos (“Escolher arquivos”) |
| 5 | CTAs duplicados de “Gerar PRD” | ✅ Corrigido | Topbar só mostra “Gerar PRD” quando ainda não há PRD; card vira “Gerar nova versão do PRD — a atual continua no histórico”; removido o “Gerar PRD agora” do editor da Especificação |
| 6 | Relatório de validação em inglês | ✅ Corrigido | Rótulos estruturais (título, nota, resumo, seções) localizados na exibição; novos relatórios em pt-BR usam “**Nota:**” por seção |
| 7 | Vocabulário (Score × Nota, slug no título, separadores) | ✅ Corrigido | “Score” → “Nota”; títulos das abas usam o nome da iniciativa (`display_name`) e sempre “·” |
| 8 | Pluralização (“1 arquivos”) | ✅ Corrigido | Filtro `tn` com chave `.one` para singular (arquivos, validações, versões, fontes, itens, docs, linhas, colunas) |
| 9 | “Nota de segurança 0.0 — Crítico” sem avaliação | ✅ Corrigido | Estado “Não avaliado · Avaliar segurança →” até a primeira resposta |
| 10 | Ícones híbridos | ✅ Corrigido | Set único Lucide (SVG inline, offline, ISC) via `icon()`; `aria-hidden` por padrão; Roadmap e Dashboard com ícones distintos; emoji removidos da UI (o tour guiado mantém os seus) |
| 11 | Escala tipográfica | ✅ Corrigido | Tokens `--fs-*`; tamanhos fora da escala normalizados (nada abaixo de 11px); pesos 650/800 → 600/700 |
| 12 | Fonte documentada ≠ real | ✅ Corrigido | AGENTS.md atualizado para a pilha do sistema; “JetBrains Mono” não carregada substituída por `--font-mono` |
| — | Item “validation” no histórico de PRDs | ✅ Corrigido | `prd-validation*.md` não é mais listado como versão |
| — | Filtros do Feed de insights sem efeito | ✅ Corrigido | Botões filtram por métrica/feedback (com `aria-pressed`) e só aparecem quando há insights |
| — | Botão “Aprovar versão” desabilitado sem motivo | ✅ Corrigido | Texto explicando que é preciso salvar um rascunho; mesmo padrão no “Gerar e validar PRD” |
| — | Hierarquia invertida na lateral da Especificação | ✅ Corrigido | Títulos de cards laterais em `--fs-md`; hero da Especificação reorganizado em linhas |
| — | Abas cortadas no mobile | ✅ Corrigido | Fade lateral indicando rolagem em abas da iniciativa, stepper e Configurações |
| — | Estilos inline | ◐ Parcial | Extraídos os que causavam bugs (topbar, sidebar, seletor de workspace, abas de Configurações); o restante fica para uma limpeza dedicada |
