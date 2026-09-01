import json
import re
from datetime import datetime, timezone

from pm_os.web.security_assessment_service import (
    SECURITY_DIMENSIONS,
    SECURITY_RISKS,
    SECURITY_STATUSES,
)


class SecurityAssessmentGenerationError(ValueError):
    """Raised when the provider does not return a usable security assessment."""


class SecurityAssessmentAIService:
    """Create a source-grounded, reviewable security assessment draft."""

    def build_prompt(self, context: str, lang: str = "pt-BR") -> str:
        language = "English" if lang == "en" else "Brazilian Portuguese"
        dimensions = ", ".join(SECURITY_DIMENSIONS)
        return f"""You are a senior Security by Design reviewer.
Analyze ONLY the source material below. Return valid JSON, without markdown, in {language}.
Never invent a control, implementation, owner, deadline, or evidence.
For every factual conclusion, cite one or more source IDs exactly as [SOURCE_ID].
If the material does not support a conclusion, use status \"not_assessed\", leave evidence empty,
and write the missing information as an actionable question in \"action\".
Use \"planned\" for an explicit intention, and \"implemented\" only for an explicitly implemented control.
Never use \"verified\": verification requires a human reviewer.

Return this exact shape:
{{
  "answers": {{
    "dimension_key": {{
      "status": "not_assessed|planned|implemented|not_applicable",
      "risk": "critical|high|medium|low",
      "evidence": "concise conclusion with [SOURCE_ID] citations",
      "action": "next action or question",
      "not_applicable_reason": "source-grounded reason or empty",
      "confidence": "high|medium|low",
      "source_ids": ["SOURCE_ID"]
    }}
  }}
}}

Required dimension keys: {dimensions}.

SOURCE MATERIAL
{context}
END SOURCE MATERIAL"""

    def generate(self, ai_client, context: str, existing: dict, lang: str = "pt-BR") -> dict:
        if not context.strip():
            raise SecurityAssessmentGenerationError("empty_context")
        raw = ai_client.generate(self.build_prompt(context, lang))
        payload = self._parse_json(raw)
        generated = payload.get("answers") if isinstance(payload, dict) else None
        if not isinstance(generated, dict):
            raise SecurityAssessmentGenerationError("invalid_response")

        valid_source_ids = self._source_ids(context)
        answers = {}
        existing_answers = existing.get("answers") or {}
        for dimension in SECURITY_DIMENSIONS:
            current = dict(existing_answers.get(dimension) or {})
            human_answer = (
                current.get("origin") != "ai"
                and current.get("status") not in {"", "not_assessed", None}
            )
            if current.get("status") == "verified" or human_answer:
                answers[dimension] = current
                continue
            answers[dimension] = self._normalize_answer(
                generated.get(dimension), valid_source_ids
            )
            for field in ("owner", "due_date"):
                if current.get(field):
                    answers[dimension][field] = current[field]
        return {
            "answers": answers,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_count": len(valid_source_ids),
        }

    def _normalize_answer(self, source, valid_source_ids: set[str]) -> dict:
        source = source if isinstance(source, dict) else {}
        status = str(source.get("status", "not_assessed"))
        if status not in SECURITY_STATUSES or status == "verified":
            status = "not_assessed" if status != "verified" else "implemented"
        risk = str(source.get("risk", "medium"))
        if risk not in SECURITY_RISKS:
            risk = "medium"
        evidence = str(source.get("evidence", "")).strip()[:4000]
        requested_ids = source.get("source_ids") or []
        if not isinstance(requested_ids, list):
            requested_ids = []
        cited_ids = {
            item for item in (str(value).strip() for value in requested_ids)
            if item in valid_source_ids
        }
        cited_ids.update(
            match.group(1)
            for match in re.finditer(r"\[([A-Za-z0-9_.:-]+)\]", evidence)
            if match.group(1) in valid_source_ids
        )
        if status in {"planned", "implemented", "not_applicable"} and not cited_ids:
            status = "not_assessed"
            evidence = ""
        not_applicable_reason = str(source.get("not_applicable_reason", "")).strip()[:4000]
        if status == "not_applicable" and not not_applicable_reason:
            status = "not_assessed"
        confidence = str(source.get("confidence", "low")).lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        return {
            "status": status,
            "risk": risk,
            "evidence": evidence,
            "action": str(source.get("action", "")).strip()[:4000],
            "owner": "",
            "due_date": "",
            "not_applicable_reason": not_applicable_reason,
            "origin": "ai",
            "confidence": confidence,
            "source_ids": ",".join(sorted(cited_ids)),
        }

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = str(raw or "").strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            text = fenced.group(1)
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, TypeError) as error:
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end <= start:
                raise SecurityAssessmentGenerationError("invalid_response") from error
            try:
                payload = json.loads(text[start:end + 1])
            except json.JSONDecodeError as nested_error:
                raise SecurityAssessmentGenerationError("invalid_response") from nested_error
        if not isinstance(payload, dict):
            raise SecurityAssessmentGenerationError("invalid_response")
        return payload

    @staticmethod
    def _source_ids(context: str) -> set[str]:
        ids = set(re.findall(r'<<<SOURCE id="([^"]+)"', context))
        ids.update(re.findall(r'<<<ARTIFACT id="([^"]+)"', context))
        ids.update(re.findall(r'<<<SIGNAL id="([^"]+)"', context))
        return ids
