-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('created', 'queued', 'preprocessing', 'rendering', 'uploading', 'completed', 'failed');

-- CreateEnum
CREATE TYPE "AssetType" AS ENUM ('photo', 'video');

-- CreateTable
CREATE TABLE "Job" (
    "id" TEXT NOT NULL,
    "templateId" TEXT NOT NULL DEFAULT 'baby_full_moon_v1',
    "status" "JobStatus" NOT NULL DEFAULT 'created',
    "progress" INTEGER NOT NULL DEFAULT 0,
    "errorMsg" TEXT,
    "babyName" TEXT NOT NULL,
    "eventDate" TEXT NOT NULL,
    "blessing" TEXT,
    "bgmPreset" TEXT NOT NULL DEFAULT 'warm_piano',
    "outputPath" TEXT,
    "outputUrl" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Job_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "JobAsset" (
    "id" TEXT NOT NULL,
    "jobId" TEXT NOT NULL,
    "type" "AssetType" NOT NULL,
    "fileName" TEXT NOT NULL,
    "filePath" TEXT NOT NULL,
    "sortOrder" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "JobAsset_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "Job_status_createdAt_idx" ON "Job"("status", "createdAt");

-- CreateIndex
CREATE INDEX "JobAsset_jobId_sortOrder_idx" ON "JobAsset"("jobId", "sortOrder");

-- AddForeignKey
ALTER TABLE "JobAsset" ADD CONSTRAINT "JobAsset_jobId_fkey" FOREIGN KEY ("jobId") REFERENCES "Job"("id") ON DELETE CASCADE ON UPDATE CASCADE;
