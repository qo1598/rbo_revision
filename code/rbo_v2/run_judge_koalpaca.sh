#!/bin/bash
# PROTOCOL_KOALPACA350.md: comparisons (1)-(3) in fixed order, 4 parallel cache-filling shards each, then the full write.
# Stops after (3) for the budget checkpoint. gen_judge fails closed on 401/402/403/429.
cd /c/rbov2/revision/rbo_s_v1
for comp in archived:gpt4o_archived archived:deepseek_archived archived:rbo_v1_main; do
  for i in 0 1 2 3; do SHARD=$i/4 python gen_eval.py orig350 orig350_policies_select.jsonl ext:rbov2 $comp & done
  wait
  python gen_eval.py orig350 orig350_policies_select.jsonl ext:rbov2 $comp || { echo JUDGE_HALT $comp; exit 1; }
  echo COMPARISON_DONE $comp
done
echo CHECKPOINT_AFTER_3
