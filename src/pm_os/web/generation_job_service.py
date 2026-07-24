import uuid
from concurrent.futures import Executor
from typing import Callable

from pm_os.repositories.job_repository import JobRepository


class GenerationJob:
    def __init__(
        self,
        job_id: str,
        owner_email: str,
        squad_name: str,
        repository: JobRepository,
        payload: dict,
    ):
        self.job_id = job_id
        self.owner_email = owner_email
        self.squad_name = squad_name
        self.repository = repository
        self.payload = payload

    def set_step(self, index: int, status: str, detail: str = "") -> None:
        if not 0 <= index < len(self.payload["steps"]):
            return
        self.payload["steps"][index].update(status=status, detail=detail)
        self.payload.update(step=index + 1, message=detail)
        self._save()

    def complete(self, result: dict) -> None:
        self.payload["result"] = result
        self.payload["done"] = True
        self.payload["steps"][-1]["status"] = "done"
        self.payload["step"] = len(self.payload["steps"])
        self._save()

    def fail(self, message: str) -> None:
        self.payload["error"] = message
        self.payload["done"] = True
        self._save()

    def _save(self) -> None:
        self.repository.save(
            self.job_id,
            self.owner_email,
            self.squad_name,
            self.payload,
        )


class GenerationJobService:
    """Create and execute persistent, scope-aware generation jobs."""

    def __init__(self, repository: JobRepository, executor: Executor):
        self.repository = repository
        self.executor = executor

    def start(
        self,
        owner_email: str,
        squad_name: str,
        initial_message: str,
        operation: Callable[[GenerationJob], None],
    ) -> str:
        job_id = uuid.uuid4().hex
        payload = {
            "steps": [
                {"status": "pending", "detail": ""}
                for _ in range(4)
            ],
            "step": 0,
            "message": initial_message,
            "done": False,
            "error": None,
            "result": None,
        }
        self.repository.create(job_id, owner_email, squad_name, payload)
        job = GenerationJob(
            job_id,
            owner_email,
            squad_name,
            self.repository,
            payload,
        )
        self.executor.submit(operation, job)
        return job_id
