import fs from "node:fs/promises"
import path from "node:path"
import { getTemplatesDir } from "@/lib/storage"

export type TemplateConstraints = {
  photos: { min: number; max: number }
  videos: { min: number; max: number }
}

export type BabyMoonTemplate = {
  id: string
  name: string
  formFields: Array<{
    key: string
    label: string
    required?: boolean
    maxLength?: number
    type?: string
  }>
  constraints: TemplateConstraints
  segments: Array<{
    id: string
    type: string
    duration?: number
    optional?: boolean
    style?: Record<string, unknown>
  }>
  audio: {
    bgm: {
      presets: string[]
    }
  }
}

export async function loadBabyMoonTemplate(): Promise<BabyMoonTemplate> {
  const filePath = path.join(getTemplatesDir(), "baby_full_moon_v1.json")
  const raw = await fs.readFile(filePath, "utf-8")
  return JSON.parse(raw) as BabyMoonTemplate
}

export function getBgmPresets(template: BabyMoonTemplate): string[] {
  return template.audio.bgm.presets
}
