"""堆读 alwaysApply:true 文档完整内容，stdout 输出纯文本。

SKILL.md 的 Phase 1 用它一次性把所有核心文档读进上下文，省 N 次 read_file。
用法：uv run python .agents/skills/docs-read/scripts/print_always.py [--dir <path>]
"""

import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_script_dir / "lib"))

from parse_docs import list_docs, read_full

args = sys.argv[1:]
directory = "docs"
for i, arg in enumerate(args):
    if arg == "--dir" and i + 1 < len(args):
        directory = args[i + 1]
        break

always = [d for d in list_docs(directory) if d["alwaysApply"]]
if not always:
    sys.stderr.write("warn: no alwaysApply:true docs found\n")
    sys.exit(0)

base = Path(directory)
out_parts = []
for d in always:
    out_parts.append(f"=== {d['file']} ===")
    out_parts.append(read_full(base / d["file"]))
    out_parts.append("")

print("\n".join(out_parts))
