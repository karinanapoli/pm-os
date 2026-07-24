import logging
from dataclasses import asdict, dataclass
from typing import Callable

from pm_os.citation_verifier import extract_source_ids, verify_citations
from pm_os.context_builder import ContextBuilder
from pm_os.domain.initiative import Initiative
from pm_os.infrastructure.ai.clients.ollama_client import OllamaConnectionError
from pm_os.infrastructure.utils import version_file
from pm_os.infrastructure.validators.prd_validator import PRDValidator
from pm_os.prompt_builder import PromptBuilder
from pm_os.web.generation_job_service import GenerationJob
from pm_os.writers.markdown_writer import MarkdownWriter

_logger = logging.getLogger("pm_os")


@dataclass
class PRDGenerationRequest:
    initiative_name: str
    selected: Initiative
    additional: list[str]
    selected_source_ids: set[str]
    source_selection_enabled: bool
    use_product_docs: bool
    use_mcp: bool
    squad_name: str
    lang: str


class PRDGenerationOperation:
    def __init__(
        self,
        ai_client_factory: Callable,
        initiative_loader: Callable,
        product_docs_service,
        mcp_context_loader: Callable,
        change_tracker_factory: Callable,
        translate: Callable,
    ):
        self.ai_client_factory = ai_client_factory
        self.initiative_loader = initiative_loader
        self.product_docs_service = product_docs_service
        self.mcp_context_loader = mcp_context_loader
        self.change_tracker_factory = change_tracker_factory
        self.translate = translate

    def run(self, job: GenerationJob, request: PRDGenerationRequest) -> None:
        try:
            self._run(job, request)
        except OllamaConnectionError:
            job.fail(self.translate("error.ollama", request.lang))
        except Exception as exc:
            _logger.exception("Background PRD generation failed")
            job.fail(str(exc))

    def _run(self, job: GenerationJob, request: PRDGenerationRequest) -> None:
        job.set_step(0, "active", self.translate("generate.progress_context", request.lang))
        ai_client = self.ai_client_factory()
        context_parts = []
        builder = ContextBuilder()
        main_context = (
            builder.build_selected(request.selected, request.selected_source_ids)
            if request.source_selection_enabled else builder.build(request.selected)
        )
        if main_context.strip():
            context_parts.append(
                f"--- Contexto Principal: {request.selected.name} ---\n\n{main_context}"
            )

        used_additional = []
        for name in request.additional:
            initiative = self.initiative_loader(name, request.squad_name)
            if not initiative or not initiative.documents:
                continue
            content = (
                builder.build_selected(initiative, request.selected_source_ids)
                if request.source_selection_enabled else builder.build(initiative)
            )
            if content.strip():
                context_parts.append(
                    f"--- Contexto Adicional: {initiative.name} ---\n\n{content}"
                )
                used_additional.append(name)

        used_product_docs = False
        if request.use_product_docs:
            content = self.product_docs_service.build_context()
            if content.strip():
                context_parts.append(f"--- Documentação complementar ---\n\n{content}")
                used_product_docs = True

        used_mcp = []
        if request.use_mcp:
            for item in self.mcp_context_loader():
                context_parts.append(
                    f"--- Contexto MCP: {item['name']} ---\n\n{item['content']}"
                )
                used_mcp.append(item["name"])

        context = "\n\n".join(context_parts)
        job.set_step(0, "done")
        job.set_step(1, "active", self.translate("generate.progress_generating", request.lang))
        prompt = PromptBuilder().build("create_prd", context, lang=request.lang)
        job.set_step(1, "done")
        job.set_step(2, "active")
        prd_content = ai_client.generate(prompt)
        citations = verify_citations(prd_content, extract_source_ids(context))

        artifacts = request.selected.path / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        version_file(artifacts / "prd.md")
        version_file(artifacts / "prd-validation.md")
        writer = MarkdownWriter()
        writer.write(prd_content, str(artifacts / "prd.md"))

        job.set_step(2, "done")
        job.set_step(3, "active", self.translate("generate.progress_validating", request.lang))
        report = PRDValidator(ai_client, request.lang).validate(prd_content)
        if report.is_valid:
            writer.write(
                report.to_markdown(request.lang),
                str(artifacts / "prd-validation.md"),
            )
        self.change_tracker_factory().update_manifest(str(request.selected.path))
        job.complete({
            "prd": prd_content,
            "score": report.overall_score,
            "sections": [asdict(section) for section in report.sections],
            "initiative": request.initiative_name,
            "additional": used_additional,
            "product_docs_used": used_product_docs,
            "mcp_used": used_mcp,
            "source_ids": citations.available_ids,
            "citation_report": asdict(citations),
        })
