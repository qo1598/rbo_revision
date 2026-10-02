#!/bin/bash
# Resume after the user's 1-hour pause (2026-09-26 ~22:50). Same prespecified order as run_ext.sh; journals skip done items.
cd /c/rbov2/revision/rbo_v2
python rbo.py confirm T2 ax7 ax7 ax7 ax7
python rbo.py confirm T qwen8 ax7 qwen8 qwen8
python rbo.py confirm T2 midm2 ax7 midm2 hcx3
python rbo.py confirm T2 qwen4 qwen4 qwen4 qwen4
python run_single.py confirm qwen1.7
echo ALL_RESUME_DONE
