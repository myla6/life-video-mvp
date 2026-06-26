const PHOTO_MIME = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
])
const VIDEO_MIME = new Set(["video/mp4", "video/quicktime"])

const PHOTO_EXT = new Set([".jpg", ".jpeg", ".png", ".webp"])
const VIDEO_EXT = new Set([".mp4", ".mov"])

export const LIMITS = {
  photoMaxBytes: 10 * 1024 * 1024,
  videoMaxBytes: 100 * 1024 * 1024,
  babyNameMax: 20,
  blessingMax: 50,
} as const

export type ValidationResult =
  | { ok: true }
  | { ok: false; error: string; details?: Record<string, unknown> }

export function validateBabyName(value: string): ValidationResult {
  const trimmed = value.trim()
  if (!trimmed) {
    return { ok: false, error: "请填写宝宝昵称" }
  }
  if (trimmed.length > LIMITS.babyNameMax) {
    return {
      ok: false,
      error: `宝宝昵称不能超过 ${LIMITS.babyNameMax} 字`,
    }
  }
  return { ok: true }
}

export function validateEventDate(value: string): ValidationResult {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return { ok: false, error: "请填写正确的满月日期（YYYY-MM-DD）" }
  }
  return { ok: true }
}

export function validateBlessing(value: string | null): ValidationResult {
  if (!value) return { ok: true }
  if (value.length > LIMITS.blessingMax) {
    return {
      ok: false,
      error: `祝福语不能超过 ${LIMITS.blessingMax} 字`,
    }
  }
  return { ok: true }
}

export function validateBgmPreset(
  value: string,
  allowed: string[],
): ValidationResult {
  if (!allowed.includes(value)) {
    return { ok: false, error: "请选择有效的背景音乐" }
  }
  return { ok: true }
}

function getExtension(name: string): string {
  const idx = name.lastIndexOf(".")
  return idx >= 0 ? name.slice(idx).toLowerCase() : ""
}

export function isPhotoFile(file: File): boolean {
  if (PHOTO_MIME.has(file.type)) return true
  return PHOTO_EXT.has(getExtension(file.name))
}

export function isVideoFile(file: File): boolean {
  if (VIDEO_MIME.has(file.type)) return true
  return VIDEO_EXT.has(getExtension(file.name))
}

export function validatePhotos(
  files: File[],
  min: number,
  max: number,
): ValidationResult {
  if (files.length < min) {
    return {
      ok: false,
      error: `至少需要 ${min} 张照片`,
      details: { photos: { min, received: files.length } },
    }
  }
  if (files.length > max) {
    return {
      ok: false,
      error: `最多上传 ${max} 张照片`,
      details: { photos: { max, received: files.length } },
    }
  }
  for (const file of files) {
    if (!isPhotoFile(file)) {
      return { ok: false, error: "照片仅支持 JPG、PNG、WEBP" }
    }
    if (file.size > LIMITS.photoMaxBytes) {
      return { ok: false, error: `单张照片不能超过 10MB：${file.name}` }
    }
  }
  return { ok: true }
}

export function validateVideos(
  files: File[],
  max: number,
): ValidationResult {
  if (files.length > max) {
    return {
      ok: false,
      error: `最多上传 ${max} 段视频`,
      details: { videos: { max, received: files.length } },
    }
  }
  for (const file of files) {
    if (!isVideoFile(file)) {
      return { ok: false, error: "视频仅支持 MP4、MOV" }
    }
    if (file.size > LIMITS.videoMaxBytes) {
      return { ok: false, error: `单段视频不能超过 100MB：${file.name}` }
    }
  }
  return { ok: true }
}

export function photoExtension(file: File): string {
  const ext = getExtension(file.name)
  if (ext === ".jpeg") return ".jpg"
  if (PHOTO_EXT.has(ext)) return ext
  if (file.type === "image/png") return ".png"
  if (file.type === "image/webp") return ".webp"
  return ".jpg"
}

export function videoExtension(file: File): string {
  const ext = getExtension(file.name)
  if (VIDEO_EXT.has(ext)) return ext === ".mov" ? ".mov" : ".mp4"
  return file.type === "video/quicktime" ? ".mov" : ".mp4"
}
