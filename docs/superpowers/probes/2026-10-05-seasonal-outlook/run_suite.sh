#!/usr/bin/env bash
# Full suite in the issue10 worktree, FAILED/ERROR names compared with the baseline.
# Usage: bash run_suite.sh <tag>   -> ../suite-<tag>.txt, ../names-<tag>.txt
# Baseline: names-base.txt (bbf2e151, measured in this worktree before any change).
set -u
TAG="$1"
cd /d/Entwicklung/HASI/issue10-work/wt || exit 2
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests \
  -p _local_socket_unblock -q --no-header -rfE > "../suite-$TAG.txt" 2>&1
tr '\r' '\n' < "../suite-$TAG.txt" | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' \
  | sort > "../names-$TAG.txt"
echo "HEAD $(git rev-parse --short HEAD)"
tail -c 300 "../suite-$TAG.txt"
echo
if [ "$TAG" = "base" ]; then
  if diff /d/Entwicklung/HASI/issue8-work/names-base-bbf2.txt ../names-base.txt; then
    echo "BASE NAMES IDENTICAL WITH issue8 bbf2 BASELINE ($(wc -l < ../names-base.txt) names)"
  else
    echo "BASE NAMES DIFFER FROM issue8 bbf2 BASELINE"
  fi
elif diff -q ../names-base.txt "../names-$TAG.txt" > /dev/null; then
  echo "NAMES IDENTICAL ($(wc -l < "../names-$TAG.txt") names)"
else
  echo "NAMES DIFFER ($(wc -l < ../names-base.txt) -> $(wc -l < "../names-$TAG.txt"))"
  echo "--- added:"
  comm -13 ../names-base.txt "../names-$TAG.txt"
  echo "--- gone:"
  comm -23 ../names-base.txt "../names-$TAG.txt"
fi
