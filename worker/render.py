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
FONTS_DIR = ASSETS_DIR / "fonts"

# macOS 常见中文字体 fallback（assets/fonts 无 Noto 时）
_MACOS_FONT_CANDIDATES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
]


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


def _resolve_font_path() -> Path:
    if FONTS_DIR.is_dir():
        for pattern in ("*.otf", "*.ttf", "*.OTF", "*.TTF", "*.ttc"):
            matches = sorted(FONTS_DIR.glob(pattern))
            if matches:
                return matches[0]
    for candidate in _MACOS_FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "未找到中文字体。请将 NotoSansSC-Medium.otf 放入 assets/fonts/，"
        "或在 macOS 上确保系统字体可用。"
    )


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"ffmpeg 失败: {stderr[-800:]}")


def _load_pil_font(font_path: Path, size: int):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(font_path), size)
    except OSError:
        return ImageFont.truetype(str(font_path), size, index=0)


def _draw_centered_text(
    draw,
    text: str,
    *,
    y: int,
    width: int,
    font,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) // 2
    draw.text((x, y), text, font=font, fill=fill)


def _png_to_video_segment(
    *,
    png_path: Path,
    output: Path,
    width: int,
    height: int,
    fps: int,
    duration: float,
) -> None:
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},format=yuv420p"
    )
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(png_path),
            "-t",
            str(duration),
            "-vf",
            vf,
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _render_intro_card(
    *,
    output: Path,
    template: dict,
    width: int,
    height: int,
    fps: int,
    baby_name: str,
    event_date: str,
    font_path: Path,
    tmp_dir: Path,
) -> None:
    from PIL import Image, ImageDraw

    intro = _segment_map(template)["intro"]
    style = intro["style"]
    duration = float(intro["duration"])
    bg = style.get("backgroundColor", "#FFF5F5")
    subtitle = style.get("subtitleTemplate", "满月快乐")

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    title_font = _load_pil_font(font_path, 56)
    subtitle_font = _load_pil_font(font_path, 42)
    date_font = _load_pil_font(font_path, 30)
    color_title = "#881337"
    color_sub = "#9F1239"
    color_date = "#BE123C"

    _draw_centered_text(
        draw, baby_name, y=int(height * 0.36), width=width, font=title_font, fill=color_title
    )
    _draw_centered_text(
        draw, subtitle, y=int(height * 0.46), width=width, font=subtitle_font, fill=color_sub
    )
    if event_date:
        _draw_centered_text(
            draw,
            event_date,
            y=int(height * 0.54),
            width=width,
            font=date_font,
            fill=color_date,
        )

    png_path = tmp_dir / "intro.png"
    img.save(png_path)
    _png_to_video_segment(
        png_path=png_path,
        output=output,
        width=width,
        height=height,
        fps=fps,
        duration=duration,
    )


def _ending_font_size(text: str) -> int:
    length = len(text)
    if length <= 10:
        return 44
    if length <= 18:
        return 38
    if length <= 28:
        return 32
    return 28


def _render_ending_card(
    *,
    output: Path,
    template: dict,
    width: int,
    height: int,
    fps: int,
    blessing: str,
    font_path: Path,
    tmp_dir: Path,
) -> None:
    from PIL import Image, ImageDraw

    ending = _segment_map(template)["ending"]
    style = ending["style"]
    duration = float(ending["duration"])
    bg = style.get("backgroundColor", "#FFF5F5")
    default = style.get("defaultBlessing", "健康成长，平安喜乐")
    text = (blessing or default).strip() or default

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    font = _load_pil_font(font_path, _ending_font_size(text))
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2
    draw.text((x, y), text, font=font, fill="#881337")

    png_path = tmp_dir / "ending.png"
    img.save(png_path)
    _png_to_video_segment(
        png_path=png_path,
        output=output,
        width=width,
        height=height,
        fps=fps,
        duration=duration,
    )


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
    include_cards: bool = True,
) -> Path:
    """
    照片轮播 + 可选标题/结尾卡 + BGM，输出竖屏 mp4。
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

    if include_cards:
        font_path = _resolve_font_path()
        intro_seg = tmp_dir / "intro.mp4"
        _render_intro_card(
            output=intro_seg,
            template=template,
            width=width,
            height=height,
            fps=fps,
            baby_name=baby_name,
            event_date=event_date,
            font_path=font_path,
            tmp_dir=tmp_dir,
        )
        segment_files.append(intro_seg)

    for i, photo in enumerate(photo_paths):
        seg = tmp_dir / f"seg_{i:03d}.mp4"
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},format=yuv420p"
        )
        _run_ffmpeg(
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
            ]
        )
        segment_files.append(seg)

    if include_cards:
        ending_seg = tmp_dir / "ending.mp4"
        _render_ending_card(
            output=ending_seg,
            template=template,
            width=width,
            height=height,
            fps=fps,
            blessing=blessing,
            font_path=font_path,
            tmp_dir=tmp_dir,
        )
        segment_files.append(ending_seg)

    concat_list = tmp_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{f.resolve()}'\n" for f in segment_files),
        encoding="utf-8",
    )

    main_video = tmp_dir / "main_video.mp4"
    _run_ffmpeg(
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
            str(main_video),
        ]
    )

    resolved_bgm = _resolve_bgm_path(bgm_preset, bgm_path)
    if resolved_bgm:
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(main_video),
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
            ]
        )
    else:
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(main_video),
                "-c",
                "copy",
                "-t",
                str(duration),
                str(output_path),
            ]
        )

    shutil.rmtree(tmp_dir)
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
    render_baby_full_moon(
        photo_paths=photos,
        output_path=output,
        baby_name="小糯米",
        event_date="2026-05-20",
        blessing="健康成长，平安喜乐",
        include_cards=True,
    )
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
