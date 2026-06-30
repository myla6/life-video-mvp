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
CARDS_DIR = ASSETS_DIR / "cards"

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
    slide_style = segments["slideshow"]["style"]
    if photo_count > 1 and slide_style.get("transition") == "fade":
        transition_duration = float(slide_style.get("transitionDuration", 0))
        slideshow_duration -= (photo_count - 1) * transition_duration

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


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _render_video_segment(
    *,
    video_path: Path,
    output: Path,
    width: int,
    height: int,
    fps: int,
    clip_duration: float,
) -> None:
    """用户短视频：裁切为竖屏、截断时长、去掉原声（成片只用 BGM）。"""
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},format=yuv420p"
    )
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-t",
            str(clip_duration),
            "-vf",
            vf,
            "-an",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _load_pil_font(font_path: Path, size: int):
    from PIL import ImageFont

    # PingFang.ttc 等合集字体：优先 index 0（简中 Regular）
    for index in (0, 1, 2):
        try:
            return ImageFont.truetype(str(font_path), size, index=index)
        except OSError:
            continue
    return ImageFont.truetype(str(font_path), size)


def _measure_text(draw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(draw, text: str, font, max_width: int, *, max_lines: int = 4) -> list[str]:
    """按像素宽度换行；优先在逗号/顿号处断行，避免拆开词组。"""
    import re

    text = text.strip()
    if not text:
        return []

    tokens = [t for t in re.split(r"([，,、；;])", text) if t]
    clauses: list[str] = []
    buf = ""
    for token in tokens:
        if token in "，,、；;":
            buf += token
            clauses.append(buf)
            buf = ""
        else:
            buf += token
    if buf:
        clauses.append(buf)

    lines: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        if current.strip():
            lines.append(current.strip())
        current = ""

    def append_chars(fragment: str) -> None:
        nonlocal current
        for char in fragment:
            trial = current + char
            width, _ = _measure_text(draw, trial, font)
            if width <= max_width:
                current = trial
                continue
            flush_current()
            current = char
            if len(lines) >= max_lines:
                return

    for clause in clauses:
        if len(lines) >= max_lines:
            break
        candidate = current + clause
        width, _ = _measure_text(draw, candidate, font)
        if width <= max_width:
            current = candidate
            continue
        flush_current()
        clause_width, _ = _measure_text(draw, clause, font)
        if clause_width <= max_width:
            current = clause
        else:
            append_chars(clause)

    if len(lines) < max_lines and current.strip():
        lines.append(current.strip())

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    consumed = sum(len(line) for line in lines)
    if consumed < len(text.replace("\n", "")) and lines:
        last = lines[-1]
        while last and _measure_text(draw, f"{last}…", font)[0] > max_width:
            last = last[:-1]
        lines[-1] = f"{last}…" if last else "…"

    return lines


def _balance_lines(draw, lines: list[str], font, max_width: int) -> list[str]:
    """避免最后一行只剩一两个字。"""
    if len(lines) < 2:
        return lines

    balanced = list(lines)
    while len(balanced) >= 2 and len(balanced[-1]) <= 2:
        merged = balanced[-2] + balanced[-1]
        if _measure_text(draw, merged, font)[0] <= max_width:
            balanced = balanced[:-2] + [merged]
            continue
        if len(balanced[-2]) <= 1:
            break
        moved = balanced[-2][-1] + balanced[-1]
        remaining = balanced[-2][:-1]
        if (
            _measure_text(draw, remaining, font)[0] <= max_width
            and _measure_text(draw, moved, font)[0] <= max_width
        ):
            balanced = balanced[:-2] + [remaining, moved]
        else:
            break
    return balanced


def _fit_font_for_lines(
    draw,
    font_path: Path,
    lines: list[str],
    *,
    max_width: int,
    start_size: int,
    min_size: int,
):
    for size in range(start_size, min_size - 1, -2):
        font = _load_pil_font(font_path, size)
        if all(_measure_text(draw, line, font)[0] <= max_width for line in lines):
            return font, size
    font = _load_pil_font(font_path, min_size)
    return font, min_size


def _format_event_date(raw: str) -> str:
    import re

    raw = raw.strip()
    if not raw:
        return ""
    match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", raw)
    if match:
        year, month, day = match.groups()
        return f"{year}年{int(month)}月{int(day)}日"
    return raw


def _draw_text_block(
    draw,
    *,
    width: int,
    height: int,
    font_path: Path,
    sections: list[tuple[str, int, str, int]],
    horizontal_margin_ratio: float = 0.1,
    section_gap: int = 32,
    line_gap_ratio: float = 0.35,
) -> None:
    """
    多段文字垂直居中绘制。sections: (text, start_font_size, color, max_lines)
    """
    margin = int(width * horizontal_margin_ratio)
    max_width = width - margin * 2

    prepared: list[tuple[list[str], object, str, int]] = []
    for text, start_size, color, max_lines in sections:
        if not text.strip():
            continue
        font = _load_pil_font(font_path, start_size)
        lines: list[str] = []
        size = start_size
        for size in range(start_size, max(22, start_size // 2) - 1, -2):
            font = _load_pil_font(font_path, size)
            lines = _wrap_text(draw, text, font, max_width, max_lines=max_lines)
            lines = _balance_lines(draw, lines, font, max_width)
            if all(_measure_text(draw, line, font)[0] <= max_width for line in lines):
                break
        if lines:
            prepared.append((lines, font, color, size))

    if not prepared:
        return

    total_height = 0
    section_heights: list[int] = []
    for lines, font, _color, size in prepared:
        _, line_h = _measure_text(draw, "满", font)
        block_h = len(lines) * line_h + max(0, len(lines) - 1) * int(size * line_gap_ratio)
        section_heights.append(block_h)
        total_height += block_h
    total_height += section_gap * (len(prepared) - 1)

    y = (height - total_height) // 2
    for idx, (lines, font, color, size) in enumerate(prepared):
        _, line_h = _measure_text(draw, "满", font)
        line_gap = int(size * line_gap_ratio)
        for line in lines:
            text_w, _ = _measure_text(draw, line, font)
            x = (width - text_w) // 2
            draw.text((x, y), line, font=font, fill=color)
            y += line_h + line_gap
        if idx < len(prepared) - 1:
            y += section_gap - line_gap


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


def _render_photo_segment(
    *,
    photo_path: Path,
    output: Path,
    width: int,
    height: int,
    fps: int,
    duration: float,
    ken_burns: bool,
    zoom_end: float = 1.08,
) -> None:
    frames = max(int(duration * fps), 1)
    if ken_burns:
        zoom_step = (zoom_end - 1.0) / frames
        vf = (
            f"scale={width * 4}:{height * 4}:force_original_aspect_ratio=increase,"
            f"crop={width * 4}:{height * 4},"
            f"zoompan=z='min(zoom+{zoom_step:.6f},{zoom_end})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
        )
    else:
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
            str(photo_path),
            "-t",
            str(duration),
            "-vf",
            vf,
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _concat_videos_with_xfade(
    segments: list[Path],
    output: Path,
    *,
    transition_duration: float,
    segment_duration: float,
) -> None:
    import shutil

    if len(segments) == 1:
        shutil.copy(segments[0], output)
        return

    inputs: list[str] = []
    for seg in segments:
        inputs.extend(["-i", str(seg)])

    filters: list[str] = []
    for i in range(1, len(segments)):
        offset = i * (segment_duration - transition_duration)
        left = "[0:v]" if i == 1 else f"[v{i - 1}]"
        out = "[vout]" if i == len(segments) - 1 else f"[v{i}]"
        filters.append(
            f"{left}[{i}:v]xfade=transition=fade:duration={transition_duration}:"
            f"offset={offset:.3f}{out}"
        )

    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _generate_intro_card_template(path: Path, width: int, height: int) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), "#FFF8F8")
    draw = ImageDraw.Draw(img)

    draw.ellipse([-100, -60, 460, 340], fill="#FFE4EC")
    draw.ellipse([420, 880, 880, 1320], fill="#FCE7F3")
    draw.rounded_rectangle(
        [40, 360, width - 40, height - 360],
        radius=28,
        outline="#FDA4AF",
        width=2,
    )

    cx = width // 2
    draw.line([(cx - 72, 500), (cx + 72, 500)], fill="#FB7185", width=2)
    draw.line([(cx - 36, 514), (cx + 36, 514)], fill="#FDA4AF", width=1)
    draw.ellipse([cx - 6, 330, cx + 6, 342], fill="#FB7185")

    img.save(path, "PNG")


def _generate_ending_card_template(path: Path, width: int, height: int) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), "#FFF8F8")
    draw = ImageDraw.Draw(img)

    draw.ellipse([-80, 200, 320, 560], fill="#FCE7F3")
    draw.ellipse([500, 760, 900, 1100], fill="#FFE4EC")
    draw.rounded_rectangle(
        [56, 420, width - 56, height - 420],
        radius=24,
        outline="#FDA4AF",
        width=2,
    )

    draw.arc([80, 460, 160, 540], start=200, end=340, fill="#FDA4AF", width=3)
    draw.arc([width - 160, height - 540, width - 80, height - 460], start=20, end=160, fill="#FDA4AF", width=3)

    img.save(path, "PNG")


