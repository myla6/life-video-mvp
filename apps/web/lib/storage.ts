import fs from "node:fs/promises"
import path from "node:path"

const webRoot = process.cwd()
const projectRoot = path.resolve(webRoot, "../..")

export function getStorageRoot(): string {
  const configured = process.env.STORAGE_ROOT
  if (configured) {
    return path.isAbsolute(configured)
      ? configured
      : path.resolve(webRoot, configured)
  }
  return path.join(projectRoot, "storage")
}

export function getProjectRoot(): string {
  return projectRoot
}

export function getTemplatesDir(): string {
  return path.join(projectRoot, "templates")
}

export async function ensureStorageDirs(): Promise<void> {
  const root = getStorageRoot()
  await fs.mkdir(path.join(root, "uploads"), { recursive: true })
  await fs.mkdir(path.join(root, "outputs"), { recursive: true })
}

export function getJobUploadDir(jobId: string): string {
  return path.join(getStorageRoot(), "uploads", jobId)
}

export function getJobOutputPath(jobId: string): string {
  return path.join(getStorageRoot(), "outputs", `${jobId}.mp4`)
}

/** DB 存相对 storage 根目录的路径 */
export function toStorageRelativePath(absolutePath: string): string {
  const root = getStorageRoot()
  return path.relative(root, absolutePath).split(path.sep).join("/")
}

export function resolveStoragePath(relativePath: string): string {
  return path.join(getStorageRoot(), relativePath)
}

export function getJobDownloadUrl(jobId: string): string {
  return `/api/jobs/${jobId}/download`
}
