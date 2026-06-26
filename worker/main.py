"""
Worker 入口：从队列拉取任务 → 调用 render → 更新状态。
第一周可先由 API 直接 subprocess 调用 render.py，再演进为独立 Worker。
"""

from render import check_ffmpeg

if __name__ == "__main__":
    check_ffmpeg()
    print("life-video-mvp worker ready (queue integration TODO)")