def _ensure_card_template(kind: str, width: int, height: int) -> Path:
    path = CARDS_DIR / f"{kind}_bg.png"
    if not path.exists():
        if kind == "intro":
            _generate_intro_card_template(path, width, height)
        else:
            _generate_ending_card_template(path, width, height)
    return path


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
    subtitle = style.get("subtitleTemplate", "满月快乐")

    template_path = _ensure_card_template("intro", width, height)
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    _draw_text_block(
        draw,
        width=width,
        height=height,
        font_path=font_path,
        sections=[
            (baby_name.strip() or "宝宝", 64, "#881337", 2),
            (subtitle, 44, "#9F1239", 1),
            (_format_event_date(event_date), 34, "#BE123C", 1),
        ],
        horizontal_margin_ratio=0.12,
        section_gap=36,
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
    default = style.get("defaultBlessing", "健康成长，平安喜乐")
    text = (blessing or default).strip() or default

    template_path = _ensure_card_template("ending", width, height)
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    _draw_text_block(
        draw,
        width=width,
        height=height,
        font_path=font_path,
        sections=[(text, 48, "#881337", 4)],
        horizontal_margin_ratio=0.14,
        section_gap=24,
        line_gap_ratio=0.45,
    )

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
    片头 + 照片轮播 + 可选视频片段 + 片尾 + BGM，输出竖屏 mp4。
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
        clip_cfg = _segment_map(template)["video_clips"]["style"]
        max_clip = float(clip_cfg["clipMaxDuration"])
        max_clips = int(clip_cfg["maxClips"])
        for video in video_paths[:max_clips]:
            raw = _probe_duration(video)
            video_durations.append(min(raw, max_clip))

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
    slide_style = _segment_map(template)["slideshow"]["style"]
    ken_burns = bool(slide_style.get("kenBurns", False))
    transition = slide_style.get("transition", "none")
    transition_duration = float(slide_style.get("transitionDuration", 0.5))

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

    photo_segments: list[Path] = []
    for i, photo in enumerate(photo_paths):
        seg = tmp_dir / f"seg_{i:03d}.mp4"
        _render_photo_segment(
            photo_path=photo,
            output=seg,
            width=width,
            height=height,
            fps=fps,
            duration=photo_duration,
            ken_burns=ken_burns,
        )
        photo_segments.append(seg)

    if photo_segments:
        if len(photo_segments) > 1 and transition == "fade":
            slideshow = tmp_dir / "slideshow.mp4"
            _concat_videos_with_xfade(
                photo_segments,
                slideshow,
                transition_duration=transition_duration,
                segment_duration=photo_duration,
            )
            segment_files.append(slideshow)
        else:
            segment_files.extend(photo_segments)

    if video_paths and video_durations:
        clip_cfg = _segment_map(template)["video_clips"]["style"]
        max_clips = int(clip_cfg["maxClips"])
        for i, (video, clip_duration) in enumerate(
            zip(video_paths[:max_clips], video_durations)
        ):
            seg = tmp_dir / f"video_{i:03d}.mp4"
            _render_video_segment(
                video_path=video,
                output=seg,
                width=width,
                height=height,
                fps=fps,
                clip_duration=clip_duration,
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
