#!/usr/bin/env bash
# Full suite in a prodrebuild worktree; FAILED/ERROR names compared with the base run.
# Usage: bash run_suite.sh <worktree-dir> <tag>   (tag "base" records the baseline)
set -u
WT="$1"
TAG="$2"
OUT=/d/Entwicklung/HASI/prodrebuild-1006-work
cd "$OUT/$WT" || exit 2
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests \
  -p _local_socket_unblock -q --no-header -rfE > "$OUT/suite-$TAG.txt" 2>&1
tr '\r' '\n' < "$OUT/suite-$TAG.txt" | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' \
  | sort > "$OUT/names-$TAG.txt"
echo "HEAD $(git rev-parse --short HEAD)"
tr '\r' '\n' < "$OUT/suite-$TAG.txt" | grep -E "^=+ .*(passed|failed).* =+$" | tail -1
if [ "$TAG" = "base" ]; then
  echo "BASE: $(wc -l < "$OUT/names-base.txt") names"
elif diff -q "$OUT/names-base.txt" "$OUT/names-$TAG.txt" > /dev/null; then
  echo "NAMES IDENTICAL ($(wc -l < "$OUT/names-$TAG.txt") names)"
else
  echo "NAMES DIFFER ($(wc -l < "$OUT/names-base.txt") -> $(wc -l < "$OUT/names-$TAG.txt"))"
  echo "--- added:"; comm -13 "$OUT/names-base.txt" "$OUT/names-$TAG.txt"
  echo "--- gone:"; comm -23 "$OUT/names-base.txt" "$OUT/names-$TAG.txt"
fi
