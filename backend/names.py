"""Write personal names in Dzongkha script.

Known Bhutanese names use the traditional spelling. Other names are
written the way an English–Dzongkha translator reads them, syllable by syllable.
"""

from __future__ import annotations

import re

# Traditional spellings. The key is the usual English form.
KNOWN = {
    "tshering": "ཚེ་རིང་",
    "tshring": "ཚེ་རིང་",
    "dorji": "རྡོ་རྗེ་",
    "dorje": "རྡོ་རྗེ་",
    "karma": "ཀརྨ་",
    "wangchuk": "དབང་ཕྱུག་",
    "wangchuck": "དབང་ཕྱུག་",
    "wangmo": "དབང་མོ་",
    "sonam": "བསོད་ནམས་",
    "pema": "པདྨ་",
    "kinley": "ཀུན་ལེགས་",
    "kunley": "ཀུན་ལེགས་",
    "jigme": "འཇིགས་མེད་",
    "ugyen": "ཨོ་རྒྱན་",
    "tashi": "བཀྲ་ཤིས་",
    "dechen": "བདེ་ཆེན་",
    "deki": "བདེ་སྐྱིད་",
    "yangchen": "དབྱངས་ཅན་",
    "choden": "ཆོས་སྒྲོན་",
    "lhamo": "ལྷ་མོ་",
    "penjor": "དཔལ་འབྱོར་",
    "gyeltshen": "རྒྱལ་མཚན་",
    "gyaltsen": "རྒྱལ་མཚན་",
    "phuntsho": "ཕུན་ཚོགས་",
    "norbu": "ནོར་བུ་",
    "sangay": "སངས་རྒྱས་",
    "kuenga": "ཀུན་དགའ་",
    "yeshi": "ཡེ་ཤེས་",
    "yeshey": "ཡེ་ཤེས་",
    "rinzin": "རིག་འཛིན་",
    "dendup": "དོན་གྲུབ་",
    "dema": "བདེ་མ་",
    "chimi": "འཆི་མེད་",
    "kezang": "སྐལ་བཟང་",
    "kelzang": "སྐལ་བཟང་",
    "thinley": "འཕྲིན་ལས་",
    "namgay": "རྣམ་རྒྱལ་",
    "namgyal": "རྣམ་རྒྱལ་",
    "tshewang": "ཚེ་དབང་",
    "nima": "ཉི་མ་",
    "nyima": "ཉི་མ་",
    "dawa": "ཟླ་བ་",
    "zangmo": "བཟང་མོ་",
    "tenzin": "བསྟན་འཛིན་",
    "sherab": "ཤེས་རབ་",
    "arjun": "ཨར་ཇུན་",
    "rai": "རའི་",
    "thimphu": "ཐིམ་ཕུག་",
    "paro": "སྤ་རོ་",
    "punakha": "སྤུ་ན་ཁ་",
    "bumthang": "བུམ་ཐང་",
    "bhutan": "འབྲུག་",
}

ONSETS = (
    ("tsh", "ཚ"),
    ("chh", "ཆ"),
    ("ny", "ཉ"),
    ("ng", "ང"),
    ("zh", "ཞ"),
    ("sh", "ཤ"),
    ("ch", "ཅ"),
    ("th", "ཐ"),
    ("kh", "ཁ"),
    ("ph", "ཕ"),
    ("ts", "ཙ"),
    ("dz", "ཛ"),
    ("tr", "ཏྲ"),
    ("dr", "དྲ"),
    ("k", "ཀ"),
    ("g", "ག"),
    ("j", "ཇ"),
    ("t", "ཏ"),
    ("d", "ད"),
    ("n", "ན"),
    ("p", "པ"),
    ("b", "བ"),
    ("m", "མ"),
    ("z", "ཟ"),
    ("y", "ཡ"),
    ("r", "ར"),
    ("l", "ལ"),
    ("w", "ཝ"),
    ("v", "ཝ"),
    ("h", "ཧ"),
    ("s", "ས"),
    ("f", "ཕ"),
    ("c", "ཀ"),
)

VOWELS = (
    ("ai", "ai"),
    ("au", "au"),
    ("aa", "a"),
    ("ee", "i"),
    ("ii", "i"),
    ("oo", "u"),
    ("uu", "u"),
    ("a", "a"),
    ("e", "e"),
    ("i", "i"),
    ("o", "o"),
    ("u", "u"),
    ("y", "i"),
)

SIGNS = {"a": "", "i": "ི", "u": "ུ", "e": "ེ", "o": "ོ"}

CODAS = (
    ("ng", "ང"),
    ("n", "ན"),
    ("m", "མ"),
    ("r", "ར"),
    ("l", "ལ"),
    ("k", "ག"),
    ("p", "བ"),
    ("t", "ཏ"),
    ("d", "ད"),
    ("s", ""),
)


def _take(text: str, index: int, table: tuple[tuple[str, str], ...]) -> tuple[str, int] | None:
    for roman, script in table:
        if text.startswith(roman, index):
            return script, index + len(roman)
    return None


def _phonetic(word: str) -> str:
    text = word.lower()
    syllables: list[str] = []
    index = 0
    while index < len(text):
        if text[index] in "-'":
            index += 1
            continue
        start = index
        onset = _take(text, index, ONSETS)
        if onset:
            base, index = onset
        else:
            base = "ཨ"
        vowel = _take(text, index, VOWELS)
        if vowel:
            kind, index = vowel
        else:
            kind = "a"
        coda = _take(text, index, CODAS)
        ending = ""
        if coda:
            ending, index = coda
        if kind == "ai":
            piece = base + "འི" + ending
        elif kind == "au":
            piece = base + "ཽ" + ending
        else:
            piece = base + SIGNS[kind] + ending
        syllables.append(piece)
        if index == start:
            index += 1
    return "་".join(syllables) + "་"


def in_dzongkha(word: str) -> str:
    key = word.lower().strip("'-")
    if key in KNOWN:
        return KNOWN[key]
    return _phonetic(key)


def replace_english(text: str) -> str:
    """Turn any Latin word left inside a Dzongkha line into Dzongkha script."""

    def swap(match: re.Match[str]) -> str:
        return in_dzongkha(match.group(0))

    return re.sub(r"[A-Za-z][A-Za-z'\-]*", swap, text)
