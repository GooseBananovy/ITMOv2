#!/usr/bin/env python3
"""Полная сетка 2x2 по шести вопросам на локальной модели через Ollama.

Условия прогона зафиксированы в preregistration.md до первого запуска.
Только стандартная библиотека: lab/Makefile проверяет это при install.

Авторский lab/experiment.py не заменяется и не изменяется: в нём вопрос
захардкожен (lab/experiment.py:21), поэтому остальные пять он задать не может.
"""
import argparse
import json
import re
import statistics
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAB = ROOT / "lab"
CONTEXT_FILES = ["demo/README.md", "demo/Makefile", "demo/service.py", "demo/test_service.py"]
ENDPOINT = "http://localhost:11434/api/chat"

# Шестой вопрос — собственная инициатива, контроль на подсказку. Обоснование в
# preregistration.md. Намеренно не содержит ни слова из запретного списка
# system.txt, ни оговорки «если сведений нет».
CONTROL_QUESTION = "Под какой лицензией распространяется этот сервис? Укажи файл-источник."

CELLS = {
    "sysoff-thinkoff": (False, False),
    "syson-thinkoff": (True, False),
    "sysoff-thinkon": (False, True),
    "syson-thinkon": (True, True),
}

FIXED = {"temperature": 0.2, "seed": 42, "num_ctx": 4096, "num_predict": 2048}


def load_questions():
    """Пять вопросов читаем из lab/QUESTIONS.md дословно, а не копией в коде."""
    text = (LAB / "QUESTIONS.md").read_text(encoding="utf-8")
    found = []
    for line in text.splitlines():
        m = re.match(r"^(\d+)\.\s+(.*\S)\s*$", line)
        if m:
            found.append((int(m.group(1)), m.group(2)))
    found.sort()
    if [n for n, _ in found] != [1, 2, 3, 4, 5]:
        raise SystemExit(f"Ожидались вопросы 1-5, разобрано: {[n for n, _ in found]}")
    return [q for _, q in found] + [CONTROL_QUESTION]


def build_context():
    parts = []
    for rel in CONTEXT_FILES:
        lines = (LAB / rel).read_text(encoding="utf-8").splitlines()
        body = "\n".join(f"{i}: {l}" for i, l in enumerate(lines, 1))
        parts.append(f"=== {rel} ===\n{body}")
    return "Материалы проекта (номер строки перед каждой строкой):\n\n" + "\n\n".join(parts)


def ask(model, context, question, use_system, think):
    messages = []
    if use_system:
        messages.append({"role": "system", "content": (LAB / "system.txt").read_text(encoding="utf-8")})
    messages.append({"role": "user", "content": f"{context}\n\nВопрос: {question}"})
    payload = {"model": model, "messages": messages, "stream": False, "think": think, "options": dict(FIXED)}
    request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        answer = json.load(response)
    wall = time.perf_counter() - started
    eval_ns = answer.get("eval_duration", 0)
    return {
        "request": payload,
        "response": answer,
        "wall_seconds": round(wall, 2),
        "load_seconds": round(answer.get("load_duration", 0) / 1e9, 2),
        "prompt_tokens": answer.get("prompt_eval_count"),
        "generated_tokens": answer.get("eval_count"),
        "decode_tokens_per_second": round(answer.get("eval_count", 0) / (eval_ns / 1e9), 2) if eval_ns else None,
        "done_reason": answer.get("done_reason"),
    }


def run_matrix(model, out_dir, force):
    questions = load_questions()
    context = build_context()
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for cell, (use_system, think) in CELLS.items():
        for number, question in enumerate(questions, 1):
            path = out_dir / f"{cell}__q{number}.json"
            if path.exists() and not force:
                print(f"пропуск (уже есть): {path.name}")
                continue
            print(f"прогон {cell} q{number} ... ", end="", flush=True)
            record = ask(model, context, question, use_system, think)
            record["cell"] = cell
            record["question_number"] = number
            record["question"] = question
            record["system_prompt_used"] = use_system
            record["think"] = think
            record["control_question"] = number == 6
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            msg = record["response"].get("message", {})
            print(f"{record['wall_seconds']}s, {record['generated_tokens']} ток, "
                  f"{record['done_reason']}, рассуждение {len(msg.get('thinking') or '')} симв.")
            index.append({k: record[k] for k in ("cell", "question_number", "wall_seconds",
                                                 "generated_tokens", "decode_tokens_per_second", "done_reason")})
    if index:
        (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nготово, файлов в {out_dir}: {len(list(out_dir.glob('*__q*.json')))}")


def run_speed(model, out_dir, repeats):
    """Холодный старт отдельно от прогретых: это величины разной природы."""
    context = build_context()
    question = load_questions()[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    print("модель выгружена вызывающей стороной; первый замер считается холодным")
    runs = []
    for i in range(repeats + 1):
        record = ask(model, context, question, use_system=True, think=False)
        kind = "cold" if i == 0 else "warm"
        record["kind"] = kind
        runs.append(record)
        print(f"{kind}: wall {record['wall_seconds']}s, load {record['load_seconds']}s, "
              f"{record['decode_tokens_per_second']} ток/с")
    warm = [r["decode_tokens_per_second"] for r in runs if r["kind"] == "warm"]
    summary = {
        "model": model,
        "fixed_options": FIXED,
        "cold": {k: runs[0][k] for k in ("wall_seconds", "load_seconds", "decode_tokens_per_second")},
        "warm_runs": [{k: r[k] for k in ("wall_seconds", "load_seconds", "decode_tokens_per_second")} for r in runs[1:]],
        "warm_median_tokens_per_second": round(statistics.median(warm), 2) if warm else None,
        "units": "tokens/second on decode, seconds wall-clock",
    }
    (out_dir / "speed.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nмедиана прогретых: {summary['warm_median_tokens_per_second']} ток/с")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:4b",
                        help="базовый тег, а не itmo-local: в нём системный промпт вшит")
    parser.add_argument("--out", default=str(ROOT / "results"))
    parser.add_argument("--mode", choices=["matrix", "speed"], default="matrix")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--force", action="store_true", help="перезаписать уже существующие прогоны")
    args = parser.parse_args()
    out_dir = Path(args.out)
    if args.mode == "matrix":
        run_matrix(args.model, out_dir, args.force)
    else:
        run_speed(args.model, out_dir, args.repeats)


if __name__ == "__main__":
    main()
