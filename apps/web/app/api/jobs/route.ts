import fs from "node:fs/promises"
import path from "node:path"
import { AssetType } from "@/app/generated/prisma/client"
import { formatEstimatedDuration } from "@/lib/duration"
import { prisma } from "@/lib/prisma"
import {
  ensureStorageDirs,
  getJobDownloadUrl,
  getJobUploadDir,
  toStorageRelativePath,
} from "@/lib/storage"
import { getBgmPresets, loadBabyMoonTemplate } from "@/lib/template"
import {
  photoExtension,
  validateBabyName,
  validateBgmPreset,
  validateBlessing,
  validateEventDate,
  validatePhotos,
  validateVideos,
  videoExtension,
} from "@/lib/validation"
import { NextResponse } from "next/server"

export const runtime = "nodejs"

async function saveFile(file: File, targetPath: string): Promise<void> {
  const buffer = Buffer.from(await file.arrayBuffer())
  await fs.writeFile(targetPath, buffer)
}

export async function POST(request: Request) {
  try {
    const template = await loadBabyMoonTemplate()
    const formData = await request.formData()

    const babyName = String(formData.get("babyName") ?? "").trim()
    const eventDate = String(formData.get("eventDate") ?? "").trim()
    const blessingRaw = formData.get("blessing")
    const blessing =
      blessingRaw === null || blessingRaw === undefined
        ? null
        : String(blessingRaw).trim() || null
    const bgmPreset = String(formData.get("bgmPreset") ?? "warm_piano")

    const photos = formData
      .getAll("photos")
      .filter((item): item is File => item instanceof File && item.size > 0)
    const videos = formData
      .getAll("videos")
      .filter((item): item is File => item instanceof File && item.size > 0)

    const checks = [
      validateBabyName(babyName),
      validateEventDate(eventDate),
      validateBlessing(blessing),
      validateBgmPreset(bgmPreset, getBgmPresets(template)),
      validatePhotos(
        photos,
        template.constraints.photos.min,
        template.constraints.photos.max,
      ),
      validateVideos(videos, template.constraints.videos.max),
    ]

    for (const check of checks) {
      if (!check.ok) {
        return NextResponse.json(
          {
            error: "VALIDATION_ERROR",
            message: check.error,
            details: check.details,
          },
          { status: 400 },
        )
      }
    }

    await ensureStorageDirs()

    const job = await prisma.job.create({
      data: {
        templateId: template.id,
        babyName,
        eventDate,
        blessing,
        bgmPreset,
        status: "created",
        progress: 0,
      },
    })

    const uploadDir = getJobUploadDir(job.id)
    await fs.mkdir(uploadDir, { recursive: true })

    const assetRows: Array<{
      type: AssetType
      fileName: string
      filePath: string
      sortOrder: number
    }> = []

    for (let i = 0; i < photos.length; i++) {
      const file = photos[i]
      const ext = photoExtension(file)
      const fileName = `photo_${String(i).padStart(3, "0")}${ext}`
      const absolutePath = path.join(uploadDir, fileName)
      await saveFile(file, absolutePath)
      assetRows.push({
        type: AssetType.photo,
        fileName,
        filePath: toStorageRelativePath(absolutePath),
        sortOrder: i,
      })
    }

    for (let i = 0; i < videos.length; i++) {
      const file = videos[i]
      const ext = videoExtension(file)
      const fileName = `video_${String(i).padStart(3, "0")}${ext}`
      const absolutePath = path.join(uploadDir, fileName)
      await saveFile(file, absolutePath)
      assetRows.push({
        type: AssetType.video,
        fileName,
        filePath: toStorageRelativePath(absolutePath),
        sortOrder: photos.length + i,
      })
    }

    if (assetRows.length > 0) {
      await prisma.jobAsset.createMany({
        data: assetRows.map((row) => ({
          jobId: job.id,
          ...row,
        })),
      })
    }

    const duration = formatEstimatedDuration(photos.length, videos.length)

    return NextResponse.json(
      {
        id: job.id,
        status: job.status,
        ...duration,
      },
      { status: 201 },
    )
  } catch (error) {
    console.error("POST /api/jobs failed:", error)
    return NextResponse.json(
      {
        error: "INTERNAL_ERROR",
        message: "创建任务失败，请稍后重试",
      },
      { status: 500 },
    )
  }
}
