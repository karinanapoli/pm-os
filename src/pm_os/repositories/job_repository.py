import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class JobRepository:
    """Persistent, scope-aware storage for background generation jobs."""

    def __init__(self, database_path: Optional[Path] = None):
        config_dir = Path(os.getenv("PM_OS_CONFIG_DIR", str(Path.home() / ".pm_os")))
        self.database_path = database_path or config_dir / "jobs.db"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_jobs (
                    id TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    squad_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_generation_jobs_scope "
                "ON generation_jobs(owner_email, squad_name, updated_at)"
            )

    def create(self, job_id: str, owner_email: str, squad_name: str, payload: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(payload, ensure_ascii=False)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generation_jobs
                    (id, owner_email, squad_name, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, owner_email, squad_name, serialized, now, now),
            )

    def save(self, job_id: str, owner_email: str, squad_name: str, payload: dict) -> bool:
        serialized = json.dumps(payload, ensure_ascii=False)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE generation_jobs
                SET payload = ?, updated_at = ?
                WHERE id = ? AND owner_email = ? AND squad_name = ?
                """,
                (serialized, now, job_id, owner_email, squad_name),
            )
            return cursor.rowcount == 1

    def get_for_scope(self, job_id: str, owner_email: str, squad_name: str) -> Optional[dict]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload FROM generation_jobs
                WHERE id = ? AND owner_email = ? AND squad_name = ?
                """,
                (job_id, owner_email, squad_name),
            ).fetchone()
        return json.loads(row[0]) if row else None
