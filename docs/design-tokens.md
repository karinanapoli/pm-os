# PM Studio — Design Tokens & Component Spec

> Versão 2.0 — Sistema de cores semânticas, modais de confirmação, toast e selo de reversibilidade.
> Baseado no protótipo navegável `pmos-redesign.html` e nas 11 correções do audit de UX.

---

## 1. Cores Semânticas

| Token | HEX | Uso | Significado |
|-------|-----|-----|-------------|
| `--amber` | `#f0a940` | Ações reversíveis (arquivar) | ⚠️ Atenção, mas pode voltar atrás |
| `--amber-dim` | `rgba(240,169,64,0.14)` | Fundo de badge/selo reversível | — |
| `--amber-border` | `rgba(240,169,64,0.3)` | Borda de botão âmbar | — |
| `--coral` | `#ef5a6f` | Ações permanentes (excluir, remover) | 🛑 Destrutivo, sem volta |
| `--coral-dim` | `rgba(239,90,111,0.14)` | Fundo de badge/selo permanente | — |
| `--coral-border` | `rgba(239,90,111,0.3)` | Borda de botão coral | — |
| `--success` | `#34d399` | Confirmação, restauro concluído | ✅ Tudo certo |
| `--warning` | `#f59e0b` | Score médio, alertas moderados | ⚠️ |
| `--danger` | `#ef4444` | Erro, score baixo | ❌ |

### Mapa de decisão cromática

```
Ação com consequência?
├── Sim, mas dá pra reverter → `--amber` + selo `seal-reversible`
├── Sim, e NÃO dá pra reverter → `--coral` + selo `seal-permanent`
└── Não, é informacional → cor do componente padrão (violet/teal)
```

---

## 2. Selo de Reversibilidade (`seal`)

Elemento de assinatura do sistema. Acompanha **toda** ação destrutiva ou semi-destrutiva.

```html
<span class="seal seal-reversible">↺ Reversível a qualquer momento</span>
<span class="seal seal-permanent">⚠ Não é possível desfazer</span>
```

### Variantes

| Classe | Cor | Ícone | Quando usar |
|--------|-----|-------|-------------|
| `seal-reversible` | `--amber` | ↺ | Archive, desativar MCP, qualquer ação com undo |
| `seal-permanent` | `--coral` | ⚠ | Excluir documento, remover servidor, delete permanente |

### Regras
1. O selo **sempre** aparece dentro do modal de confirmação, abaixo da descrição.
2. O selo **nunca** aparece isolado — sempre contextualizado por um título e descrição.
3. O selo pode aparecer inline (`<br><span class="seal ...">`) ou em bloco.

---

## 3. Modal de Ação (`modal-overlay` + `modal modal-sm`)

Substitui `confirm()` nativo. Estrutura fixa:

```html
<div class="modal-overlay" id="modal-{nome}">
    <div class="modal modal-sm">
        <div class="modal-icon-box {amber|coral}">🗄</div>           <!-- (1) -->
        <div class="modal-title">{{ "chave.titulo"|t }}</div>        <!-- (2) -->
        <div class="modal-desc">                                      <!-- (3) -->
            {{ "chave.descricao"|t }}
            <br><span class="seal seal-{reversible|permanent}">...</span>  <!-- (4) -->
        </div>
        <div class="modal-actions">                                    <!-- (5) -->
            <button class="btn btn-ghost btn-sm" onclick="PMOS.closeModal('{nome}')">
                {{ "chave.cancelar"|t }}
            </button>
            <button class="btn btn-{amber|coral} btn-sm" onclick="...">
                {{ "chave.confirmar"|t }}
            </button>
        </div>
    </div>
</div>
```

### Abrir/fechar via JS

```js
// Abrir
PMOS.openModal('archive')        // procura #modal-archive

// Fechar
PMOS.closeModal('archive')       // remove .active de #modal-archive

// Fechar clicando no backdrop (automático via base.html)
```

### Modais implementados

| ID | Cor | Ação | Selo |
|----|-----|------|------|
| `modal-archive` | amber | Arquivar iniciativa | `seal-reversible` |
| `modal-delete-doc` | coral | Excluir documento de contexto | `seal-permanent` |
| `modal-delete-mcp` | coral | Remover servidor MCP | `seal-permanent` |
| `modal-perm-archive` | coral | Arquivar permanentemente | `seal-permanent` |
| `modal-delete-link` | coral | Remover link de referência | `seal-permanent` |
| `modal-delete-doc` (product-docs) | coral | Excluir documento do hub | `seal-permanent` |

---

## 4. Toast (`toast-container` + `toast`)

Notificação não-bloqueante no canto inferior centralizado. Suporta ação "Desfazer".

```html
<div class="toast-container">
    <div class="toast" id="toast">
        <span class="toast-icon">✕</span>
        <span class="toast-text" id="toastText">Mensagem.</span>
        <button class="toast-undo" id="toastUndoBtn" onclick="PMOS.hideToast()">Desfazer</button>
    </div>
</div>
```

### API JS

```js
// Toast simples (some em 3.2s)
PMOS.toast('Arquivo excluído.')

// Toast com undo (some em 6s, botão "Desfazer" visível)
PMOS.toast('Arquivo excluído.', function() {
    // lógica de undo aqui
})

// Esconder manualmente
PMOS.hideToast()
```

