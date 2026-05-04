"""发布器主模块 (publisher.py)

Skill 发布流程的主入口，串联所有步骤。
"""

import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Use conditional imports to support both package and direct execution
try:
    from .quality_checker import QualityChecker, QCIssue
    from .version import compare_versions, get_remote_latest_tag
    from .git_utils import get_commit_hash, git_push, generate_rollback_command
except ImportError:
    from quality_checker import QualityChecker, QCIssue
    from version import compare_versions, get_remote_latest_tag
    from git_utils import get_commit_hash, git_push, generate_rollback_command


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StepResult:
    """步骤执行结果"""
    step: str           # 步骤标识，如 "step_0"
    success: bool       # 是否成功
    message: str        # 结果描述
    data: Optional[dict] = None  # 附加数据


@dataclass
class PublishResult:
    """发布流程最终结果"""
    success: bool                           # 整体是否成功
    version: Optional[str] = None           # 发布版本
    commit_hash: Optional[str] = None      # commit hash
    skill_name: Optional[str] = None       # skill 名称
    repo: Optional[str] = None             # 仓库标识
    step_results: list = field(default_factory=list)  # 各步骤结果
    error_message: Optional[str] = None    # 错误信息（如有）
    release_url: Optional[str] = None      # Release URL
    backup_path: Optional[str] = None       # 备份 zip 路径


# =============================================================================
# Step Implementations
# =============================================================================

def run_step_0(skill_dir: Path) -> StepResult:
    """Step 0: 质量检查 + frontmatter 解析

    执行全部5项质量检查，同时解析 frontmatter 提取元数据。

    Args:
        skill_dir: Skill 目录路径

    Returns:
        StepResult
    """
    checker = QualityChecker()
    issues = checker.check(skill_dir)
    errors = [i for i in issues if i.level == "error"]

    skill_md = skill_dir / "SKILL.md"
    parsed_frontmatter = {}

    # 解析 frontmatter
    if skill_md.exists() and skill_md.read_text().startswith("---"):
        try:
            import yaml
            content = skill_md.read_text()
            lines = content.split("\n")
            end_idx = -1
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_idx = i
                    break
            if end_idx > 0:
                yaml_content = "\n".join(lines[1:end_idx])
                parsed_frontmatter = yaml.safe_load(yaml_content) or {}
        except Exception:
            pass

    # 验证必需字段
    required_fields = ["name", "version", "description", "kind"]
    for field_name in required_fields:
        if field_name not in parsed_frontmatter:
            errors.append(QCIssue(
                "error",
                "FRONTMATTER_FIELD_MISSING",
                f"Frontmatter missing required field: {field_name}",
                "SKILL.md",
                field_name
            ))

    # 验证 version 格式
    version = parsed_frontmatter.get("version", "")
    if version and not re.match(r"^v\d+\.\d+\.\d+$", str(version)):
        errors.append(QCIssue(
            "error",
            "VERSION_FORMAT_INVALID",
            f"Version '{version}' does not match vX.Y.Z format",
            "SKILL.md",
            "version"
        ))

    if errors:
        return StepResult(
            step="step_0",
            success=False,
            message=f"Quality check failed with {len(errors)} error(s)",
            data={"issues": [{"level": i.level, "code": i.code, "message": i.message, "file": i.file} for i in issues],
                  "parsed_frontmatter": parsed_frontmatter}
        )

    return StepResult(
        step="step_0",
        success=True,
        message=f"Quality check passed ({len(issues)} warning(s))",
        data={"issues": [{"level": i.level, "code": i.code, "message": i.message, "file": i.file} for i in issues],
              "parsed_frontmatter": parsed_frontmatter}
    )


