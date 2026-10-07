#!/bin/sh
# Машинная проверка запретов проекта. Выход 0 - можно сдавать.
set -u
cd "$(dirname "$0")/../../../.." || exit 2

FAILED=0

say() { printf '%s\n' "$1"; }
fail() { say "FAIL  $1"; FAILED=1; }
pass() { say "ok    $1"; }

say "== доверенный раннер =="
if sh scripts/check.sh; then
  pass "sh scripts/check.sh зелёный"
else
  fail "sh scripts/check.sh красный"
fi

say ""
say "== запреты =="

PROTECTED="docs/requirements.md scripts/check.sh"
for file in $PROTECTED; do
  if git diff --quiet HEAD -- "$file" 2>/dev/null; then
    pass "$file не менялся"
  else
    fail "$file изменён, а его менять нельзя без поручения"
  fi
done

if git diff --quiet HEAD -- app/subscribe.py 2>/dev/null; then
  pass "app/subscribe.py не менялся"
else
  fail "app/subscribe.py изменён, он регрессионная поверхность"
fi

if git status --porcelain ../practice_03 2>/dev/null | grep -q .; then
  fail "есть правки в practices/practice_03 - это сданная работа"
else
  pass "practices/practice_03 не тронут"
fi

ALLOWED="argparse collections dataclasses functools http json os pathlib re socket subprocess sys time typing unittest urllib app tests"
ADDED=$(git diff HEAD -- app tests | sed -n 's/^+\(import\|from\) \([A-Za-z_][A-Za-z0-9_]*\).*/\2/p' | sort -u)
UNKNOWN=""
for module in $ADDED; do
  case " $ALLOWED " in
    *" $module "*) ;;
    *) UNKNOWN="$UNKNOWN $module" ;;
  esac
done
if [ -n "$UNKNOWN" ]; then
  fail "добавлены импорты вне стандартной библиотеки:$UNKNOWN"
else
  pass "новых зависимостей нет"
fi

DEBUG=$(git diff HEAD -- app | grep -c '^+[[:space:]]*print(' || true)
if [ "$DEBUG" -gt 0 ]; then
  fail "в app/ добавлено $DEBUG отладочных print("
else
  pass "отладочных print( в app/ нет"
fi

say ""
if [ "$FAILED" -eq 0 ]; then
  say "ИТОГ: можно сдавать"
else
  say "ИТОГ: сдавать нельзя, см. FAIL выше"
fi
exit "$FAILED"
