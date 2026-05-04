---
name: skill-publisher
version: v1.1.0
description: |
  Skill 发布流水线 — 自动完成质量检查 → 版本管理 → 文件上传 → README 更新 → GitHub push → Release 创建 → zip 上传 → CherryStudio 同步。
  所有执行均内嵌 PDCA 循环（Plan → Do → Check → Act）。
  Use when 需要发布或更新任何已接入 GitHub 仓库的 Skill。
  触发场景：
  - "发布这个 skill"、"发布新版本"、"更新 skill"
  - "创建 Release"、"发布到 GitHub"
  - 对任何 skill 做完改动后需要同步到 GitHub
  核心功能：质量门 + 语义版本自动判断 + 多仓库发布 + 发布后验证 + 完整可视化日志。
kind: utility-skill
---

# Skill Publisher — 发布流水线 v1.1

## Identity

> *"我是发布官。我的职责是把 Skill 的每一次改动安全、完整、可追溯地推送到 GitHub，并生成完整的 Release。"*

skill-publisher 是工具型 Skill，专注执行发布流水线。每个 Skill 应声明依赖 `skill-publisher`，完成每次更新后的 GitHub 同步。

**所有执行均内嵌 PDCA 循环**，以下为 PDCA 驱动的完整执行流程。

---

# PDCA 驱动的发布流程

> Skill 发布 = Plan → Do → Check → Act，每一轮 PDCA 对应发布生命周期的不同阶段。

---

## L1: Plan — 发布规划

**目标**：明确本次发布的目标、环境和约束，确保发布条件具备。

### 调用参数确认

| 参数 | 说明 | 必填 |
|------|------|------|
| `SKILL_DIR` | Skill 目录绝对路径 | ✅ |
| `SKILL_NAME` | Skill 名称（英文，文件夹名） | ✅ |
| `REPO_URL` | GitHub 仓库地址（.git 结尾） | ✅ |
| `REPO` | GitHub 仓库标识（owner/repo） | ✅ |
| `CHANGE_SUMMARY` | 本次改动摘要 | ✅ |
| `bump` | major / minor / patch（默认 patch） | 否 |

### 环境检查

- `gh auth status`：确认 GitHub CLI 已登录
- Skill 目录存在性检查
- Git 仓库状态检查（是否为 git 仓库）

### 目标设定

- **发布目标版本**：根据 bump 参数和当前版本计算目标版本
- **发布范围**：本次涉及哪些文件（读取文件清单）
- **风险识别**：可能失败的步骤（git push 冲突、Release 已存在等）

**Plan Gate**：所有必填参数是否齐全？环境是否就绪？

---

## L1: Do — 执行发布

> 以下 12 个 Step 构成 Do 的完整执行过程。每个 Step 完成即记录。

### Step 0 — 质量检查

执行 5 项质量检查，任何 `error` 级别问题导致流程停止：

| 检查项 | 代码 | 级别 | 说明 |
|--------|------|------|------|
| frontmatter 必填字段 | QC-001 | error | 必须有 name/version/description/kind |
| version 格式 | QC-002 | error | 必须为 `vX.Y.Z` 格式 |
| 必须文件存在 | QC-003 | error | SKILL.md 必须存在 |
| 文件名合规 | QC-004 | error | 无空格、无 `..` 路径遍历 |
| CHANGELOG 格式 | QC-006 | warning | 若存在必须有 `## [Unreleased]` 或 `## vX.Y.Z` |

### Step 0.5 — 版本警告

检查 remote 最新 tag，若本地版本 ≤ remote 版本则警告（不阻止）。

### Step 0.75 — 语义版本自动判断

> AI 分析 git diff，自动判断 major/minor/patch，用户无需手动指定。

| 变更类型 | 推荐版本 |
|---------|---------|
| **MAJOR** | SKILL.md 重大变更、kind 类型变化 |
| **MINOR** | 新增章节/角色/API |
| **PATCH** | 文档修正、CHANGELOG 更新 |