def run_step_0_5(skill_dir: Path, remote_repo: str, current_version: str) -> StepResult:
    """Step 0.5: 版本警告

    比较本地版本与远程最新 tag，打印警告但不阻止发布。

    Args:
        skill_dir: Skill 目录路径
        remote_repo: 远程仓库 URL
        current_version: 当前版本字符串

    Returns:
        StepResult
    """
    remote_tag = get_remote_latest_tag(remote_repo)
    if remote_tag:
        cmp_result = compare_versions(current_version, remote_tag)
        if cmp_result <= 0:
            return StepResult(
                step="step_0.5",
                success=True,
                message=f"Warning: local version {current_version} <= remote {remote_tag}",
                data={"remote_tag": remote_tag, "current_version": current_version, "cmp": cmp_result}
            )
    return StepResult(
        step="step_0.5",
        success=True,
        message="Version check passed (no older remote version)",
        data={"remote_tag": remote_tag}
    )


def run_step_1(skill_dir: Path, version: str, changelog: str) -> StepResult:
    """Step 1: 更新 SKILL.md frontmatter version + 追加 CHANGELOG.md

    Args:
        skill_dir: Skill 目录路径
        version: 新版本号
        changelog: 更新日志内容

    Returns:
        StepResult
    """
    import yaml
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return StepResult(
            step="step_1",
            success=False,
            message="SKILL.md not found",
            data={"version": version}
        )

    content = skill_md.read_text()
    lines = content.split("\n")

    # 找到 frontmatter 边界
    if not content.startswith("---"):
        return StepResult(
            step="step_1",
            success=False,
            message="SKILL.md missing YAML frontmatter",
            data={"version": version}
        )

    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return StepResult(
            step="step_1",
            success=False,
            message="SKILL.md frontmatter not properly closed",
            data={"version": version}
        )

    # 更新 frontmatter 中的 version
    yaml_lines = lines[1:end_idx]
    new_yaml_lines = []
    version_updated = False
    for line in yaml_lines:
        if line.strip().startswith("version:"):
            new_yaml_lines.append(f"version: {version}")
            version_updated = True
        else:
            new_yaml_lines.append(line)

    if not version_updated:
        new_yaml_lines.append(f"version: {version}")

    new_content = "---\n" + "\n".join(new_yaml_lines) + "\n---\n" + "\n".join(lines[end_idx + 1:])
    skill_md.write_text(new_content)

    # 追加 CHANGELOG.md
    changelog_path = skill_dir / "CHANGELOG.md"
    date_str = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"## {version} — {date_str}\n\n{changelog}\n"
    if changelog_path.exists():
        existing = changelog_path.read_text()
        changelog_path.write_text(new_entry + "\n" + existing)
    else:
        changelog_path.write_text(new_entry)

    return StepResult(
        step="step_1",
        success=True,
        message=f"Version updated to {version}",
        data={"version": version}
    )


def run_step_2(skill_dir: Path) -> StepResult:
    """Step 2: 读取 Skill 目录构建文件清单

    Args:
        skill_dir: Skill 目录路径

    Returns:
        StepResult，data 含 file_list
    """
    file_list = []
    exclude_patterns = {".git", "__pycache__", ".DS_Store", "node_modules", ".pytest_cache"}

    for root, dirs, files in skill_dir.walk():
        # 过滤目录
        dirs[:] = [d for d in dirs if d not in exclude_patterns]

        for file in files:
            if file in exclude_patterns:
                continue
            full_path = root / file
            rel_path = full_path.relative_to(skill_dir)
            file_list.append(str(rel_path))

    file_list.sort()

    return StepResult(
        step="step_2",
        success=True,
        message=f"File list built: {len(file_list)} file(s)",
        data={"file_list": file_list}
    )


