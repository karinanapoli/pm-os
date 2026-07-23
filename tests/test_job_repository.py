from pm_os.repositories.job_repository import JobRepository


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
