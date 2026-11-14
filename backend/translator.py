"""Turn English into spoken Bhutanese Dzongkha.

The model is Grok. The instruction set forces Bhutanese Dzongkha (dzo),
not Central Tibetan. A few everyday lines are locked so they cannot drift.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from backend.dataset import exact as corpus_exact
from backend.dataset import similar as corpus_similar
from backend.textbook import TEXTBOOK

MODEL = "grok-4.5"
API_URL = "https://api.x.ai/v1/chat/completions"

SYSTEM = """You are Druk Kha, a Bhutanese assistant. The user writes in English. Understand the request, then answer in spoken Bhutanese Dzongkha as it is written in Bhutanese school books.

Do the task. Do not translate the instruction back.
- A greeting is answered with the greeting.
- "How do you say X" means translate X.
- "Write a poem about a flower" means write the poem about the flower (མེ་ཏོག་). The gloss is the English of that poem.

Writing rules, from Bhutanese orthography (traditional spelling, the form kept by the Dzongkha Development Commission grammar, not a phonetic respelling):
- Put a tsheg ་ between syllables: སྐུ་གཟུགས་ not སྐུགཟུགས and never ཀུ་ཟུ་.
- Put a space between words, as in printed Dzongkha.
- End every sentence and every line of a poem with a shad །
- A poem is one verse per line.
- No English letters inside the Dzongkha except a person's name.

Grammar, from The Grammar of Dzongkha (van Driem and Karma Tshering, Dzongkha Development Commission):
- Word order is subject, object, verb. Postpositions come after the noun.
- Identity, "am/is/are" a noun: ཨིན།  Negative མེན།  Question ཨིན་ན།
  ང་ སློབ་ཕྲུག་ ཨིན།  I am a student.
- Location, possession, and "how someone is": ཡོད།  Negative མེད།
  ང་ ལེགས་ཤོམ་ སྦེ་ ཡོད།  I am fine.
- Something the speaker has just seen can use འདུག།  Do not use it as a general "to be".
- "To" or "for": ལུ་    Agent "by": གིས་    Of: གི་    Manner: སྦེ་
- Infinitive "to do": verb + ནི་    འགྱོ་ནི་ to go, སླབ་ནི་ to say.
- Ongoing action: verb + དོ་ ཨིན། or verb + པའི་སྒང་ ཨིན།
- Completed action the speaker knows: verb + ཅི། or ཡི།
- Question words: ག་ཅི་ what, ག་ཏེ་ where, ག་དེ་ how, ག་དེམ་ཅིག་ how much, ག་ཨ་ who.
- Polite greeting and thanks take ལགས།
- Spell place names the school way: Thimphu ཐིམ་ཕུག་  Bhutan འབྲུག་  flower མེ་ཏོག་  student སློབ་ཕྲུག་  teacher སློབ་དཔོན་
- I ང་  you ཁྱོད་  he ཁོ་  she ཁོ་མོ་  we ང་བཅས་  this འདི་  that དེ་

Never write Tibetan:
- བཀའ་དྲིན་མེད།  ཐུགས་རྗེ་ཆེ།  ཁྱེད་རང་  ཡིན།  རེད།  ཡིན་པས།  ཡོད་པས།  ཡོད་རེད།  བདེ་པོ་ཡིན།  ཀུ་ཟུ་བཟང་པོ།

Fixed lines when that is really what they asked:
- Hello: སྐུ་གཟུགས་བཟང་པོ་ལགས། / Kuzuzangpo la
- How are you?: ཁྱོད་ག་དེ་སྦེ་ཡོད། / Chö gadey be yö?
- I am fine: ང་ལེགས་ཤོམ་སྦེ་ཡོད། / Nga lekshom be yö
- Thank you: བཀའ་དྲིན་ཆེ་ལགས། / Kadrinche la
- You're welcome: རྗེམ་པ་ལེགས་སོ། / Jembalaekso
- Yes: ཨིན། / Inn    No: མེན། / Men

