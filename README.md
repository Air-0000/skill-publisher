# skill-publisher

> Skill 发布流水线 — 自动完成质量检查 → 版本管理 → 文件上传 → README 更新 → GitHub push → Release 创建 → zip 上传 → CherryStudio 同步。

## 版本

**当前版本**：v1.1.0（2026-05-04）

## 核心功能

- **质量门**：发布前自动检查 frontmatter、版本格式、文件合规性
- **语义版本**：分析 git diff 自动判断 major/minor/patch，无需手动指定
- **多仓库发布**：并行/顺序发布到多个 GitHub 仓库
- **发布后验证**：pytest 或健康检查，失败自动回滚
- **自动同步**：GitHub README、仓库描述、topics 自动更新
- **完整日志**：Mermaid 工作流图 + 终端 ASCII 可视化

## 工作流

```
Step 0:   质量检查
          ↓ 有 error → 停止
Step 0.5: 版本警告（remote vs local）
Step 0.75: 语义版本自动判断
Step 1:   更新版本号 + 追加 CHANGELOG
Step 2:   读取文件清单
Step 3:   更新 GitHub README
Step 3.5: 更新仓库元数据（description + topics）
Step 4:   Git commit
Step 5:   Git tag
Step 6:   Backup zip（含 commit hash）
Step 7:   Git push
          ↓ 失败 → 打印回滚命令
Step 8:   创建 GitHub Release
Step 9:   上传 zip 作为 Asset
Step 10:  清理临时文件
Step 11:  同步到 Cherry Studio 本地
```

## 调用参数

| 参数 | 说明 | 必填 |
|------|------|------|
| `SKILL_DIR` | Skill 目录绝对路径 | ✅ |
| `SKILL_NAME` | Skill 名称（文件夹名） | ✅ |
| `REPO_URL` | GitHub 仓库地址 | ✅ |
| `REPO` | GitHub 仓库标识（owner/repo） | ✅ |
| `CHANGE_SUMMARY` | 本次改动摘要 | ✅ |
| `bump` | major / minor / patch（默认 patch） | 否 |

## 安装

**CherryStudio**：将本仓库 `skill-publisher/` 目录放入 Skills 目录

**Claude Code**：
```bash
claude skill install https://github.com/Air-0000/skill-publisher
```

## 声明依赖

在 `{SKILL_NAME}/dependencies.yaml` 中声明：

```yaml
skills:
  - name: skill-publisher
    source: local
    required: false
    purpose: Skill 更新完成后自动发布到 GitHub
```

## 相关仓库

- [skill-publisher](https://github.com/Air-0000/skill-publisher)（本仓库）：发布流水线工具

## License

MIT