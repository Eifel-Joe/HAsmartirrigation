#!/usr/bin/env bash
# task_compare.sh <label> <test files...>: run them, compare FAILED/ERROR names with the baseline of those files.
set -u
label=$1; shift
W=/d/Entwicklung/HASI/issue8-pr3-work
# Temp files on D:, never on the system drive C: (pytest writes to TEMP).
mkdir -p $W/tmp && export TEMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMPDIR=D:/Entwicklung/HASI/issue8-pr3-work/tmp
cd $W/wt || exit 2
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "$@" -p _local_socket_unblock -q --no-header -rfE > $W/task-$label.txt 2>&1
tr '\r' '\n' < $W/task-$label.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > $W/task-$label-names.txt
pat=$(printf '%s\n' "$@" | sed 's#tests/##; s#\.py$##' | paste -sd'|')
grep -E "$pat" $W/names-base-wt.txt | sort > $W/task-$label-base.txt
echo "baseline names missing now: $(comm -23 $W/task-$label-base.txt $W/task-$label-names.txt | wc -l)"
comm -23 $W/task-$label-base.txt $W/task-$label-names.txt
echo "new FAILED: $(comm -13 $W/task-$label-base.txt $W/task-$label-names.txt | grep -c '^FAILED')"
echo "new ERROR per file:"; comm -13 $W/task-$label-base.txt $W/task-$label-names.txt | grep '^ERROR' | sed -E 's/::.*//' | sort | uniq -c
tr '\r' '\n' < $W/task-$label.txt | grep -E "^=+ .*(passed|failed).* in " | tail -1