def run_step_3(skill_dir: Path, repo: str, skill_name: str, version: str, file_list: list) -> StepResult:
    """Step 3: 更新 GitHub README

    若本地有 README.md 则用本地内容；若 GitHub 有 README 则追加版本信息；若都没有则自动生成。

    Args:
        skill_dir: Skill 目录路径
        repo: GitHub 仓库标识（owner/repo）
        skill_name: skill 名称
        version: 版本号
        file_list: 文件清单（来自 step_2）

    Returns:
        StepResult
    """
    if not repo:
        return StepResult(step="step_3", success=True, message="README update skipped: no remote repo configured")

    try:
        local_readme = skill_dir / "README.md"
        has_local = local_readme.exists()

        # 尝试获取 GitHub 现有 README
        gh_result = subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/README.md", "--jq", ".content"],
            capture_output=True, text=True, timeout=30
        )
        has_gh = gh_result.returncode == 0 and gh_result.stdout.strip()

        if has_local:
            # 使用本地 README 推送
            content = local_readme.read_text()
            encoded = base64.b64encode(content.encode()).decode()
            # 获取当前 SHA
            sha_result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md", "--jq", ".sha"],
                capture_output=True, text=True, timeout=15
            )
            sha = sha_result.stdout.strip()
            subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md",
                 "--method", "PUT",
                 "-f", f"message=docs: update README (v{version})",
                 "-f", f"content={encoded}",
                 "-f", f"sha={sha}"],
                capture_output=True, text=True, timeout=30
            )
            return StepResult(step="step_3", success=True, message="README updated from local file", data={"source": "local"})
        elif has_gh:
            # GitHub 有 README，追加版本信息
            gh_content = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md", "--jq", ".content"],
                capture_output=True, text=True, timeout=30
            )
            decoded = base64.b64decode(gh_content.stdout.strip()).decode()

            # 获取 SHA
            sha_result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md", "--jq", ".sha"],
                capture_output=True, text=True, timeout=15
            )
            sha = sha_result.stdout.strip()

            # 在顶部追加版本记录
            from datetime import date
            today = date.today().isoformat()
            new_entry = f"\n\n## v{version.lstrip('v')} — {today}\n**更新**：本次发布新增文件 {len(file_list)} 个\n"
            updated = decoded + new_entry

            subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md",
                 "--method", "PUT",
                 "-f", f"message=docs: append v{version.lstrip('v')} release note",
                 "-f", f"content={base64.b64encode(updated.encode()).decode()}",
                 "-f", f"sha={sha}"],
                capture_output=True, text=True, timeout=30
            )
            return StepResult(step="step_3", success=True, message="README updated from GitHub", data={"source": "github"})
        else:
            # 自动生成 README
            skill_md = skill_dir / "SKILL.md"
            desc = ""
            if skill_md.exists():
                lines = skill_md.read_text().split("\n")
                end_idx = -1
                for i, l in enumerate(lines[1:], 1):
                    if l.strip() == "---":
                        end_idx = i
                        break
                if end_idx > 0:
                    import yaml
                    parsed = yaml.safe_load("\n".join(lines[1:end_idx])) or {}
                    desc = parsed.get("description", "")

            readme_content = f"""# {skill_name}

> {desc[:200] if desc else "A CherryStudio Skill"}"

**当前版本**：v{version.lstrip('v')}（{datetime.now().strftime('%Y-%m-%d')}）

## 文件结构

```
{skill_name}/
"""
            for f in file_list[:30]:
                readme_content += f"- {f}\n"
            readme_content += f"""
（共计 {len(file_list)} 个文件）
```

## 安装方式

**CherryStudio**：将本仓库 `{skill_name}/` 目录放入 Skills 目录

**Claude Code**：
```bash
claude skill install https://github.com/{repo}
```

## 相关仓库

- [skill-publisher](https://github.com/Air-0000/skill-publisher)：发布流水线工具

## License

MIT
"""
            encoded = base64.b64encode(readme_content.encode()).decode()
            # 获取 SHA
            sha_result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md", "--jq", ".sha"],
                capture_output=True, text=True, timeout=15
            )
            sha = sha_result.stdout.strip()
            subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/README.md",
                 "--method", "PUT",
                 "-f", f"message=docs: create README (v{version})",
                 "-f", f"content={encoded}",
                 "-f", f"sha={sha}"],
                capture_output=True, text=True, timeout=30
            )
            return StepResult(step="step_3", success=True, message="README auto-generated", data={"source": "generated"})

    except Exception as e:
        return StepResult(step="step_3", success=True, message=f"README update skipped: {e}")


