"""
Worker 入口：轮询 DB → 调用 render.py → 更新任务状态。
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from config import POLL_INTERVAL_SEC, get_storage_root, resolve_storage_path
from db import AssetRow, JobRow, claim_next_job, fetch_job_assets, update_job
from render import check_ffmpeg, render_baby_full_moon


def _asset_paths(assets: list[AssetRow], asset_type: str) -> list[Path]:
    paths: list[Path] = []
    for asset in assets:
        if asset.type != asset_type:
            continue
        path = resolve_storage_path(asset.file_path)
        if not path.exists():
            raise FileNotFoundError(f"素材不存在: {path}")
        paths.append(path)
    return paths


def process_job_row(job: JobRow) -> None:
    job_id = job.id
    print(f"[worker] 处理任务 {job_id}（{job.baby_name}）")

    assets = fetch_job_assets(job_id)
    photos = _asset_paths(assets, "photo")
    videos = _asset_paths(assets, "video")

    if not photos:
        raise ValueError("任务没有照片素材")

    storage_root = get_storage_root()
    output_abs = storage_root / "outputs" / f"{job_id}.mp4"
    output_rel = f"outputs/{job_id}.mp4"
    download_url = f"/api/jobs/{job_id}/download"

    update_job(job_id, status="rendering", progress=60)

    render_baby_full_moon(
        photo_paths=photos,
        output_path=output_abs,
        baby_name=job.baby_name,
        event_date=job.event_date,
        blessing=job.blessing or "健康成长，平安喜乐",
        bgm_preset=job.bgm_preset,
        video_paths=videos or None,
    )

    if not output_abs.exists():
        raise RuntimeError(f"合成完成但找不到成片: {output_abs}")

    update_job(
        job_id,
        status="completed",
        progress=100,
        outputPath=output_rel,
        outputUrl=download_url,
        errorMsg=None,
    )
    print(f"[worker] 完成 {job_id} → {output_abs}")


def run_loop() -> None:
    check_ffmpeg()
    storage_root = get_storage_root()
    storage_root.mkdir(parents=True, exist_ok=True)
    (storage_root / "outputs").mkdir(parents=True, exist_ok=True)

    print(f"[worker] storage: {storage_root}")
    print(f"[worker] 轮询间隔 {POLL_INTERVAL_SEC}s，等待 created 任务…")

    while True:
        job = claim_next_job()
        if not job:
            time.sleep(POLL_INTERVAL_SEC)
            continue

        try:
            process_job_row(job)
        except Exception as exc:
            err = str(exc) or exc.__class__.__name__
            print(f"[worker] 失败 {job.id}: {err}", file=sys.stderr)
            traceback.print_exc()
            update_job(job.id, status="failed", errorMsg=err[:500])


if __name__ == "__main__":
    run_loop()
