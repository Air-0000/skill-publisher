"""Git 操作封装模块 (git_utils.py)

提供 Git 相关操作的封装，包括：
- 获取当前 commit hash
- 执行 git push
- 生成回滚命令
"""

from typing import Tuple


def get_commit_hash(repo_path: str = ".") -> str | None:
    """获取当前 commit hash（缩写）

    Args:
        repo_path: 仓库路径，默认为当前目录

    Returns:
        缩写的 commit hash，失败返回 None
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def git_push(repo_path: str = ".") -> Tuple[bool, str]:
    """执行 git push

    Args:
        repo_path: 仓库路径，默认为当前目录

    Returns:
        (success, error_message) 元组
        - 成功：success=True, error_message=""
        - 失败：success=False, error_message=错误信息
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "push", "origin", "HEAD"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def generate_rollback_command(repo_path: str = ".") -> str:
    """生成回滚命令

    生成回退到上一个 commit 的命令字符串（包含 --force push）。

    Args:
        repo_path: 仓库路径，默认为当前目录

    Returns:
        回滚命令字符串
    """
    return f"git -C {repo_path} reset --hard HEAD~1 && git -C {repo_path} push --force"
