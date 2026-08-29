#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$(dirname "$0")" || exit 1

printf '\n=== AUTO Android Vision Probe ===\n'
printf 'Project: kentcacho090-netizen/gg\n\n'

python android_vision_probe.py --download-model
status=$?

printf '\nProbe exit code: %s\n' "$status"
printf 'Screenshot: %s/autoc_test.png\n' "$PWD"
printf 'If YOLO is reported as a native crash, do NOT repeatedly rerun it;\nwe will switch the model runtime rather than chasing a Termux segfault.\n'
exit "$status"
