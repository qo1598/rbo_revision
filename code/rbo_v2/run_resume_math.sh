#!/bin/bash
# Resume HRM8K confirm after the user's pause (2026-09-27 evening); same fixed order, journals skip done items.
cd /c/rbov2/revision/rbo_v2
for a in "sc ax7 3" "single qwen8" "rbo midm2 ax7 midm2 hcx3" "sr ax7"; do python rbo_math.py confirm $a; done
echo MATH_DONE
