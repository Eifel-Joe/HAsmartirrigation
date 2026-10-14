#!/usr/bin/env bash
# Full suite in the worktree + three-part name comparison against the baseline
# (plan Task 10 Step 2). Usage: suite_compare.sh <label>
# Writes sdd/suite-<label>.txt, names-<label>.txt, compare-<label>.txt.
set -u
label=$1
W=/d/Entwicklung/HASI/issue8-pr3-work
S=$W/sdd
# Temp files on D:, never on the system drive C: (pytest writes to TEMP).
mkdir -p $W/tmp && export TEMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMPDIR=D:/Entwicklung/HASI/issue8-pr3-work/tmp
cd $W/wt || exit 2
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > $S/suite-$label.txt 2>&1
echo $? > $S/suite-$label.exit
tr '\r' '\n' < $S/suite-$label.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > $S/names-$label.txt
{
  echo "HEAD $(git rev-parse --short=8 HEAD)  label=$label  exit=$(cat $S/suite-$label.exit)"
  echo "-- baseline summary:"; tr '\r' '\n' < $W/suite-base-wt.txt | grep -E "^=+ .*(passed|failed).* in " | tail -1
  echo "-- this run summary:"; tr '\r' '\n' < $S/suite-$label.txt | grep -E "^=+ .*(passed|failed).* in " | tail -1
  echo "-- (1) baseline names missing now (expected: only the 2 renamed in the hourly-switch task):"
  comm -23 $W/names-base-wt.txt $S/names-$label.txt | wc -l
  comm -23 $W/names-base-wt.txt $S/names-$label.txt | head -20
  echo "-- (2) FAILED sets:"
  if grep "^FAILED" $W/names-base-wt.txt | diff - <(grep "^FAILED" $S/names-$label.txt) > /dev/null; then echo "FAILED gleich"; else echo "FAILED DIFFER"; grep "^FAILED" $W/names-base-wt.txt | diff - <(grep "^FAILED" $S/names-$label.txt); fi
  echo "-- (3) new names per file (allowed: only teardown 'Lingering timer' ERRORs of new tests):"
  comm -13 $W/names-base-wt.txt $S/names-$label.txt | sed -E 's/::.*//' | sort | uniq -c
  echo "-- classification of new names (UNEXPECTED must be 0):"
  python $S/classify_new_errors.py $W/names-base-wt.txt $S/names-$label.txt $S/suite-$label.txt | grep -E "^BAD|^UNEXPECTED"
  echo "-- 'Lingering timer' counts: baseline $(tr '\r' '\n' < $W/suite-base-wt.txt | grep -c 'Lingering timer')  now $(tr '\r' '\n' < $S/suite-$label.txt | grep -c 'Lingering timer')"
} > $S/compare-$label.txt 2>&1
cat $S/compare-$label.txt
