#!/bin/bash
# Prespecified order (PROTOCOL_IFEVAL_EXT.md). Journals are resumable.
cd /c/rbov2/revision/rbo_v2
python rbo.py confirm L2 qwen8 ax7 qwen8 qwen8
python rbo.py confirm T2 midm2 ax7 midm2 hcx3
for m in qwen4 qwen1.7 qwen8 exaone2 midm2 hcx3 exaone8 ax7; do
  python run_single.py confirm $m
  python rbo.py confirm T2 $m $m $m $m
done
python rbo.py confirm T qwen8 ax7 qwen8 qwen8
echo ALL_DONE
# Amendment 1: resume the two crashed runs (journals resume)
python rbo.py confirm T2 midm2 ax7 midm2 hcx3
python rbo.py confirm T2 qwen4 qwen4 qwen4 qwen4
echo RESUME_DONE
# Amendment 2: resume the crashed single Qwen3-1.7B run
python run_single.py confirm qwen1.7
echo RESUME2_DONE
