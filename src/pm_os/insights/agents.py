"""Specialised insight agents.

Each agent reads only the ``InsightContext`` it is given and returns insights that
cite their evidence. The deterministic agents run fully offline (Demo included);
``SynthesisAgent`` optionally rewrites findings with an AI provider but can never
add facts or evidence.
"""

from __future__ import annotations

import json
import re
import statistics
import unicodedata

from pm_os.insights.models import Evidence, Insight, InsightContext, TextGenerator

_TEXTS = {
    "pt-BR": {
        "up": "subiu", "down": "caiu",
        "trend": "{metric} {direction} {pct}% ({first} → {last})",
        "trend_summary": "Na planilha {sheet}, {metric} foi de {first} ({first_label}) para {last} ({last_label}) em {n} registros.",
        "anomaly": "{metric} fora do padrão no último registro ({value})",
        "anomaly_summary": "O último valor de {metric} ({value}, {label}) está {sigma:.1f} desvios-padrão longe da média anterior ({mean}).",
        "theme": "Dor recorrente: {theme}",
        "theme_summary": "{mentions} menções em {sources} fonte(s) apontam para {theme}.",
        "gap_metrics": "Há dados de métricas, mas a especificação não define métricas de sucesso",
        "gap_metrics_summary": "As planilhas trazem {metrics}, que podem servir de base para as métricas da especificação.",
        "gap_metric_missing": "{metric} variou {pct}% e não aparece na especificação",
        "gap_metric_missing_summary": "A métrica muda de forma relevante, mas a especificação não a acompanha.",
        "gap_problem": "A especificação ainda não descreve o problema apontado nas fontes",
        "gap_problem_summary": "As fontes indicam {themes}, mas o campo Problema da especificação está vazio.",
        "themes": {
            "slowness": "lentidão e tempo perdido",
            "manual": "processos manuais",
            "errors": "erros e falhas",
            "delays": "atrasos e prazos",
            "scattered": "informação dispersa",
            "cost": "custo",
        },
    },
    "en": {
        "up": "rose", "down": "fell",
        "trend": "{metric} {direction} {pct}% ({first} → {last})",
        "trend_summary": "In {sheet}, {metric} went from {first} ({first_label}) to {last} ({last_label}) across {n} records.",
        "anomaly": "{metric} is off-pattern in the latest record ({value})",
        "anomaly_summary": "The latest {metric} value ({value}, {label}) is {sigma:.1f} standard deviations from the previous mean ({mean}).",
        "theme": "Recurring pain: {theme}",
        "theme_summary": "{mentions} mentions across {sources} source(s) point to {theme}.",
        "gap_metrics": "There is metric data, but the specification defines no success metrics",
        "gap_metrics_summary": "The spreadsheets include {metrics}, which could ground the specification metrics.",
        "gap_metric_missing": "{metric} changed {pct}% and is not in the specification",
        "gap_metric_missing_summary": "The metric moves meaningfully, but the specification does not track it.",
        "gap_problem": "The specification does not yet describe the problem found in the sources",
        "gap_problem_summary": "Sources point to {themes}, but the specification Problem field is empty.",
        "themes": {
            "slowness": "slowness and lost time",
            "manual": "manual processes",
            "errors": "errors and failures",
            "delays": "delays and deadlines",
            "scattered": "scattered information",
            "cost": "cost",
        },
    },
}

_THEME_TERMS = {
    "slowness": ("demor", "lent", "minuto", "horas", "tempo", "slow", "wait", "minutes", "hours"),
    "manual": ("manual", "planilh", "e-mail", "email", "copiar", "spreadsheet", "copy"),
    "errors": ("erro", "falha", "trava", "bug", "quebr", "error", "fail", "crash"),
    "delays": ("atras", "prazo", "late", "delay", "deadline"),
    "scattered": ("dispers", "sistemas", "silo", "scattered", "fragment"),
    "cost": ("custo", "caro", "preço", "cost", "expensive", "price"),
}
_PAIN_TERMS = (
    "reclam", "dor", "dores", "problema", "frustr", "difícil", "dificil", "perde", "não consegue",
    "nao consegue", "complain", "pain", "problem", "frustrat", "hard to", "struggle",
)


def _texts(lang: str) -> dict:
    return _TEXTS["en"] if lang == "en" else _TEXTS["pt-BR"]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _number(value: str) -> float | None:
    cleaned = (value or "").strip().replace("%", "").replace("R$", "").replace(" ", "")
    if not cleaned:
        return None
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(",") and cleaned.count("."):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _fmt(value: float) -> str:
    return f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _label(column: str) -> str:
    return column.replace("_", " ").strip()


