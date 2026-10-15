import json

from pm_os.insights.agents import CustomerVoiceAgent, GapAgent, MetricsAgent, SynthesisAgent
from pm_os.insights.engine import InsightEngine, InsightStore
from pm_os.insights.models import InsightContext, SourceDocument, Spreadsheet

RESEARCH = """# Pesquisa
## Dores
1. **Processo manual**: 78% dos entrevistados usam planilhas e e-mails
2. **Retrabalho**: Cada consulta leva em média 45 minutos
## Preços de concorrentes
- Preço: R$ 2.500/mês
## Citações
> "Eu passo mais tempo procurando informação do que analisando fornecedor."
"""


def _sheet(values):
    return Spreadsheet("metricas.csv", [
        {"semana": f"S{index}", "tempo_medio_min": str(value)} for index, value in enumerate(values, 1)
    ])


def test_metrics_agent_reports_trend_with_first_and_last_evidence():
    context = InsightContext("INT-X", spreadsheets=[_sheet([14, 13, 9])])

    insights = MetricsAgent().analyze(context, [])

    assert len(insights) == 1
    assert insights[0].title == "tempo medio min caiu 36% (14 → 9)"
    assert [item.excerpt for item in insights[0].evidence] == ["S1: tempo medio min = 14", "S3: tempo medio min = 9"]
    assert insights[0].signal_type == "metric"


def test_metrics_agent_flags_anomaly_in_latest_record():
    context = InsightContext("INT-X", spreadsheets=[_sheet([10, 11, 10, 11, 9.4])])

    insights = MetricsAgent().analyze(context, [])

    assert [item.kind for item in insights] == ["anomaly"]


def test_metrics_agent_folds_anomaly_into_trend_of_same_metric():
    context = InsightContext("INT-X", spreadsheets=[_sheet([10, 11, 10, 11, 30])])

    insights = MetricsAgent().analyze(context, [])

    assert [item.kind for item in insights] == ["trend"]
    assert "desvios-padrão" in insights[0].summary


def test_metrics_agent_ignores_short_or_text_columns():
    short = InsightContext("INT-X", spreadsheets=[_sheet([1, 2])])
    text = InsightContext("INT-X", spreadsheets=[Spreadsheet("t.csv", [{"a": "x"}, {"a": "y"}, {"a": "z"}])])

    assert MetricsAgent().analyze(short, []) == []
    assert MetricsAgent().analyze(text, []) == []


def test_customer_voice_uses_pain_sections_and_quotes_but_not_prices():
    context = InsightContext("INT-X", documents=[SourceDocument("SRC-1", "pesquisa.md", RESEARCH)])

    insights = {item.key: item for item in CustomerVoiceAgent().analyze(context, [])}

    assert set(insights) == {"manual", "slowness"}
    assert len(insights["slowness"].evidence) == 2
    assert insights["slowness"].signal_type == "customer_feedback"
    assert all("R$" not in evidence.excerpt for item in insights.values() for evidence in item.evidence)


def test_gap_agent_points_to_missing_metrics_and_problem():
    context = InsightContext(
        "INT-X",
        spreadsheets=[_sheet([14, 13, 9])],
        documents=[SourceDocument("SRC-1", "pesquisa.md", RESEARCH)],
        specification={"problem": "", "metrics": ""},
    )
    prior = MetricsAgent().analyze(context, []) + CustomerVoiceAgent().analyze(context, [])

    keys = {item.key for item in GapAgent().analyze(context, prior)}

    assert keys == {"metrics-undefined", "problem-undefined"}


def test_engine_ranks_and_gives_stable_ids():
    context = InsightContext(
        "INT-X",
        spreadsheets=[_sheet([14, 13, 9])],
        documents=[SourceDocument("SRC-1", "pesquisa.md", RESEARCH)],
        specification={"problem": "", "metrics": ""},
    )

    first = InsightEngine().run(context)
    second = InsightEngine().run(context)

    assert [item.id for item in first] == [item.id for item in second]
    assert [item.score for item in first] == sorted((item.score for item in first), reverse=True)
    assert all(item.evidence for item in first)


def test_synthesis_cannot_touch_unknown_ids_and_survives_bad_output():
    context = InsightContext("INT-X", spreadsheets=[_sheet([14, 13, 9])])
    insight = MetricsAgent().analyze(context, [])[0]

    class Client:
        def generate(self, prompt):
            assert "tempo medio min" in prompt
            return json.dumps([
                {"id": insight.fingerprint, "title": "Consultas ficaram 36% mais rápidas", "implication": "Menos espera.", "recommendation": "Acompanhar semanalmente."},
                {"id": "metrics:trend:invented", "title": "Inventado"},
            ])

    class Broken:
        def generate(self, prompt):
            raise RuntimeError("offline")

    refined = SynthesisAgent(Client()).refine([insight], "pt-BR")
    untouched = SynthesisAgent(Broken()).refine(MetricsAgent().analyze(context, []), "pt-BR")

    assert refined[0].title == "Consultas ficaram 36% mais rápidas"
    assert refined[0].synthesized and refined[0].recommendation == "Acompanhar semanalmente."
    assert len(refined) == 1
    assert untouched[0].title.startswith("tempo medio min caiu") and not untouched[0].synthesized


def test_store_keeps_decisions_across_runs(tmp_path):
    context = InsightContext("INT-X", spreadsheets=[_sheet([14, 13, 9])])
    store = InsightStore()
    run = store.save_run(tmp_path, InsightEngine().run(context), agents=["metrics"], synthesized=False)
    insight_id = run["insights"][0].id

    store.set_status(tmp_path, insight_id, "accepted", "SIG-1")
    rerun = store.save_run(tmp_path, InsightEngine().run(context), agents=["metrics"], synthesized=False)

    assert rerun["insights"][0].status == "accepted"
    assert rerun["insights"][0].signal_id == "SIG-1"
    assert store.set_status(tmp_path, "INS-missing", "dismissed") is None
