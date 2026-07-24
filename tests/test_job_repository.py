from pm_os.repositories.job_repository import JobRepository
from datetime import datetime, timedelta, timezone


def test_job_persists_across_repository_instances(tmp_path):
    database = tmp_path / "jobs.db"
    first = JobRepository(database)
    first.create("job-1", "pm@example.com", "growth", {"done": False, "step": 1})

    second = JobRepository(database)

    assert second.get_for_scope("job-1", "pm@example.com", "growth") == {
        "done": False,
        "step": 1,
    }


def test_job_is_hidden_from_other_users_and_squads(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db")
    repository.create("job-secret", "owner@example.com", "alpha", {"result": "private"})

    assert repository.get_for_scope("job-secret", "other@example.com", "alpha") is None
    assert repository.get_for_scope("job-secret", "owner@example.com", "beta") is None


def test_save_requires_matching_scope(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db")
    repository.create("job-1", "owner@example.com", "", {"done": False})

    assert not repository.save("job-1", "other@example.com", "", {"done": True})
    assert repository.save("job-1", "owner@example.com", "", {"done": True})
    assert repository.get_for_scope("job-1", "owner@example.com", "") == {"done": True}


def test_prunes_only_completed_jobs_older_than_retention(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db", retention_days=7)
    repository.create("old-done", "pm@example.com", "", {"done": True})
    repository.create("old-active", "pm@example.com", "", {"done": False})
    repository.create("recent-done", "pm@example.com", "", {"done": True})
    old_timestamp = (
        datetime.now(timezone.utc) - timedelta(days=8)
    ).isoformat()
    with repository._connect() as connection:
        connection.execute(
            "UPDATE generation_jobs SET updated_at = ? WHERE id IN (?, ?)",
            (old_timestamp, "old-done", "old-active"),
        )

    assert repository.prune_completed() == 1
    assert repository.get_for_scope("old-done", "pm@example.com", "") is None
    assert repository.get_for_scope("old-active", "pm@example.com", "") == {
        "done": False
    }
    assert repository.get_for_scope("recent-done", "pm@example.com", "") == {
        "done": True
    }


def test_creating_job_triggers_retention_cleanup(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db", retention_days=1)
    repository.create("expired", "pm@example.com", "", {"done": True})
    old_timestamp = (
        datetime.now(timezone.utc) - timedelta(days=2)
    ).isoformat()
    with repository._connect() as connection:
        connection.execute(
            "UPDATE generation_jobs SET updated_at = ? WHERE id = ?",
            (old_timestamp, "expired"),
        )

    repository.create("new", "pm@example.com", "", {"done": False})

    assert repository.get_for_scope("expired", "pm@example.com", "") is None
    assert repository.get_for_scope("new", "pm@example.com", "") == {
        "done": False
    }