class MetricsAgent:
    """Finds trends and anomalies in numeric spreadsheet columns."""

    name = "metrics"

    def analyze(self, context: InsightContext, prior: list[Insight]) -> list[Insight]:
        texts = _texts(context.lang)
        insights: list[Insight] = []
        for sheet in context.spreadsheets:
            if len(sheet.rows) < 3:
                continue
            columns = list(sheet.rows[0].keys())
            numeric = [col for col in columns if all(_number(row.get(col, "")) is not None for row in sheet.rows)]
            label_col = next((col for col in columns if col not in numeric), None)
            source_id = f"SHEET:{sheet.name}"
            for column in numeric:
                if label_col is None and column == columns[0]:
                    continue
                values = [_number(row[column]) for row in sheet.rows]
                labels = [row.get(label_col, str(index + 1)) if label_col else str(index + 1) for index, row in enumerate(sheet.rows)]
                first, last = values[0], values[-1]
                metric = _label(column)
                trend = None
                if first:
                    pct = (last - first) / abs(first) * 100
                    if abs(pct) >= 10:
                        trend = Insight(
                            agent=self.name, kind="trend", key=f"{sheet.name}:{column}",
                            title=texts["trend"].format(metric=metric, direction=texts["up"] if pct > 0 else texts["down"], pct=_fmt(round(abs(pct))), first=_fmt(first), last=_fmt(last)),
                            summary=texts["trend_summary"].format(sheet=sheet.name, metric=metric, first=_fmt(first), first_label=labels[0], last=_fmt(last), last_label=labels[-1], n=len(values)),
                            evidence=[
                                Evidence(source_id, sheet.name, f"{labels[0]}: {metric} = {_fmt(first)}"),
                                Evidence(source_id, sheet.name, f"{labels[-1]}: {metric} = {_fmt(last)}"),
                            ],
                            confidence=min(0.9, 0.5 + 0.05 * len(values)),
                            impact=min(1.0, abs(pct) / 50),
                            signal_type="metric",
                        )
                        insights.append(trend)
                previous = values[:-1]
                if len(previous) >= 4:
                    spread = statistics.pstdev(previous)
                    mean = statistics.mean(previous)
                    if spread and abs(last - mean) / spread >= 2:
                        sigma = abs(last - mean) / spread
                        anomaly_summary = texts["anomaly_summary"].format(metric=metric, value=_fmt(last), label=labels[-1], sigma=sigma, mean=_fmt(round(mean, 2)))
                        if trend is not None:
                            # One card per metric: the jump explains the trend, so it reinforces it.
                            trend.summary = f"{trend.summary} {anomaly_summary}"
                            trend.confidence = min(0.95, trend.confidence + 0.1)
                            continue
                        insights.append(Insight(
                            agent=self.name, kind="anomaly", key=f"{sheet.name}:{column}",
                            title=texts["anomaly"].format(metric=metric, value=_fmt(last)),
                            summary=anomaly_summary,
                            evidence=[Evidence(source_id, sheet.name, f"{labels[-1]}: {metric} = {_fmt(last)}")],
                            confidence=min(0.85, 0.4 + 0.05 * len(values)),
                            impact=min(1.0, sigma / 4),
                            signal_type="metric",
                        ))
        return insights


class CustomerVoiceAgent:
    """Groups pains, quotes and numbers found in documents into recurring themes."""

    name = "voice"

    def analyze(self, context: InsightContext, prior: list[Insight]) -> list[Insight]:
        texts = _texts(context.lang)
        themes: dict[str, list[Evidence]] = {}
        pain_terms = [_normalize(term) for term in _PAIN_TERMS]
        for document in context.documents:
            in_pain_section = False
            for raw in document.content.splitlines():
                stripped = raw.strip()
                if stripped.startswith("#"):
                    heading = _normalize(stripped.lstrip("#"))
                    in_pain_section = any(term in heading for term in pain_terms)
                    continue
                for sentence in re.split(r"(?<=[.!?])\s+", stripped):
                    line = sentence.strip().lstrip("-*>0123456789. ").replace("**", "").strip()
                    if len(line) < 15:
                        continue
                    normalized = _normalize(line)
                    is_quote = bool(re.search(r"[\"“”]", line))
                    is_pain = in_pain_section or any(term in normalized for term in pain_terms)
                    if not (is_pain or is_quote):
                        continue
                    theme = next(
                        (name for name, terms in _THEME_TERMS.items()
                         if any(_normalize(term) in normalized for term in terms)),
                        None,
                    )
                    if theme:
                        themes.setdefault(theme, []).append(Evidence(document.source_id, document.name, line[:240]))
        insights = []
        for theme, evidence in themes.items():
            sources = {item.source_id for item in evidence}
            quantified = any("%" in item.excerpt for item in evidence)
            if len(evidence) < 2 and len(sources) < 2 and not quantified:
                continue
            label = texts["themes"][theme]
            quotes = any(re.search(r"[\"“”]", item.excerpt) for item in evidence)
            insights.append(Insight(
                agent=self.name, kind="pain", key=theme,
                title=texts["theme"].format(theme=label),
                summary=texts["theme_summary"].format(mentions=len(evidence), sources=len(sources), theme=label),
                evidence=evidence[:4],
                confidence=min(0.9, 0.45 + 0.1 * len(evidence) + 0.1 * (len(sources) - 1)),
                impact=min(1.0, 0.3 + 0.15 * len(evidence)),
                signal_type="customer_feedback" if quotes else "research",
            ))
        return insights


