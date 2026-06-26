"""
根据 templates/*.json 与用户素材，调用 ffmpeg 合成成片。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"


def load_template(template_id: str) -> dict:
    path = TEMPLATES_DIR / f"{template_id}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def check_ffmpeg() -> None:
    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)


def _segment_map(template: dict) -> dict[str, dict]:
    return {seg["id"]: seg for seg in template["segments"]}


def compute_duration(
    template: dict,
    photo_count: int,
    video_durations: list[float] | None = None,
    *,
    include_cards: bool = True,
) -> tuple[float, float]:
    """
    按开工包 4.4：开头 + 照片×2.8 + 视频 + 结尾。
    include_cards=False 时仅算轮播段（Day 2 幻灯片阶段用）。
    """
    segments = _segment_map(template)
    photo_duration = float(segments["slideshow"]["style"]["photoDuration"])
    slideshow_duration = photo_count * photo_duration

    video_total = 0.0
    if video_durations:
        clip_cfg = segments["video_clips"]["style"]
        max_clip = float(clip_cfg["clipMaxDuration"])
        max_clips = int(clip_cfg["maxClips"])
        for raw in video_durations[:max_clips]:
            video_total += min(float(raw), max_clip)

    if include_cards:
        intro = float(segments["intro"]["duration"])
        ending = float(segments["ending"]["duration"])
        total = intro + slideshow_duration + video_total + ending
    else:
        total = slideshow_duration + video_total

    return total, photo_duration


def _resolve_bgm_path(bgm_preset: str, bgm_path: Path | None) -> Path | None:
    if bgm_path and bgm_path.exists():
        return bgm_path
    preset = ASSETS_DIR / "bgm" / f"{bgm_preset}.mp3"
    if preset.exists():
        return preset
    test_bgm_dir = ROOT / "test-assets" / "bgm"
    if test_bgm_dir.is_dir():
        for ext in (".mp3", ".MP3", ".m4a", ".wav"):
            matches = sorted(test_bgm_dir.glob(f"*{ext}"))
            if matches:
                return matches[0]
    return None


def render_baby_full_moon(
    *,
    photo_paths: list[Path],
    output_path: Path,
    baby_name: str = "宝宝",
    event_date: str = "",
    blessing: str = "健康成长，平安喜乐",
    bgm_preset: str = "warm_piano",
    bgm_path: Path | None = None,
    video_paths: list[Path] | None = None,
    include_cards: bool = False,
) -> Path:
    """
    照片轮播 + BGM，输出竖屏 mp4。
    include_cards=False：当前仅轮播（标题/结尾卡 TODO）。
    时长按模板 4.4 计算，不凑固定 60 秒。
    """
    import shutil

    min_photos = load_template("baby_full_moon_v1")["constraints"]["photos"]["min"]
    if len(photo_paths) < min_photos:
        raise ValueError(f"至少需要 {min_photos} 张照片，当前 {len(photo_paths)} 张")

    template = load_template("baby_full_moon_v1")
    width = template["output"]["width"]
    height = template["output"]["height"]
    fps = template["output"]["fps"]

    video_durations: list[float] = []
    if video_paths:
        # TODO: ffprobe 读取实际时长；MVP 先按上限估算
        max_clip = float(_segment_map(template)["video_clips"]["style"]["clipMaxDuration"])
        video_durations = [max_clip] * len(video_paths)

    duration, photo_duration = compute_duration(
        template,
        len(photo_paths),
        video_durations or None,
        include_cards=include_cards,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_path.parent / f".tmp_{output_path.stem}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    segment_files: list[Path] = []
    for i, photo in enumerate(photo_paths):
        seg = tmp_dir / f"seg_{i:03d}.mp4"
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},format=yuv420p"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(photo),
                "-t",
                str(photo_duration),
                "-vf",
                vf,
                "-pix_fmt",
                "yuv420p",
                str(seg),
            ],
            check=True,
            capture_output=True,
        )
        segment_files.append(seg)

    concat_list = tmp_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{f.resolve()}'\n" for f in segment_files),
        encoding="utf-8",
    )

    slideshow = tmp_dir / "slideshow.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(slideshow),
        ],
        check=True,
        capture_output=True,
    )

    resolved_bgm = _resolve_bgm_path(bgm_preset, bgm_path)
    if resolved_bgm:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(slideshow),
                "-stream_loop",
                "-1",
                "-i",
                str(resolved_bgm),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                str(duration),
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(slideshow),
                "-c",
                "copy",
                "-t",
                str(duration),
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

    shutil.rmtree(tmp_dir)
    # TODO: intro / ending 标题卡、video_clips、xfade 转场
    return output_path


def estimate_duration_text(template_id: str, photo_count: int, video_count: int = 0) -> str:
    template = load_template(template_id)
    max_clip = float(_segment_map(template)["video_clips"]["style"]["clipMaxDuration"])
    video_durations = [max_clip] * video_count if video_count else None
    total, _ = compute_duration(template, photo_count, video_durations, include_cards=True)
    return f"预计成片约 {int(round(total))} 秒（{photo_count} 张照片）"


def _collect_photos(photos_dir: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP"}
    return sorted(p for p in photos_dir.iterdir() if p.suffix in exts)


if __name__ == "__main__":
    check_ffmpeg()
    photos_dir = ROOT / "test-assets" / "photos"
    output = ROOT / "test-assets" / "output" / "final.mp4"
    photos = _collect_photos(photos_dir)
    print(estimate_duration_text("baby_full_moon_v1", len(photos)))
    print(f"照片 {len(photos)} 张 → {output}")
    render_baby_full_moon(photo_paths=photos, output_path=output)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=width,height,codec_type",
            "-of",
            "default=noprint_wrappers=1",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(probe.stdout.strip())
    print(f"完成: {output}")
