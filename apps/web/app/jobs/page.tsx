"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

type JobStatus =
  | "created"
  | "queued"
  | "preprocessing"
  | "rendering"
  | "uploading"
  | "completed"
  | "failed"

type JobListItem = {
  id: string
  status: JobStatus
  babyName: string
  eventDate: string
  blessing: string | null
  createdAt: string
  outputUrl: string | null
  errorMsg: string | null
}

const STATUS_LABEL: Record<JobStatus, string> = {
  created: "排队中",
  queued: "排队中",
  preprocessing: "处理中",
  rendering: "合成中",
  uploading: "即将完成",
  completed: "已完成",
  failed: "失败",
}

const STATUS_STYLE: Record<JobStatus, string> = {
  created: "bg-amber-50 text-amber-800",
  queued: "bg-amber-50 text-amber-800",
  preprocessing: "bg-sky-50 text-sky-800",
  rendering: "bg-sky-50 text-sky-800",
  uploading: "bg-sky-50 text-sky-800",
  completed: "bg-emerald-50 text-emerald-800",
  failed: "bg-red-50 text-red-800",
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function JobsHistoryPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch("/api/jobs?limit=50")
        const data = await res.json()
        if (!res.ok) {
          if (!cancelled) setError(data.message ?? "加载失败")
          return
        }
        if (!cancelled) {
          setJobs(data.jobs ?? [])
          setError(null)
        }
      } catch {
        if (!cancelled) setError("无法连接服务器")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    const timer = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return (
    <main className="min-h-full bg-[#FFF5F5]">
      <header className="border-b border-rose-100 bg-white/60">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-rose-700 hover:text-rose-900">
            ← 返回首页
          </Link>
          <span className="font-medium text-rose-900">历史成片</span>
          <Link
            href="/create/baby-moon"
            className="text-sm font-medium text-rose-700 hover:text-rose-900"
          >
            新建
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-rose-950">历史成片</h1>
          <p className="mt-2 text-sm text-rose-800/75">
            对比不同版本的渲染效果。优化片头片尾后，重新制作一条即可在此并排查看。
          </p>
        </div>

        {loading && !jobs.length && (
          <div className="rounded-3xl border border-rose-100 bg-white p-8 text-center text-rose-700">
            加载中…
          </div>
        )}

        {error && (
          <div className="rounded-3xl border border-red-200 bg-white p-8 text-center text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="rounded-3xl border border-rose-100 bg-white p-8 text-center">
            <p className="text-rose-800">还没有成片记录</p>
            <Link
              href="/create/baby-moon"
              className="mt-4 inline-flex rounded-full bg-rose-600 px-5 py-2 text-sm font-medium text-white hover:bg-rose-700"
            >
              开始制作
            </Link>
          </div>
        )}

        <ul className="space-y-6">
          {jobs.map((job) => (
            <li
              key={job.id}
              className="overflow-hidden rounded-3xl border border-rose-100 bg-white shadow-sm"
            >
              <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
                {job.status === "completed" && job.outputUrl ? (
                  <video
                    controls
                    preload="metadata"
                    className="h-48 w-full shrink-0 rounded-2xl bg-black object-contain sm:h-40 sm:w-[120px]"
                    src={job.outputUrl}
                  >
                    <track kind="captions" />
                  </video>
                ) : (
                  <div className="flex h-48 w-full shrink-0 items-center justify-center rounded-2xl bg-rose-50 sm:h-40 sm:w-[120px]">
                    <span className="text-xs text-rose-500">
                      {job.status === "failed" ? "生成失败" : "等待成片…"}
                    </span>
                  </div>
                )}

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold text-rose-950">
                      {job.babyName} 的满月短片
                    </h2>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[job.status]}`}
                    >
                      {STATUS_LABEL[job.status]}
                    </span>
                  </div>

                  <p className="mt-1 text-sm text-rose-700">
                    满月 {job.eventDate} · {formatTime(job.createdAt)}
                  </p>

                  {job.blessing && (
                    <p className="mt-2 line-clamp-2 text-sm text-rose-800/80">
                      {job.blessing}
                    </p>
                  )}

                  {job.status === "failed" && job.errorMsg && (
                    <p className="mt-2 text-sm text-red-700">{job.errorMsg}</p>
                  )}

                  <div className="mt-4 flex flex-wrap gap-3">
                    <Link
                      href={`/jobs/${job.id}`}
                      className="text-sm font-medium text-rose-700 underline hover:text-rose-900"
                    >
                      查看详情
                    </Link>
                    {job.status === "completed" && job.outputUrl && (
                      <a
                        href={job.outputUrl}
                        download
                        className="text-sm font-medium text-rose-700 underline hover:text-rose-900"
                      >
                        下载 MP4
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
