"""MCP-сервер review-mini: даёт агенту ревью диффа локальной моделью.

Запуск: uv run --with fastmcp python mcp/review_mcp.py
Транспорт stdio, сетевых портов не открывает.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.review import review_diff as service_review  # noqa: E402

from fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("review-mini")


@mcp.tool
def review_diff(diff: str) -> dict:
    """Отправить unified diff на ревью локальной модели проекта review-mini.

    Возвращает ответ по контракту docs/requirements.md:
    status=ok и review с текстом замечаний; status=rejected и code при
    нарушении входных ограничений; status=error и code при сбое зависимости.

    Ревью даёт локальная модель, ответ является мнением, а не приговором.
    """
    try:
        return service_review(diff)
    except Exception as error:
        return {
            "status": "error",
            "code": "service_exception",
            "message": f"{type(error).__name__}: {error}",
        }


if __name__ == "__main__":
    mcp.run()
