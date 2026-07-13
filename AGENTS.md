# PM OS — Session Summary

## Context
- **Project**: PM OS, an open-source AI Product Manager Operating System
- **Mentor recommended**: gemma4:e2b model (still downloading in bg)
- **Language**: pt-BR default, English also supported
- **Target**: Product Managers
- **Architecture**: Core-first, decoupled via Protocols, Composition Root (bootstrap.py)
- **Ollama**: Running at localhost:11434

## Installed Models
| Model | Size | Status |
|-------|------|--------|
| llama3.2:1b | 1.3 GB | ✅ Active & configured |
| llama3.2 | 2.0 GB | ✅ Available |
| qwen2.5:7b | 4.7 GB | ✅ Available |
| gemma4:e2b | 7.2 GB | ⏳ Downloading in bg |

## Visual Identity (v2)
- Dark theme (`#0f0d1e` bg, `#16132b` cards)
- Purple/teal gradient accents
- Inter font
- Card-based layout with subtle borders/shadows
- Sidebar with sections: Discovery, Workspace, System
- Models configured in `static/style.css`

## Routes (app.py)
| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard with stats, initiative grid, onboarding |
| `/onboarding/show` | GET | Re-opens interactive tour |
| `/onboarding/dismiss` | POST | Dismisses onboarding |
| `/generate` | GET/POST | Generate PRD + auto-validate (supports cross-initiative context + product docs) |
| `/consult` | GET/POST | Q&A over product documentation + initiative docs |
| `/validate/{name}` | GET/POST | Validate existing PRD |
| `/config` | GET/POST | Model, URL, language settings |
| `/config/mcp/add` | POST | Add MCP server |
| `/config/mcp/toggle` | POST | Enable/disable MCP server |
| `/config/mcp/delete` | POST | Remove MCP server |
| `/initiatives/new` | GET/POST | Create new initiative |
| `/initiative/{name}` | GET | Initiative detail with docs, PRD, validation |
| `/initiative/{name}/upload` | POST | Multi-file upload (.md, .txt) |
| `/initiative/{name}/delete-doc` | POST | Delete context doc |
| `/initiative/{name}/delete` | POST | Archive initiative |
| `/product-docs` | GET | Manage product documentation hub |
| `/product-docs/upload` | POST | Upload product docs (.md, .txt) |
| `/product-docs/add-link` | POST | Add reference link (Google Sites, Drive, etc.) |
| `/product-docs/delete-doc/{filename}` | POST | Delete product document |
| `/product-docs/delete-link` | POST | Delete reference link |

## Templates (Jinja2)
All templates use `|t` filter for i18n:
- `base.html` — Layout, sidebar with "?" tour button, "Docs do Produto" + "Consult Docs" links, loading overlay
- `dashboard.html` — Stats row, initiative grid, empty state, tour trigger
- `generate.html` — Initiative selector, multi-select for additional context, product docs checkbox, result with sections + PRD preview
- `consult.html` — Q&A form with initiative multi-select + product docs checkbox, answer with references
- `validate.html` — Validation report with scores per section
- `config.html` — Model, URL, language selector
- `initiative_new.html` — Create form with auto-ID
- `initiative_detail.html` — Detail view, doc list, upload, delete
- `product_docs.html` — Document list, upload form, link manager

## i18n (`src/pm_os/web/i18n.py`)
- Two languages: `pt-BR` (default) and `en`
- Accessed via `{{ "key"|t }}` filter in templates
- Language set in config page (`/config`)
- Stored in `~/.pm_os/config.json` as `lang` field

## Features Built

### Onboarding & Tour
- **Interactive tour** (`static/tour.js` + `static/tour.css`):
  - 8 steps with tooltips pointing to UI elements
  - Highlight glow on target elements
  - Skip/Next/Previous/Finish buttons
  - Auto-dismisses onboarding on finish
  - Re-trigger via "?" button in sidebar footer
  - i18n in both languages
- Fallback: dismissed via `config.json` `onboarding_dismissed` flag

### Initiative Management
- Create initiative with name, ID, status, initial context
- Auto-generate ID from name (`INT-{NAME}`)
- Archive (not delete) with timestamp to `workspace/archived/`
- Archive confirmation dialog
- Dashboard shows archived count

### Document Management
- Multi-file upload (`<input type="file" multiple>`)
- Accepts .md and .txt files
- List docs with sizes, delete individual docs
- Change Tracker updates manifest on changes

### PRD Workflow
1. Change Tracker → detect new/modified files
2. Scope Guard → analyze context for vague scope
3. AI generates PRD (llama3.2:1b)
4. PRD Validator → evaluate quality
5. Results displayed: score + section breakdown + PRD preview

### Cross-Initiative Context (new)
- On `/generate`, multi-select "Contexto Adicional" lists all other initiatives
- Selected initiatives' documents are included as labeled extra context in the PRD prompt
- JS auto-filters the selected main initiative from the additional list
- Result section shows which additional initiatives were used

