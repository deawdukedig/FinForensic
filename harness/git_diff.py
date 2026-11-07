"""
Git Delta & Diff Extractor.
Extracts unified diffs for modified artifacts to dramatically reduce token consumption.
"""

from __future__ import annotations
from pathlib import Path
import subprocess
from typing import List, Optional


class GitDeltaExtractor:
    """Extracts git unified diffs for specified files."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root).resolve()

    def get_diff(self, file_paths: Optional[List[str]] = None, context_lines: int = 4) -> str:
        """
        Runs `git diff -U<context_lines>` for unstaged and staged changes.
        If file_paths is provided, limits diff to those files.
        """
        cmd = ["git", "diff", f"-U{context_lines}"]
        if file_paths:
            # Format relative paths
            rel_paths = []
            for p in file_paths:
                path_obj = Path(p)
                if path_obj.is_absolute():
                    try:
                        rel_paths.append(str(path_obj.relative_to(self.repo_root)))
                    except ValueError:
                        rel_paths.append(str(path_obj))
                else:
                    rel_paths.append(str(p))
            cmd.extend(["--"] + rel_paths)

        try:
            res = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True, check=False)
            diff_text = res.stdout.strip()
            if diff_text:
                return diff_text

            # If no unstaged diff, check diff against HEAD~1 if in git repo
            cmd_head = ["git", "diff", f"-U{context_lines}", "HEAD~1"]
            if file_paths:
                cmd_head.extend(["--"] + rel_paths)
            res_head = subprocess.run(cmd_head, cwd=self.repo_root, capture_output=True, text=True, check=False)
            return res_head.stdout.strip()
        except Exception:
            return ""

    def get_file_content_snippet(self, file_path: str, max_lines: int = 120) -> str:
        """Fallback when git diff is not available: returns concise snippet."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.repo_root / path

        if not path.exists() or not path.is_file():
            return f"[File {file_path} not found]"

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) <= max_lines:
                return "".join(lines)
            return "".join(lines[:max_lines]) + f"\n... [Truncated: {len(lines) - max_lines} more lines]"
        except Exception as e:
            return f"[Error reading file: {e}]"
