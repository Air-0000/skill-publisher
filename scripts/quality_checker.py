"""质量检查器模块 (quality_checker.py)

提供 Skill 仓库的质量检查功能，包括：
- frontmatter 校验
- 必须文件检查
- 文件名合规性
- changelog 格式
- readme 一致性
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re


@dataclass
class QCIssue:
    """质量检查问题 dataclass"""
    level: str          # "error" | "warning"
    code: str           # 问题代码
    message: str        # 人类可读消息
    file: Optional[str] = None   # 相关文件路径
    field: Optional[str] = None  # 相关字段


class QualityChecker:
    """质量检查器，执行5项检查"""

    REQUIRED_FILES = ["SKILL.md", "CHANGELOG.md", "README.md"]
    VALID_NAME_PATTERN = r"^[a-z0-9][a-z0-9_-]*$"

    def check(self, skill_dir: Path) -> list[QCIssue]:
        """执行所有质量检查，返回问题列表

        Args:
            skill_dir: Skill 目录路径

        Returns:
            QCIssue 列表
        """
        issues = []
        issues.extend(self.check_frontmatter(skill_dir))
        issues.extend(self.check_required_files(skill_dir))
        issues.extend(self.check_filename_compliance(skill_dir))
        issues.extend(self.check_changelog_format(skill_dir))
        issues.extend(self.check_readme_consistency(skill_dir))
        return issues

    def check_frontmatter(self, skill_dir: Path) -> list[QCIssue]:
        """检查 SKILL.md 的 YAML frontmatter 是否存在且有效

        Args:
            skill_dir: Skill 目录路径

        Returns:
            QCIssue 列表
        """
        issues = []
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return [QCIssue("error", "FRONTMATTER_MISSING", "SKILL.md not found", "SKILL.md")]

        content = skill_md.read_text()
        if not content.startswith("---"):
            issues.append(QCIssue(
                "error",
                "FRONTMATTER_MISSING",
                "SKILL.md missing YAML frontmatter",
                "SKILL.md"
            ))
            return issues

        # 检查 frontmatter 闭合
        lines = content.split("\n")
        end_idx = -1
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break

        if end_idx == -1:
            issues.append(QCIssue(
                "error",
                "FRONTMATTER_UNCLOSED",
                "SKILL.md frontmatter not properly closed",
                "SKILL.md"
            ))

        return issues

    def check_required_files(self, skill_dir: Path) -> list[QCIssue]:
        """检查必须文件是否存在

        Args:
            skill_dir: Skill 目录路径

        Returns:
            QCIssue 列表
        """
        issues = []
        for fname in self.REQUIRED_FILES:
            if not (skill_dir / fname).exists():
                issues.append(QCIssue(
                    "error",
                    "REQUIRED_FILE_MISSING",
                    f"Required file missing: {fname}",
                    fname
                ))
        return issues

    def check_filename_compliance(self, skill_dir: Path) -> list[QCIssue]:
        """检查目录名和文件名合规性（小写字母、数字、连字符）

        Args:
            skill_dir: Skill 目录路径

        Returns:
            QCIssue 列表
        """
        issues = []
        name = skill_dir.name
        if not re.match(self.VALID_NAME_PATTERN, name):
            issues.append(QCIssue(
                "error",
                "FILENAME_NONCOMPLIANT",
                f"Directory name '{name}' does not match pattern {self.VALID_NAME_PATTERN}",
                skill_dir.name
            ))
        return issues

    def check_changelog_format(self, skill_dir: Path) -> list[QCIssue]:
        """检查 CHANGELOG.md 格式（存在且非空）

        Args:
            skill_dir: Skill 目录路径

        Returns:
            QCIssue 列表
        """
        issues = []
        changelog = skill_dir / "CHANGELOG.md"
        if not changelog.exists():
            issues.append(QCIssue(
                "warning",
                "CHANGELOG_MISSING",
                "CHANGELOG.md not found",
                "CHANGELOG.md"
            ))
        elif changelog.stat().st_size == 0:
            issues.append(QCIssue(
                "warning",
                "CHANGELOG_EMPTY",
                "CHANGELOG.md is empty",
                "CHANGELOG.md"
            ))
        return issues

    def check_readme_consistency(self, skill_dir: Path) -> list[QCIssue]:
        """检查 README.md 与 SKILL.md 的一致性

        Args:
            skill_dir: Skill 目录路径

        Returns:
            QCIssue 列表
        """
        issues = []
        readme = skill_dir / "README.md"
        if not readme.exists():
            issues.append(QCIssue(
                "warning",
                "README_MISSING",
                "README.md not found",
                "README.md"
            ))
        return issues
