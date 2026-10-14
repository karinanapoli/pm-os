# PM Studio — Bateria de testes com usuários sintéticos (rodada 3)

> **Base:** `main` @ `c7da559` (após #60 e #61). Instalação nova, provedor **Demo**, idioma pt-BR (e EN para uma persona).
> **Método:** 9 personas, 40 passos executados no navegador (Playwright) em workspace isolado. Em cada passo foram coletados automaticamente: sucesso/falha, tempo, avisos exibidos, erros de JavaScript, respostas HTTP ≥ 400, chaves de tradução vazando, campos sem rótulo, botões sem nome e número de `h1`.
> **Lembrete:** personas e falas são sintéticas. Os problemas listados foram **reproduzidos** no app; já a priorização e as ideias de funcionalidade são hipóteses a validar com PMs reais.

## Resultado geral

| Persona | Perfil | Jornada | Passos | Resultado |
|---------|--------|---------|:-:|-----------|
| Lucas | APM, celular | Estado vazio → tour → 1ª iniciativa → menu → backlog inicial | 5 | ✅ fluida |
| Marina | PM pleno | Docs → validar PRD externo → spec automática → entregáveis | 6 | ⚠️ PRD validado “some” da jornada; spec Demo com texto genérico |
| Helena | Head de Produto | Criar squad → iniciativa no squad → decisões → arquivar/restaurar → portfólio | 7 | ⚠️ restauração sem confirmação; sem visão entre squads |
| Ana | Product Ops | Extrair sinais de arquivo → vincular → listar | 4 | ⚠️ 4 feedbacks viraram 1 sinal |
| Diego | Tech Lead | Backlog → exportar para GitHub → confirmar → Cursor | 4 | 🔴 **erro 500 ao preparar exportação** (corrigido nesta branch) |
| Bia | PM de segurança | Avaliação de segurança → rascunho IA → 1 dimensão → nota | 4 | ⚠️ nota “Crítico” após a 1ª resposta positiva |
| Paulo | PM de plataforma | Base de conhecimento: doc + link → consulta | 3 | ✅ |
| Joana | Navega só por teclado | Skip link → sidebar → formulário | 3 | ✅ skip link e ordem de foco corretos |
| Rafael | PM em inglês | Trocar idioma → 15 páginas | 4 | ✅ nenhum texto em português vazando |

**Saúde técnica:** nenhum erro de JavaScript fora o 500 da exportação; nenhuma chave de tradução vazando (os alertas do probe eram nomes de arquivo, como `prd.md`); uma `h1` por página; tempo médio por passo de 0,85 s.

---

## 1. Problemas encontrados

| # | Problema | Persona | Severidade | Evidência |
|---|----------|---------|-----------|-----------|
| P1 | **Exportar backlog dava erro 500** ao abrir o pacote preparado: `preview.items` resolvia para o método `dict.items`. Atingia todo mundo que exporta, e o teste existente não abria a página. | Diego | 🔴 Crítico | ✅ **Corrigido** em `2ebcde4`, com o teste ampliado para abrir as páginas de prévia e de confirmação |
| P2 | Depois de **validar um PRD enviado**, a página trata o arquivo como “prd.md — documento oficial” e oferece “Validar PRD atual”. A nota passa a aparecer como nota da iniciativa, mas a Visão geral mostra “PRD: Ainda não”, e a Especificação não aceita esse PRD como fonte. | Marina | 🟠 Alto | `screens/battery-validate-external-prd.png` |
| P3 | Em **Demo**, “Gerar rascunho com dados e contexto” preenche a especificação com o texto genérico do PRD de exemplo (“Informações de produto ficam dispersas…”), que não vem dos documentos da pessoa. | Marina | 🟠 Alto | `screens/battery-demo-spec-draft.png` |
| P4 | A **extração de sinais** sem IA juntou 4 feedbacks distintos (2 citações, 1 métrica de NPS, 1 contagem de reclamações) em **uma** sugestão, com título truncado e tipo “Pesquisa/entrevista”. A lista mostra “1 sinais”. | Ana | 🟠 Alto | log da bateria |
| P5 | **Nota de segurança punitiva:** marcar 1 de 6 dimensões como “Implementado” leva de “Não avaliado” para **1.2/10 Crítico**. | Bia | 🟡 Médio | `screens/battery-security-score.png` |
| P6 | **Arquivar e restaurar** respondem ao POST sem redirecionar (a URL fica `/initiative/X/delete` e `/archived/restore`), e restaurar não mostra confirmação. Atualizar a página reenvia a ação. | Helena | 🟡 Médio | `screens/battery-restore-no-feedback.png` |
| P7 | “Rascunho de segurança com IA” no Demo só avisa **depois** do clique; é o mesmo padrão já corrigido em Gerar PRD. | Bia | 🟡 Médio | log da bateria |
| P8 | Squad ativo na sidebar: texto cinza sobre o gradiente violeta, com contraste baixo; a contagem de membros fica quase invisível (estilos inline). | Helena | 🔵 Baixo | `screens/battery-restore-no-feedback.png` |

## 2. Insights por persona

- **Marina — “o que eu valido deveria virar meu PRD”.** Validar um PRD feito fora do PM Studio é um ótimo ponto de entrada, mas o resultado não aproveita a jornada: o PRD não é adotado, a especificação não parte dele e o backlog também não.
- **Helena — “gerencio vários squads, não um”.** Criar o squad e alternar de workspace funciona, mas o Dashboard mostra um workspace por vez. A Memória de decisões começa vazia, sem sugestão de onde vêm as decisões.
- **Ana — “cada evidência é um sinal”.** O valor da tela está em transformar um relatório em vários sinais revisáveis; juntar tudo em um elimina esse valor.
- **Bia — “quero ver progresso, não reprovação”.** Uma avaliação em andamento precisa mostrar cobertura (quantas dimensões avaliadas) antes de uma nota.
- **Diego — “exportar é o momento da verdade”.** É a etapa que leva o trabalho do PM para o time de engenharia; um erro 500 aqui mina a confiança no produto inteiro.
- **Lucas, Paulo, Joana e Rafael:** jornadas sem atrito relevante. Celular, tour, base de conhecimento, teclado e inglês estão sólidos.

## 3. Melhorias e novas funcionalidades propostas

Priorização por impacto nas jornadas × esforço estimado.

| # | Proposta | Tipo | Resolve | Impacto | Esforço |
|---|----------|------|---------|:-:|:-:|
| F1 | **Especificação automática local (sem IA):** mapear títulos e listas dos documentos e do PRD (“Problema”, “Requisitos”, “Métricas”, “Riscos”…) para os campos da spec, com citação `[SRC-…]`. É a visão do produto (spec preenchida a partir de dados, documentos e PRD) funcionando já no Demo. | Funcionalidade | P3 | Alto | Médio |
| F2 | **“Adotar como PRD da iniciativa”** ao validar um documento enviado: versiona o atual, passa a ser o `prd.md` e libera spec e backlog a partir dele. Sem adoção, a nota fica só no relatório do arquivo, não na iniciativa. | Funcionalidade | P2 | Alto | Baixo |
| F3 | **Detecção de provedor local:** se o Ollama responder em `localhost:11434`, oferecer “Usar Ollama · llama3.2” em um clique no Dashboard e nos avisos de Demo. A maior parte dos bloqueios de jornada vem de o Demo ser o padrão. | Funcionalidade | P3, P7 e rodada 2 | Alto | Baixo |
| F4 | **Extração de sinais item a item:** separar por bullet ou citação, inferir o tipo (número ou percentual → métrica; citação → feedback), deduplicar e permitir **confirmar vários de uma vez**. | Melhoria | P4 | Alto | Médio |
| F5 | **Visão de portfólio:** uma tela com todas as iniciativas dos squads da pessoa (status, PRD, nota, decisões vigentes, pendências de segurança, última atividade). | Funcionalidade | Helena | Médio | Médio |
| F6 | **Cobertura antes da nota de segurança:** “2 de 6 dimensões avaliadas”; nota exibida como “parcial” até um mínimo de dimensões avaliadas. | Melhoria | P5 | Médio | Baixo |
| F7 | **Aviso de Demo antes do clique** também em Segurança e em Especificação, reaproveitando o componente de Gerar PRD. | Melhoria | P7 | Médio | Baixo |
| F8 | **Decisões sugeridas:** detectar frases de decisão nos documentos e no PRD (“decidimos”, “não faremos”, “fica fora”) e propor registros revisáveis. | Funcionalidade | Helena | Médio | Médio |
| F9 | **Comparar versões do PRD** (diff entre versões do histórico) e mostrar a nota de cada uma. | Funcionalidade | Marina, Helena | Médio | Médio |
| F10 | Padrão POST → redirect → GET com toast em arquivar e restaurar. | Correção | P6 | Baixo | Baixo |
| F11 | Squad ativo na sidebar com classes do design system (contraste AA). | Correção | P8 | Baixo | Baixo |

### Sequência sugerida
1. **Agora (baixo esforço, destrava jornadas):** F2, F3, F6, F7, F10, F11.
2. **Próximo ciclo (valor central do produto):** F1 e F4, que fazem o PM Studio entregar valor mesmo sem IA configurada.
3. **Depois (escala para lideranças):** F5, F8 e F9.

## 4. Como reproduzir

O roteiro da bateria fica fora do repositório (scratchpad da sessão). Para transformá-lo em teste permanente, o caminho natural é um job opcional de Playwright no CI rodando as jornadas de Lucas, Marina e Diego.
