"use client"

import { useObjectUrls } from "@/hooks/use-object-urls"
import { formatFileSize } from "@/lib/format"
import { useRef, useState } from "react"

type MediaUploadFieldProps = {
  kind: "photo" | "video"
  label: string
  hint: string
  accept: string
  files: File[]
  maxCount: number
  minCount?: number
  onChange: (files: File[]) => void
}

export function MediaUploadField({
  kind,
  label,
  hint,
  accept,
  files,
  maxCount,
  minCount = 0,
  onChange,
}: MediaUploadFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const previewUrls = useObjectUrls(files)

  function mergeFiles(incoming: File[]) {
    const merged = [...files, ...incoming].slice(0, maxCount)
    onChange(merged)
  }

  function handleInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    mergeFiles(Array.from(event.target.files ?? []))
    event.target.value = ""
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault()
    setDragOver(false)
    const dropped = Array.from(event.dataTransfer.files ?? [])
    const filtered =
      kind === "photo"
        ? dropped.filter((f) => f.type.startsWith("image/"))
        : dropped.filter((f) => f.type.startsWith("video/"))
    if (filtered.length === 0) return
    mergeFiles(filtered)
  }

  function removeAt(index: number) {
    onChange(files.filter((_, i) => i !== index))
  }

  function clearAll() {
    onChange([])
  }

  const atMax = files.length >= maxCount
  const countOk = files.length >= minCount

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-rose-900">{label}</span>
        {files.length > 0 && (
          <button
            type="button"
            onClick={clearAll}
            className="text-xs text-rose-600 underline hover:text-rose-900"
          >
            清空
          </button>
        )}
      </div>

      <button
        type="button"
        disabled={atMax}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          if (!atMax) setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={atMax ? undefined : handleDrop}
        className={`flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition ${
          atMax
            ? "cursor-not-allowed border-rose-100 bg-rose-50/50 text-rose-400"
            : dragOver
              ? "border-rose-400 bg-rose-50 text-rose-900"
              : "border-rose-200 bg-rose-50/30 text-rose-800 hover:border-rose-300 hover:bg-rose-50"
        }`}
      >
        <span className="text-2xl">{kind === "photo" ? "🖼️" : "🎬"}</span>
        <span className="mt-2 text-sm font-medium">
          {atMax ? "已达上限" : "点击选择或拖拽到此处"}
        </span>
        <span className="mt-1 text-xs text-rose-600/80">{hint}</span>
        {files.length > 0 && (
          <span
            className={`mt-2 rounded-full px-3 py-0.5 text-xs font-medium ${
              countOk ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
            }`}
          >
            已选 {files.length}/{maxCount}
            {minCount > 0 && !countOk && `（至少 ${minCount} 张）`}
          </span>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={maxCount > 1}
        className="hidden"
        onChange={handleInputChange}
      />

      {kind === "photo" && files.length > 0 && (
        <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {files.map((file, index) => (
            <li key={`${file.name}-${file.size}-${index}`} className="group relative">
              <div className="aspect-3/4 overflow-hidden rounded-xl border border-rose-100 bg-rose-50">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrls[index]}
                  alt={file.name}
                  className="h-full w-full object-cover"
                />
              </div>
              <span className="absolute left-1.5 top-1.5 rounded-md bg-black/50 px-1.5 py-0.5 text-[10px] font-medium text-white">
                {index + 1}
              </span>
              <button
                type="button"
                aria-label={`移除 ${file.name}`}
                onClick={() => removeAt(index)}
                className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-black/55 text-xs text-white hover:bg-black/70"
              >
                ×
              </button>
              <p className="mt-1 truncate text-[10px] text-rose-700/80">{file.name}</p>
            </li>
          ))}
        </ul>
      )}

      {kind === "video" && files.length > 0 && (
        <ul className="space-y-3">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${file.size}-${index}`}
              className="group relative overflow-hidden rounded-2xl border border-rose-100 bg-rose-50/50"
            >
              <video
                src={previewUrls[index]}
                controls
                playsInline
                preload="metadata"
                className="max-h-48 w-full bg-black object-contain"
              >
                <track kind="captions" />
              </video>
              <div className="flex items-center justify-between gap-2 px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-rose-900">
                    视频 {index + 1}：{file.name}
                  </p>
                  <p className="text-xs text-rose-600">{formatFileSize(file.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeAt(index)}
                  className="shrink-0 rounded-full border border-rose-200 bg-white px-3 py-1 text-xs text-rose-800 hover:bg-rose-50"
                >
                  移除
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