class GapAgent:
    """Cross-checks what the data shows against what the specification says."""

    name = "gaps"

    def analyze(self, context: InsightContext, prior: list[Insight]) -> list[Insight]:
        texts = _texts(context.lang)
        spec_text = _normalize(" ".join(context.specification.values()))
        insights = []
        trends = [item for item in prior if item.agent == "metrics" and item.kind == "trend"]
        if context.spreadsheets and not context.specification.get("metrics", "").strip():
            metrics = sorted({_label(item.key.split(":", 1)[1]) for item in trends}) or [sheet.name for sheet in context.spreadsheets]
            insights.append(Insight(
                agent=self.name, kind="gap", key="metrics-undefined",
                title=texts["gap_metrics"],
                summary=texts["gap_metrics_summary"].format(metrics=", ".join(metrics[:4])),
                evidence=[evidence for item in trends[:2] for evidence in item.evidence[:1]] or [
                    Evidence(f"SHEET:{sheet.name}", sheet.name, sheet.name) for sheet in context.spreadsheets[:2]
                ],
                confidence=0.7, impact=0.6, signal_type="internal_hypothesis",
            ))
        elif spec_text:
            for item in trends:
                metric = _label(item.key.split(":", 1)[1])
                if _normalize(metric) not in spec_text and item.impact >= 0.4:
                    pct = re.search(r"(\d+)%", item.title)
                    insights.append(Insight(
                        agent=self.name, kind="gap", key=f"metric-missing:{item.key}",
                        title=texts["gap_metric_missing"].format(metric=metric, pct=pct.group(1) if pct else "?"),
                        summary=texts["gap_metric_missing_summary"],
                        evidence=item.evidence[:2], confidence=0.6, impact=item.impact * 0.8,
                        signal_type="internal_hypothesis",
                    ))
        pains = [item for item in prior if item.agent == "voice"]
        if pains and not context.specification.get("problem", "").strip():
            insights.append(Insight(
                agent=self.name, kind="gap", key="problem-undefined",
                title=texts["gap_problem"],
                summary=texts["gap_problem_summary"].format(themes=", ".join(item.title.split(": ", 1)[-1] for item in pains[:3])),
                evidence=[item.evidence[0] for item in pains[:3] if item.evidence],
                confidence=0.75, impact=0.7, signal_type="internal_hypothesis",
            ))
        return insights


class SynthesisAgent:
    """Rewrites deterministic findings with an AI provider, without adding facts or sources."""

    name = "synthesis"

    def __init__(self, client: TextGenerator):
        self.client = client

    def refine(self, insights: list[Insight], lang: str) -> list[Insight]:
        if not insights:
            return insights
        payload = [
            {"id": item.fingerprint, "title": item.title, "summary": item.summary,
             "evidence": [evidence.excerpt for evidence in item.evidence[:3]]}
            for item in insights[:12]
        ]
        language = "português do Brasil" if lang != "en" else "English"
        prompt = (
            "You are a senior product manager reviewing findings extracted from product data.\n"
            f"Write in {language}. For each finding return a JSON array of objects with the keys "
            '"id", "title", "implication" and "recommendation". Keep "id" exactly as given. '
            "Use ONLY the facts in the findings and their evidence; do not add numbers, sources or claims. "
            "Title: at most 90 characters. Implication and recommendation: one sentence each.\n\n"
            f"Findings:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            raw = self.client.generate(prompt)
            match = re.search(r"\[.*\]", raw or "", re.DOTALL)
            refined = json.loads(match.group(0)) if match else []
        except Exception:  # provider failures must never block deterministic insights
            return insights
        by_id = {item.fingerprint: item for item in insights}
        for entry in refined if isinstance(refined, list) else []:
            if not isinstance(entry, dict):
                continue
            target = by_id.get(str(entry.get("id", "")))
            if target is None:
                continue
            title = str(entry.get("title") or "").strip()
            if title:
                target.title = title[:120]
            target.implication = str(entry.get("implication") or "").strip()[:300]
            target.recommendation = str(entry.get("recommendation") or "").strip()[:300]
            target.synthesized = True
        return insights


DEFAULT_AGENTS = (MetricsAgent(), CustomerVoiceAgent(), GapAgent())
