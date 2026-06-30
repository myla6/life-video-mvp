"use client"

import { daysInMonth, formatDateDisplay } from "@/lib/format"
import { useMemo } from "react"

type DatePickerFieldProps = {
  value: string
  onChange: (value: string) => void
  id?: string
}

const CURRENT_YEAR = new Date().getFullYear()
const YEAR_OPTIONS = Array.from({ length: 8 }, (_, i) => CURRENT_YEAR - i)

function parseIsoDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return { year: "", month: "", day: "" }
  return { year: match[1], month: String(Number(match[2])), day: String(Number(match[3])) }
}

function toIsoDate(year: string, month: string, day: string): string {
  if (!year || !month || !day) return ""
  const y = Number(year)
  const m = Number(month)
  const d = Number(day)
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return ""
  const maxDay = daysInMonth(y, m)
  if (d < 1 || d > maxDay) return ""
  return `${year}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`
}

const selectClass =
  "w-full appearance-none rounded-xl border border-rose-200 bg-white px-3 py-3 text-rose-950 outline-none ring-rose-300 focus:ring-2"

export function DatePickerField({ value, onChange, id }: DatePickerFieldProps) {
  const { year, month, day } = parseIsoDate(value)

  const dayOptions = useMemo(() => {
    if (!year || !month) return Array.from({ length: 31 }, (_, i) => i + 1)
    return Array.from(
      { length: daysInMonth(Number(year), Number(month)) },
      (_, i) => i + 1,
    )
  }, [year, month])

  function update(part: "year" | "month" | "day", next: string) {
    const nextYear = part === "year" ? next : year
    const nextMonth = part === "month" ? next : month
    let nextDay = part === "day" ? next : day
    if (nextYear && nextMonth && nextDay) {
      const max = daysInMonth(Number(nextYear), Number(nextMonth))
      if (Number(nextDay) > max) nextDay = String(max)
    }
    onChange(toIsoDate(nextYear, nextMonth, nextDay))
  }

  const display = formatDateDisplay(value)

  return (
    <div className="space-y-3" id={id}>
      <div className="grid grid-cols-3 gap-3">
        <label className="space-y-1">
          <span className="text-xs text-rose-600">年</span>
          <select
            required
            value={year}
            onChange={(e) => update("year", e.target.value)}
            className={selectClass}
          >
            <option value="">选择</option>
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={String(y)}>
                {y} 年
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs text-rose-600">月</span>
          <select
            required
            value={month}
            onChange={(e) => update("month", e.target.value)}
            className={selectClass}
          >
            <option value="">选择</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={String(m)}>
                {m} 月
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs text-rose-600">日</span>
          <select
            required
            value={day}
            onChange={(e) => update("day", e.target.value)}
            className={selectClass}
          >
            <option value="">选择</option>
            {dayOptions.map((d) => (
              <option key={d} value={String(d)}>
                {d} 日
              </option>
            ))}
          </select>
        </label>
      </div>
      {display ? (
        <p className="rounded-xl bg-rose-50 px-4 py-2 text-sm text-rose-800">
          满月日期：{display}
        </p>
      ) : (
        <p className="text-xs text-rose-600/80">请选择宝宝的满月日期</p>
      )}
    </div>
  )
}