### Comportamento
- Toast simples: desaparece em 3.2s
- Toast com undo: desaparece em 6s, botão "Desfazer" à direita
- Múltiplos toasts: o novo substitui o anterior (apenas um visível por vez)
- Undo: esconde o toast e executa callback; se o callback não for fornecido, não mostra o botão

---

## 5. Checkbox Group (`checkbox-group` + `checkbox-row` + `check-all-bar`)

Substitui `<select multiple>` nos formulários de Generate PRD e Consult.

```html
<div class="check-all-bar">
    <span class="hint" id="countEl">3 de 4 selecionadas</span>
    <button type="button" onclick="toggleAll(true)">Selecionar todas</button>
</div>
<div class="checkbox-group">
    <label class="checkbox-row">
        <input type="checkbox" name="items" value="a" checked>
        <span>Item A</span>
    </label>
    <label class="checkbox-row">
        <input type="checkbox" name="items" value="b">
        <span>Item B</span>
    </label>
</div>
```

### Regras
1. `check-all-bar` é opcional — usar quando houver 3+ itens
2. `checkbox-row` sempre dentro de `checkbox-group`
3. Checkboxes individuais (ex: "Incluir docs do produto") usam `checkbox-label` isolado, **não** `checkbox-row`

---

## 6. Botões (variações)

| Classe | Cor | Uso |
|--------|-----|-----|
| `btn btn-primary` | violet gradient | Ação primária (Gerar PRD, Salvar) |
| `btn btn-secondary` | surface + border | Ação secundária (Cancelar, Voltar) |
| `btn btn-ghost` | transparente | Ação terciária (links, toggle) |
| `btn btn-amber` | `--amber` | Ação reversível (Arquivar) |
| `btn btn-coral` | `--coral` | Ação destrutiva (Excluir) |

---

## 7. Status Badges

| Classe | Cor | Estado |
|--------|-----|--------|
| `badge-discovery` | `--primary-light` / violet | Descoberta |
| `badge-planning` | `--warning` / amber | Planejamento |
| `badge-development` | `--accent-light` / teal | Desenvolvimento |
| `badge-completed` | `--success` / green | Concluído |
| `badge-unknown` | `--text-muted` | Desconhecido |

---

## 8. Loading Overlay (ações)

O overlay de carregamento agora é contextualizado pelo atributo `data-loading`:

| `data-loading` | Texto exibido | Subtítulo |
|---------------|---------------|-----------|
| `processing` | Gerando com IA... | Revise os docs enquanto espera |
| `saving` | Salvando... | (vazio) |
| `deleting` | Excluindo... | (vazio) |
| `restoring` | Restaurando... | (vazio) |
| (default) | Processando... | (vazio) |

---

## 9. Componentes do Protótipo vs. Implementação Atual

| Componente | Protótipo | Implementado | Arquivo |
|------------|-----------|--------------|---------|
| Selo reversible/permanent | ✅ | ✅ | `style.css` |
| Modal de ação (archive) | ✅ | ✅ | `initiative_detail.html` |
| Modal de ação (delete doc) | ✅ | ✅ | `initiative_detail.html` |
| Modal de ação (delete MCP) | ✅ | ✅ | `config.html` |
| Modal de ação (perm archive) | ✅ | ✅ | `archived.html` |
| Modal de ação (delete link) | ✅ | ✅ | `product_docs.html` |
| Modal de ação (delete doc hub) | ✅ | ✅ | `product_docs.html` |
| Toast com undo | ✅ | ✅ | `base.html` |
| Checkbox group com select all | ✅ | ✅ | `generate.html`, `consult.html` |
| Botão âmbar | ✅ | ✅ | `style.css` |
| Botão coral | ✅ | ✅ | `style.css` |
| Stat card arquivado clicável | ✅ | ✅ | `dashboard.html` |
| Status badges traduzidos | ✅ | ✅ | (já implementado) |
| Loading contextual | ✅ | ✅ | `base.html` (já implementado) |
| Toggle MCP com verbo ação | ✅ | ✅ | `config.html` (já implementado) |
| Tela Arquivadas com restore | ✅ | ✅ | `archived.html` + `app.py` |
| Esc key no tour | ✅ | ✅ | `tour.js` (já implementado) |
| Aria-live no tour | ✅ | ✅ | `tour.js` (já implementado) |

---

## 10. Checklist de Implementação

- [x] Variáveis CSS (amber, coral, success, amber-dim, coral-dim, amber-border, coral-border)
- [x] Selo reversible (`seal-reversible`)
- [x] Selo permanent (`seal-permanent`)
- [x] Botão âmbar (`btn-amber`)
- [x] Botão coral (`btn-coral`)
- [x] Modal compacto (`modal-sm`)
- [x] Modal icon box (`modal-icon-box.amber`, `modal-icon-box.coral`)
- [x] Overlay de modal com backdrop blur
- [x] Fechar modal no backdrop click
- [x] Toast container + toast
- [x] Toast com undo
- [x] Checkbox group + checkbox-row
- [x] Check-all bar com contador e "Selecionar todas"
- [x] Stat card arquivado clicável
- [x] Status badges com cor por estágio
- [x] Loading contextual por ação
- [x] Toggle MCP com verbo de ação
- [x] Substituir `confirm()` por modal (templates)
- [x] Substituir `confirm()` nativo nos forms restantes
