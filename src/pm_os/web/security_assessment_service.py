import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path


SECURITY_DIMENSIONS = (
    "data_privacy", "access_control", "threat_abuse",
    "data_protection", "compliance", "operations",
)
SECURITY_STATUSES = ("not_assessed", "planned", "implemented", "verified", "not_applicable")
SECURITY_RISKS = ("critical", "high", "medium", "low")
_STATUS_POINTS = {"not_assessed": 0.0, "planned": 0.35, "implemented": 0.7, "verified": 1.0}


class SecurityAssessmentValidationError(ValueError):
    pass


class SecurityAssessmentService:
    """Persist an auditable, evidence-based initiative security review."""

    filename = "security-assessment.json"

    def __init__(self):
        self._lock = threading.RLock()

    def _empty_answer(self) -> dict:
        return {
            "status": "not_assessed", "risk": "medium", "evidence": "",
            "action": "", "owner": "", "due_date": "", "not_applicable_reason": "",
            "origin": "", "confidence": "", "source_ids": "",
        }

    def load(self, initiative_path: Path) -> dict:
        path = initiative_path / "artifacts" / self.filename
        saved = {}
        if path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                saved = {}
        answers = {}
        for key in SECURITY_DIMENSIONS:
            source = ((saved.get("answers") or {}).get(key) or {})
            answer = self._empty_answer()
            answer.update({field: str(source.get(field, answer[field]))[:4000] for field in answer})
            # Backward compatibility with the first assessment format.
            if not answer["evidence"] and source.get("notes"):
                answer["evidence"] = str(source["notes"])[:4000]
            if answer["status"] not in SECURITY_STATUSES:
                answer["status"] = "not_assessed"
            if answer["risk"] not in SECURITY_RISKS:
                answer["risk"] = "medium"
            answers[key] = answer
        return self._result(
            answers,
            str(saved.get("updated_at", "")),
            str(saved.get("updated_by", "")),
            list(saved.get("history") or [])[-20:],
        )

    def save(self, initiative_path: Path, submitted: dict[str, dict[str, str]], actor: str = "") -> dict:
        with self._lock:
            return self._save_locked(initiative_path, submitted, actor)

    def _save_locked(self, initiative_path: Path, submitted: dict[str, dict[str, str]], actor: str = "") -> dict:
        previous = self.load(initiative_path)
        answers = {}
        errors = []
        for key in SECURITY_DIMENSIONS:
            source = submitted.get(key) or {}
            answer = self._empty_answer()
            answer.update({field: str(source.get(field, answer[field])).strip()[:4000] for field in answer})
            if answer["status"] not in SECURITY_STATUSES:
                answer["status"] = "not_assessed"
            if answer["risk"] not in SECURITY_RISKS:
                answer["risk"] = "medium"
            if answer["status"] in {"implemented", "verified"} and not answer["evidence"]:
                errors.append(key)
            if answer["status"] == "not_applicable" and not answer["not_applicable_reason"]:
                errors.append(key)
            answers[key] = answer
        if errors:
            raise SecurityAssessmentValidationError(",".join(sorted(set(errors))))

        if answers == previous["answers"]:
            return previous

        updated_at = datetime.now(timezone.utc).isoformat()
        result = self._result(answers, updated_at, actor, previous["history"])
        history = list(previous["history"])
        history.append({
            "updated_at": updated_at,
            "updated_by": actor,
            "score": result["score"],
            "band": result["band"],
        })
        result["history"] = history[-20:]
        artifacts = initiative_path / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        payload = {
            "answers": answers, "score": result["score"], "band": result["band"],
            "updated_at": updated_at, "updated_by": actor, "history": result["history"],
        }
        fd, temporary = tempfile.mkstemp(prefix=".security-", suffix=".json", dir=artifacts)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, artifacts / self.filename)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return result

    def _result(self, answers: dict, updated_at: str, updated_by: str, history: list) -> dict:
        applicable = [item for item in answers.values() if item["status"] != "not_applicable"]
        raw_score = (sum(_STATUS_POINTS[item["status"]] for item in applicable) / len(applicable) * 10) if applicable else 0.0
        critical_blockers = [
            key for key, item in answers.items()
            if item["risk"] == "critical" and item["status"] not in {"implemented", "verified", "not_applicable"}
        ]
        score = round(min(raw_score, 5.0) if critical_blockers else raw_score, 1)
        band = "critical" if score <= 3 else "mitigation" if score <= 6 else "validation" if score <= 8 else "verified"
        pending = [key for key, item in answers.items() if item["status"] in {"not_assessed", "planned"}]
        evidence_count = sum(bool(item["evidence"]) for item in applicable)
        ai_generated_count = sum(item.get("origin") == "ai" for item in answers.values())
        return {
            "answers": answers, "score": score, "band": band, "pending": pending,
            "critical_blockers": critical_blockers, "evidence_count": evidence_count,
            "ai_generated_count": ai_generated_count,
            "applicable_count": len(applicable), "updated_at": updated_at,
            "updated_by": updated_by, "history": history,
        }
