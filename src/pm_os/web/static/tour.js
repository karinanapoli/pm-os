/* ── PM OS Interactive Tour ── */

var PMOSTour = (function() {
    var currentStep = 0;
    var active = false;

    var i18n = {
        'pt-BR': {
            welcome: 'Bem-vindo ao PM OS',
            welcome_desc: 'Seu hub de iniciativas de produto. Em menos de um minuto você conhece os principais recursos.',
            sidebar: 'Menu de navegação',
            sidebar_desc: 'Acesse o Dashboard, gere PRDs, crie iniciativas e ajuste as configurações.',
            stats: 'Visão geral',
            stats_desc: 'Aqui você vê o total de iniciativas, PRDs gerados, documentos carregados e a nota média das validações.',
            initiative: 'Cartão de iniciativa',
            initiative_desc: 'Cada iniciativa é um cartão. Clique para ver detalhes, documentos e o PRD.',
            generate: 'Gerar PRD',
            generate_desc: 'Com um clique, a IA gera um PRD completo usando os documentos de contexto da iniciativa.',
            new_init: 'Nova iniciativa',
            new_init_desc: 'Crie uma iniciativa com nome, status e contexto inicial.',
            settings: 'Ajustes',
            settings_desc: 'Configure o modelo de IA, URL do Ollama e idioma da interface.',
            done: '🎉 Tudo pronto!',
            done_desc: 'Agora você conhece o PM OS. Crie sua primeira iniciativa e comece a construir.',
            skip: 'Pular',
            next: 'Próximo',
            prev: 'Anterior',
            finish: 'Finalizar',
            step: 'Passo',
            of: 'de',
        },
        'en': {
            welcome: 'Welcome to PM OS',
            welcome_desc: 'Your product initiative hub. Get to know the main features in under a minute.',
            sidebar: 'Navigation menu',
            sidebar_desc: 'Access the Dashboard, generate PRDs, create initiatives, and adjust settings.',
            stats: 'Overview',
            stats_desc: 'See total initiatives, PRDs generated, uploaded documents, and average validation score.',
            initiative: 'Initiative card',
            initiative_desc: 'Each initiative is a card. Click to view details, documents, and PRD.',
            generate: 'Generate PRD',
            generate_desc: 'With one click, AI generates a complete PRD using the initiative\'s context documents.',
            new_init: 'New initiative',
            new_init_desc: 'Create an initiative with a name, status, and initial context.',
            settings: 'Settings',
            settings_desc: 'Configure the AI model, Ollama URL, and interface language.',
            done: '🎉 All set!',
            done_desc: 'Now you know PM OS. Create your first initiative and start building.',
            skip: 'Skip',
            next: 'Next',
            prev: 'Previous',
            finish: 'Finish',
            step: 'Step',
            of: 'of',
        }
    };

    var steps = [
        { target: null, icon: '🚀', key: 'welcome', position: 'center' },
        { target: '.sidebar', icon: '📂', key: 'sidebar', position: 'right' },
        { target: '.stats-row', icon: '📊', key: 'stats', position: 'bottom' },
        { target: '.init-card', icon: '📋', key: 'initiative', position: 'top' },
        { target: 'a[href="/generate"]', icon: '📝', key: 'generate', position: 'right' },
        { target: 'a[href="/initiatives/new"]', icon: '➕', key: 'new_init', position: 'right' },
        { target: 'a[href="/config"]', icon: '⚙️', key: 'settings', position: 'right' },
        { target: null, icon: '🎉', key: 'done', position: 'center' },
    ];

    var lang = document.documentElement.lang || 'en';
    var t = i18n[lang] || i18n['en'];

    function createElements() {
        var overlay = document.createElement('div');
        overlay.className = 'tour-overlay';
        overlay.id = 'pmosTour';

        var backdrop = document.createElement('div');
        backdrop.className = 'tour-backdrop';
        overlay.appendChild(backdrop);

        var highlight = document.createElement('div');
        highlight.className = 'tour-highlight';
        highlight.id = 'tourHighlight';
        overlay.appendChild(highlight);

        var tooltip = document.createElement('div');
        tooltip.className = 'tour-tooltip';
        tooltip.id = 'tourTooltip';
        overlay.appendChild(tooltip);

        document.body.appendChild(overlay);
    }

    function handleKeydown(e) {
        if (!active) return;
        if (e.key === 'Escape') {
            e.preventDefault();
            PMOSTour.end();
        }
    }

    document.addEventListener('keydown', handleKeydown);

    function getElement(selector) {
        if (!selector) return null;
        var el = document.querySelector(selector);
        // Try fallback by text content
        if (!el) {
            var links = document.querySelectorAll('a, button, .nav-item');
            for (var i = 0; i < links.length; i++) {
                if (links[i].textContent.trim().toLowerCase() === selector.toLowerCase()) {
                    return links[i];
                }
            }
        }
        return el;
    }

    function getElementRect(el) {
        if (!el) return { top: 0, left: 0, width: 0, height: 0 };
        var rect = el.getBoundingClientRect();
        return {
            top: rect.top + window.scrollY,
            left: rect.left + window.scrollX,
            width: rect.width,
            height: rect.height,
            bottom: rect.bottom + window.scrollY,
            right: rect.right + window.scrollX,
        };
    }

    function showStep(index) {
        var stepList = window.__pmosSteps || steps;
        var step = stepList[index];
        if (!step) return;

        var overlay = document.getElementById('pmosTour');
        var tooltip = document.getElementById('tourTooltip');
        var highlight = document.getElementById('tourHighlight');

        // Set aria-live for accessibility
        tooltip.setAttribute('role', 'dialog');
        tooltip.setAttribute('aria-live', 'polite');
        tooltip.setAttribute('aria-label', (t[step.key] || step.key) + ' - ' + (t[step.key + '_desc'] || ''));

        currentStep = index;
        var title = t[step.key] || step.key;
        var desc = t[step.key + '_desc'] || '';
        var total = stepList.length;

        var isCenter = step.position === 'center';
        var targetEl = getElement(step.target);

        // Highlight
        if (targetEl && !isCenter) {
            var rect = targetEl.getBoundingClientRect();
            highlight.style.display = 'block';
            highlight.style.top = (rect.top + window.scrollY - 4) + 'px';
            highlight.style.left = (rect.left + window.scrollX - 4) + 'px';
            highlight.style.width = rect.width + 'px';
            highlight.style.height = rect.height + 'px';
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            highlight.style.display = 'none';
        }

        // Tooltip
        tooltip.className = 'tour-tooltip ' + (isCenter ? 'center' : '');
        tooltip.innerHTML = '' +
            '<div class="tour-tooltip-icon">' + step.icon + '</div>' +
            '<h3>' + title + '</h3>' +
            '<p>' + desc + '</p>' +
            '<div class="tour-tooltip-footer">' +
                '<span class="tour-step-indicator">' + t.step + ' ' + (index + 1) + ' ' + t.of + ' ' + total + '</span>' +
                '<div class="tour-actions">' +
                    (index > 0 ? '<button class="tour-btn tour-btn-ghost" onclick="PMOSTour.prev()">← ' + t.prev + '</button>' : '') +
                    (index < total - 1
                        ? '<button class="tour-btn tour-btn-ghost" onclick="PMOSTour.end()">' + t.skip + '</button>' +
                          '<button class="tour-btn tour-btn-primary" onclick="PMOSTour.next()">' + t.next + ' →</button>'
                        : '<button class="tour-btn tour-btn-primary" onclick="PMOSTour.end()">' + t.finish + ' ✓</button>'
                    ) +
                '</div>' +
            '</div>';

        // Position
        if (!isCenter && targetEl) {
            var rect = targetEl.getBoundingClientRect();
            var tip = tooltip.getBoundingClientRect();
            var top, left;

            switch (step.position) {
                case 'bottom':
                    top = rect.bottom + 12;
                    left = rect.left + rect.width / 2 - 190;
                    break;
                case 'top':
                    top = rect.top - tip.height - 12;
                    left = rect.left + rect.width / 2 - 190;
                    break;
                case 'right':
                    top = rect.top + rect.height / 2 - tip.height / 2;
                    left = rect.right + 16;
                    break;
                case 'left':
                    top = rect.top + rect.height / 2 - tip.height / 2;
                    left = rect.left - tip.width - 16;
                    break;
                default:
                    top = rect.bottom + 12;
                    left = rect.left + rect.width / 2 - 190;
            }

            // Clamp to viewport
            if (left < 8) left = 8;
            if (left + tip.width > window.innerWidth - 8) left = window.innerWidth - tip.width - 8;
            if (top < 8) top = 8;
            if (top + tip.height > window.innerHeight - 8) top = rect.top - tip.height - 12;

            tooltip.style.top = top + 'px';
            tooltip.style.left = left + 'px';
            tooltip.style.transform = 'none';
        }

        overlay.classList.add('active');
        active = true;
    }

    return {
        start: function() {
            if (!document.getElementById('pmosTour')) createElements();
            // Skip init-card step if no cards exist on dashboard
            var hasCards = document.querySelector('.init-card') || document.querySelector('.init-card-link');
            var filteredSteps = steps.filter(function(s) {
                if (s.target === '.init-card' && !hasCards) return false;
                return true;
            });
            // Reassign global steps if filtered
            window.__pmosSteps = filteredSteps;
            showStep(0);
        },
        next: function() {
            var stepList = window.__pmosSteps || steps;
            if (currentStep < stepList.length - 1) showStep(currentStep + 1);
        },
        prev: function() {
            if (currentStep > 0) showStep(currentStep - 1);
        },
        end: function() {
            var overlay = document.getElementById('pmosTour');
            if (overlay) overlay.classList.remove('active');
            active = false;

            // Dismiss onboarding
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '/onboarding/dismiss';
            form.style.display = 'none';
            document.body.appendChild(form);
            form.submit();
        },
        isActive: function() {
            return active;
        }
    };
})();
