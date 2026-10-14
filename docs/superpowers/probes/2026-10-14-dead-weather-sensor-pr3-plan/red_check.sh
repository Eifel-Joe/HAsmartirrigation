#!/usr/bin/env bash
# For each task: the state of the task before it, plus only that task's tests, then the
# plan's RED command. Records the summary line and the first error kind per task.
set -u
W=/d/Entwicklung/HASI/issue8-pr3-work
PY=/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
R=$W/redcheck-wt
cd $W/probe-wt
declare -A SHA
for n in 1 2 3 4 5 6 7 8 9; do
  SHA[$n]=$(git log --format=%H --grep="probe T$n:" -1)
done
SHA[0]=6fa424e8
if [ ! -d "$R" ]; then
  git worktree add --detach "$R" 6fa424e8 > /dev/null 2>&1
  cp /d/Entwicklung/HASI/HAsmartirrigation/_local_socket_unblock.py "$R/"
fi
declare -A RUN
RUN[1]="tests/test_sensor_liveness_blocked.py"
RUN[2]="tests/test_hourly_rows_blocked.py"
RUN[3]="tests/test_substeps_blocked.py"
RUN[4]="tests/test_silent_sensor_hourly_commit.py"
RUN[5]="tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py"
RUN[6]="tests/test_live_estimate_silent_sensor.py"
RUN[7]="tests/test_live_estimate_silent_sensor_daily.py"
RUN[8]="tests/test_live_estimate_silent_sensor_daily.py"
RUN[9]="tests/test_sensor_liveness_coordinator.py"
declare -A K
K[5]="test_the_hourly_calculation_is_cut_the_same or test_a_pausing_group_under_the_hourly_switch_is_cut_too or test_under_the_hourly_calculation_too_they_are_no_longer_used or test_switching_the_hourly_calculation_leaves_the_notice_alone"
K[8]="Projection"
K[9]="TestTheEstimateFollowsTheRecord"
for n in 1 2 3 4 5 6 7 8 9; do
  prev=${SHA[$((n-1))]}
  cur=${SHA[$n]}
  cd "$R"
  git checkout -q --detach "$prev"
  git clean -fdq tests/
  files=$(git diff --name-only "$prev" "$cur" -- tests/)
  git checkout -q "$cur" -- $files
  kexpr=${K[$n]:-}
  if [ -n "$kexpr" ]; then
    out=$(TZ=UTC $PY -m pytest ${RUN[$n]} -p _local_socket_unblock -q --no-header -rf -k "$kexpr" 2>&1 | tr '\r' '\n')
  else
    out=$(TZ=UTC $PY -m pytest ${RUN[$n]} -p _local_socket_unblock -q --no-header -rf 2>&1 | tr '\r' '\n')
  fi
  summary=$(echo "$out" | grep -E "^=+ .*(passed|failed|error).* in " | tail -1)
  first=$(echo "$out" | grep -E "^E +[A-Za-z]+(Error|Exception)?:|^E +assert" | grep -v "Lingering" | head -2 | cut -c1-160)
  echo "T$n tests=[$files]"
  echo "   $summary"
  echo "$first" | sed 's/^/   /'
done
cd "$R" && git checkout -q --detach 6fa424e8 && git clean -fdq tests/
