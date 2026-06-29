# life-video-mvp 路线图

## Phase 1 — 满月模板（当前）

**目标**：跑通上传 → 任务队列 → ffmpeg 合成 → 预览下载 全链路。

- [ ] Day 1：读开工包，访谈 1 个朋友
- [x] Day 2：本地 ffmpeg 出第一条竖屏 mp4（时长按 4.4 随素材计算）
- [x] Day 3：Next.js 上传 + 创建任务 API
- [x] Day 4：Worker 轮询 DB + render.py 合成
- [ ] Day 5～6：全链路联调打磨 + 标题卡
- [ ] Day 7：给朋友做 1 条真实满月成片

**模板**：`templates/baby_full_moon_v1.json`

---

## Phase 2 — 结婚纪念模板

**前置**：Phase 1 全链路稳定，连续 3 次生成至少 2 次成功。

**目标**：复用任务流，新增结婚场景模板。

| 维度 | 满月 | 结婚纪念（草案） |
|------|------|------------------|
| 时长 | 60 秒 | 60～90 秒 |
| 竖屏 | 720×1280（MVP） | 同左 |
| 照片 | 5～15 张 | 10～20 张 |
| 文案 | 宝宝名、日期、祝福 | 新人姓名、婚礼日期、誓言/祝福 |
| 结构 | 标题 → 轮播 → 视频 → 结尾 | 标题 → 恋爱/婚礼照轮播 → 仪式片段 → 结尾 |
| BGM | 温馨钢琴等 | 浪漫钢琴/弦乐 |

**模板草案**：`templates/wedding_v1.json`（结构已定，合成逻辑 Phase 2 实现）

---

## Phase 3 — 工程化与上线

**前置**：Phase 1 给朋友做出至少 1 条满意成片。

**目标**：从「本机三终端」迁到可访问的生产环境，并为扩展打基础。

- [ ] Redis + BullMQ 队列（替代 DB 轮询）
- [ ] OSS 存储（`storage/` → 对象存储 + 签名下载）
- [ ] ECS + Docker Compose 部署（Web + Worker + Postgres + Redis）
- [ ] Worker 镜像内置 **ffmpeg**（`apt install ffmpeg`，不依赖宿主机手动装）
- [ ] 数据盘挂载 `/data/storage` 或全 OSS
- [ ] CI/CD + 简单限流 / 错误监控

**关于服务器压力**：朋友场景量级，单机 Worker + ffmpeg 足够；并发上来后加队列 + 多 Worker 水平扩展，而不是一开始堆 Agent。

> 架构细节见 [技术方案 §13 部署](./docs/技术方案-MVP全栈架构.md#13-部署与上线第二周)、[§15 Agent 演进](./docs/技术方案-MVP全栈架构.md#15-演进agentffmpeg-部署与扩展)。

---

## Phase 4 — 多模板、体验与触达

**前置**：Phase 2 结婚模板或同类场景模板跑通。

- [ ] 标题卡 / 结尾卡完善（ffmpeg drawtext 或 PNG 叠加）
- [ ] 横屏版本
- [ ] AI 空镜（5 秒点缀，非核心，可选云 API）
- [ ] **微信小程序**（新客户端，**复用现有 Job API + Worker**，不能直接把 Next.js 变成小程序）

小程序要点（详见 [技术方案 §15.6](./docs/技术方案-MVP全栈架构.md#156-微信小程序能直接变吗api-怎么复用)）：

- 复用：`POST/GET /api/jobs`、下载、Worker、模板 JSON
- 新做：小程序 UI、`wx.uploadFile`、HTTPS 合法域名、（可选）微信登录
- 建议：Web 全链路稳定后再做，可用 Taro/uni-app 或原生

---

## Phase 5 — Agent / LLM 接入（演进，非推翻 MVP）

**核心原则**：现有 **Job 状态机 + Worker + ffmpeg** 不变；Agent 只替换或增强「用户怎么描述需求 → 生成任务参数」这一层。

**前置**：Phase 1 全链路稳定，Phase 3 至少完成 Worker 可部署（ffmpeg 在镜像里）。

### 5A — 对话生成任务参数（最小 Agent，优先）

用户自然语言 → LLM 输出结构化 JSON → 仍走 `POST /api/jobs` → Worker → ffmpeg。

- [ ] 对话 UI（或聊天式创作页）
- [ ] LLM 调用层（OpenAI / Claude / 通义等 API，不占自机 GPU）
- [ ] Prompt + JSON Schema 对齐现有 Job 字段（`babyName`、`bgmPreset`、`blessing`…）
- [ ] 人工确认后再提交（避免幻觉直接成片）

### 5B — 工具编排（Agent 调工具）

LLM 拆任务并按需调用工具，ffmpeg 只是工具链中的 **`render_video`**：

| 工具（草案） | 作用 |
|--------------|------|
| `analyze_photos` | 识别人脸/场景，建议排序 |
| `pick_bgm` | 按情绪选 BGM preset |
| `render_video` | 调现有 `render.py` / Worker |
| `generate_blessing` | 生成/润色文案 |

- [ ] 工具注册与调用协议（函数 calling / 自建 orchestrator）
- [ ] 每步结果写回 Job 或子任务表，前端可展示进度

### 5C — 动态剪辑（产品升级，后期）

超出固定 `templates/*.json`：高光检测、动态时间轴、多段 vlog。工作量和成本明显高于 5A/5B，**有真实用户反馈后再做**。

**ffmpeg 在 Agent 阶段仍保留**：LLM/视觉模型负责理解与选片，`render_video` 工具仍调 Worker + ffmpeg 出片。详见 [技术方案 §15.5](./docs/技术方案-MVP全栈架构.md#155-agent-阶段还要-ffmpeg-吗和大模型怎么分工)。

**面试叙事**：第一版模板 + ffmpeg 打通全链路；第二版在用户输入层加 LLM 理解诉求并编排工具；合成仍由异步 Worker 执行，保证可控成本与可扩展。

---

## 学习路径备忘（全栈 + Agent 同一产品）

> 详细表见 [技术方案 §15.7](./docs/技术方案-MVP全栈架构.md#157-产品与学习路径全栈--agent-叠层备忘)。

| 时间（参考） | 重点 | 产出 |
|--------------|------|------|
| 第 1 个月 | Day 5～7、朋友满月成片 | E2E 可演示、全栈面试能讲 10 分钟 |
| 第 2 个月 | 第二场景模板 + Phase 3 任选 2 项（Redis/OSS/部署） | 多模板 + 能上线 |
| 第 3 个月 | Phase 5A 对话填参数 + 可选一个工具 | 简历可写 Agent + 视频流水线 |

场景顺序：**满月 → 结婚/日常 → 旅行（后期）**。不必第一版堆齐全场景 + 小程序 + Agent。
