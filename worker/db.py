"""PostgreSQL 读写 Job / JobAsset（与 Prisma schema 对齐）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras

from config import get_database_url


@dataclass
class JobRow:
    id: str
    template_id: str
    baby_name: str
    event_date: str
    blessing: str | None
    bgm_preset: str


@dataclass
class AssetRow:
    type: str
    file_path: str
    sort_order: int


def _connect():
    return psycopg2.connect(get_database_url())


def claim_next_job() -> JobRow | None:
    """
    认领最早的一条 created 任务（乐观锁，避免重复消费）。
    成功则 status → preprocessing。
    """
    with _connect() as conn:
        conn.autocommit = False
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id FROM "Job"
                WHERE status = 'created'
                ORDER BY "createdAt" ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None

            job_id = row["id"]
            cur.execute(
                """
                UPDATE "Job"
                SET status = 'preprocessing',
                    progress = 30,
                    "updatedAt" = NOW()
                WHERE id = %s AND status = 'created'
                RETURNING id, "templateId", "babyName", "eventDate", blessing, "bgmPreset"
                """,
                (job_id,),
            )
            claimed = cur.fetchone()
            conn.commit()
            if not claimed:
                return None

            return JobRow(
                id=claimed["id"],
                template_id=claimed["templateId"],
                baby_name=claimed["babyName"],
                event_date=claimed["eventDate"],
                blessing=claimed["blessing"],
                bgm_preset=claimed["bgmPreset"],
            )


def fetch_job_assets(job_id: str) -> list[AssetRow]:
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT type, "filePath", "sortOrder"
                FROM "JobAsset"
                WHERE "jobId" = %s
                ORDER BY "sortOrder" ASC
                """,
                (job_id,),
            )
            rows = cur.fetchall()
            return [
                AssetRow(
                    type=r["type"],
                    file_path=r["filePath"],
                    sort_order=r["sortOrder"],
                )
                for r in rows
            ]


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return

    columns = []
    values: list[Any] = []
    for key, value in fields.items():
        columns.append(f'"{key}" = %s')
        values.append(value)

    columns.append('"updatedAt" = NOW()')
    values.append(job_id)

    sql = f'UPDATE "Job" SET {", ".join(columns)} WHERE id = %s'

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()
