# Sprint 005 Review

> "Async, accessible, and in your language — Sprint 005 made PM Studio production-ready for daily use."

---

# Sprint Objective

Eliminate blocking issues from Sprint 004 (sync generation, untranslated status, missing accessibility) and polish the UX through a systematic writing audit.

---

# Stories Delivered

## ✅ Story 1 — Async PRD Generation & Progress Bar

### Objective

The server should not freeze during the 5–7 minute PRD generation + validation cycle. The user should see what's happening.

### Deliverables

- `ThreadPoolExecutor` for background generation — server stays responsive;
- `generate_processing.html` — intermediate page with 4-step progress bar;
- `GET /generate/status/{task_id}` — polling endpoint returning JSON `{step, message, done, error}`;
- `GET /generate/result/{task_id}` — renders full result HTML when complete;
- `_gen_tasks` global dict tracks task state;
- `_get_initiative_by_name_sync()` — sync variant for background threads (no Request object);
- Progress bar CSS with animated fill, step dots, gradient.

---

## ✅ Story 2 — UX Writing Audit (P12–P18)

### Objective

Every user-facing string should be intentional, consistent, and localized. Remove technical jargon (Ollama) from user messages. Standardize terminology across pt-BR and EN.

### Deliverables

| Key | Before | After |
|-----|--------|-------|
| `nav.generate_prd` | Gerar documentação / Generate documentation | **Gerar PRD / Generate PRD** |
| `nav.qa` | Perguntas / Q&A | **Consultar Docs / Consult Docs** |
| `generate.cta` | Gerar documentação + Validar | **Gerar e validar PRD** |
| `error.ollama` | "Não foi possível conectar ao Ollama" | **Sem menção a Ollama** |
| `quickstart.prd_fail` | "Ollama pode estar offline" | **Sem menção a Ollama** |
| `loading.sub` | "Enquanto isso, revise os docs" | **"Só um instante"** |
| `validate.score_label` | "Score do PRD" | **"Nota do PRD"** |
| `validate.not_yet_desc` | "Clique em Revalidar" | **Descrição do que a validação faz** |
| `squad.leave_confirm` | "Tem certeza?" | **Explica consequência + como reverter** |
| `initiative.detail.validation_score` | "Score de Validação" | **"Nota de Validação"** |
| `generate.result_score` | "Score de validação" | **"Nota de validação"** |
| `dashboard.attention.cta_generate` | "Gerar documentação" | **"Gerar PRD"** |
| `onboarding.cta_generate` | "Gerar documentação" | **"Gerar PRD"** |
| `tour.js` | "Gerar documentação" | **"Gerar PRD"** |

Plus: `initiative.new.id_auto_generated`, `initiative.new.id_manual`, `initiative.new.in_workspace`, `generate.no_docs_badge`, `config.empty_plugins`, `app.skip_to_content` i18n keys added.

---

## ✅ Story 3 — Status Translation

### Objective

Initiative status ("discovery", "planning", etc.) displayed in English even when the UI was in pt-BR.

### Deliverables

- i18n keys added: `status.discovery`, `status.planning`, `status.development`, `status.completed`, `status.unknown`;
- Dashboard and initiative detail templates changed from `{{ status|t }}` to `{{ ("status." + status)|t }}`;
- English counterparts added for EN locale.

---

## ✅ Story 4 — Skip-link & Accessibility

### Objective

The skip-to-content link was verbose (29 chars), positioned via `top: -1000px` with a jarring jump animation.

### Deliverables

- Text shortened: "Pular para o conteúdo principal" → "Ir para conteúdo";
- CSS changed from `position: absolute; top: -1000px` → `fixed; transform: translateY(-100%)` — smooth slide-in;
- Full-width bar with bg-card background, centered text, subtle shadow;
- `aria-live="polite"`, `role="dialog"`, `aria-label` on tour tooltip;
- Escape key dismisses tour.

---

## ✅ Story 5 — Tour Auto-Trigger on First Visit

### Objective

Newly registered users should see the interactive tour without having to discover the "?" button.

### Deliverables

- `config_manager.set("onboarding_dismissed", False)` added to the registration handler;
- Ensures the config resets even if previously set to `True` by other users/testing.

---

## ✅ Story 6 — Hardcoded Strings Eliminated

### Objective

All hardcoded UI strings should pass through the i18n system.

### Deliverables

| Template | Line | Before | After |
|----------|------|--------|-------|
| `generate.html` | 41 | `sem docs` | `{{ "generate.no_docs_badge"|t }}` |
| `config.html` | 304 | `Em breve — extensões...` | `{{ "config.empty_plugins"|t }}` |
| `initiative_new.html` | 11 | `em` | `{{ "initiative.new.in_workspace"|t }}` |
| `initiative_new.html` | 12 | `"Pessoal"` | `{{ "squad.personal"|t }}` |
| `initiative_new.html` | 35,87,107 | `auto` | i18n key |
| `initiative_new.html` | 83 | `auto-gerado` | i18n key |
| `initiative_new.html` | 96,104 | `manual` | i18n key |
| `initiative_new.html` | 54 | `Observações` | `{{ "initiative.new.context"|t }}` |
| `initiative_new.html` | 55 | Placeholder hardcoded | i18n key |
| `initiative_new.html` | 56 | Hint hardcoded | i18n key |
| `tour.js` | 17 | `"Gerar documentação"` | `"Gerar PRD"` |

---

## ✅ Story 7 — PRDValidator Robustness

### Objective

PRDValidator should handle non-ideal AI output (strings instead of lists, truncated JSON, dicts inside issue lists).

### Deliverables

- `_ensure_list()` / `_ensure_str()` — normalize mixed AI responses;
- `_fix_json()` — repair trailing commas, single quotes, unbalanced braces, truncated JSON;
- `_flatten_item()` — convert dict-like issues/suggestions to readable strings;
- Retry logic (up to 3 attempts) for JSON parsing failures.

---

# Sprint Result

By the end of Sprint 005:

- **Async generation** — server stays responsive during PRD generation;
- **4-step progress bar** — visibility into what the AI is doing;
- **Status translated** — "Descoberta" instead of "discovery";
- **Consistent UX writing** — "Gerar PRD", "Consultar Docs", "Nota de Validação";
- **Zero hardcoded UI strings** — all pass through i18n;
- **Skip-link redesigned** — full-width bar, smooth animation;
- **Tour auto-triggers** on first login;
- **PRDValidator** handles malformed AI output gracefully;
- **151 tests passing** (up from 74 in Sprint 004);
- `user-journey.md` updated with async flow, sidebar structure, progress bar.

---

# Main Architectural Decisions

- Background processing uses in-process `ThreadPoolExecutor` — no external queue needed;
- Task state stored in-memory dict (`_gen_tasks`) — lost on server restart, acceptable for single-user;
- Status translation uses prefix pattern `("status." + status)|t` — consistent with timeline approach;
- Skip-link uses `transform: translateY()` — better performance than animating `top`.

---

# Next Sprint

- Create Backlog (user stories from PRDs);
- Smart OKRs;
- AI Prototyping;
- Security Score;
- Metrics Integration;
- Export/Import initiatives.
