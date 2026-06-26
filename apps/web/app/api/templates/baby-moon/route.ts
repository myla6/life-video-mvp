import { loadBabyMoonTemplate } from "@/lib/template"
import { NextResponse } from "next/server"

export const runtime = "nodejs"

export async function GET() {
  try {
    const template = await loadBabyMoonTemplate()
    return NextResponse.json({
      id: template.id,
      name: template.name,
      formFields: template.formFields,
      constraints: template.constraints,
      bgmPresets: template.audio.bgm.presets,
    })
  } catch (error) {
    console.error("GET /api/templates/baby-moon failed:", error)
    return NextResponse.json(
      { error: "INTERNAL_ERROR", message: "读取模板失败" },
      { status: 500 },
    )
  }
}
