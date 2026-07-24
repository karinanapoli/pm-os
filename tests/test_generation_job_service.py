from concurrent.futures import Future

from pm_os.repositories.job_repository import JobRepository
from pm_os.web.generation_job_service import GenerationJobService


class ImmediateExecutor:
    def submit(self, function, *args):
        future = Future()
        try:
            future.set_result(function(*args))
        except Exception as exc:
            future.set_exception(exc)
        return future


def test_job_lifecycle_is_persisted_and_scoped(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db")
    service = GenerationJobService(repository, ImmediateExecutor())

    def operation(job):
        job.set_step(0, "active", "Building context")
        job.set_step(0, "done")
        job.complete({"prd": "# PRD"})

    job_id = service.start("pm@example.com", "growth", "Starting", operation)
    payload = repository.get_for_scope(job_id, "pm@example.com", "growth")

    assert payload["done"] is True
    assert payload["step"] == 4
    assert payload["steps"][0]["status"] == "done"
    assert payload["steps"][-1]["status"] == "done"
    assert payload["result"] == {"prd": "# PRD"}
    assert repository.get_for_scope(job_id, "other@example.com", "growth") is None


def test_failed_job_keeps_error_for_status_endpoint(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db")
    service = GenerationJobService(repository, ImmediateExecutor())

    job_id = service.start(
        "pm@example.com",
        "",
        "Starting",
        lambda job: job.fail("Provider unavailable"),
    )

    payload = repository.get_for_scope(job_id, "pm@example.com", "")
    assert payload["done"] is True
    assert payload["error"] == "Provider unavailable"
