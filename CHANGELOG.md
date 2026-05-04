## [Unreleased]

## v1.0.0 — 2026-05-04

### 清理重构
- **三文件职责明确化**：SKILL.md 只含最新版本内容，CHANGELOG.md 沉淀历史版本，README.md 为发布用精简说明
- **SKILL.md 主标题对齐**：对齐 frontmatter version 至 v1.0
- **CHANGELOG.md 清理**：移除顶部垃圾条目，补全 GitHub Release 中的所有历史版本，达到版本号连续（v0.1.0 → v0.10.12）
- **README.md 新建**：发布用精简 README，替代原来的内嵌 SKILL.md 大段代码示例

---

## v0.10.12 — 2026-05-02

README 版本号更新为 v0.10.11（CHANGELOG 已修正）

---

## v0.10.11 — 2026-05-02

修复 CHANGELOG 混乱格式 + 本地 README 同步到 GitHub（Step 3 终于生效）

---

## v0.10.10 — 2026-05-02

修复 Step 3 README 更新逻辑（`--field` 改为 `-f` 参数 + 添加 SHA）

---

## v0.10.9 — 2026-05-02

修复 Step 编号（实际执行顺序对齐 SKILL.md 描述）+ 新增 Step 3 README 自动更新 + Step 3.5 元数据同步

---

## v0.10.8 — 2026-05-02

（v0.10.5 修复内容的同次提交）

---

## v0.10.7 — 2026-05-02

（v0.10.5 修复内容的同次提交）

---

## v0.10.5 — 2026-05-02

修复 Step 7 判断逻辑（先检查 Release 是否存在再决定创建或上传）+ Release 失败时整体流程失败（不再静默跳过）

---

## v0.10.4 — 2026-05-02

修复 Release 创建：检查 Release 是否已存在 + 跳过重复创建

---

## v0.10.3 — 2026-05-02

修复 Release 创建（忽略 tag 已存在错误）+ 修复 gh 命令 flag

---

## v0.10.2 — 2026-05-02

修复 Release 创建（忽略 tag 已存在错误）+ 修复 gh 命令 flag

---

## v0.10.1 — 2026-05-02

实现 Step 7 GitHub Release 创建 + Step 8 zip Asset 上传

---

## v0.9.0 — 2026-05-02

### 新增
- **Step 0.75 语义版本自动判断**：分析 git diff 自动判定 major/minor/patch，用户无需手动指定 bump
- **自动判断规则**：SKILL.md 重大变更为 MAJOR、新增章节/角色为 MINOR、文档修正/小调整为 PATCH
- **语义版本分析报告**：输出变更文件统计、变更类型分析、判定结果和判定依据

### 变更
- 流程从 11 步扩展为 12 步（新增 Step 0.75）
- 约束新增"语义版本优先：用户未指定 bump 时，以自动判断结果为准"

---

## v0.8.0 — 2026-05-02

### 新增

#### 发布工作流可视化
- **PublishWorkflowVisualizer 类**：将发布结果渲染为可视化工作流图
- **Mermaid 工作流图**：在支持 Markdown 的地方直接渲染 pipeline 流程
- **终端 ASCII 可视化**：在终端中渲染可读的工作流状态（✅⏳❌⚠️⏭️）
- **失败分析 API**：`analyze_failure()` 定位失败步骤、分析原因、生成修复建议
- **发布历史可视化**：版本时间线、发布频率、质量趋势图表

### 变更
- SKILL.md frontmatter：version v0.7.0 → v0.8.0
- SKILL.md 主标题保持 v0.7（内容更新为 v0.8 新增）

---

## v0.7.0 — 2026-05-02

### 新增

#### 并行多仓库发布
- **多仓库配置**：`.skill-publisher.yml` 中配置 `multi_repo.repos` 列表，支持 priority 优先级
- **并行发布**：`MultiRepoPublisher.publish_all()` 同时发布到多个仓库
- **顺序发布**：`MultiRepoPublisher.publish_sequential()` 一个成功后发布下一个
- **错误处理**：主仓库失败停止，镜像仓库失败继续，返回汇总结果 + 回滚命令

