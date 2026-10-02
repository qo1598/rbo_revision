#!/bin/bash
# Reorder (2026-09-27, user request): when KorQuAD confirm finishes, pause the chain before HRM8K, generate KoAlpaca350,
# then resume HRM8K. Order change only; journals resume.
cd /c/rbov2/revision/rbo_v2
until [ -f runs/korquad_sr_ax7.jsonl ] && [ $(wc -l < runs/korquad_sr_ax7.jsonl) -ge 950 ]; do sleep 20; done
for pid in $(ps -W | grep -E "bash|python" | awk '{print $1}'); do :; done
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'run_mathqa.sh' -or \$_.CommandLine -match 'rbo_math.py confirm' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }"
echo KORQUAD_DONE_CHAIN_PAUSED
python run_koalpaca.py single
python run_koalpaca.py rbo
echo KOALPACA_GEN_DONE
for a in "single ax7" "rbo qwen8 ax7 qwen8 qwen8" "sc ax7 3" "single qwen8" "rbo midm2 ax7 midm2 hcx3" "sr ax7"; do python rbo_math.py confirm $a; done
echo MATH_DONE
