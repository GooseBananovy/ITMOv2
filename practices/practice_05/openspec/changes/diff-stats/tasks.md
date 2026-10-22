# Tasks

## 1. Подсчёт статистики и подключение к успешному ответу

- [ ] 1.1 В `app/review.py` добавить приватную функцию подсчёта статистики
      диффа по правилам из `specs/review-diff/spec.md` (заголовок файла —
      строка `--- X`, сразу за которой следует `+++ Y`; `-- ...` без
      следующей `+++ ...` — удалённая строка; прочие строки `+`/`-` считаются
      в `added`/`removed`; диффы без распознаваемых конструкций дают
      `{"files": 0, "added": 0, "removed": 0}`) и проверить через
      `python3 -m compileall -q app`.
- [ ] 1.2 Подключить подсчёт к ветке `{"status": "ok", ...}`: добавить ключ
      `"stats"` к возвращаемому словарю и проверить через новый тест
      `test_returns_stats_for_successful_review` в `tests/test_review.py`
      (вызов `review_diff` с диффом, содержащим пару `---`/`+++` и строки
      `+`/`-`, проверка точных значений `files`/`added`/`removed`).
- [ ] 1.3 Добавить тест на правило "`--- x` без следующей `+++`" — дифф с
      удалённым SQL-комментарием `-- x` без заголовка — и проверить, что он
      учтён в `removed`, а `files` не увеличился: тест
      `test_removed_line_without_file_header_is_not_counted_as_file` в
      `tests/test_review.py`.
- [ ] 1.4 Добавить тест на дифф без распознаваемых конструкций (например,
      только текст без `+`/`-`/`---`/`+++`) и проверить, что `stats` равен
      `{"files": 0, "added": 0, "removed": 0}`: тест
      `test_returns_zero_stats_when_diff_has_no_recognizable_markers` в
      `tests/test_review.py`.

## 2. Статистика в ответах об ошибке зависимости

- [ ] 2.1 Подключить тот же подсчёт к каждой ветке
      `{"status": "error", "code": "model_*", ...}` в `app/review.py` и
      проверить через новый тест
      `test_returns_stats_when_model_times_out` в `tests/test_review.py`
      (используя существующий `TimeoutClient`, проверить наличие и значения
      `stats` в ответе).
- [ ] 2.2 Добавить аналогичный тест для `model_unavailable`:
      `test_returns_stats_when_model_unavailable` в `tests/test_review.py`
      (используя существующий `UnavailableClient`).

## 3. Регрессия: rejected-ответы без stats

- [ ] 3.1 Добавить тесты, подтверждающие, что ключ `"stats"` отсутствует в
      ответах `{"status": "rejected", ...}`: тесты
      `test_rejected_empty_diff_has_no_stats_key` и
      `test_rejected_oversized_diff_has_no_stats_key` в
      `tests/test_review.py`, проверяющие `"stats" not in result`.

## 4. Документация контракта

- [ ] 4.1 Обновить `docs/requirements.md`: описать поле `"stats":
      {"files": N, "added": N, "removed": N}` в разделе успеха и в разделе
      фичи B (ошибка зависимости), явно указать правило распознавания
      заголовка файла и случай `--- x` без `+++`, а также то, что поле
      отсутствует в `rejected`-ответах. Проверить, что текст не меняет
      существующие таблицы кодов и сигнатуру `review_diff`.

## 5. Финальная проверка

- [ ] 5.1 Запустить `sh scripts/check.sh` из `practices/practice_05` и
      убедиться, что компиляция и все тесты (старые и новые) проходят
      зелёным.

## Workflow follow-up

- Показать итоговый вывод `sh scripts/check.sh` и отчитаться по
  `файл:строка` для каждого утверждения, как требует `AGENTS.md`.
- Архивировать change после приёмки результата.
