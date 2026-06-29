# 技术方案：MVP 全栈架构

> 项目：`life-video-mvp`  
> 版本：v1.0 · 2026-06-26  
> 读者：前端背景、正在补全链路能力的开发者  
> 配套文档：[MVP 开工包](./mvp-满月短片-开工包.md) · [全链路方案](./生活场景AI短片工具-全链路方案.md)

---

## 目录

1. [文档目的](#1-文档目的)
2. [技术选型结论](#2-技术选型结论)
3. [整体架构](#3-整体架构)
4. [仓库结构](#4-仓库结构)
5. [各层职责](#5-各层职责)
6. [数据模型](#6-数据模型)
7. [API 设计](#7-api-设计)
8. [文件存储约定](#8-文件存储约定)
9. [任务状态机与 Worker](#9-任务状态机与-worker)
10. [前端页面与交互](#10-前端页面与交互)
11. [本地开发环境](#11-本地开发环境)
12. [分阶段演进](#12-分阶段演进)
13. [部署与上线（第二周）](#13-部署与上线第二周)
14. [前端开发者的学习地图](#14-前端开发者的学习地图)
15. [明确不做的事](#15-明确不做的事)
16. [附录：Biome 配置要点](#16-附录biome-配置要点)

---

## 1. 文档目的

开工包回答「做什么、按天干什么」；本文回答「**用什么技术、怎么拆、为什么这样选**」。

当前进度（2026-06-26）：

| 模块 | 状态 |
|------|------|
| `worker/render.py` 本地 ffmpeg 成片 | ✅ 已完成（Day 2） |
| `templates/baby_full_moon_v1.json` | ✅ 已有 |
| `docker-compose.yml`（Postgres + Redis） | ✅ 已有 |
| `apps/web` Next.js 全栈 | ✅ Day 3（上传 + API + 页面） |
| Worker 消费任务 | ✅ Day 4（DB 轮询 + render.py） |

---

## 2. 技术选型结论

### 2.1 总览

| 层级 | 选型 | 备选（不采用原因） |
|------|------|-------------------|
| 前端框架 | **Next.js 15 App Router + TypeScript** | TanStack Start：生态较新，MVP 第一周不确定性高 |
| 代码规范 | **Biome**（lint + format） | ESLint + Prettier：可以，但 Biome 更轻、更快 |
| Web API | **Next.js Route Handlers** | NestJS / Java：多一个服务，个人 MVP 过重 |
| ORM | **Prisma** | Drizzle：也可以，Prisma 资料更多、schema 直观 |
| 数据库 | **PostgreSQL 16** | SQLite：够用但和上线环境不一致 |
| 队列（第一周） | **DB 轮询** | 直接上 Redis：可以，但第一周少一个依赖 |
| 队列（第二周） | **Redis + BullMQ 或 Python 侧简单队列** | — |
| 视频合成 | **Python 3.11 + ffmpeg** | Node fluent-ffmpeg：生态不如 Python，且已有脚本 |
| 包管理 | **pnpm** | npm/yarn 均可，pnpm 省磁盘、workspace 友好 |
| 仓库模式 | **单 Git 仓库 + 目录分模块** | 多 repo：模板/assets 共享麻烦 |
| 存储（MVP） | **本地 `storage/`** | 直接 OSS：可以，但本地调试更快 |
| 部署（MVP 后） | **一台 ECS + Docker Compose** | Serverless：ffmpeg 长任务不适合 |

### 2.2 为什么不用 TanStack Start？

TanStack Start 和 Biome **不是绑定关系**。Biome 可以单独用在 Next.js 里。

| 维度 | Next.js | TanStack Start |
|------|---------|----------------|
| 全栈 API | Route Handlers，成熟 | Server Functions，较新 |
| 资料 / AI 辅助 | 极多 | 较少 |
| 与现有文档 | 开工包、目录结构已对齐 | 需重写规划 |
| 本产品需求 | 4 页 + 上传 + 轮询，App Router 足够 | 复杂客户端路由不是刚需 |
| 学习价值 | 面试叙事、部署路径清晰 | 适合专门学 TanStack 生态时再开 |

**定案：Phase 1 用 Next.js；TanStack Start 留作 Phase 2+ 技术探索，不挡 MVP。**

### 2.3 为什么 Web 层和后端合成层分开？

```text
         TypeScript 世界                    Python 世界
┌─────────────────────────┐          ┌─────────────────────────┐
│ Next.js                 │          │ worker/                 │
│ · 页面 / 上传 / 轮询     │   Job    │ · 读 DB / 队列          │
│ · API / Prisma / 校验    │ ──────▶  │ · render.py / ffmpeg    │
│ · 写任务、返回 jobId     │          │ · 更新 status、写成片   │
└─────────────────────────┘          └─────────────────────────┘
```

- **你主力写 TS**：页面、API、数据库，和前端技能栈一致。
- **合成放 Python**：ffmpeg 命令、字幕字体、视频处理社区实践都在 Python 侧；`render.py` 已验证，不必重写。
- **边界清晰**：Web 层只负责「接任务、存文件、查状态」；Worker 只负责「读任务、合成、改状态」。

---

## 3. 整体架构

### 3.1 MVP 架构图（第一周：DB 轮询版）

```mermaid
flowchart TB
    subgraph Browser
        UI[Next.js 页面]
    end

    subgraph Web["apps/web (Next.js)"]
        API[Route Handlers]
        Prisma[Prisma Client]
    end

    subgraph Infra
        PG[(PostgreSQL)]
        FS[storage/ 本地磁盘]
    end

    subgraph Worker["worker/ (Python)"]
        Poll[轮询 created 任务]
        Render[render.py + ffmpeg]
    end

    UI -->|上传 + 表单| API
    UI -->|轮询 GET /api/jobs/:id| API
    API --> Prisma --> PG
    API -->|保存素材| FS
    Poll -->|SELECT status=created| PG
    Poll --> Render
    Render -->|读素材| FS
    Render -->|写 final.mp4| FS
    Render -->|UPDATE status| PG
    API -->|completed 时返回 outputUrl| UI
```

### 3.2 目标架构图（第二周：加 Redis + OSS）

```mermaid
flowchart TB
    UI[Next.js] --> API[Route Handlers]
    API --> PG[(PostgreSQL)]
    API -->|enqueue| Redis[(Redis)]
    Redis --> Worker[Python Worker]
    Worker --> OSS[对象存储 OSS]
    Worker --> PG
    API -->|签名 URL| UI
```

第一周刻意**不依赖 Redis**，Worker 每 N 秒查一次 DB 即可跑通全链路；队列是优化项，不是阻塞项。

---

## 4. 仓库结构

### 4.1 定案：单仓库 + 轻量 Monorepo

保持一个 Git 仓库，按目录分模块。**不拆多个 repo，不上 Turborepo/Nx。**

```text
life-video-mvp/
├── apps/
│   └── web/                      # Next.js：前端 + API + Prisma
│       ├── app/
│       │   ├── page.tsx                    # 首页
│       │   ├── create/baby-moon/page.tsx   # 创作页
│       │   ├── jobs/[id]/page.tsx          # 等待 / 结果页
│       │   └── api/
│       │       ├── jobs/route.ts           # POST 创建
│       │       ├── jobs/[id]/route.ts      # GET 状态
│       │       └── jobs/[id]/download/route.ts
│       ├── lib/
│       │   ├── prisma.ts                   # Prisma 单例
│       │   ├── storage.ts                  # 本地路径工具
│       │   └── duration.ts                 # 时长预估（对齐模板 4.4）
│       ├── prisma/
│       │   └── schema.prisma
│       ├── biome.json
│       ├── package.json
│       └── next.config.ts
├── worker/
│   ├── main.py                   # 轮询 DB → 调 render
│   ├── render.py                 # ffmpeg 合成（已有）
│   ├── db.py                     # 读/写 Job（psycopg 或 SQLAlchemy）
│   └── requirements.txt
├── templates/                    # 模板 JSON（Web 可读元信息，Worker 读时间轴）
├── assets/
│   ├── bgm/
│   └── fonts/
├── storage/                      # gitignore，运行时文件
│   ├── uploads/{jobId}/
│   └── outputs/{jobId}.mp4
├── test-assets/                  # 本地 ffmpeg 验证用
├── docker-compose.yml
├── pnpm-workspace.yaml           # 可选，仅 apps/web 时也建议保留扩展位
├── docs/
└── README.md
```

### 4.2 为什么不用「纯融在一起」或「重型 Monorepo」？

| 方案 | 评价 |
|------|------|
| 所有代码堆在根目录 | ❌ Web / Worker / 模板边界模糊，后期难维护 |
| **单 repo + 目录分模块**（现方案） | ✅ 共享 templates/assets/storage，一次 commit 可改 API + Worker |
| pnpm workspace + `packages/shared` | ⚠️ 第一版可选；等有第二个 TS 包（如 admin）再加 |
| Web / Worker 两个 Git 仓库 | ❌ 路径约定、模板同步、联调成本都更高 |

### 4.3 根目录 `pnpm-workspace.yaml`（建议）

```yaml
packages:
  - "apps/*"
  # - "packages/*"   # 以后加 shared 类型包时再打开
```

Worker 不用 pnpm 管理，独立 `python -m venv` 即可。

---

## 5. 各层职责

### 5.1 Next.js（apps/web）

| 职责 | 说明 |
|------|------|
| 页面渲染 | 首页、创作页、任务页 |
| 上传与校验 | 照片 5～15、视频 0～2、格式与大小 |
| 创建任务 | 写 DB、存文件、返回 `jobId` |
| 查询状态 | 供前端轮询 |
| 提供下载 | `completed` 时返回可访问 URL |
| 时长预估 | 根据照片数调用与模板一致的公式 |

**不做：** ffmpeg 合成、长时间阻塞请求。

### 5.2 PostgreSQL + Prisma

| 职责 | 说明 |
|------|------|
| 任务持久化 | Job 状态、进度、错误信息 |
| 素材元数据 | JobAsset 路径、排序 |
| Worker 协作 | Worker 通过 SQL 拉取 `created` 任务 |

### 5.3 Python Worker

| 职责 | 说明 |
|------|------|
| 消费任务 | 轮询 DB（后演进 Redis） |
| 预处理 | 确认素材存在、可选 ffprobe |
| 合成 | 调用 `render.render_baby_full_moon()` |
| 更新状态 | `preprocessing → rendering → completed / failed` |
| 写成片 | `storage/outputs/{jobId}.mp4` |

**不要求：** 你手写复杂 Python，但要能读日志、改参数、理解状态流转。

### 5.4 共享资产（templates / assets）

| 路径 | 读者 | 用途 |
|------|------|------|
| `templates/*.json` | Web（表单字段、约束）、Worker（时间轴） | 单一事实来源 |
| `assets/bgm/` | Worker | BGM 文件 |
| `assets/fonts/` | Worker | 中文字幕（Day 6+） |

Web 可通过 `fs.readFile` 或 API 读取模板 JSON 的 `formFields`、`constraints`；不必在前端硬编码一份。

---

## 6. 数据模型

### 6.1 Prisma Schema（定稿草案）

```prisma
// apps/web/prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Job {
  id         String   @id @default(cuid())
  templateId String   @default("baby_full_moon_v1")
  status     JobStatus @default(created)
  progress   Int      @default(0)
  errorMsg   String?

  babyName   String
  eventDate  String
  blessing   String?
  bgmPreset  String   @default("warm_piano")

  outputPath String?  // 本地: storage/outputs/{id}.mp4
  outputUrl  String?  // 对外 URL，MVP 可为 /api/jobs/{id}/download

  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt

  assets     JobAsset[]

  @@index([status, createdAt])
}

model JobAsset {
  id        String   @id @default(cuid())
  jobId     String
  job       Job      @relation(fields: [jobId], references: [id], onDelete: Cascade)
  type      AssetType
  fileName  String
  filePath  String   // 相对或绝对路径，见 §8
  sortOrder Int      @default(0)
  createdAt DateTime @default(now())

  @@index([jobId, sortOrder])
}

enum JobStatus {
  created
  queued
  preprocessing
  rendering
  uploading
  completed
  failed
}

enum AssetType {
  photo
  video
}
```

第一版**不建 `users` 表**。限流可用 IP + 内存计数或 middleware 简单实现。

### 6.2 状态与 progress 映射

与开工包第三节一致：

| status | progress | 含义 |
|--------|----------|------|
| `created` | 0 | API 刚写入，等待 Worker |
| `queued` | 10 | 可选，接 Redis 后使用 |
| `preprocessing` | 30 | Worker 已认领，检查素材 |
| `rendering` | 60 | ffmpeg 合成中 |
| `uploading` | 90 | 第二周上传 OSS 时用；本地版可跳过 |
| `completed` | 100 | 成片可下载 |
| `failed` | — | `errorMsg` 必填 |

---

## 7. API 设计

### 7.1 接口清单

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/jobs` | 创建任务（multipart） |
| `GET` | `/api/jobs/[id]` | 查询状态 |
| `GET` | `/api/jobs/[id]/download` | 下载成片（`completed` 时） |
| `GET` | `/api/templates/baby-moon` | 返回模板元信息（可选） |

### 7.2 POST `/api/jobs`

**Content-Type：** `multipart/form-data`

| 字段 | 类型 | 必填 | 校验 |
|------|------|------|------|
| `babyName` | string | ✅ | ≤ 20 字 |
| `eventDate` | string | ✅ | `YYYY-MM-DD` |
| `blessing` | string | ❌ | ≤ 50 字 |
| `bgmPreset` | string | ❌ | `warm_piano` \| `soft_guitar` \| `lullaby` |
| `photos` | File[] | ✅ | 5～15，jpg/png/webp，单张 < 10MB |
| `videos` | File[] | ❌ | 0～2，mp4/mov，单段 < 100MB |

**处理流程：**

```text
1. 校验字段与文件
2. prisma.job.create({ status: created, ... })
3. mkdir storage/uploads/{jobId}/
4. 按顺序保存 photos → JobAsset(type: photo, sortOrder)
5. 保存 videos → JobAsset(type: video)
6. 返回 { id, status: "created", estimatedDurationSec }
```

**成功响应 201：**

```json
{
  "id": "clxabc123",
  "status": "created",
  "estimatedDurationSec": 38,
  "estimatedDurationText": "预计成片约 38 秒（10 张照片）"
}
```

**错误响应 400 示例：**

```json
{
  "error": "VALIDATION_ERROR",
  "message": "至少需要 5 张照片",
  "details": { "photos": { "min": 5, "received": 3 } }
}
```

### 7.3 GET `/api/jobs/[id]`

**成功 200：**

```json
{
  "id": "clxabc123",
  "status": "rendering",
  "progress": 60,
  "babyName": "小糯米",
  "outputUrl": null,
  "errorMsg": null,
  "createdAt": "2026-06-26T08:00:00.000Z",
  "updatedAt": "2026-06-26T08:01:30.000Z"
}
```

`completed` 时：

```json
{
  "status": "completed",
  "progress": 100,
  "outputUrl": "/api/jobs/clxabc123/download"
}
```

### 7.4 GET `/api/jobs/[id]/download`

- 仅 `status === completed` 且文件存在时返回 `200`
- `Content-Type: video/mp4`
- `Content-Disposition: attachment; filename="baby-moon-{id}.mp4"`
- 本地 MVP：`createReadStream(outputPath)` 流式返回

### 7.5 时长预估（前后端一致）

公式与开工包 [4.4](./mvp-满月短片-开工包.md#44-时长规则) 一致：

```text
总时长 = 开头(5s) + 照片数 × 2.8s + 视频时长(0～10s) + 结尾(5s)
```

Web 端 `lib/duration.ts` 可读 `templates/baby_full_moon_v1.json` 计算；Worker 端 `render.compute_duration()` 已实现对齐。

---

## 8. 文件存储约定

### 8.1 目录布局

```text
storage/
├── uploads/
│   └── {jobId}/
│       ├── photo_000.jpg
│       ├── photo_001.jpg
│       └── video_000.mp4          # 可选
└── outputs/
    └── {jobId}.mp4
```

### 8.2 路径存 DB 的方式

建议 DB 存**相对项目根的路径**，便于本地与服务器一致：

```text
uploads/clxabc123/photo_000.jpg
outputs/clxabc123.mp4
```

Web 与 Worker 各自用 `ROOT / "storage" / filePath` 解析。

### 8.3 环境变量

```bash
# apps/web/.env
DATABASE_URL="postgresql://lifevideo:lifevideo@localhost:5433/life_video_mvp"
STORAGE_ROOT="../../storage"   # 或使用绝对路径

# worker/.env
DATABASE_URL="postgresql://lifevideo:lifevideo@localhost:5433/life_video_mvp"
STORAGE_ROOT="../storage"
PROJECT_ROOT=".."
```

---

## 9. 任务状态机与 Worker

### 9.1 状态流转

```mermaid
stateDiagram-v2
    [*] --> created: POST /api/jobs
    created --> preprocessing: Worker 认领
    preprocessing --> rendering: 素材 OK
    preprocessing --> failed: 素材缺失/损坏
    rendering --> completed: ffmpeg 成功
    rendering --> failed: ffmpeg 失败
    completed --> [*]
    failed --> [*]
```

第二周可在 `created → queued` 之间插入 Redis；`uploading` 在接 OSS 时启用。

### 9.2 Worker 主循环（第一周）

```python
# 伪代码 — worker/main.py 目标形态

while True:
    job = db.fetch_one(status="created", order="createdAt")
    if not job:
        sleep(3)
        continue

    try:
        db.update(job.id, status="preprocessing", progress=30)
        photos = load_photo_paths(job)
        output = STORAGE / "outputs" / f"{job.id}.mp4"

        db.update(job.id, status="rendering", progress=60)
        render_baby_full_moon(
            photo_paths=photos,
            output_path=output,
            baby_name=job.babyName,
            event_date=job.eventDate,
            blessing=job.blessing or "",
            bgm_preset=job.bgmPreset,
        )

        db.update(job.id, status="completed", progress=100,
                   outputPath=f"outputs/{job.id}.mp4",
                   outputUrl=f"/api/jobs/{job.id}/download")
    except Exception as e:
        db.update(job.id, status="failed", errorMsg=str(e))
```

### 9.3 并发与认领

MVP 单 Worker 进程即可。认领任务时用**乐观锁**避免重复消费：

```sql
UPDATE "Job"
SET status = 'preprocessing', progress = 30, "updatedAt" = NOW()
WHERE id = $1 AND status = 'created'
RETURNING *;
```

若 `RETURNING` 为空，说明已被其他 Worker 抢走。

### 9.4 替代方案：API 直接 subprocess（仅调试）

Day 3 若只想最快看到「上传 → 出片」，可临时在 `POST /api/jobs` 里 `spawn('python', ['worker/render.py', ...])`。**不要作为正式方案**：会阻塞 API 进程、难扩展。Day 4 应切到独立 Worker。

---

## 10. 前端页面与交互

### 10.1 页面清单

| 路由 | 作用 | 关键组件/逻辑 |
|------|------|----------------|
| `/` | 首页 | 介绍 + 进入「宝宝满月」 |
| `/create/baby-moon` | 创作页 | 多选上传、表单、BGM、时长预估、提交 |
| `/jobs/[id]` | 等待/结果 | 2s 轮询、`progress` 进度条、`completed` 时 `<video>` + 下载 |

### 10.2 创作页交互要点

1. **照片选择后**立即显示：`预计成片约 XX 秒（N 张照片）`
2. **提交前校验**：照片 < 5 拦截，不发起请求
3. **提交中**：按钮 loading，防止重复提交
4. **成功后** `router.push(/jobs/${id})`

### 10.3 轮询策略

```typescript
// 伪代码
useEffect(() => {
  if (!id || status === "completed" || status === "failed") return;
  const timer = setInterval(async () => {
    const job = await fetch(`/api/jobs/${id}`).then(r => r.json());
    setJob(job);
  }, 2000);
  return () => clearInterval(timer);
}, [id, status]);
```

`failed` 展示 `errorMsg` +「返回修改」链接。

### 10.4 技术栈（前端部分）

| 用途 | 选型 | 说明 |
|------|------|------|
| 框架 | Next.js App Router | Server / Client Component 按需 |
| 样式 | Tailwind CSS | create-next-app 默认带上 |
| 表单 | 原生 + 少量 state 即可 | MVP 不必上 react-hook-form |
| 上传 | `<input type="file" multiple>` | 简单可控；大文件优化放第二周 |
| 数据请求 | `fetch` | 不必先上 TanStack Query；页面简单 |

---

## 11. 本地开发环境

### 11.1 启动顺序

```bash
# 1. 基础设施
docker compose up -d

# 2. Web
cd apps/web
pnpm install
pnpm prisma migrate dev
pnpm dev                    # http://localhost:3000

# 3. Worker（另开终端）
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 11.2 端口约定

| 服务 | 端口 |
|------|------|
| Next.js | 3000 |
| PostgreSQL | 5433（映射容器 5432） |
| Redis | 6380（第二周用） |

### 11.3 首次初始化 checklist

- [ ] `brew install ffmpeg` 且 `ffmpeg -version` 正常
- [ ] `docker compose up -d` 后 Postgres 可连
- [ ] `apps/web` 创建并 `prisma migrate`
- [ ] `storage/uploads`、`storage/outputs` 目录存在且可写
- [ ] Worker 能读到 `templates/` 与 `assets/bgm/`

---

## 12. 分阶段演进

与 [ROADMAP](../ROADMAP.md) 对齐，技术侧拆成三档：

### Phase A — 纵向打通（Day 3～5，当前目标）

| 项 | 做法 |
|----|------|
| Web | Next.js + 创作页 + API |
| DB | Prisma + Postgres |
| Worker | DB 轮询 + `render.py` |
| 存储 | 本地 `storage/` |
| 队列 | **不用 Redis** |
| 成片能力 | 照片轮播 + BGM（标题卡 Day 6） |

**完成标准：** 浏览器上传 → 等进度 → 下载 mp4。

### Phase B — 体验打磨（Day 6～7）

- 标题卡 / 结尾卡（ffmpeg drawtext 或 PNG 叠加）
- 前端校验、失败重试
- 连续 3 次生成至少 2 次成功

### Phase C — 工程化（第二周）

- Redis 队列
- OSS 存储 + `uploading` 状态
- ECS Docker 部署
- 简单限流 / 日志

---

## 13. 部署与上线（第二周）

MVP 本地跑通后再做，避免过早优化。

### 13.1 推荐拓扑（单机）

```text
同一台 ECS
├── docker compose
│   ├── postgres
│   ├── redis
│   ├── web (Next.js standalone 或 Node 进程)
│   └── worker (Python 常驻)
└── 数据盘挂载 /data/storage 或 直接用 OSS
```

### 13.2 为何不全放 Vercel？

- Vercel Serverless **不适合**跑 ffmpeg 长任务（超时、无持久磁盘）
- 合理分工：**Web 可 Vercel，Worker 必须常驻机**；个人 MVP 更简单的是**整机 Compose**

### 13.3 环境变量（生产）

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | 生产 Postgres |
| `STORAGE_ROOT` | 本地盘或 OSS mount |
| `OSS_*` | 第二周接入对象存储 |
| `REDIS_URL` | 第二周队列 |

### 13.4 ffmpeg 为何不在 package.json / requirements.txt

| 组件 | 依赖文件 | ffmpeg |
|------|----------|--------|
| Web（Next.js） | `apps/web/package.json` | 不涉及 |
| Worker（Python） | `worker/requirements.txt` | **不在此列** |

ffmpeg 是**系统级可执行文件**，Worker 通过 `subprocess.run(["ffmpeg", ...])` 调用（见 `worker/render.py`）。本地 `brew install ffmpeg`；生产环境在 **Worker Docker 镜像**里安装：

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# … pip install、COPY worker、CMD python main.py
```

Web 可放 Vercel；**Worker 必须常驻机**且带 ffmpeg。朋友场景 CPU 压力可控；扩展靠队列 + 多 Worker，而非 Serverless 跑合成。

---

## 14. 前端开发者的学习地图

按「必须懂」到「可以后学」排序：

### 必须懂（第一周）

| 主题 | 你要会什么 | 对应实践 |
|------|------------|----------|
| Route Handlers | 收 multipart、返回 JSON | `POST /api/jobs` |
| Prisma | schema、migrate、CRUD | Job / JobAsset |
| 异步任务思维 | 请求不阻塞合成 | 创建任务 vs 轮询结果 |
| 文件 IO | 存盘、流式下载 | `storage/`、`download` API |
| Docker 基础 | `compose up`、看日志 | Postgres 本地 |

### 跟着做即可（第一周）

| 主题 | 说明 |
|------|------|
| Python Worker | 会启动、看日志、改 `render.py` 参数 |
| ffmpeg | 不必背命令，理解输入输出即可 |
| SQL 索引 | `@@index([status, createdAt])` 知道为何存在 |

### 第二周再学

| 主题 | 说明 |
|------|------|
| Redis / 队列 | 解耦与扩展 |
| OSS 签名 URL | 安全下载 |
| CI/CD | 自动部署 |
| 监控 | 错误率、合成耗时 |

### 面试可讲的叙事

> 生活场景纪念短片 MVP：Next.js 全栈负责上传与任务 API，Postgres 持久化任务状态，Python Worker 消费任务并用 ffmpeg 按模板 JSON 合成竖屏 mp4；第一周 DB 轮询打通链路，第二周演进 Redis 与 OSS；后续可在输入层接 LLM Agent，合成层不变。

---

## 15. 演进：Agent、ffmpeg 部署与扩展

> 与 [ROADMAP Phase 3～5](../ROADMAP.md) 对齐。本文档为**架构备忘**，避免后续对话丢失上下文；Implementation 仍以当前 Phase 1 Day 清单为准，Agent 不挡 MVP 打通。

### 15.1 当前架构（Phase 1）

```text
用户填表单 + 选模板
    → POST /api/jobs（Next.js）
    → Postgres Job(status=created)
    → Python Worker 轮询 → render.py + ffmpeg
    → status=completed → 前端轮询预览/下载
```

这是 **固定模板 + 规则引擎**，无大模型，但已是典型的 **长任务 + 状态机 + 工具（ffmpeg）** 结构。

### 15.2 Agent 接入点（Phase 5，不推翻底层）

Agent **不替代** Worker/ffmpeg，只增强「诉求 → 任务参数」：

```text
Phase 5A（最小）
  用户自然语言 → LLM → 结构化 JSON（对齐 Job 字段）
    → 仍 POST /api/jobs → Worker → ffmpeg

Phase 5B（工具编排）
  用户诉求 → LLM 拆任务 → 调工具 analyze_photos / pick_bgm / render_video …
    → 各步写 Job 状态 → 最终 render_video 进现有 Worker

Phase 5C（后期）
  动态时间轴、高光检测、非固定 template — 工作量大，有用户后再做
```

**不变的部分**：`Job` / `JobAsset` 表、storage、Worker 消费、ffmpeg 成片、前端轮询。

**新增的部分**：对话 UI、LLM API 路由、Prompt/Schema、（可选）工具注册表。

### 15.3 资源与成本

| 组件 | 资源 | 说明 |
|------|------|------|
| ffmpeg Worker | CPU、磁盘 IO | ECS / Docker；1～3 分钟/条，朋友量级单机够用 |
| LLM | 云 API 按 token | 不占自机 GPU；思考几秒，瓶颈仍在合成 |
| 自部署大模型 | GPU | MVP 不做 |

### 15.4 扩展路径（量上来时）

```text
DB 轮询 → Redis/BullMQ → 多 Worker 实例
本地 storage → OSS + 签名 URL
单机 Compose → Web（Vercel）+ Worker 集群（ECS）
```

Agent 层与上述扩展正交：LLM 只负责「理解 + 编排」，重活仍在 Worker。

### 15.5 Agent 阶段还要 ffmpeg 吗？和大模型怎么分工？

**要。** Phase 5 变的是「谁理解用户、谁拆任务」，不是「谁编码出 mp4」。  
「更像 Agent」= **LLM 编排更多工具**，不等于 **用 LLM 直接生成整段视频、去掉 ffmpeg**。

| 能力 | 谁来做 | 例子 |
|------|--------|------|
| 理解用户说了啥 | **LLM** | 「温馨一点、宝宝照放前面」 |
| 拆任务、选工具 | **Agent / Orchestrator** | 先 analyze，再 pick_bgm，再 render |
| 看图 / 看视频内容 | **视觉模型（工具）** | 人脸、场景、模糊、高光片段 |
| 生成文案 | **LLM** | 祝福语、字幕 |
| **按时间轴拼片、编码、混音、字幕烧录** | **ffmpeg（工具）** | 720×1280 mp4、BGM、drawtext |

LLM **擅长思考和编排**，不擅长：把 N 张照片按秒数精确拼接、H.264 编码、音画同步、批量稳定出片——这些仍是 **ffmpeg 或云转码 API** 的领域。

**Phase 5B 示例（旅行 vlog 混剪）：**

```text
用户：「旅行 vlog 剪成 1 分钟，高潮放中间，轻快 BGM」

Agent → 调工具：
  1. analyze_videos      （视觉模型：镜头、运动强度）
  2. pick_highlights       （规则 + 模型：选片段）
  3. build_timeline        （LLM/规则：输出时间轴 JSON）
  4. render_video          （ffmpeg：按 JSON 执行出 mp4）  ← 仍在 Worker
  5. generate_subtitle     （LLM 文案 → ffmpeg drawtext）
```

**何时可以少依赖 ffmpeg？**

| 路径 | 说明 | 与本项目关系 |
|------|------|--------------|
| AI 成片 API（Runway、可灵等） | 模型直接出视频 | 贵、不可控；生活纪念「用户素材成片」形态不匹配 |
| 文生视频 | 几乎不用用户素材 | 产品形态不同 |
| 云剪辑 SaaS | 底层仍是转码管线 | 可接 API，面试叙事弱于自建 Worker |

**结论（生活场景模板 + 用户素材）：** LLM/视觉模型负责 **懂和选**，ffmpeg 负责 **拼和出**。Agent 越强，`render_video` 越像被调用的工具之一，而不是被 LLM 替代。

**面试一句话：**

> Agent 层用 LLM 做意图理解和工具编排；重编码合成仍在 Worker 里用 ffmpeg，保证成本、时延和成片质量可控；视觉模型作为 analyze 工具接入，而不是用 LLM 直接生成整段 mp4。

### 15.6 微信小程序：能直接变吗？API 怎么复用？

**不能一键把 Next.js 变成小程序**，但 **后端 API + Worker + ffmpeg 流水线可复用**；小程序是 **新增客户端**，不是重写后端。

```text
                    ┌─────────────────┐
  Web 浏览器  ──────▶│  Next.js        │
                    │  Route Handlers │──▶ Postgres → Worker → ffmpeg
  微信小程序  ──────▶│  （同一套 API）  │
                    └─────────────────┘
```

| 维度 | 现在（Web） | 微信小程序（Phase 4+） |
|------|-------------|------------------------|
| UI | React / Next.js | WXML + WXSS，或 Taro / uni-app |
| 上传 | `<input type="file">` | `wx.chooseMedia` + `wx.uploadFile` |
| 预览 | `<video>` | 小程序 `<video>`（需配置合法域名） |
| 任务 / 合成 | 共用 API | **复用** `POST/GET /api/jobs`、下载接口 |
| 部署 | Vercel / ECS | 微信开放平台审核 + **HTTPS 域名** |

**可直接复用：** Job 状态机、Prisma、`POST /api/jobs`、`GET /api/jobs/[id]`、下载、Worker、`templates/*.json`、storage/OSS。

**需新做：** 小程序页面（创作 / 进度 / 预览）、上传适配、（可选）微信登录、服务器域名与备案。

**技术选型（届时再定）：**

| 方案 | 优点 | 缺点 |
|------|------|------|
| 原生小程序 | 官方、体验好 | 与 React 两套 UI |
| Taro / uni-app | 部分 React 语法可复用 | 仍要适配差异，非零成本 |

**顺序：** 先 Web + API + Worker 全链路打穿（Phase 1～3），小程序作 Phase 4 触达层，不挡 MVP。

**面试一句话：**

> 架构上 API 与客户端解耦；Web 与小程序共用同一套 Job API 和 Worker 流水线，各端只适配上传与展示。

### 15.7 产品与学习路径（全栈 + Agent 叠层，备忘）

同一产品演进，不另起炉灶：

| 阶段 | 产品 | 学什么 | 客户端 |
|------|------|--------|--------|
| 现在～Day 7 | 满月 Web 全链路 | 异步任务、Worker、ffmpeg | Web |
| Phase 2 | 结婚 / 日常等多模板 | 模板复用、多场景 | Web |
| Phase 3 | 上线 | Redis、OSS、Docker、ffmpeg 镜像 | Web |
| Phase 5A | 对话生成 Job 参数 | LLM + JSON Schema + 人工确认 | Web |
| Phase 5B | 工具编排 | 函数 calling、视觉 analyze 工具 | Web |
| Phase 4+ | 触达 | — | **+ 小程序** |

场景扩展建议顺序：**满月 → 结婚或小朋友日常 → 旅行 vlog（偏 Phase 5C，时间轴更自由）**。

「完整产品」对个人作品集：**1～2 个场景真实交付 + 可部署 +（可选）Agent 5A**，比同时堆全场景 + 小程序 + 大模型更利于面试叙事。

| 不做 | 原因 |
|------|------|
| TanStack Start 作 MVP 主框架 | 学习成本高，与文档不对齐 |
| NestJS / Java 独立后端 | 个人 MVP 过重 |
| 第一版上 Redis 队列 | 可 Day 4 后再加，不挡打通 |
| Node 重写 ffmpeg 合成 | 已有 Python 脚本 |
| 第一版用户登录 / 支付 | 开工包 Out of Scope |
| 第一版微信小程序 | 先 Web |
| Turborepo / 多 Git 仓库 | 当前规模不需要 |
| API 内 subprocess 合成（正式环境） | 阻塞、难扩展 |

---

## 17. 附录：Biome 配置要点

Biome 与 Next.js 搭配，不依赖 TanStack Start。

**安装（在 `apps/web`）：**

```bash
pnpm add -D @biomejs/biome
pnpm biome init
```

**`biome.json` 建议：**

```json
{
  "$schema": "https://biomejs.dev/schemas/2.0.0/schema.json",
  "organizeImports": { "enabled": true },
  "linter": { "enabled": true, "rules": { "recommended": true } },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2 },
  "javascript": { "formatter": { "quoteStyle": "double", "semicolons": "asNeeded" } }
}
```

**`package.json` scripts：**

```json
{
  "scripts": {
    "lint": "biome check .",
    "format": "biome format --write ."
  }
}
```

若 `create-next-app` 默认带了 ESLint，MVP 阶段**二选一**：要么禁用 ESLint 用 Biome，要么先保留 ESLint、Biome 只 format。推荐 **Biome 统一 lint + format**，配置更少。

---

## 相关文档

- [MVP 开工包：满月](./mvp-满月短片-开工包.md) — 产品范围、按天任务
- [生活场景 AI 短片工具 — 全链路方案](./生活场景AI短片工具-全链路方案.md) — 产品战略与 6 周计划
- [和 AI 协作指南 — 全链路项目](./和AI协作指南-全链路项目.md) — 怎么和 AI 分工写代码
- [ROADMAP](../ROADMAP.md) — 阶段里程碑

---

*技术方案 v1.1 · 与开工包、全链路方案、ROADMAP Phase 3～5 保持一致；Implementation 以本文 + 开工包 Day 3～7 清单为准。*