用户指定 bump 时优先使用用户指定值。

### Step 1 — 更新版本号 + CHANGELOG

- 读取 SKILL.md frontmatter 的 `version` 字段
- 按 bump 参数递增，写回 `version: "v{新版本}"`
- CHANGELOG.md 存在时，在 `## [Unreleased]` 后插入新版本节

### Step 2 — 读取文件清单

遍历 Skill 目录，构建发布文件列表（排除 `.git/`、`roles/skills/`、`skills/`、`__pycache__/`、`.pytest_cache/`）。

### Step 3 — 更新 GitHub README

- **本地有 README.md**：使用本地版本推送
- **本地无，GitHub 有**：下载后追加本次版本信息
- **均无**：自动生成模板 README

### Step 3.5 — 更新 GitHub 仓库元数据

- **description**：从 SKILL.md frontmatter `description` 读取（取前 160 字符），通过 `gh repo edit --description` 更新
- **topics**：根据 Skill 类型自动打标

| Skill 类型 | topics |
|---|---|
| `team-skill` | agent-skill, claude-code, cherry-studio, multi-agent, pipeline, code-development |
| `utility-skill` | agent-skill, claude-code, cherry-studio, automation |
| 其他 | agent-skill, claude-code, cherry-studio |

### Step 4 — Git commit

`git add . && git commit -m "release: v{VERSION}\n\nCo-Authored-By: skill-publisher"`

### Step 5 — Git tag

`git tag -a v{VERSION} -m "Release v{VERSION}"`

### Step 6 — Backup zip

文件名格式：`{skill-name}_v{VERSION}_{COMMIT}_{TIMESTAMP}.zip`（排除 `.git/`、`__pycache__/`、`.pytest_cache/`）

### Step 7 — Git push

`git push origin main:main --force`，若失败打印回滚命令。

### Step 8 — 创建 GitHub Release

- **标题格式**：`v0.8.0 — 2026-05-01`（版本号 + 日期，不重复 Skill 名称）
- **只写本次版本**：每个 Release 只记录当前版本的改动，不混写历史

Release Notes 模板：

```markdown
# {VERSION} — {DATE}

## 本次改动
{CHANGE_SUMMARY}

## 本次文件
{本次新增/改动的文件列表}

## 安装方式
**CherryStudio**：将本仓库 `{SKILL_NAME}/` 目录放入 Skills 目录

**Claude Code**：`claude skill install https://github.com/{owner}/{repo}`
```

### Step 9 — 上传 zip 作为 Asset

`gh release upload v{VERSION} {ZIP_PATH} --repo {REPO}`

### Step 10 — 清理

删除临时文件和 `__pycache__`。

### Step 11 — 同步到 Cherry Studio

使用 `rsync -a --delete --exclude=.git` 同步到：
`~/Library/Application Support/CherryStudio/Data/Skills/{skill_name}/`

**Do Gate**：12 个 Step 全部执行完成？是否有 Step 失败？

---

## L1: Check — 验证发布

**目标**：对照 Plan 的目标，验证所有产出是否就绪。

### KR 完成情况

| 验证项 | 目标 | 实际 | 状态 |
|--------|------|------|------|
| GitHub Release 创建 | 存在且可访问 | ✅/❌ | |
| zip Asset 上传 | Asset 列表包含 zip | ✅/❌ | |
| Git tag 推送 | tag 出现在 GitHub | ✅/❌ | |
| README 推送 | GitHub 最新提交包含 README | ✅/❌ | |
| topics 更新 | 仓库有 topics | ✅/❌ | |
| CherryStudio 同步 | 本地文件与 GitHub 一致 | ✅/❌ | |

### 问题清单

| # | 问题 | 严重程度 | 是否阻塞 |
|---|------|---------|---------|
| ... | ... | P1/P2 | 是/否 |

**Check Gate**：所有 KR 是否逐一验证？P1 级问题是否已解决？

---

## L1: Act — 发布后决策

**目标**：根据 Check 结果做出决策，沉淀改进经验。

### 决策

| 情况 | 决策 |
|------|------|
| 全部成功 | 记录本次发布成功，输出 Release 链接 |
| 部分失败 | 回滚失败的步骤，输出回滚命令 |
| Cherry 同步失败 | 手动告知用户需同步的目录 |
| Release 已存在 | 跳过 Step 8，仅上传 zip |

### 标准化项（本次有效，下次复用）

- [经验1]：发布前必须 `gh auth status`
- [经验2]：本地已有 README.md 时直接推送，不生成
- [经验3]：zip 打包排除 `__pycache__` / `.pytest_cache` / `.DS_Store`

### 改进项（下次要改）

- [改进1]：...

### 最终复盘摘要

[一句话总结本次发布的核心收获]

---

## 并行多仓库发布（嵌套于 Do 阶段）

> 当配置了 `.skill-publisher.yml` 时，Do 阶段展开为 L2 子 PDCA：

```
L1: Do
└── L2: 多仓库发布
    ├── 子 PDCA Repo1（并行/顺序）
    ├── 子 PDCA Repo2（并行/顺序）
    └── 子 PDCA Repo3（并行/顺序）
