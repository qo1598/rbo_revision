"""Pinned KLUE-MRC-compatible scoring plus explicit sensitivity metrics.

The official implementation is preserved byte-for-byte in
``official_klue_metrics_utils.py`` from KLUE-baseline commit 8a03c944... .
This wrapper does not extract spans from verbose generations.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from official_klue_metrics_utils import (
    compute_em_and_rouge_w_score_for_klue_mrc,
    normalize_answer_for_klue_mrc,
)

OFFICIAL_COMMIT = "8a03c9447e4c225e806877a84242aea11258c790"
OFFICIAL_SOURCE_SHA256 = "6ec7e78e0e9687f1601058d23f3e270c281aaa3f3cf9db686705e0ebb723221c"


def normalize(text: str) -> str:
    return normalize_answer_for_klue_mrc(str(text))


def official_scores(prediction: str, references: Iterable[str]) -> dict[str, float]:
    refs = [normalize(x) for x in references]
    if not refs:
        refs = [""]
    em, rouge_w = compute_em_and_rouge_w_score_for_klue_mrc(normalize(prediction), refs)
    return {"em": float(em), "rouge_w": float(rouge_w)}


def _multiset_f1(pred_tokens: list[str], ref_tokens: list[str]) -> float:
    if not pred_tokens and not ref_tokens:
        return 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0
    overlap = sum((Counter(pred_tokens) & Counter(ref_tokens)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def character_f1(prediction: str, references: Iterable[str], *, include_spaces: bool = False) -> float:
    """Maximum multiset Unicode-character F1 after official normalization.

    This is a named sensitivity metric, not KLUE ROUGE-W. By default normalized
    ASCII spaces are removed so Korean spacing variants do not dominate it.
    """
    pred = normalize(prediction)
    if not include_spaces:
        pred = pred.replace(" ", "")
    refs = list(references) or [""]
    values = []
    for ref in refs:
        text = normalize(ref)
        if not include_spaces:
            text = text.replace(" ", "")
        values.append(_multiset_f1(list(pred), list(text)))
    return max(values)


def score(prediction: str, references: Iterable[str]) -> dict[str, float]:
    references = list(references)
    return {**official_scores(prediction, references),
            "character_f1_no_spaces": character_f1(prediction, references, include_spaces=False),
            "character_f1_with_spaces": character_f1(prediction, references, include_spaces=True)}

