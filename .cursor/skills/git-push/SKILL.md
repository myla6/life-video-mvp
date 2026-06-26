---
name: git-push
description: >-
  Commits local changes and pushes to GitHub when the user says 推到仓库.
  Use when the user says 推到仓库, push to repo, or sync to GitHub for
  life-video-mvp.
---

# 推到仓库

用户说 **「推到仓库」** 时，执行完整同步流程：检查 → 提交（如有改动）→ 推送到 GitHub。

## 仓库信息

| 项 | 值 |
|----|-----|
| 远程 | `origin` → `https://github.com/myla6/life-video-mvp.git` |
| 分支 | `main`（跟踪 `origin/main`） |
| 可见性 | 私有 |

## 执行方式

1. 先看 `git status` 和 `git diff`，确认无 `.env`、密钥等敏感文件
2. 再运行脚本（路径相对于仓库根目录）：

```bash
# 有未提交改动：先写 commit message，再一条命令提交+推送
bash .cursor/skills/git-push/scripts/git-sync.sh -m "feat: 简短说明"

# 无改动：只推送
bash .cursor/skills/git-push/scripts/git-sync.sh
```

脚本会拒绝 `.env` 等敏感文件；`test-assets/`、`storage/` 已在 `.gitignore` 中。

若脚本不可用，手动等效：`git add` → `git commit -m "..."` → `git push origin main`。

## 流程

1. **安全检查**（必须先做）
   - `git status` / `git diff` 确认改动内容
   - 若出现 `.env`、密钥、token、credentials → **停止**，告知用户

2. **提交 + 推送**
   - commit message：`feat:` / `fix:` / `docs:` / `chore:` + 简短说明
   - 有改动：带 `-m` 运行脚本；无改动：不带 `-m`

3. **回报用户**
   - 是否新建了 commit（hash + message）
   - push 是否成功
   - 若失败：贴出错误；HTTPS 认证失败时提示检查 GitHub Token 或改用 SSH

## 边界情况

| 情况 | 处理 |
|------|------|
| working tree clean | 直接 `git push`，告知「无新改动，已与远程同步或已是最新」 |
| 无 `origin` remote | 停止，提示用户先配置 remote |
| push 被拒绝（remote 有新提交） | 告知用户需先 `git pull --rebase`，不要 force push |
| 用户只说「只 push」 | 只 push，不 commit |

## 禁止

- 不要 `git push --force` 到 `main`
- 不要改 git config
- 不要提交 `.env` 或含密钥的文件
- 不要 skip hooks（`--no-verify`）
