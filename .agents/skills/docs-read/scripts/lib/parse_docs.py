"""共享 front matter 解析：list/print/create 三个入口复用。

只认 YAML front matter（--- 包围），取 name/description/alwaysApply 三字段。
alwaysApply 缺省视为 false。front matter 不合法 → 跳过并 stderr warn，不挂掉整批。
"""

import re
import sys
from pathlib import Path


def parse_file(file_path: Path) -> dict | None:
    """解析单个 .mdc 文件的 front matter。失败返回 None 并 warn。"""
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"warn: cannot read {file_path}: {e}\n")
        return None

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        sys.stderr.write(f"warn: {file_path} has no front matter\n")
        return None

    # 找结束的 ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end_idx = i
            break
    if end_idx is None:
        sys.stderr.write(f"warn: {file_path} front matter not terminated\n")
        return None

    fm: dict = {}
    for i in range(1, end_idx):
        line = lines[i]
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m:
            continue
        key = m.group(1)
        val = m.group(2).strip()
        # 剥掉外层配对引号
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        fm[key] = val

    if "name" not in fm:
        sys.stderr.write(f"warn: {file_path} missing required field: name\n")
        return None

    always_raw = fm.get("alwaysApply", "").lower()
    fm["alwaysApply"] = always_raw in ("true", "1")
    fm.setdefault("description", "")
    return fm


def walk_mdc(directory: Path, base: Path | None = None) -> list[str]:
    """递归枚举 dir 下所有 .mdc 文件相对路径（正斜杠），子目录深度不限。"""
    if base is None:
        base = directory
    out = []
    try:
        for entry in sorted(directory.iterdir()):
            if entry.is_dir():
                out.extend(walk_mdc(entry, base))
            elif entry.is_file() and entry.suffix == ".mdc":
                rel = entry.relative_to(base).as_posix()
                out.append(rel)
    except OSError as e:
        sys.stderr.write(f"error: cannot readdir {directory}: {e}\n")
        sys.exit(1)
    return out


def list_docs(directory: str = "docs") -> list[dict]:
    """枚举 dir 下所有 .mdc 文件，解析 front matter。

    alwaysApply:true 优先、然后按相对路径排序。
    file 字段是相对 dir 的路径（含子目录，如 spec/preset.mdc）。
    """
    base = Path(directory)
    names = walk_mdc(base)
    parsed = []
    for n in names:
        fm = parse_file(base / n)
        if fm:
            fm["file"] = n
            parsed.append(fm)
    parsed.sort(key=lambda d: (not d["alwaysApply"], d["file"]))
    return parsed


def read_full(file_path: Path) -> str:
    """读单个文件的完整内容（含 front matter）。"""
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"warn: cannot read {file_path}: {e}\n")
        return ""