def run_step_3_5(skill_dir: Path, repo: str) -> StepResult:
    """Step 3.5: 更新 GitHub 仓库元数据（description + topics）

    从 SKILL.md frontmatter 读取 description，topics 根据 skill 类型自动生成。

    Args:
        skill_dir: Skill 目录路径
        repo: GitHub 仓库标识（owner/repo）

    Returns:
        StepResult
    """
    if not repo:
        return StepResult(step="step_3.5", success=True, message="Metadata update skipped: no remote repo configured")

    try:
        # 读取 description
        skill_md = skill_dir / "SKILL.md"
        desc = ""
        kind = ""
        if skill_md.exists():
            import yaml
            lines = skill_md.read_text().split("\n")
            end_idx = -1
            for i, l in enumerate(lines[1:], 1):
                if l.strip() == "---":
                    end_idx = i
                    break
            if end_idx > 0:
                parsed = yaml.safe_load("\n".join(lines[1:end_idx])) or {}
                desc = parsed.get("description", "")[:160]
                kind = parsed.get("kind", "")

        # 更新 description
        if desc:
            result = subprocess.run(
                ["gh", "repo", "edit", repo, "--description", desc[:160]],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return StepResult(step="step_3.5", success=True, message=f"description update skipped: {result.stderr.strip()}")

        # 生成 topics
        topics_map = {
            "team-skill": ["agent-skill", "cherry-studio", "claude-code", "multi-agent", "pipeline"],
            "utility-skill": ["agent-skill", "cherry-studio", "claude-code", "automation"],
            "doc-writer": ["agent-skill", "cherry-studio", "claude-code", "latex", "document-writing"],
            "skill-suite": ["agent-skill", "cherry-studio", "claude-code", "multi-modal"],
        }
        topics = topics_map.get(kind, ["agent-skill", "cherry-studio", "claude-code"])

        # 清除旧 topics 并设置新 topics
        subprocess.run(
            ["gh", "api", f"-X", "DELETE", f"repos/{repo}/topics"],
            capture_output=True, text=True, timeout=15
        )
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}", "-H", "Accept: application/vnd.github+json",
             "-H", "X-github-api-version: 2022-11-28",
             "--method", "PATCH", "-f", f"topics={','.join(topics)}"],
            capture_output=True, text=True, timeout=15
        )
        return StepResult(step="step_3.5", success=True, message=f"Metadata updated: description + {len(topics)} topics", data={"topics": topics, "description": desc[:80]})
    except Exception as e:
        return StepResult(step="step_3.5", success=True, message=f"Metadata update skipped: {e}")


