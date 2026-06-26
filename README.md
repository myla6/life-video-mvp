# life-video-mvp

生活场景纪念短片生成工具。用户上传照片/视频，选模板、填信息、选音乐，一键生成约 1 分钟成片。

## 模板路线

| 阶段 | 模板 | 状态 |
|------|------|------|
| v1 | 宝宝满月纪念（60 秒） | 开发中 |
| v2 | 结婚纪念短片（60～90 秒） | 待做 |

## 技术栈

- **前端**：Next.js + TypeScript（`apps/web`，待初始化）
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

### 1. 基础设施

```bash
docker compose up -d
```

### 2. 验证 ffmpeg（Day 2 必做）

```bash
brew install ffmpeg
# 见 docs/mvp-满月短片-开工包.md 第八节
```

### 3. Worker（本地试跑）

```bash
cd worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. 前端（待初始化）

```bash
cd apps
pnpm create next-app web --typescript --tailwind --eslint --app --src-dir=false
```

## 文档

- [MVP 开工包：满月](./docs/mvp-满月短片-开工包.md)
- [技术方案：MVP 全栈架构](./docs/技术方案-MVP全栈架构.md)
- [全链路方案](./docs/生活场景AI短片工具-全链路方案.md)
- [和 AI 协作指南](./docs/和AI协作指南-全链路项目.md)
- [ROADMAP](./ROADMAP.md)
