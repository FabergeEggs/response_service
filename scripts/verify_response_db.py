#!/usr/bin/env python3
"""Verify response_db schema and comment/post consistency.

Usage:
  export MIGRATIONS_DATABASE_URL='postgresql://faberge:faberge_dev@localhost:5433/response_db'
  PYTHONPATH=. python scripts/verify_response_db.py
"""

from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

DEFAULT_DSN = (
    "postgresql://faberge:faberge_dev@127.0.0.1:5433/response_db"
)


def _connect(dsn: str):
    return psycopg2.connect(dsn, cursor_factory=RealDictCursor)


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def _check_project_counts(
    project_dsn: str, response_dsn: str, errors: list[str]
) -> None:
    resp = _connect(response_dsn)
    proj = _connect(project_dsn)
    try:
        with resp.cursor() as rcur, proj.cursor() as pcur:
            rcur.execute(
                """
                SELECT post_id, COUNT(*) AS cnt
                FROM comments
                GROUP BY post_id
                """
            )
            comment_counts = {row["post_id"]: row["cnt"] for row in rcur.fetchall()}

            pcur.execute("SELECT id, comments_count FROM post")
            mismatches = []
            for row in pcur.fetchall():
                post_id = row["id"]
                expected = comment_counts.get(post_id, 0)
                actual = row["comments_count"]
                if actual != expected:
                    mismatches.append(
                        f"post {post_id}: comments_count={actual}, "
                        f"actual comments in response_db={expected}"
                    )

            for post_id, cnt in comment_counts.items():
                pcur.execute("SELECT 1 FROM post WHERE id = %s", (post_id,))
                if pcur.fetchone() is None:
                    mismatches.append(
                        f"post {post_id}: has {cnt} comment(s) in response_db "
                        "but missing in project_db.post"
                    )

            print(f"  posts checked: {len(comment_counts) or 'n/a'}")
            if mismatches:
                for line in mismatches[:10]:
                    print(f"  MISMATCH: {line}")
                if len(mismatches) > 10:
                    print(f"  ... and {len(mismatches) - 10} more")
                errors.append(
                    f"{len(mismatches)} post(s) with comments_count mismatch"
                )
            else:
                print("  all comments_count values match response_db")
    finally:
        resp.close()
        proj.close()


def main() -> int:
    dsn = os.environ.get("MIGRATIONS_DATABASE_URL", DEFAULT_DSN)
    project_dsn = os.environ.get("PROJECT_DATABASE_URL")
    print(f"DSN: {dsn.split('@')[-1]}")

    try:
        conn = _connect(dsn)
    except Exception as exc:
        print(f"ERROR: cannot connect: {exc}", file=sys.stderr)
        print(
            "Start Postgres (e.g. cd infra_faberge && docker compose up -d postgres). "
            "Host port 5433 maps to container 5432.",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []

    with conn:
        with conn.cursor() as cur:
            _print_section("Applied migrations")
            cur.execute(
                """
                SELECT *
                FROM _yoyo_migration
                ORDER BY 1
                """
            )
            rows = cur.fetchall()
            if not rows:
                errors.append("No yoyo migrations applied (_yoyo_migration empty)")
            migration_ids: list[str] = []
            for row in rows:
                mid = row.get("migration_id") or row.get("id") or str(row)
                migration_ids.append(str(mid))
                print(f"  {mid}")

            if not any("0007" in mid for mid in migration_ids):
                errors.append("Migration 0007 not applied — comments may still FK to response")

            _print_section("comments FK target")
            cur.execute(
                """
                SELECT
                    tc.constraint_name,
                    ccu.table_name AS references_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_name = 'comments'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND tc.constraint_name LIKE '%post_id%'
                """
            )
            fk_rows = cur.fetchall()
            if not fk_rows:
                errors.append("comments.post_id foreign key not found")
            else:
                for fk in fk_rows:
                    ref = fk["references_table"]
                    print(f"  {fk['constraint_name']} -> {ref}")
                    if ref != "denormalized_post":
                        errors.append(
                            f"comments.post_id references {ref}, expected denormalized_post"
                        )

            _print_section("Orphan comments (post_id not in denormalized_post)")
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM comments c
                LEFT JOIN denormalized_post p ON p.id = c.post_id
                WHERE c.post_id IS NOT NULL AND p.id IS NULL
                """
            )
            orphan_count = cur.fetchone()["cnt"]
            print(f"  count: {orphan_count}")
            if orphan_count:
                errors.append(f"{orphan_count} orphan comment(s)")

            _print_section("Comments linked to response table (legacy)")
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM comments c
                INNER JOIN response r ON r.id = c.post_id
                """
            )
            legacy_count = cur.fetchone()["cnt"]
            print(f"  count: {legacy_count}")
            if legacy_count:
                errors.append(
                    f"{legacy_count} comment(s) still keyed to response.id (run migration 0007)"
                )

            _print_section("Row counts")
            for table in (
                "denormalized_post",
                "denormalized_user",
                "response",
                "comments",
            ):
                cur.execute(
                    sql.SQL("SELECT COUNT(*) AS cnt FROM {}").format(
                        sql.Identifier(table)
                    )
                )
                print(f"  {table}: {cur.fetchone()['cnt']}")

            _print_section("Sample comments (last 5)")
            cur.execute(
                """
                SELECT
                    c.id,
                    c.post_id,
                    c.user_id,
                    LEFT(c.text, 40) AS text_preview,
                    p.id IS NOT NULL AS post_exists
                FROM comments c
                LEFT JOIN denormalized_post p ON p.id = c.post_id
                ORDER BY c.created_at DESC NULLS LAST
                LIMIT 5
                """
            )
            samples = cur.fetchall()
            if not samples:
                print("  (no comments)")
            for row in samples:
                ok = "OK" if row["post_exists"] else "ORPHAN"
                print(
                    f"  [{ok}] comment={row['id']} post={row['post_id']} "
                    f"user={row['user_id']} text={row['text_preview']!r}"
                )

    conn.close()

    if project_dsn:
        _print_section("project_db vs response_db (comments_count)")
        try:
            _check_project_counts(project_dsn, dsn, errors)
        except Exception as exc:
            errors.append(f"project_db check failed: {exc}")
    else:
        print(
            "\n(skip project_db: set PROJECT_DATABASE_URL to compare comments_count)"
        )

    _print_section("Result")
    if errors:
        for err in errors:
            print(f"  FAIL: {err}")
        return 1

    print("  OK: schema and data look consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
