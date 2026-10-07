#!/bin/sh
# Запуск MCP-сервера review-mini. Каталог проекта определяется от этого файла,
# поэтому от текущего каталога запуск не зависит.
set -eu
cd "$(dirname "$0")/.."
exec uv run --quiet --with fastmcp python mcp/review_mcp.py
