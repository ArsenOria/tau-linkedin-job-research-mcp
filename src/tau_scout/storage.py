"""Small local store; reservations commit before any non-idempotent provider call."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from .errors import ScoutError
from .models import Job, now_iso


class Store:
    def __init__(self, directory: Path):
        if directory.is_symlink():
            raise ScoutError("invalid_data_directory", "Scout requires a dedicated private data directory, not a symbolic link.")
        try:
            directory.mkdir(parents=True, mode=0o700)
        except FileExistsError:
            if not directory.is_dir() or (os.name == "posix" and directory.stat().st_mode & 0o077):
                raise ScoutError("invalid_data_directory", "Choose a dedicated private data directory. Existing directory permissions were not changed.") from None
        self.path = directory / "scout.sqlite3"
        if self.path.is_symlink():
            raise ScoutError("invalid_data_directory", "Scout cannot use a symbolic-link database.")
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS plans (
                    id TEXT PRIMARY KEY, source TEXT NOT NULL, brief TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS searches (
                    id TEXT PRIMARY KEY, plan_id TEXT UNIQUE,
                    source TEXT NOT NULL, status TEXT NOT NULL,
                    run_id TEXT, dataset_id TEXT,
                    warnings TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(plan_id) REFERENCES plans(id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    search_id TEXT NOT NULL, external_id TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(search_id, external_id),
                    FOREIGN KEY(search_id) REFERENCES searches(id)
                );
            """)
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    def plan(self, brief: dict, source: str) -> dict:
        result = {"id": str(uuid4()), "brief": brief, "source": source}
        with self.connect() as conn:
            conn.execute("INSERT INTO plans VALUES (?, ?, ?, ?)",
                         (result["id"], source, json.dumps(brief), now_iso()))
        return result

    def get_plan(self, plan_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        if not row:
            raise ScoutError("plan_not_found", "This search plan was not found.")
        return {**dict(row), "brief": json.loads(row["brief"])}

    @staticmethod
    def decoded(row: sqlite3.Row) -> dict:
        return {**dict(row), "warnings": json.loads(row["warnings"])}

    def reserve(self, plan: dict) -> tuple[dict, bool]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT * FROM searches WHERE plan_id=?", (plan["id"],)).fetchone()
                if row:
                    conn.execute("COMMIT")
                    return self.decoded(row), False
                search_id = str(uuid4())
                conn.execute("INSERT INTO searches (id,plan_id,source,status,created_at) VALUES (?,?,?,?,?)",
                             (search_id, plan["id"], plan["source"], "starting", now_iso()))
                row = conn.execute("SELECT * FROM searches WHERE id=?", (search_id,)).fetchone()
                conn.execute("COMMIT")
                return self.decoded(row), True
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def imported_search(self, source: str) -> dict:
        search_id = str(uuid4())
        with self.connect() as conn:
            conn.execute("INSERT INTO searches (id,source,status,created_at) VALUES (?,?,?,?)",
                         (search_id, source, "ready", now_iso()))
        return self.search(search_id)

    def search(self, search_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM searches WHERE id=?", (search_id,)).fetchone()
        if not row:
            raise ScoutError("search_not_found", "This search was not found.")
        return self.decoded(row)

    def update(self, search_id: str, **fields) -> dict:
        allowed = {"status", "run_id", "dataset_id", "warnings"}
        if not fields or not fields.keys() <= allowed:
            raise ValueError("Unsupported stored search fields")
        if "warnings" in fields:
            fields["warnings"] = json.dumps(fields["warnings"])
        with self.connect() as conn:
            conn.execute("UPDATE searches SET " + ", ".join(f"{key}=?" for key in fields) + " WHERE id=?",
                         (*fields.values(), search_id))
        return self.search(search_id)

    def update_active(self, search_id: str, **fields) -> dict:
        """A stale provider poll cannot regress a completed/uncertain search."""
        allowed = {"status", "run_id", "dataset_id", "warnings"}
        if not fields or not fields.keys() <= allowed:
            raise ValueError("Unsupported stored search fields")
        if "warnings" in fields:
            fields["warnings"] = json.dumps(fields["warnings"])
        with self.connect() as conn:
            conn.execute("UPDATE searches SET " + ", ".join(f"{key}=?" for key in fields) +
                         " WHERE id=? AND status IN ('starting','running','results_unavailable')",
                         (*fields.values(), search_id))
        return self.search(search_id)

    def save_jobs(self, search_id: str, jobs: list[Job], *, status: str, warnings: list[str], active_only=False) -> dict:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if active_only:
                    row = conn.execute("SELECT status FROM searches WHERE id=?", (search_id,)).fetchone()
                    if not row or row["status"] not in {"starting", "running", "results_unavailable"}:
                        conn.execute("COMMIT")
                        return self.search(search_id)
                # A successful read is a bounded snapshot, not an append-only feed.
                # Keep the previous snapshot if normalization could not succeed.
                if status == "ready":
                    conn.execute("DELETE FROM jobs WHERE search_id=?", (search_id,))
                for job in jobs:
                    conn.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?)",
                                 (search_id, job.external_id, job.model_dump_json()))
                conn.execute("UPDATE searches SET status=?,warnings=? WHERE id=?",
                             (status, json.dumps(warnings), search_id))
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return self.search(search_id)

    def jobs(self, search_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT body FROM jobs WHERE search_id=? ORDER BY rowid", (search_id,)).fetchall()
        return [json.loads(row["body"]) for row in rows]
