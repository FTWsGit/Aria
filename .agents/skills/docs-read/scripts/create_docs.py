"""脚手架生成一个新的 docs/*.mdc 文档，frontmatter 字段齐全。

用法：
  uv run python .agents/skills/docs-read/scripts/create_docs.py <name> "<description>" --kind <kind> [--always] [--dir <path>] [--force]

  <name>         文档名，同时用作文件名（<name>.mdc）和 frontmatter 的 name 字段，不要带 .mdc 后缀
  <description>  "何时读"，必须是单行纯文本
  --kind <kind>  文档性质：guide / contract / spec / architecture / subsystem / decision
  --always       设置 alwaysApply: true（默认 false）
  --dir <path>   目标目录，默认 docs
  --force        目标文件已存在时允许覆盖（默认拒绝）
"""

import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_script_dir / "lib"))

from parse_docs import parse_file

args = sys.argv[1:]
positional = []
directory = "docs"
kind = ""
always = False
force = False

i = 0
while i < len(args):
    if args[i] == "--dir" and i + 1 < len(args):
        directory = args[i + 1]; i += 1
    elif args[i] == "--kind" and i + 1 < len(args):
        kind = args[i + 1]; i += 1
    elif args[i] == "--always":
        always = True
    elif args[i] == "--force":
        force = True
    else:
        positional.append(args[i])
    i += 1

if len(positional) < 2:
    sys.stderr.write(
        'usage: create_docs.py <name> "<description>" --kind <spec|architecture|subsystem|decision|contract> [--always] [--dir <path>] [--force]\n'
    )
    sys.exit(1)

name, description = positional[0], positional[1]

if not kind:
    sys.stderr.write(
        "warn: 没给 --kind，生成的文档不会被归类到任何知识性质——建议补一个（contract/spec/architecture/subsystem/decision）\n"
    )
if '"' in kind:
    sys.stderr.write("error: kind 不能含双引号\n")
    sys.exit(1)
if "\n" in description or "\r" in description:
    sys.stderr.write("error: description 必须是单行，不支持换行\n")
    sys.exit(1)
if name.lower().endswith(".mdc"):
    sys.stderr.write("error: <name> 不要带 .mdc 后缀，脚本会自动加\n")
    sys.exit(1)
if '"' in name:
    sys.stderr.write("error: name 不能含双引号\n")
    sys.exit(1)

safe_description = description
if '"' in safe_description:
    safe_description = safe_description.replace('"', "'")
    sys.stderr.write(
        "warn: description 里的双引号已自动替换成单引号（frontmatter 用双引号包裹整体，解析器不支持转义）\n"
    )

target_dir = Path(directory)
if not target_dir.is_dir():
    sys.stderr.write(f"error: 目录 {target_dir} 不存在\n")
    sys.exit(1)

file_path = target_dir / f"{name}.mdc"

if file_path.exists() and not force:
    sys.stderr.write(f"error: {file_path} 已存在，加 --force 才允许覆盖\n")
    sys.exit(1)

body = f"""---
name: "{name}"
kind: "{kind}"
description: "{safe_description}"
alwaysApply: {str(always).lower()}
---

# {name}

"""

file_path.write_text(body, encoding="utf-8")

# 自检
check = parse_file(file_path)
if not check:
    sys.stderr.write(f"error: 生成的 {file_path} 没能通过 frontmatter 自检\n")
    sys.exit(1)

print(f"created {file_path}")
print(f"  name: {check['name']}")
print(f"  kind: {check.get('kind', '(未设置)')}")
print(f"  description: {check['description']}")
print(f"  alwaysApply: {check['alwaysApply']}")
print("\n下一步：填正文内容，支持直接append到文件末尾")