"roman" is how a person in Bhutan reads the line aloud, with the same line breaks. Not Wylie.
"gloss" is the English of what you wrote.
Return only JSON: {"dzongkha":"...","roman":"...","gloss":"..."}"""

LOCKED = {
    "hello": ("སྐུ་གཟུགས་བཟང་པོ་ལགས།", "Kuzuzangpo la", "Hello."),
    "hi": ("སྐུ་གཟུགས་བཟང་པོ་ལགས།", "Kuzuzangpo la", "Hello."),
    "hey": ("སྐུ་གཟུགས་བཟང་པོ་ལགས།", "Kuzuzangpo la", "Hello."),
    "good morning": ("སྐུ་གཟུགས་བཟང་པོ་ལགས།", "Kuzuzangpo la", "Good morning."),
    "how are you": ("ཁྱོད་ག་དེ་སྦེ་ཡོད།", "Chö gadey be yö?", "How are you?"),
    "i am fine": ("ང་ལེགས་ཤོམ་སྦེ་ཡོད།", "Nga lekshom be yö", "I am fine."),
    "i'm fine": ("ང་ལེགས་ཤོམ་སྦེ་ཡོད།", "Nga lekshom be yö", "I am fine."),
    "thank you": ("བཀའ་དྲིན་ཆེ་ལགས།", "Kadrinche la", "Thank you."),
    "thanks": ("བཀའ་དྲིན་ཆེ་ལགས།", "Kadrinche la", "Thank you."),
    "thank you so much": ("བཀའ་དྲིན་ཆེ་ལགས།", "Kadrinche la", "Thank you so much."),
    "you're welcome": ("རྗེམ་པ་ལེགས་སོ།", "Jembalaekso", "You're welcome."),
    "you are welcome": ("རྗེམ་པ་ལེགས་སོ།", "Jembalaekso", "You're welcome."),
    "yes": ("ཨིན།", "Inn", "Yes."),
    "no": ("མེན།", "Men", "No."),
}

TIBETAN = (
    "བཀའ་དྲིན་མེད",
    "ཐུགས་རྗེ",
    "ཁྱེད་རང",
    "ཡིན་པས",
    "ཡོད་པས",
    "ཡོད་རེད",
    "བདེ་པོ་ཡིན",
    "ཀུ་ཟུ་བཟང",
)


def normalize(text: str) -> str:
    cleaned = text.strip().lower().replace("’", "'")
    cleaned = re.sub(r"[.!?]+$", "", cleaned).strip()
    return re.sub(r"\s+", " ", cleaned)


def _format_dzongkha(text: str) -> str:
    """School-book shape: tsheg stays, each line ends with a shad."""
    lines = [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]
    shaped = []
    for line in lines:
        line = re.sub(r"[ \t]+", " ", line)
        line = line.replace("༌", "་")
        if line.endswith("་"):
            line = line[:-1] + "།"
        elif not line.endswith(("།", "༎")):
            line += "།"
        shaped.append(line)
    return "\n".join(shaped)


def _pack(dzongkha: str, roman: str, gloss: str) -> dict:
    return {"dzongkha": _format_dzongkha(dzongkha), "roman": roman.strip(), "gloss": gloss.strip()}


def translate(english: str, history: list[dict] | None = None, taught: list[dict] | None = None) -> dict:
    key = normalize(english)
    for row in taught or []:
        if normalize(row["english"]) == key:
            return _pack(row["dzongkha"], row["roman"], row["gloss"])
    for sample, dzongkha, roman, gloss in TEXTBOOK:
        if normalize(sample) == key:
            return _pack(dzongkha, roman, gloss)
    if key in LOCKED:
        dzo, roman, gloss = LOCKED[key]
        return _pack(dzo, roman, gloss)
    known = corpus_exact(english)
    if known:
        return _pack(known, "", key[:1].upper() + key[1:] + ".")

    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("The language model key is missing. Add XAI_API_KEY and restart.")

    messages = [{"role": "system", "content": _system(taught or [])}]
    refs = corpus_similar(english)
    if refs:
        lines = "\n".join(f"- {en} → {dz}" for en, dz in refs)
        messages[0]["content"] += (
            "\n\nThese lines are from a downloaded Bhutanese Dzongkha corpus (OPUS). "
            "If the user asked for the same meaning, answer with that Dzongkha. "
            "Otherwise copy the spelling of any word that also appears there. "
            "Do not reply with a software menu unless they asked for one.\n"
            + lines
        )
    for turn in (history or [])[-6:]:
        if turn["role"] == "user":
            messages.append({"role": "user", "content": turn["english"]})
        elif turn.get("dzongkha"):
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "dzongkha": turn["dzongkha"],
                            "roman": turn.get("roman") or "",
                            "gloss": turn.get("gloss") or "",
                        },
                        ensure_ascii=False,
                    ),
                }
            )
    messages.append({"role": "user", "content": english.strip()})

    raw = _complete(api_key, messages)
    parsed = _parse(raw)
    if _bad(parsed["dzongkha"]) or _echoes_task(english, parsed):
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": (
                    "That did not do the task. If they asked for a poem or a description, "
                    "write that content in spoken Bhutanese Dzongkha. Do not translate their instruction. "
                    "A poem about a flower must mention the flower (མེ་ཏོག་). "
                    "The gloss must be the English of the poem or answer, not the instruction. "
                    "Never use Tibetan such as བཀའ་དྲིན་མེད། or ཐུགས་རྗེ་ཆེ།."
                ),
            }
        )
        parsed = _parse(_complete(api_key, messages))
    if _bad(parsed["dzongkha"]):
        raise RuntimeError("The model answered in Tibetan. Try the sentence again.")
    if _echoes_task(english, parsed):
        raise RuntimeError("The model repeated the request instead of answering it. Try once more.")
    return parsed


def _system(taught: list[dict]) -> str:
    book = "\n".join(
        f"- {english}: {dzongkha} / {roman}" for english, dzongkha, roman, _gloss in TEXTBOOK
    )
    text = SYSTEM + "\n\nCopy these spellings when the meaning is the same. Put a space between words:\n" + book
    if not taught:
        return text
    lines = "\n".join(
        f"- {row['english']}: {row['dzongkha']} / {row['roman']}" for row in taught[:40]
    )
    return text + "\n\nAdmin-taught lines. Use these exactly when the English matches:\n" + lines


def _complete(api_key: str, messages: list[dict]) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "temperature": 0.7,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
    ).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=70) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:240]
        raise RuntimeError(f"The model did not answer ({exc.code}). {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach the language model. Check the internet and try again.") from exc
    return body["choices"][0]["message"]["content"]


def _parse(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The model sent a reply that could not be read.") from exc
    dzongkha = str(data.get("dzongkha") or "").strip()
    roman = str(data.get("roman") or "").strip()
    gloss = str(data.get("gloss") or "").strip()
    if not dzongkha:
        raise RuntimeError("The model sent an empty Dzongkha line.")
    return _pack(dzongkha, roman, gloss)


TASK = re.compile(
    r"\b(write|poem|story|describe|explain|tell|about|compose|sing|essay|paragraph|joke)\b",
    re.I,
)


def _bad(dzongkha: str) -> bool:
    return any(marker in dzongkha for marker in TIBETAN)


def _echoes_task(english: str, parsed: dict) -> bool:
    if not TASK.search(english):
        return False
    gloss = normalize(parsed.get("gloss") or "")
    key = normalize(english)
    if not gloss:
        return True
    return gloss == key or key in gloss
