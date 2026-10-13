#!/usr/bin/env bash
# Build the brief for task N: header + task text from the plan + notes/tN.md
set -euo pipefail
n=$1
S=/d/Entwicklung/HASI/issue8-pr2-work/sdd
PLAN=/d/Entwicklung/HASI/HAsmartirrigation/docs/superpowers/plans/2026-10-12-dead-weather-sensor-pr2.md
SK=/c/Users/Nutzer/.claude/plugins/cache/claude-plugins-official/superpowers/6.4.1/skills/subagent-driven-development/scripts
bash $SK/task-brief $PLAN $n $S/task-$n-plantext.md
{
  cat $S/header.md
  echo "## Hinweise für diesen Task"
  echo
  cat $S/notes/t$n.md
  echo
  echo "## Dein Task — Plantext, wörtlich"
  echo
  cat $S/task-$n-plantext.md
} > $S/task-$n-brief.md
echo "brief: $S/task-$n-brief.md ($(wc -l < $S/task-$n-brief.md) lines)"
