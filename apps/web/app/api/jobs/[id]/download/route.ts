import fs from "node:fs"
import { prisma } from "@/lib/prisma"
import { getJobOutputPath, resolveStoragePath } from "@/lib/storage"
import { NextResponse } from "next/server"

export const runtime = "nodejs"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const { id } = await context.params
    const job = await prisma.job.findUnique({ where: { id } })

    if (!job || job.status !== "completed") {
      return NextResponse.json(
        { error: "NOT_READY", message: "成片尚未生成完成" },
        { status: 404 },
      )
    }

    const outputPath = job.outputPath
      ? resolveStoragePath(job.outputPath)
      : getJobOutputPath(id)

    if (!fs.existsSync(outputPath)) {
      return NextResponse.json(
        { error: "FILE_NOT_FOUND", message: "成片文件不存在" },
        { status: 404 },
      )
    }

    const stream = fs.createReadStream(outputPath)
    const fileName = `baby-moon-${id.slice(0, 8)}.mp4`

    return new NextResponse(stream as unknown as BodyInit, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": `attachment; filename="${fileName}"`,
      },
    })
  } catch (error) {
    console.error("GET /api/jobs/[id]/download failed:", error)
    return NextResponse.json(
      { error: "INTERNAL_ERROR", message: "下载失败" },
      { status: 500 },
    )
  }
}
