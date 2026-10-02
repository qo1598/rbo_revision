#!/bin/bash
cd /c/rbov2/revision/rbo_v2
for T in qa math; do
  S=rbo_$T.py
  python $S confirm single ax7
  python $S confirm rbo qwen8 ax7 qwen8 qwen8
  python $S confirm sc ax7 3
  python $S confirm single qwen8
  python $S confirm rbo midm2 ax7 midm2 hcx3
  python $S confirm sr ax7
done
echo ALL_DONE
