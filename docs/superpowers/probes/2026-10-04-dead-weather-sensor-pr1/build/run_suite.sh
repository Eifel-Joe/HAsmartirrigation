#!/usr/bin/env bash
# Full suite in the worktree, FAILED/ERROR names compared with the Task-0 baseline.
# Usage: bash run_suite.sh <tag>   -> ../suite-<tag>.txt, ../names-<tag>.txt
set -u
TAG="$1"
cd /d/Entwicklung/HASI/issue8-work/wt || exit 2
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests \
  -p _local_socket_unblock -q --no-header -rfE > "../suite-$TAG.txt" 2>&1
tr '\r' '\n' < "../suite-$TAG.txt" | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' \
  | sort > "../names-$TAG.txt"
echo "HEAD $(git rev-parse --short HEAD)"
tail -c 300 "../suite-$TAG.txt"
echo
if diff ../names-baseline.txt "../names-$TAG.txt"; then
  echo "NAMES IDENTICAL ($(wc -l < "../names-$TAG.txt") names)"
else
  echo "NAMES DIFFER"
fi