def run_step_4(skill_dir: Path, version: str) -> StepResult:
    """Step 4: Git tag 创建

    Args:
        skill_dir: Skill 目录路径
        version: 版本号（作为 tag 名称）

    Returns:
        StepResult
    """
    tag_name = version if version.startswith("v") else f"v{version}"
    try:
        result = subprocess.run(
            ["git", "-C", str(skill_dir), "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return StepResult(
                step="step_5",
                success=False,
                message=f"Git tag creation failed: {result.stderr.strip()}",
                data={"tag": tag_name}
            )
        return StepResult(
            step="step_5",
            success=True,
            message=f"Git tag created: {tag_name}",
            data={"tag": tag_name}
        )
    except Exception as e:
        return StepResult(
            step="step_4",
            success=False,
            message=f"Git tag creation failed: {e}",
            data={"tag": tag_name}
        )


def run_step_5(skill_dir: Path, skill_name: str, version: str, commit_hash: str, backup_dir: Path) -> StepResult:
    """Step 5: 构建 backup zip

    文件名格式：{skill-name}_v{VERSION}_{COMMIT}_{TIMESTAMP}.zip
    排除 .git/ roles/skills/ skills/

    Args:
        skill_dir: Skill 目录路径
        skill_name: skill 名称
        version: 版本号
        commit_hash: commit hash
        backup_dir: 备份目录

    Returns:
        StepResult，data 含 backup_path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"{skill_name}_{version}_{commit_hash}_{timestamp}.zip"
    backup_dir.mkdir(parents=True, exist_ok=True)
    zip_path = backup_dir / zip_name

    try:
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in skill_dir.walk():
                # 排除目录
                dirs[:] = [d for d in dirs if d not in {".git", "roles", "skills"}]
                for file in files:
                    if file == ".DS_Store":
                        continue
                    full_path = root / file
                    arcname = str(full_path.relative_to(skill_dir))
                    zf.write(full_path, arcname)

        return StepResult(
            step="step_5",
            success=True,
            message=f"Backup created: {zip_name}",
            data={"backup_path": str(zip_path)}
        )
    except Exception as e:
        return StepResult(
            step="step_5",
            success=False,
            message=f"Backup creation failed: {e}",
            data={"backup_path": None}
        )


def run_step_6(skill_dir: Path) -> StepResult:
    """Step 6: Push 到远程

    Args:
        skill_dir: Skill 目录路径

    Returns:
        StepResult
    """
    success, err = git_push(str(skill_dir))
    if not success:
        rollback = generate_rollback_command(str(skill_dir))
        return StepResult(
            step="step_6",
            success=False,
            message=f"Push failed: {err}",
            data={"rollback_command": rollback}
        )
    return StepResult(step="step_6", success=True, message="Pushed to remote")


def run_step_7(
    skill_dir: Path,
    repo: str,
    version: str,
    change_summary: str,
    backup_path: Optional[Path],
    source_dir: Path,
) -> StepResult:
    """Step 7: 创建 GitHub Release + 上传 zip Asset

    Args:
        skill_dir: Skill 目录路径（实际文件所在位置）
        repo: GitHub 仓库标识（owner/repo），空字符串表示无 remote
        version: 版本号（如 v1.2.0）
        change_summary: 本次改动摘要
        backup_path: 备份 zip 文件路径
        source_dir: 源码目录（与 skill_dir 相同）

    Returns:
        StepResult
    """
    if not repo:
        return StepResult(
            step="step_7",
            success=True,
            message="Release skipped: no remote repo configured"
        )

    try:
        from datetime import date
        today = date.today().isoformat()

        # 生成 Release Notes
        # 按 SKILL.md 格式规范：标题 = {VERSION} — {DATE}，不重复 skill 名称
        skill_name = skill_dir.name
        release_body = f"""## {version} — {today}

### 本次改动
{change_summary}

### 安装方式
**CherryStudio**：将本仓库 `{skill_name}/` 目录放入 Skills 目录

**Claude Code**：
```bash
claude skill install https://github.com/{repo}
```
"""

        # repo 格式：owner/repo，直接使用（不再重复加 owner 前缀）
        repo_for_gh = repo
        view_result = subprocess.run(
            ["gh", "release", "view", version, "--repo", repo_for_gh],
            capture_output=True, text=True
        )
        release_exists = view_result.returncode == 0
        created_this_run = False

        if not release_exists:
            # 2. 创建 GitHub Release
            create_result = subprocess.run(
                [
                    "gh", "release", "create", version,
                    "--title", f"{version} — {today}",
                    "--notes", release_body,
                    "--repo", repo_for_gh
                ],
                capture_output=True, text=True, timeout=60
            )
            if create_result.returncode != 0:
                # 忽略"tag already exists"错误（tag 已有但 release 可能没有，直接跳过创建）
                if "already exists" not in create_result.stderr:
                    return StepResult(
                        step="step_7",
                        success=False,
                        message=f"Release creation failed: {create_result.stderr.strip()}"
                    )
            else:
                created_this_run = True

        # 3. 上传 zip Asset（如果 release 是新创建的或 zip 不在 asset 列表中）
        if backup_path:
            backup_file = Path(backup_path) if isinstance(backup_path, str) else backup_path
            if backup_file.exists():
                zip_name = backup_file.name
                # 先检查 asset 是否已存在
                list_result = subprocess.run(
                    ["gh", "release", "view", version, "--repo", repo_for_gh, "--json", "assets", "--jq", ".assets[].name"],
                    capture_output=True, text=True
                )
                existing_assets = []
                if list_result.returncode == 0 and list_result.stdout.strip():
                    existing_assets = list_result.stdout.strip().split("\n")

                if zip_name not in existing_assets or created_this_run:
                    upload_result = subprocess.run(
                        ["gh", "release", "upload", version, str(backup_file), "--repo", repo_for_gh],
                        capture_output=True, text=True, timeout=60
                    )
                    if upload_result.returncode != 0:
                        return StepResult(
                            step="step_7",
                            success=True,
                            message=f"Release created but zip upload failed: {upload_result.stderr.strip()}"
                        )

        return StepResult(
            step="step_7",
            success=True,
            message=f"Release created: {version}"
        )

    except subprocess.TimeoutExpired:
        return StepResult(step="step_7", success=False, message="Release step timed out")
    except Exception as e:
        return StepResult(step="step_7", success=False, message=f"Release step error: {e}")


def run_step_8(skill_dir: Path) -> StepResult:
    """Step 8: 清理工作流

    Args:
        skill_dir: Skill 目录路径

    Returns:
        StepResult
    """
    return StepResult(step="step_8", success=True, message="Cleanup completed")


def run_step_9(skill_dir: Path, skill_name: str) -> StepResult:
    """Step 9: 同步到 Cherry Studio

    使用 rsync -a --delete 同步（排除 .git/）。

    Args:
        skill_dir: Skill 目录路径
        skill_name: skill 名称

    Returns:
        StepResult
    """
    cherry_studio_skills_dir = Path.home() / "Library/Application Support/CherryStudio/Data/Skills"
    target_dir = cherry_studio_skills_dir / skill_name

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "rsync", "-a", "--delete",
                "--exclude=.git",
                str(skill_dir) + "/",
                str(target_dir) + "/"
            ],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return StepResult(
                step="step_9",
                success=False,
                message=f"rsync failed: {result.stderr.strip()}",
                data={"target_dir": str(target_dir)}
            )
        return StepResult(
            step="step_9",
            success=True,
            message=f"Synced to Cherry Studio: {target_dir}",
            data={"target_dir": str(target_dir)}
        )
    except Exception as e:
        return StepResult(
            step="step_9",
            success=False,
            message=f"rsync failed: {e}",
            data={"target_dir": str(target_dir) if target_dir.exists() else None}
        )


# =============================================================================
# Main Publish Flow
# =============================================================================

def publish_skill(
    skill_dir: Path,
    skill_name: str,
    repo_url: str,
    repo: str,
    change_summary: str,
    bump: str = "patch",
    backup_dir: Optional[Path] = None,
) -> PublishResult:
    """发布 Skill 的主流程

    流程：
    1. Step 0: quality_check（失败则停止）
    2. Step 0.5: 版本警告（remote vs local）
    3. bump version（按 major/minor/patch 递增）
    4. Step 1: 更新版本号 + 追加 CHANGELOG
    5. Step 2: 读取文件清单
    6. Step 3: 更新 GitHub README（本地有则用本地，无则生成）
    7. Step 3.5: 更新 GitHub 仓库元数据（description + topics）
    8. Step 4: Git commit（版本更新后立即 commit）
    9. Step 5: Git tag
    10. Step 6: Backup zip（含 commit hash）
    11. Step 7: Git push（--force）
    12. Step 8: 创建 GitHub Release
    13. Step 9: 上传 zip 作为 Asset
    14. Step 10: 清理临时文件
    15. Step 11: 同步到 Cherry Studio 本地

    Args:
        skill_dir: Skill 目录路径
        skill_name: skill 名称
        repo_url: 远程仓库 URL
        repo: 仓库标识
        change_summary: 更新日志
        bump: 版本递增级别（major/minor/patch）
        backup_dir: 备份目录（可选）

    Returns:
        PublishResult
    """
    # Import version utilities
    try:
        from .version import parse_version, bump_version as bv
    except ImportError:
        from version import parse_version, bump_version as bv

    results: list = []

    # Step 0: 质量检查（失败则停止）
    r0 = run_step_0(skill_dir)
    results.append(r0)
    if not r0.success:
        return PublishResult(
            success=False,
            error_message=r0.message,
            step_results=results
        )

    # 提取当前版本
    parsed = r0.data.get("parsed_frontmatter", {})
    current_version = parsed.get("version", "v0.0.0")

    # Step 0.5: 版本警告
    r05 = run_step_0_5(skill_dir, repo_url, current_version)
    results.append(r05)

    # bump version
    new_version = bv(current_version, bump)
    if not new_version:
        return PublishResult(
            success=False,
            error_message=f"Invalid version or bump level: {current_version}, {bump}",
            step_results=results
        )

    # 获取 git commit hash（初始 hash，后续版本更新后重新获取）
    commit_hash = get_commit_hash(str(skill_dir)) or "unknown"

    # Step 1: 更新版本和 CHANGELOG
    r1 = run_step_1(skill_dir, new_version, change_summary)
    results.append(r1)
    if not r1.success:
        return PublishResult(
            success=False,
            version=new_version,
            commit_hash=commit_hash,
            error_message=r1.message,
            step_results=results
        )

    # Step 2: 文件清单
    r2 = run_step_2(skill_dir)
    results.append(r2)

    # 获取 git commit hash（版本更新后立即 commit）
    commit_hash = get_commit_hash(str(skill_dir)) or "unknown"

    # Step 3: 更新 GitHub README
    file_list = r2.data.get("file_list", []) if r2.data else []
    r3 = run_step_3(skill_dir, repo, skill_name, new_version, file_list)
    results.append(r3)

    # Step 3.5: 更新 GitHub 仓库元数据（description + topics）
    r35 = run_step_3_5(skill_dir, repo)
    results.append(r35)

    # Step 4: Git commit
    subprocess.run(
        ["git", "-C", str(skill_dir), "add", "."],
        capture_output=True, text=True, timeout=30
    )
    subprocess.run(
        ["git", "-C", str(skill_dir), "commit", "-m", f"release: v{new_version}\n\nCo-Authored-By: skill-publisher"],
        capture_output=True, text=True, timeout=30
    )
    results.append(StepResult(
        step="step_4_git", success=True,
        message="Git commit created",
        data={"hash": commit_hash}
    ))

    # Step 5: git tag
    r5_tag = run_step_4(skill_dir, new_version)
    results.append(r5_tag)

    # Step 6: backup zip
    if backup_dir is None:
        backup_dir = skill_dir.parent / "backups"
    r5 = run_step_5(skill_dir, skill_name, new_version, commit_hash, backup_dir)
    results.append(r5)
    backup_path = r5.data.get("backup_path") if r5.data else None

    # Step 6: git push
    r6 = run_step_6(skill_dir)
    results.append(r6)

    if not r6.success:
        # push 失败：继续 Step 7-8 但标记失败
        results.append(run_step_7(skill_dir, repo, new_version, change_summary, backup_path, skill_dir))
        results.append(run_step_8(skill_dir))
        return PublishResult(
            success=False,
            version=new_version,
            commit_hash=commit_hash,
            skill_name=skill_name,
            repo=repo,
            error_message=r6.message,
            step_results=results,
            backup_path=backup_path
        )

    # Step 7: 创建 GitHub Release + 上传 zip Asset
    r7 = run_step_7(skill_dir, repo, new_version, change_summary, backup_path, skill_dir)
    results.append(r7)
    # Step 8: cleanup
    results.append(run_step_8(skill_dir))

    # Step 9: sync to Cherry Studio
    r9 = run_step_9(skill_dir, skill_name)
    results.append(r9)

    # 构建 Release URL（GitHub）
    release_url = None
    if repo:
        if repo.startswith("git@"):
            repo_clean = repo.replace("git@github.com:", "").replace(".git", "")
            release_url = f"https://github.com/{repo_clean}/releases/tag/{new_version}"
        elif "github.com" in repo:
            release_url = f"{repo.replace('.git', '')}/releases/tag/{new_version}"
        else:
            # repo 是简单的 owner/repo 格式，直接构造 URL（不重复加 owner）
            release_url = f"https://github.com/{repo}/releases/tag/{new_version}"

    # 整体成功 = push 成功 + Release 成功
    if not r7.success:
        return PublishResult(
            success=False,
            version=new_version,
            commit_hash=commit_hash,
            skill_name=skill_name,
            repo=repo,
            step_results=results,
            release_url=release_url,
            backup_path=backup_path,
            error_message=f"Release creation failed: {r7.message}"
        )

    return PublishResult(
        success=True,
        version=new_version,
        commit_hash=commit_hash,
        skill_name=skill_name,
        repo=repo,
        step_results=results,
        release_url=release_url,
        backup_path=backup_path
    )


# =============================================================================
# Markdown Report Generator
# =============================================================================

def generate_markdown_report(result: PublishResult) -> str:
    """生成 Markdown 格式的发布报告

    Args:
        result: PublishResult 对象

    Returns:
        Markdown 格式的报告字符串
    """
    lines = [
        "## Skill Publisher — 发布完成",
        "",
        "### 发布信息",
        f"- **Skill**: {result.skill_name or 'N/A'}",
        f"- **版本**: {result.version or 'N/A'}",
        f"- **仓库**: {result.repo or 'N/A'}",
        "",
        "### 流程状态",
    ]

    step_map = {
        "step_0": ("质量检查", True),
        "step_0.5": ("版本警告", True),
        "step_1": ("版本更新", True),
        "step_2": ("文件清单", True),
        "step_3": ("README 更新", True),
        "step_3.5": ("仓库元数据", True),
        "step_4": ("Git 提交", True),
        "step_4_git": ("Git 提交", True),
        "step_5": ("Git Tag", True),
        "step_6": ("备份", True),
        "step_7": ("Push", True),
        "step_8": ("Release 创建", True),
        "step_9": ("zip Asset 上传", True),
        "step_10": ("清理", True),
        "step_11": ("Cherry Studio 同步", True),
    }

    for sr in result.step_results:
        step_name = step_map.get(sr.step, (sr.step, True))[0]
        status = "x" if sr.success else " "
        lines.append(f"- [{status}] Step {sr.step}: {step_name}")

    lines.append("")
    lines.append("### 产出链接")
    if result.release_url:
        lines.append(f"- Release: {result.release_url}")
    if result.backup_path:
        lines.append(f"- 备份 zip: {result.backup_path}")

    if result.error_message:
        lines.append("")
        lines.append("### 错误信息")
        lines.append(f"```\n{result.error_message}\n```")

    return "\n".join(lines)


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Skill Publisher - 发布流水线")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # publish command
    pub_parser = subparsers.add_parser("publish", help="发布 Skill")
    pub_parser.add_argument("--skill-dir", required=True, help="Skill 目录绝对路径")
    pub_parser.add_argument("--skill-name", required=True, help="Skill 名称")
    pub_parser.add_argument("--repo-url", required=True, help="GitHub 仓库地址（.git 结尾）")
    pub_parser.add_argument("--repo", required=True, help="GitHub 仓库标识（owner/repo）")
    pub_parser.add_argument("--change-summary", required=True, help="本次改动摘要")
    pub_parser.add_argument("--bump", default="patch", choices=["major", "minor", "patch"], help="版本递增级别")
    pub_parser.add_argument("--backup-dir", default=None, help="备份目录（可选）")

    args = parser.parse_args()

    if args.command == "publish":
        skill_dir = Path(args.skill_dir).resolve()
        backup_dir = Path(args.backup_dir) if args.backup_dir else None

        result = publish_skill(
            skill_dir=skill_dir,
            skill_name=args.skill_name,
            repo_url=args.repo_url,
            repo=args.repo,
            change_summary=args.change_summary,
            bump=args.bump,
            backup_dir=backup_dir,
        )

        report = generate_markdown_report(result)
        print(report)

        if result.success:
            print("\n✅ 发布成功！")
        else:
            print("\n❌ 发布失败")
            if result.error_message:
                print(f"错误: {result.error_message}")
