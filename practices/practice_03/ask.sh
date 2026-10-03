#!/usr/bin/env bash
# Один вопрос локальной модели с файлами проекта в контексте.
#
# Зачем скрипт, а не `ollama run`: флаг --think false рассуждение не выключает,
# и модель уходит в многословную «мысль вслух» на 50+ секунд. Поле think в
# нативном API работает, и тот же вопрос укладывается в 8-10 секунд.
#
# Строки контекста нумеруются: без номеров модель называет строку приблизительно.
#
# Использование:  ./ask.sh "вопрос"
set -eu

QUESTION="${1:?укажите вопрос}"
MODEL="${MODEL:-itmo-local}"
DIR="${DIR:-$(dirname "$0")/lab/demo}"

QUESTION="$QUESTION" MODEL="$MODEL" DIR="$DIR" python3 - <<'PY'
import json, os, time, urllib.request
from pathlib import Path

root = Path(os.environ["DIR"])
files = ["README.md", "Makefile", "service.py", "test_service.py"]
parts = []
for rel in files:
    lines = (root / rel).read_text(encoding="utf-8").splitlines()
    body = "\n".join(f"{i}: {l}" for i, l in enumerate(lines, 1))
    parts.append(f"=== {rel} ===\n{body}")
context = "Материалы проекта (номер строки перед каждой строкой):\n\n" + "\n\n".join(parts)

payload = {
    "model": os.environ["MODEL"],
    "stream": False,
    "think": False,
    "messages": [{"role": "user", "content": f"{context}\n\nВопрос: {os.environ['QUESTION']}"}],
    "options": {"num_predict": 1024},
}
request = urllib.request.Request(
    "http://localhost:11434/api/chat",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
started = time.perf_counter()
with urllib.request.urlopen(request, timeout=600) as response:
    answer = json.load(response)
elapsed = time.perf_counter() - started

print((answer["message"].get("content") or "").strip())
ev, ed = answer.get("eval_count", 0), answer.get("eval_duration", 0)
print(f"\n--- {elapsed:.1f} c | {ev} токенов | {ev / (ed / 1e9):.1f} ток/с | "
      f"промпт {answer.get('prompt_eval_count')} токенов | {answer.get('done_reason')}")
PY
