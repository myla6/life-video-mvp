import type { BabyMoonTemplate } from "@/lib/template"

const INTRO_DURATION = 5
const ENDING_DURATION = 5
const PHOTO_DURATION = 2.8
const TRANSITION_DURATION = 0.5
const MAX_VIDEO_CLIPS = 2
const MAX_CLIP_DURATION = 5

function slideshowDurationSec(photoCount: number): number {
  if (photoCount <= 0) return 0
  let total = photoCount * PHOTO_DURATION
  if (photoCount > 1) {
    total -= (photoCount - 1) * TRANSITION_DURATION
  }
  return total
}

export function computeEstimatedDurationSec(
  photoCount: number,
  videoCount = 0,
): number {
  const videoTotal =
    videoCount > 0
      ? Math.min(videoCount, MAX_VIDEO_CLIPS) * MAX_CLIP_DURATION
      : 0
  return (
    INTRO_DURATION +
    slideshowDurationSec(photoCount) +
    videoTotal +
    ENDING_DURATION
  )
}

export function formatEstimatedDuration(
  photoCount: number,
  videoCount = 0,
): { estimatedDurationSec: number; estimatedDurationText: string } {
  const estimatedDurationSec = Math.round(
    computeEstimatedDurationSec(photoCount, videoCount),
  )
  const parts = [`${photoCount} 张照片`]
  if (videoCount > 0) {
    parts.push(`${videoCount} 段视频`)
  }
  return {
    estimatedDurationSec,
    estimatedDurationText: `预计成片约 ${estimatedDurationSec} 秒（${parts.join("、")}）`,
  }
}

export function getDurationRulesFromTemplate(_template: BabyMoonTemplate) {
  return {
    introDuration: INTRO_DURATION,
    endingDuration: ENDING_DURATION,
    photoDuration: PHOTO_DURATION,
    maxVideoClips: MAX_VIDEO_CLIPS,
    maxClipDuration: MAX_CLIP_DURATION,
  }
}
