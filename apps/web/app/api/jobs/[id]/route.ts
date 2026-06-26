import { prisma } from "@/lib/prisma"
import { getJobDownloadUrl } from "@/lib/storage"
import { NextResponse } from "next/server"

export const runtime = "nodejs"

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const { id } = await context.params
    const job = await prisma.job.findUnique({
      where: { id },
      select: {
        id: true,
        status: true,
        progress: true,
        babyName: true,
        eventDate: true,
        blessing: true,
        bgmPreset: true,
        outputUrl: true,
        errorMsg: true,
        createdAt: true,
        updatedAt: true,
      },
    })

    if (!job) {
      return NextResponse.json(
        { error: "NOT_FOUND", message: "任务不存在" },
        { status: 404 },
      )
    }

    return NextResponse.json({
      ...job,
      outputUrl:
        job.status === "completed"
          ? job.outputUrl ?? getJobDownloadUrl(job.id)
          : null,
    })
  } catch (error) {
    console.error("GET /api/jobs/[id] failed:", error)
    return NextResponse.json(
      { error: "INTERNAL_ERROR", message: "查询任务失败" },
      { status: 500 },
    )
  }
}
