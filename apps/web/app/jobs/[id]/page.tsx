"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useEffect, useState } from "react"

type JobStatus =
  | "created"
  | "queued"
  | "preprocessing"
  | "rendering"
  | "uploading"
  | "completed"
  | "failed"

type JobResponse = {
  id: string
  status: JobStatus
  progress: number
  babyName: string
  outputUrl: string | null
  errorMsg: string | null
}

const STATUS_LABEL: Record<JobStatus, string> = {
  created: "排队中，请稍候…",
  queued: "排队中，请稍候…",
  preprocessing: "正在处理素材…",
  rendering: "正在合成短片…",
  uploading: "即将完成…",
  completed: "生成成功",
  failed: "生成失败",
}

export default function JobPage() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const [job, setJob] = useState<JobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return

    let cancelled = false

    async function fetchJob() {
      try {
        const res = await fetch(`/api/jobs/${id}`)
        const data = await res.json()
        if (!res.ok) {
          if (!cancelled) setError(data.message ?? "任务不存在")
          return
        }
        if (!cancelled) {
          setJob(data)
          setError(null)
        }
      } catch {
        if (!cancelled) setError("无法获取任务状态")
      }
    }

    fetchJob()
    const timer = setInterval(fetchJob, 2000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [id])

  const isDone = job?.status === "completed" || job?.status === "failed"
  const progress = job?.progress ?? (job?.status === "created" ? 0 : 10)

  return (
    <main className="min-h-full bg-[#FFF5F5]">
      <header className="border-b border-rose-100 bg-white/60">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
          <Link
            href="/jobs"
            className="text-sm text-rose-700 hover:text-rose-900"
          >
            ← 历史成片
          </Link>
          <span className="font-medium text-rose-900">任务进度</span>
          <Link
            href="/create/baby-moon"
            className="text-sm text-rose-700 hover:text-rose-900"
          >
            重新制作
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-2xl px-6 py-12">
        {error && !job && (
          <div className="rounded-3xl border border-red-200 bg-white p-8 text-center">
            <p className="text-red-700">{error}</p>
            <Link
              href="/create/baby-moon"
              className="mt-6 inline-block text-sm font-medium text-rose-700 underline"
            >
              返回创作页
            </Link>
          </div>
        )}

        {job && (
          <div className="space-y-8 rounded-3xl border border-rose-100 bg-white p-8 shadow-sm">
            <div>
              <p className="text-sm text-rose-600">任务 ID</p>
              <p className="mt-1 break-all font-mono text-sm text-rose-900/70">
                {job.id}
              </p>
              <h1 className="mt-4 text-2xl font-bold text-rose-950">
                {job.babyName} 的满月短片
              </h1>
              <p className="mt-2 text-rose-800">
                {STATUS_LABEL[job.status] ?? job.status}
              </p>
            </div>

            {!isDone && (
              <div>
                <div className="mb-2 flex justify-between text-sm text-rose-700">
                  <span>进度</span>
                  <span>{progress}%</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-rose-100">
                  <div
                    className="h-full rounded-full bg-rose-500 transition-all duration-500"
                    style={{ width: `${Math.max(progress, 5)}%` }}
                  />
                </div>
                <p className="mt-4 text-sm text-rose-700/80">
                  首次合成约需 1～3 分钟。请保持此页打开，或稍后通过任务 ID 查看。
                </p>
              </div>
            )}

            {job.status === "completed" && job.outputUrl && (
              <div className="space-y-4">
                <video
                  controls
                  className="w-full overflow-hidden rounded-2xl bg-black"
                  src={job.outputUrl}
                >
                  <track kind="captions" />
                </video>
                <a
                  href={job.outputUrl}
                  download
                  className="inline-flex w-full items-center justify-center rounded-full bg-rose-600 px-6 py-3 font-medium text-white hover:bg-rose-700"
                >
                  下载 MP4
                </a>
              </div>
            )}

            {job.status === "failed" && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
                <p className="text-sm font-medium text-red-800">失败原因</p>
                <p className="mt-1 text-sm text-red-700">
                  {job.errorMsg ?? "未知错误，请重试"}
                </p>
                <Link
                  href="/create/baby-moon"
                  className="mt-4 inline-flex w-full items-center justify-center rounded-full border border-rose-300 bg-white px-6 py-3 text-sm font-medium text-rose-800 hover:bg-rose-50"
                >
                  重新制作
                </Link>
              </div>
            )}
          </div>
        )}

        {!job && !error && (
          <div className="rounded-3xl border border-rose-100 bg-white p-8 text-center text-rose-700">
            加载任务状态…
          </div>
        )}
      </section>
    </main>
  )
}
