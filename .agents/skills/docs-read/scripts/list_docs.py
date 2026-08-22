"""枚举 docs front matter，stdout 输出 JSON 数组。

每项 {file, name, description, alwaysApply}。alwaysApply:true 优先、然后按文件名。
用法：uv run python .agents/skills/docs-read/scripts/list_docs.py [--dir <path>]
"""

import json
import sys
from pathlib import Path

# 确保 lib 在 sys.path 中
_script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_script_dir / "lib"))

from parse_docs import list_docs

args = sys.argv[1:]
directory = "docs"
for i, arg in enumerate(args):
    if arg == "--dir" and i + 1 < len(args):
        directory = args[i + 1]
        break

docs = list_docs(directory)
print(json.dumps(docs, indent=2, ensure_ascii=False))