```

配置格式：

```yaml
# .skill-publisher.yml
multi_repo:
  enabled: true
  repos:
    - owner: main-org
      repo: skill-name
      branch: main
      priority: 1
    - owner: backup-org
      repo: skill-name-mirror
      branch: main
      priority: 2
```

**L2 Do Gate**：所有子仓库 Release 均创建成功？

## 发布后自动验证（嵌套于 Check 阶段）

> Check 阶段可展开为 L2 子 PDCA：

```
L1: Check
└── L2: 发布验证
    ├── 子 PDCA 验证1（pytest / health check）
    └── 子 PDCA 验证2（回滚测试）
```

验证失败时触发 L2 Act（回滚），回滚完成后回到 L1 Check。

---

## 版本管理

| 参数 | 说明 | 示例 |
|------|------|------|
| `major` | 主版本 +1，清零 minor/patch | v0.3.0 → v1.0.0 |
| `minor` | 次版本 +1，清零 patch | v0.3.0 → v0.4.0 |
| `patch`（默认） | 补丁 +1 | v0.3.0 → v0.3.1 |

---

## 错误处理

| 错误场景 | 处理方式 |
|---|---|
| Step 0 质量检查失败 | 停在 Step 0，打印 QC 报告，终止发布 |
| GitHub auth 未配置 | 停在 Step 1 之前，告知需 `gh auth login` |
| git push 冲突 | 使用 `--force` 覆盖（Skill 发布场景以本地为准） |
| README.md 已存在 | 使用本地 README 推送 |
| Release 已存在 | 跳过 Step 8，直接上传 zip |
| CherryStudio 目录同步失败 | 打印警告，告知用户需手动同步 |

## 约束

- 不得覆盖已发布的 Release tag
- 不得删除 GitHub 仓库内容
- Step 0 质量检查失败则停止
- Release Notes 标题格式：`{VERSION} — {DATE}`
- 每个 Release 只写当前版本内容
- **L1 Do Gate 不通过则 Act 必须回滚**：Do 未全部完成时不得输出"发布成功"

## 文件结构

```
skill-publisher/
├── SKILL.md              # 本文件（v1.1：PDCA 驱动）
├── CHANGELOG.md         # 历史版本沉淀
├── README.md            # 发布用精简说明
├── requirements.txt
└── scripts/
    ├── publisher.py       # 主入口，PDCA 串联
    ├── quality_checker.py # Step 0 质量检查
    ├── version.py         # 版本比较/远程 tag 获取
    ├── git_utils.py       # Git 操作/回滚命令生成
    └── test_publisher.py  # 测试用例
```