#!/bin/bash
# Amendment 1 judging. (2') vs single A.X starts immediately; (1') and (3') wait for their matched outputs; (4') last.
cd /c/rbov2/revision/rbo_s_v1
judge () {
  for i in 0 1 2 3; do SHARD=$i/4 python gen_eval.py orig350 orig350_policies_select.jsonl ext:rbov2 $1 & done; wait
  python gen_eval.py orig350 orig350_policies_select.jsonl ext:rbov2 $1 || { echo JUDGE_HALT $1; exit 1; }
  echo COMPARISON_DONE $1
}
judge ext:v2single_ax7
until [ -f runs/orig350_ext_gpt4o_matched.jsonl ] && [ $(wc -l < runs/orig350_ext_gpt4o_matched.jsonl) -ge 350 ]; do sleep 20; done
judge ext:gpt4o_matched
until [ -f runs/orig350_ext_deepseek_matched.jsonl ] && [ $(wc -l < runs/orig350_ext_deepseek_matched.jsonl) -ge 350 ]; do sleep 20; done
judge ext:deepseek_matched
judge archived:rbo_v1_main
echo ALL_JUDGING_DONE