### Documentation Q&A (new)
- `/consult` page with text input + initiative multi-select + product docs checkbox
- AI answers questions based on documents from selected initiatives and/or product docs
- Answer includes references (initiative names mentioned in the AI response)
- Prompt instructs AI to cite sources and admit when info is not found

### Product Documentation Hub (new)
- Central repository at `workspace/product-docs/` for product-level documentation
- Upload `.md` and `.txt` files independent of any initiative
- Add reference links (Google Sites, Google Drive, etc.) stored in `links.json`
- Manage documents and links via `/product-docs` page
- Content can be toggled as context in PRD generation (checkbox on `/generate`)
- Content can be toggled as context in Q&A consultation (checkbox on `/consult`)

## UX Fixes (11 findings resolved)

| # | Priority | Issue | Fix |
|---|----------|-------|-----|
| P1 | CRITICAL | Archived initiatives can't be restored | Added `/archived` GET route + `/archived/restore` POST, created `archived.html` template, sidebar link from dashboard stat |
| P2 | CRITICAL | Destructive actions (delete doc, link, MCP) lack `confirm()` | Added `onsubmit="return confirm('...')"` with i18n key `archive.confirm_delete`/`mcp.confirm_delete` on all destructive forms |
| P3 | HIGH | Tour breaks when no `.init-card` exists (first visit) | `tour.js` checks for `.init-card`/`.init-card-link` on start; filters out step if absent |
| P4 | HIGH | Initiative status rendered raw (`discovery`) instead of translated | Added `|t` filter to `{{ init.status }}` in `dashboard.html` and `{{ metadata.status }}` in `initiative_detail.html` |
| P5 | HIGH | Hardcoded strings bypass i18n | Migrated to `|t` keys: `generate.initiative_hint`, `generate.issues`, `generate.suggestions`, `generate.product_docs_badge`, `validate.issues`, `validate.suggestions`, `consult.references`, `dashboard.stats.archived`, `initiative.new.name_hint`, `initiative.new.id_hint` |
| P6 | MEDIUM | `<select multiple>` requires Cmd/Ctrl+click | Replaced with `<div class="checkbox-group">` of `<label class="checkbox-label"><input type="checkbox">` in `generate.html` and `consult.html`; updated JS filtering to hide/show checkboxes |
| P7 | MEDIUM | MCP toggle shows result state ("Inativo") instead of action ("Desativar") | Changed labels to `mcp.activate`/`mcp.deactivate` action verbs |
| P8 | MEDIUM | Loading overlay text is generic for all operations | Added `data-loading` attribute on forms (`processing`, `saving`, `deleting`, `restoring`); base.html JS reads it to set dynamic text via `loading.*` i18n keys |
| P9 | LOW | `"✓"` shown when validation score is unreadable (wrongly implies perfect) | Changed to `"-"` in `app.py:197` |
| P10 | LOW | Same "✕" icon for archive and permanent delete | Archive (reversible) keeps soft icon button; permanent deletes get explicit "Excluir" button text |
| P11 | LOW | Tour lacks keyboard focus management, Esc key, aria-live | Added `aria-live="polite"`, `role="dialog"`, `aria-label` on tooltip; `Escape` key handler dismisses tour |

## Key UX Writing Decisions
- "Gerando com IA..." instead of "Processando..."
- "Enquanto isso, revise os documentos" instead of "Isso pode levar minutos"
- "Pular" instead of "Depois"
- "Salvar" instead of "Salvar Configurações"
- "Nota Média" instead of "Média de Validação"
- Archive confirm: "pode ser restaurada depois" (reversible tone)

## Config (`~/.pm_os/config.json`)
```json
{
  "model": "llama3.2:1b",
  "ollama_url": "http://localhost:11434",
  "lang": "pt-BR",
  "onboarding_dismissed": false,
  "mcp_servers": [
    {"name": "Web Search", "url": "http://localhost:3000/mcp", "enabled": true}
  ]
}
```

## Files to Reference
- `src/pm_os/web/app.py` — All route handlers
- `src/pm_os/web/templates/` — All 10 Jinja2 templates (incl. `archived.html`)
- `src/pm_os/web/static/style.css` — Complete CSS (880 lines)
- `src/pm_os/web/static/tour.js` — Interactive tour engine
- `src/pm_os/web/static/tour.css` — Tour overlay styles
- `src/pm_os/web/i18n.py` — Translation dicts (pt-BR + en)
- `src/pm_os/web/config_manager.py` — Config persistence
- `scripts/run_web.py` — Entry point (uvicorn with reload)

## Tests
- 25 unit tests pass
- Run: `.venv/bin/python -m pytest tests/ -v`

## Running
```bash
python scripts/run_web.py
# Opens at http://localhost:8000
```
