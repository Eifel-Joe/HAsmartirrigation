#!/usr/bin/env bash
# t12_suites.sh: Task 12 Step 3 — baseline on upstream/master (base-wt), then the rebased branch (wt),
# one after the other (never two pytest runs side by side), then the name comparison.
set -u
W=/d/Entwicklung/HASI/issue8-pr3-work
PY=/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
export TEMP=$W/tmp TMP=$W/tmp TMPDIR=$W/tmp UV_CACHE_DIR=$W/uv-cache
rm -f $W/t12-suites.done

cd $W/base-wt || exit 2
echo "base start $(date -u +%H:%M:%S) at $(git rev-parse --short=8 HEAD)" > $W/t12-progress.txt
TZ=UTC $PY -m pytest tests -p _local_socket_unblock -q --no-header -rfE > $W/suite-t12-base.txt 2>&1
echo "base exit $? $(date -u +%H:%M:%S)" >> $W/t12-progress.txt
tr '\r' '\n' < $W/suite-t12-base.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > $W/names-t12-base.txt

cd $W/wt || exit 2
echo "pr start $(date -u +%H:%M:%S) at $(git rev-parse --short=8 HEAD)" >> $W/t12-progress.txt
TZ=UTC $PY -m pytest tests -p _local_socket_unblock -q --no-header -rfE > $W/suite-t12-pr.txt 2>&1
echo "pr exit $? $(date -u +%H:%M:%S)" >> $W/t12-progress.txt
tr '\r' '\n' < $W/suite-t12-pr.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > $W/names-t12-pr.txt

{
  echo "=== base summary";  tr '\r' '\n' < $W/suite-t12-base.txt | grep -E "^=+ .*(passed|failed).* in " | tail -1
  echo "=== pr summary";    tr '\r' '\n' < $W/suite-t12-pr.txt   | grep -E "^=+ .*(passed|failed).* in " | tail -1
  echo "=== baseline names missing in pr:"; comm -23 $W/names-t12-base.txt $W/names-t12-pr.txt
  echo "=== FAILED compare:"; diff <(grep "^FAILED" $W/names-t12-base.txt) <(grep "^FAILED" $W/names-t12-pr.txt) && echo "FAILED gleich"
  echo "=== new names in pr per file:"; comm -13 $W/names-t12-base.txt $W/names-t12-pr.txt | sed -E 's/::.*//' | sort | uniq -c
  echo "=== Lingering timer: base $(grep -c 'Lingering timer' $W/suite-t12-base.txt) / pr $(grep -c 'Lingering timer' $W/suite-t12-pr.txt)"
} > $W/t12-compare.txt 2>&1
touch $W/t12-suites.done
echo "done $(date -u +%H:%M:%S)" >> $W/t12-progress.txt
