"""Worker 环境配置。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

WORKER_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("PROJECT_ROOT", WORKER_DIR.parent)).resolve()

load_dotenv(WORKER_DIR / ".env")


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "缺少 DATABASE_URL，请在 worker/.env 中配置（可参考 .env.example）"
        )
    # Prisma 连接串带 ?schema=public，psycopg2 不支持该参数
    if "?" in url:
        url = url.split("?", 1)[0]
    return url


def get_storage_root() -> Path:
    configured = os.environ.get("STORAGE_ROOT", "../storage")
    path = Path(configured)
    if not path.is_absolute():
        path = (WORKER_DIR / path).resolve()
    return path


def resolve_storage_path(relative_path: str) -> Path:
    return get_storage_root() / relative_path


POLL_INTERVAL_SEC = float(os.environ.get("WORKER_POLL_INTERVAL", "3"))
