# IFEval-Ko split note (2026-09-26)

- Initial split: dev 101 / confirm 241 (`SPLIT_IFEVAL.superseded_dev101.json`).
- Before any design decision, the user asked to shrink dev to 50 to enlarge confirm. New split: dev 50 / confirm 292
  (`SPLIT_IFEVAL.json`); same salt and ordering, new dev is a strict subset of the old dev (asserted in code).
- At the time of the change only single-A.X baseline outputs existed (24 items, official prompt, greedy).
  11 of them are now confirm items. They were not used for any design choice; the researcher saw the strict
  pass/fail of a few of them in a progress printout. They are kept (greedy decoding reproduces them).
- Journals are keyed by item id and are split-agnostic (`runs/ifeval_<policy>.jsonl`).