#### 发布后自动验证
- **验证配置**：`.skill-publisher.yml` 中配置 `post_publish.verify`
- **验证类型**：`test`（pytest）/ `health_check`（URL）/ `manual`
- **自动回滚**：验证失败时自动回滚到上一版本
- **验证 API**：`PublishVerifier.verify()` 跑测试或健康检查，`PublishVerifier.rollback()` 回滚

### 变更
- SKILL.md frontmatter：version v0.6.0 → v0.7.0
- SKILL.md 主标题更新为 v0.7

---

## v0.6.0 — 2026-05-02

### 新增
- **语义版本自动判断（Step 0.75 新增）**：AI 分析 git diff，自动判断应该 major/minor/patch，用户不再需要手动指定 bump 参数
- **自动判断规则**：SKILL.md 重大变更为 MAJOR、新增章节/角色/工具为 MINOR、文档修正/小调整为 PATCH
- **语义版本分析报告**：输出变更文件统计、变更类型分析、判定结果和判定依据
- **版本推荐示例**：输出格式包含当前版本、变更级别、推荐版本、判定依据

### 变更
- SKILL.md version v0.5.0 → v0.6.0
- SKILL.md description 新增"v0.6 新增：语义版本自动判断"说明
- SKILL.md 主标题更新为 v0.6
- 流程从 11 步扩展为 12 步（新增 Step 0.75）
- 输出格式新增 Step 0.75 状态显示
- 约束新增"语义版本优先：用户未指定 bump 时，Step 0.75 的自动判断结果作为默认版本"

---

## v0.5.1 — 2026-05-01

### 新增
- **Step 3.5：GitHub 仓库元数据自动更新**：description（取 SKILL.md frontmatter 前 160 字符）和 topics（根据 kind 类型自动打标），确保仓库主页与 Skill 最新功能一致

---

## v0.5.0 — 2026-05-01

### 新增
- **README 自动同步更新**（Step 3）：每次发布时根据当前发布的文件内容更新 GitHub README.md，本地存在则用本地版本，GitHub 有则追加，无则生成
- **Release Notes 标题去重规范**：明确禁止在标题中重复 Skill 名称，格式固定为 `{VERSION} — {DATE}`
- **版本格式统一**：明确版本号格式为 `v0.8.0`（无前缀词），日期格式为 `2026-05-01`

---

## v0.4.0 — 2026-05-01

### 新增
- **`scripts/publisher.py`**：主入口脚本，串联所有发布步骤
- **`scripts/quality_checker.py`**：质量检查模块（5项检查）
- **`scripts/version.py`**：版本管理模块（parse/compare/bump）
- **`scripts/git_utils.py`**：Git 操作封装
- **`scripts/test_publisher.py`**：33 个单元测试用例
- **Step 0 新增质量检查**：frontmatter 校验、必须文件、文件名合规
- **Step 0.5 新增版本警告**：remote vs local 版本对比

---

## v0.3.0 — 2026-05-01

### 新增
- **Step 9：同步到 CherryStudio 本地**：使用 rsync 将发布文件同步到 `~/Library/Application Support/CherryStudio/Data/Skills/{SKILL_NAME}/`，确保本地 Skill 与 GitHub 版本一致

---

## v0.2.0 — 2026-04-30

### 新增
- **README 自动生成**（Step 3）：若 Skill 目录下无 README.md，自动从 SKILL.md 内容生成
- **CHANGELOG 可选更新**（Step 4）：仅当文件存在时才执行
- **单版本 Release 内容**（Step 7）：每个 Release 只写当前版本内容，不混写历史
- **完整文件上传**：收集全量文件（roles/、knowledge/ 等子目录）

---

## v0.1.0 — 2026-04-30

### 新增
- 初始版本：版本号递增 + CHANGELOG.md 更新 + git push + GitHub Release 创建 + zip 备份上传