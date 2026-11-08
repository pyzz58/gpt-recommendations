#!/bin/zsh
set -euo pipefail

project_root="$(cd "$(dirname "$0")" && pwd)"
cd "$project_root"

if ! command -v uv >/dev/null 2>&1; then
  echo "缺少 uv。请先在“文件夹操作指南”中按步骤安装 uv。" >&2
  exit 1
fi

exec uv run --frozen python tools/local_experience.py "$@"
