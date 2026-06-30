export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatDateDisplay(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate)
  if (!match) return ""
  const [, year, month, day] = match
  return `${year}年${Number(month)}月${Number(day)}日`
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}
