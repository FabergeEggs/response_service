"""Integration test: migrations + comment FK to denormalized_post.

Requires Docker. Skipped when Docker is unavailable.
"""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from urllib.parse import quote_plus

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

from src.migrations import migrate

_CONTAINER = "response_db_schema_test_pg"
_IMAGE = "postgres:16-alpine"
_USER = "test"
_PASSWORD = "test"
_DB = "response_db"
_PORT = "55432"


def _docker_available() -> bool:
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "info"],
        capture_output=True,
        timeout=10,
    ).returncode == 0


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)


@pytest.fixture(scope="module")
def pg_dsn():
    if not _docker_available():
        pytest.skip("Docker not available")

    _run(["docker", "rm", "-f", _CONTAINER], check=False)

    start = _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            _CONTAINER,
            "-e",
            f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e",
            f"POSTGRES_USER={_USER}",
            "-e",
            f"POSTGRES_DB={_DB}",
            "-p",
            f"{_PORT}:5432",
            _IMAGE,
        ]
    )
    if start.returncode != 0:
        pytest.skip(f"Could not start postgres container: {start.stderr}")

    dsn = (
        f"postgresql://{quote_plus(_USER)}:{quote_plus(_PASSWORD)}"
        f"@127.0.0.1:{_PORT}/{_DB}"
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            break
        except psycopg2.OperationalError:
            time.sleep(0.5)
    else:
        _run(["docker", "rm", "-f", _CONTAINER], check=False)
        pytest.fail("Postgres container did not become ready")

    yield dsn

    _run(["docker", "rm", "-f", _CONTAINER], check=False)


def test_migrations_and_comment_fk_to_post(pg_dsn: str) -> None:
    migrate.up(pg_dsn)

    conn = psycopg2.connect(pg_dsn, cursor_factory=RealDictCursor)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ccu.table_name AS references_table
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.table_name = 'comments'
                      AND tc.constraint_type = 'FOREIGN KEY'
                      AND tc.constraint_name LIKE '%post_id%'
                    """
                )
                refs = {row["references_table"] for row in cur.fetchall()}
                assert refs == {"denormalized_post"}

                post_id = uuid.uuid4()
                user_id = uuid.uuid4()
                cur.execute(
                    "INSERT INTO denormalized_user (id, name) VALUES (%s, %s)",
                    (str(user_id), "Test User"),
                )
                cur.execute(
                    """
                    INSERT INTO denormalized_post (id, project_id, project_status)
                    VALUES (%s, %s, 'ACTIVE')
                    """,
                    (str(post_id), str(uuid.uuid4())),
                )
                cur.execute(
                    """
                    INSERT INTO comments (id, user_id, post_id, text)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (str(uuid.uuid4()), str(user_id), str(post_id), "hello post"),
                )

                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt FROM comments
                    WHERE post_id = %s
                    """,
                    (str(post_id),),
                )
                assert cur.fetchone()["cnt"] == 1

                task_id = uuid.uuid4()
                response_id = uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO denormalized_task (id, project_id, project_status)
                    VALUES (%s, %s, 'ACTIVE')
                    """,
                    (str(task_id), str(uuid.uuid4())),
                )
                cur.execute(
                    """
                    INSERT INTO response (id, user_id, task_id, text, status)
                    VALUES (%s, %s, %s, 'resp', 'PENDING')
                    """,
                    (str(response_id), str(user_id), str(task_id)),
                )

                cur.execute("SAVEPOINT bad_comment")
                with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                    cur.execute(
                        """
                        INSERT INTO comments (id, user_id, post_id, text)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            str(user_id),
                            str(response_id),
                            "bad fk",
                        ),
                    )
                cur.execute("ROLLBACK TO SAVEPOINT bad_comment")

                cur.execute(
                    "DELETE FROM denormalized_post WHERE id = %s", (str(post_id),)
                )
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM comments WHERE post_id = %s",
                    (str(post_id),),
                )
                assert cur.fetchone()["cnt"] == 0
    finally:
        conn.close()
