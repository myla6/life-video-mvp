# life-video-mvp

生活场景纪念短片生成工具。用户上传照片/视频，选模板、填信息、选音乐，一键生成约 1 分钟成片。

## 模板路线

| 阶段 | 模板 | 状态 |
|------|------|------|
| v1 | 宝宝满月纪念（60 秒） | 开发中 |
| v2 | 结婚纪念短片（60～90 秒） | 待做 |

## 技术栈

- **前端**：Next.js + TypeScript（`apps/web`）
- **API**：Next.js Route Handlers
- **数据库**：PostgreSQL + Prisma
- **队列**：Redis + BullMQ
- **合成**：Python + ffmpeg（`worker/`）
- **存储**：本地 `storage/` → 后续 OSS

## 目录结构

```text
life-video-mvp/
├── apps/web/          # Next.js 前端（pnpm create next-app）
├── worker/            # Python ffmpeg Worker
├── templates/         # 视频模板 JSON
├── assets/bgm/        # 背景音乐
├── assets/fonts/      # 中文字体（ffmpeg 字幕用）
├── storage/           # 上传素材与成片（gitignore）
└── docker-compose.yml # Postgres + Redis
```

## 快速开始

**完整步骤见 → [本地开发指南](./docs/本地开发指南.md)**（clone 后从零跑起来）

```bash
# 1. 启动数据库（需先打开 Docker Desktop）
docker compose up -d

# 2. Web
cd apps/web
cp .env.example .env    # 首次
pnpm install
pnpm db:migrate
pnpm dev                # http://localhost:3000

# 3. Worker（另开终端，合成视频）
cd worker
cp .env.example .env    # 首次
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 文档

- **[全栈学习笔记：前端转全链路](./docs/全栈学习笔记-前端转全链路.md)** — 心智模型、排查、面试叙事、和 AI 协作验收
- **[本地开发指南](./docs/本地开发指南.md)** — clone 后怎么装依赖、启数据库、跑 Web
- [MVP 开工包：满月](./docs/mvp-满月短片-开工包.md)
- [技术方案：MVP 全栈架构](./docs/技术方案-MVP全栈架构.md)
- [全链路方案](./docs/生活场景AI短片工具-全链路方案.md)
- [和 AI 协作指南](./docs/和AI协作指南-全链路项目.md)
- [ROADMAP](./ROADMAP.md)
