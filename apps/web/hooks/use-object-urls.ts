import { useEffect, useState } from "react"

/** 为 File 列表创建预览 URL，卸载或文件变化时自动 revoke */
export function useObjectUrls(files: File[]): string[] {
  const [urls, setUrls] = useState<string[]>([])

  useEffect(() => {
    const next = files.map((file) => URL.createObjectURL(file))
    setUrls(next)
    return () => {
      for (const url of next) URL.revokeObjectURL(url)
    }
  }, [files])

  return urls
}
