"""版本管理辅助模块 (version.py)

提供版本解析、比较、递增等功能，支持语义化版本（vX.Y.Z）。
"""

from dataclasses import dataclass
from typing import Optional
import re


VERSION_PATTERN = r"^v(\d+)\.(\d+)\.(\d+)$"


@dataclass
class VersionInfo:
    """版本信息 dataclass"""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def parse_version(v: str) -> Optional[VersionInfo]:
    """解析版本字符串为 VersionInfo

    Args:
        v: 版本字符串，格式为 vX.Y.Z

    Returns:
        VersionInfo 对象，解析失败返回 None
    """
    m = re.match(VERSION_PATTERN, v.strip())
    if not m:
        return None
    return VersionInfo(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def compare_versions(v1: str | VersionInfo, v2: str | VersionInfo) -> int:
    """比较两个版本

    Args:
        v1: 版本字符串或 VersionInfo
        v2: 版本字符串或 VersionInfo

    Returns:
        v1 > v2 返回 1，v1 < v2 返回 -1，相等返回 0
    """
    if isinstance(v1, str):
        v1 = parse_version(v1)
    if isinstance(v2, str):
        v2 = parse_version(v2)
    t1 = v1.to_tuple() if v1 else (0, 0, 0)
    t2 = v2.to_tuple() if v2 else (0, 0, 0)
    if t1 > t2:
        return 1
    elif t1 < t2:
        return -1
    return 0


def bump_version(v: str, level: str) -> Optional[str]:
    """根据 level 递增版本

    Args:
        v: 当前版本字符串（vX.Y.Z）
        level: 递增级别，"major" | "minor" | "patch"

    Returns:
        递增后的版本字符串，失败返回 None
    """
    vi = parse_version(v)
    if not vi:
        return None
    if level == "major":
        vi.major += 1
        vi.minor = 0
        vi.patch = 0
    elif level == "minor":
        vi.minor += 1
        vi.patch = 0
    elif level == "patch":
        vi.patch += 1
    else:
        return None
    return str(vi)


def get_remote_latest_tag(repo: str) -> Optional[str]:
    """从远程仓库获取最新 tag

    Args:
        repo: 仓库 URL（支持 git@ 和 https:// 格式）

    Returns:
        最新 tag 字符串（如 v1.2.3），无 tag 或失败返回 None
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--sort=-v:refname", repo],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) == 2:
                tag = parts[1].removeprefix("refs/tags/")
                if parse_version(tag):
                    return tag
        return None
    except Exception:
        return None
