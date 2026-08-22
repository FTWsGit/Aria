"""docs/ 文档管理调度脚本。

用法：
  uv run docs.py list          # 列出所有 .mdc 文档
  uv run docs.py print         # 打印 alwaysApply:true 文档
  uv run docs.py create <name> "<desc>" --kind <kind> [--always] [--dir <path>] [--force]
"""

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent / ".agents" / "skills" / "docs-read" / "scripts"
sys.path.insert(0, str(_SCRIPT_DIR / "lib"))


def main():
    if len(sys.argv) < 2:
        print("用法: uv run docs.py <list|print|create> [args...]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        import json

        from parse_docs import list_docs
        directory = "docs"
        for i, arg in enumerate(sys.argv[2:]):
            if arg == "--dir" and i + 1 < len(sys.argv[2:]):
                directory = sys.argv[2:][i + 1]
                break
        docs = list_docs(directory)
        print(json.dumps(docs, indent=2, ensure_ascii=False))

    elif cmd == "print":
        from parse_docs import list_docs, read_full
        directory = "docs"
        args = sys.argv[2:]
        for i, arg in enumerate(args):
            if arg == "--dir" and i + 1 < len(args):
                directory = args[i + 1]
                break
        base = Path(directory)
        always = [d for d in list_docs(directory) if d["alwaysApply"]]
        if not always:
            print("warn: no alwaysApply:true docs found", file=sys.stderr)
            sys.exit(0)
        for d in always:
            print(f"=== {d['file']} ===")
            print(read_full(base / d["file"]))
            print()

    elif cmd == "create":
        # 直接 delegate 给 create_docs.py
        import subprocess
        create_script = _SCRIPT_DIR / "create_docs.py"
        result = subprocess.run(
            [sys.executable, str(create_script)] + sys.argv[2:],
            cwd=Path(__file__).resolve().parent,
        )
        sys.exit(result.returncode)

    else:
        print(f"未知命令: {cmd}。可用: list, print, create", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()