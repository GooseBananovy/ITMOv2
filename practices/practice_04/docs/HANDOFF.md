# Состояние работы

Обновляется по ходу. Стабильные правила — в [`../AGENTS.md`](../AGENTS.md),
контракт — в [`requirements.md`](requirements.md).

## Где мы

Ветка `practice-04`. Фича A (валидация входа) принята и закоммичена. Фича B
(ошибка зависимости) сделана в отдельном worktree на ветке `practice-04-b`,
прошла ревью субагентом, по его замечанию доделывается обработка
`http.client.IncompleteRead`.

## Что сделано

- `review-mini`: подписки из практики 3 плюс ревью диффа локальной моделью;
- фича A: `empty_diff`, `diff_too_large`, модель при отказе не вызывается;
- фича B: таймаут, недоступность, HTTP-ошибка, неожидаемый ответ;
- среда: `AGENTS.md`, style guide, свой skill с машинной проверкой запретов,
  hook на событие правки, два MCP-сервера (свой и Context7).

## Источники правды

| Что | Где |
|---|---|
| Контракт фич | `docs/requirements.md` |
| Стиль кода и тестов | `docs/style-guide.md` |
| Процедура сдачи фичи | `.opencode/skills/review-acceptance/SKILL.md` |
| Провенанс skills | `docs/skills.md` |
| Подтверждения прогонов | `evidence/` |
| Отчёт по блокам оценки | `REPORT.md` |

## Проверки

```sh
sh scripts/check.sh                                          # 14 тестов
sh .opencode/skills/review-acceptance/scripts/acceptance.sh   # запреты проекта
```

Для агентной части нужны: запущенная Ollama, сборка `itmo-local:latest` из
практики 3, переменная `VSELLM_API_KEY`.

## Ограничения

- `opencode api skill.list` и `opencode mcp list` не показывают настройки этой
  практики, хотя они работают: статус смотреть в логах сервера с
  `--log-level debug`, строка `mcp connected`;
- `cwd` у локального MCP-сервера резолвится от каталога workspace. Указывать его
  не надо, запуск идёт через `mcp/serve.sh`;
- убитая сессия оставляет за собой процесс MCP-сервера; проверять
  `pgrep -f review_mcp`;
- таймаут соединения попадает в `model_unavailable`, а не `model_timeout`.

## Что дальше

1. Принять доделку фичи B, закоммитить в `practice-04-b`.
2. `git merge --ff-only practice-04-b`, прогнать проверки на объединённом
   состоянии.
3. Подтверждения ошибочного входа в MCP → `evidence/mcp-bad-input.txt`.
4. Проверить, доходит ли вердикт хука до агента после переназначения
   `event.result`.
5. PR `practice-04` → `main`.
