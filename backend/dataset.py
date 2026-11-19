"""English–Dzongkha lines from the OPUS Bhutanese corpus.

The file is data/opus_dz_en.tsv. The chat looks up similar lines and
shows them to the model so a wrong spelling can be replaced by the corpus form.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "opus_dz_en.tsv"
STOP = {
    "a", "an", "the", "of", "to", "and", "or", "in", "on", "for", "is", "are",
    "was", "be", "it", "this", "that", "with", "from", "at", "by", "as", "if",
    "you", "your", "i", "me", "my", "we", "do", "not", "no", "yes",
}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOP and len(w) > 1}


@lru_cache(maxsize=1)
def pairs() -> tuple[tuple[str, str], ...]:
    rows = []
    for line in PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "\t" not in line:
            continue
        english, dzongkha = line.split("\t", 1)
        english, dzongkha = english.strip(), dzongkha.strip()
        if english and dzongkha:
            rows.append((english, dzongkha))
    return tuple(rows)


def exact(english: str) -> str | None:
    key = re.sub(r"\s+", " ", english.strip().lower())
    hits = [dz for en, dz in pairs() if re.sub(r"\s+", " ", en.lower()) == key]
    if len(hits) == 1:
        return hits[0]
    return None


def similar(english: str, limit: int = 5) -> list[tuple[str, str]]:
    wanted = _words(english)
    if not wanted:
        return []
    scored: list[tuple[float, str, str]] = []
    for en, dz in pairs():
        have = _words(en)
        if not have:
            continue
        shared = wanted & have
        if not shared:
            continue
        score = len(shared) / len(wanted | have)
        if score < 0.34 and not wanted <= have:
            continue
        scored.append((score, en, dz))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [(en, dz) for _score, en, dz in scored[:limit]]
