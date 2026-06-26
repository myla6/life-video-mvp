"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

type TemplateMeta = {
  constraints: {
    photos: { min: number; max: number }
    videos: { min: number; max: number }
  }
  bgmPresets: string[]
}

const BGM_LABELS: Record<string, string> = {
  warm_piano: "温馨钢琴",
  soft_guitar: "轻柔吉他",
  lullaby: "童谣风",
}

function estimateDuration(photoCount: number, videoCount: number): string {
  const intro = 5
  const ending = 5
  const photoDuration = 2.8
  const videoDuration = Math.min(videoCount, 2) * 5
  const total = Math.round(
    intro + photoCount * photoDuration + videoDuration + ending,
  )
  const parts = [`${photoCount} 张照片`]
  if (videoCount > 0) parts.push(`${videoCount} 段视频`)
  return `预计成片约 ${total} 秒（${parts.join("、")}）`
}

export default function CreateBabyMoonPage() {
  const router = useRouter()
  const [template, setTemplate] = useState<TemplateMeta | null>(null)
  const [babyName, setBabyName] = useState("")
  const [eventDate, setEventDate] = useState("")
  const [blessing, setBlessing] = useState("")
  const [bgmPreset, setBgmPreset] = useState("warm_piano")
  const [photos, setPhotos] = useState<File[]>([])
  const [videos, setVideos] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/templates/baby-moon")
      .then((res) => res.json())
      .then((data: TemplateMeta) => {
        setTemplate(data)
        if (data.bgmPresets?.[0]) setBgmPreset(data.bgmPresets[0])
      })
      .catch(() => setError("无法加载模板配置"))
  }, [])

  const photoMin = template?.constraints.photos.min ?? 5
  const photoMax = template?.constraints.photos.max ?? 15
  const videoMax = template?.constraints.videos.max ?? 2

  const durationText = useMemo(
    () => estimateDuration(photos.length, videos.length),
    [photos.length, videos.length],
  )

  const canSubmit =
    babyName.trim().length > 0 &&
    eventDate.length > 0 &&
    photos.length >= photoMin &&
    !submitting

  function handlePhotoChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    setPhotos(files)
    setError(null)
  }

  function handleVideoChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    setVideos(files)
    setError(null)
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (photos.length < photoMin) {
      setError(`至少需要 ${photoMin} 张照片`)
      return
    }

    setSubmitting(true)
    setError(null)

    const formData = new FormData()
    formData.append("babyName", babyName.trim())
    formData.append("eventDate", eventDate)
    if (blessing.trim()) formData.append("blessing", blessing.trim())
    formData.append("bgmPreset", bgmPreset)
    for (const file of photos) formData.append("photos", file)
    for (const file of videos) formData.append("videos", file)

    try {
      const res = await fetch("/api/jobs", { method: "POST", body: formData })
      const data = await res.json()
      if (!res.ok) {
        setError(data.message ?? "提交失败")
        return
      }
      router.push(`/jobs/${data.id}`)
    } catch {
      setError("网络错误，请稍后重试")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-full bg-[#FFF5F5]">
      <header className="border-b border-rose-100 bg-white/60">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-rose-700 hover:text-rose-900">
            ← 返回首页
          </Link>
          <span className="font-medium text-rose-900">宝宝满月纪念</span>
        </div>
      </header>

      <form
        onSubmit={handleSubmit}
        className="mx-auto max-w-2xl space-y-8 px-6 py-10"
      >
        <section className="space-y-4 rounded-3xl border border-rose-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-rose-950">上传素材</h2>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-rose-900">
              照片（{photoMin}～{photoMax} 张）*
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={handlePhotoChange}
              className="block w-full text-sm text-rose-900 file:mr-4 file:rounded-full file:border-0 file:bg-rose-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-rose-800 hover:file:bg-rose-200"
            />
            {photos.length > 0 && (
              <p className="text-sm text-rose-700">已选 {photos.length} 张照片</p>
            )}
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-rose-900">
              短视频（可选，0～{videoMax} 段）
            </span>
            <input
              type="file"
              accept="video/mp4,video/quicktime"
              multiple
              onChange={handleVideoChange}
              className="block w-full text-sm text-rose-900 file:mr-4 file:rounded-full file:border-0 file:bg-rose-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-rose-800 hover:file:bg-rose-200"
            />
            {videos.length > 0 && (
              <p className="text-sm text-rose-700">已选 {videos.length} 段视频</p>
            )}
          </label>

          {photos.length > 0 && (
            <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-800">
              {durationText}
            </p>
          )}
        </section>

        <section className="space-y-4 rounded-3xl border border-rose-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-rose-950">宝宝信息</h2>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-rose-900">宝宝昵称 *</span>
            <input
              required
              maxLength={20}
              value={babyName}
              onChange={(e) => setBabyName(e.target.value)}
              placeholder="例如：小糯米"
              className="w-full rounded-xl border border-rose-200 px-4 py-3 text-rose-950 outline-none ring-rose-300 focus:ring-2"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-rose-900">满月日期 *</span>
            <input
              required
              type="date"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              className="w-full rounded-xl border border-rose-200 px-4 py-3 text-rose-950 outline-none ring-rose-300 focus:ring-2"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-rose-900">祝福语</span>
            <textarea
              maxLength={50}
              value={blessing}
              onChange={(e) => setBlessing(e.target.value)}
              placeholder="健康成长，平安喜乐"
              rows={2}
              className="w-full rounded-xl border border-rose-200 px-4 py-3 text-rose-950 outline-none ring-rose-300 focus:ring-2"
            />
          </label>
        </section>

        <section className="space-y-4 rounded-3xl border border-rose-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-rose-950">背景音乐</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {(template?.bgmPresets ?? ["warm_piano", "soft_guitar", "lullaby"]).map(
              (preset) => (
                <label
                  key={preset}
                  className={`cursor-pointer rounded-2xl border px-4 py-3 text-center text-sm font-medium transition ${
                    bgmPreset === preset
                      ? "border-rose-500 bg-rose-50 text-rose-900"
                      : "border-rose-100 bg-white text-rose-800 hover:border-rose-200"
                  }`}
                >
                  <input
                    type="radio"
                    name="bgmPreset"
                    value={preset}
                    checked={bgmPreset === preset}
                    onChange={() => setBgmPreset(preset)}
                    className="sr-only"
                  />
                  {BGM_LABELS[preset] ?? preset}
                </label>
              ),
            )}
          </div>
        </section>

        {error && (
          <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full rounded-full bg-rose-600 px-6 py-4 text-base font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-rose-300"
        >
          {submitting ? "提交中…" : "生成短片"}
        </button>
      </form>
    </main>
  )
}
