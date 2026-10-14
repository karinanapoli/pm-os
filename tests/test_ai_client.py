from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient


def test_ai_client_generates_fake_prd():
    client = FakeAIClient()

    result = client.generate("Test prompt")

    assert "# PRD demonstrativo" in result
    assert "Nenhum conteúdo foi enviado" in result
    assert "Test prompt" not in result


def test_ai_client_follows_english_prd_language():
    client = FakeAIClient()

    result = client.generate("Create a complete PRD in Markdown")

    assert result.startswith("# Demo PRD")
    assert "## Security by Design" in result
    assert "To be defined" in result


def test_demo_client_answers_validation_prompts_with_valid_report():
    from pm_os.infrastructure.validators.prd_validator import PRDValidator

    for lang in ("pt-BR", "en"):
        report = PRDValidator(FakeAIClient(), lang).validate("# PRD\n\n## Problema\nTexto.")

        assert report.is_valid
        assert report.overall_score == 7.5


def test_demo_client_answers_questions_with_cited_source_excerpts():
    from pm_os.prompt_builder import PromptBuilder

    context = (
        '<<<SOURCE id="SRC-AB12CD34" name="pesquisa.md" type="file" confidentiality="internal" '
        'author="x" modified="y">>>\n'
        "## Dores\n"
        "1. **Processo manual**: 78% dos analistas usam planilhas e e-mails\n"
        "Tempo médio de consulta: 14 minutos\n"
        '<<<END SOURCE id="SRC-AB12CD34">>>'
    )
    prompt = PromptBuilder().build("consult", context, "Quais as dores dos analistas?", lang="pt-BR")

    answer = FakeAIClient().generate(prompt)

    assert answer.startswith("**Modo Demo")
    assert "Processo manual: 78% dos analistas usam planilhas e e-mails [SRC-AB12CD34]" in answer
    assert "PRD demonstrativo" not in answer


def test_demo_client_says_when_no_excerpt_matches():
    from pm_os.prompt_builder import PromptBuilder

    context = '<<<SOURCE id="SRC-AB12CD34" name="a.md" type="file">>>\nNada relacionado aqui.\n<<<END SOURCE id="SRC-AB12CD34">>>'
    prompt = PromptBuilder().build("consult", context, "Which pricing tiers exist?", lang="en")

    answer = FakeAIClient().generate(prompt)

    assert "could not find excerpts" in answer
