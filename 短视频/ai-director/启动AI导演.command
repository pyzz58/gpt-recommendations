#!/bin/bash
# macOS local-only launcher. Run with: bash '启动AI导演.command'
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo '未发现 Python3。请先安装 Python 3.10+，再打开本目录的 README_V03.md。'
  exit 1
fi
python3 local_ui.py