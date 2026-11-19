
"""Druk Kha translation engine.

English question -> Groq answer -> CST Dzongkha
-> Romanized pronunciation -> English meaning.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, build_opener

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

CST_PAGE = "https://nlp.cst.edu.bt/nmt/"
CST_URL = "https://nlp.cst.edu.bt/nmt/api/"

KNOWN = {
    "hello": (
        "སྐུ་གཟུགས་བཟང་པོ་ལགས།",
        "Kuzuzangpo la",
        "Hello!",
    ),
    "hi": (
        "སྐུ་གཟུགས་བཟང་པོ་ལགས།",
        "Kuzuzangpo la",
        "Hello!",
    ),
}

DZONGKHA_PATTERN = re.compile(r"[\u0F00-\u0FFF]")


# ============================================================
# GROQ
# ============================================================

def _groq(messages, max_tokens=1500, temperature=0.3):
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing.")

    client = Groq(
        api_key=api_key,
        timeout=90.0,
    )

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", MODEL),
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max(max_tokens, 3000),
        reasoning_effort="low",
    )

    if not response.choices:
        raise RuntimeError("Groq returned no choices.")

    answer = response.choices[0].message.content

    if not answer or not answer.strip():
        raise RuntimeError(
            "Groq returned an empty answer."
        )

    return answer.strip()


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_english(text):
    """Prepare plain English for CST translation."""

    text = re.sub(
        r"[\u0F00-\u0FFF]+",
        " ",
        text,
    )

    replacements = {
        "\u2014": ", ",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "-",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[\x00-\x08\x0b-\x1f]",
        " ",
        text,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_sentences(text, max_chars=180):
    """Split long English answers into short pieces."""

    text = clean_english(text)

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    chunks = []

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(sentence) <= max_chars:
            chunks.append(sentence)
            continue

        current = ""

        for word in sentence.split():
            candidate = (
                current + " " + word
            ).strip()

            if (
                len(candidate) > max_chars
                and current
            ):
                chunks.append(current)
                current = word
            else:
                current = candidate

        if current:
            chunks.append(current)

    return chunks


# ============================================================
# CST HTTP REQUEST
# ============================================================

def _request_json(
    url,
    payload,
    headers,
    timeout=60,
    opener=None,
):
    request = urllib.request.Request(
        url,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        if opener is None:
            response = urllib.request.urlopen(
                request,
                timeout=timeout,
            )
        else:
            response = opener.open(
                request,
                timeout=timeout,
            )

        with response as resp:
            return json.loads(
                resp.read().decode("utf-8")
            )

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace",
        )[:300]

        raise RuntimeError(
            f"CST HTTP {exc.code}: {detail}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"CST network error: {exc.reason}"
        ) from exc


def _cst_translate_chunk(text):
    """Translate one short English section using CST."""

    opener = build_opener(
        HTTPCookieProcessor(CookieJar())
    )

    try:
        with opener.open(
            CST_PAGE,
            timeout=20,
        ) as response:
            page = response.read().decode(
                "utf-8",
                errors="replace",
            )

    except Exception as exc:
        raise RuntimeError(
            "Cannot reach CST website."
        ) from exc

    token_match = re.search(
        r'name=["\']csrfmiddlewaretoken["\']'
        r'\s+value=["\']([^"\']+)',
        page,
    )

    if not token_match:
        token_match = re.search(
            r'csrfmiddlewaretoken\s*:\s*'
            r'["\']([^"\']+)',
            page,
        )

    if not token_match:
        raise RuntimeError(
            "CST CSRF token not found."
        )

    token = token_match.group(1)

    result = _request_json(
        CST_URL,
        {
            "src_lang": "eng_Latn",
            "tgt_lang": "dzo_Tibt",
            "text": text,
            "csrfmiddlewaretoken": token,
        },
        {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
            "Referer": CST_PAGE,
        },
        opener=opener,
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "CST returned an unexpected response."
        )

    if result.get("error"):
        raise RuntimeError(
            f"CST: {result['error']}"
        )

    translated = result.get("text", "")

    if not isinstance(translated, str):
        translated = ""

    translated = translated.strip()

    if not DZONGKHA_PATTERN.search(translated):
        raise RuntimeError(
            "CST returned no Dzongkha translation."
        )

    return translated


# ============================================================
# BACKUP TRANSLATION
# ============================================================

def backup_translate(text, reference=""):
    """Use Groq if CST cannot translate a section."""

    prompt = (
        "Translate the supplied English into Bhutanese "
        "Dzongkha as used in Bhutan. "
        "Do not use Tibetan conversational grammar. "
        "Use natural Bhutanese Dzongkha wording. "
        "Do not explain anything. "
        "Output only the Dzongkha translation. "
        "Do not include English or pronunciation.\n\n"
        "Verified examples, if provided:\n"
        + reference
    )

    result = _groq(
        [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        max_tokens=1500,
        temperature=0.1,
    )

    if not DZONGKHA_PATTERN.search(result):
        raise RuntimeError(
            "Backup translation did not return "
            "Dzongkha script."
        )

    return result


def cst_translate(text, reference=""):
    """Translate with retries and controlled fallback."""

    chunks = split_sentences(text)

    if not chunks:
        raise RuntimeError(
            "No English answer to translate."
        )

    output = []

    for index, chunk in enumerate(chunks, 1):
        translated = None

        for attempt in range(2):
            try:
                translated = _cst_translate_chunk(
                    chunk
                )
                break

            except Exception as exc:
                print(
                    f"CST section {index}/{len(chunks)} "
                    f"attempt {attempt + 1}: {exc}"
                )

                if attempt == 0:
                    time.sleep(0.5)

        if translated is None:
            try:
                translated = backup_translate(
                    chunk,
                    reference,
                )

                print(
                    "WARNING: Groq backup translation "
                    f"used for section {index}. "
                    "Output needs human verification."
                )

            except Exception as exc:
                raise RuntimeError(
                    f"Translation failed at section "
                    f"{index}/{len(chunks)}: {exc}"
                ) from exc

        output.append(translated)

    return "\n".join(output)


# ============================================================
# PRONUNCIATION
# ============================================================

def romanize_dzongkha(dzongkha, reference=""):
    """Generate pronunciation using English letters."""

    sentences = [
        part.strip()
        for part in re.split(
            r"(?<=།)\s*",
            dzongkha,
        )
        if part.strip()
    ]

    if not sentences:
        sentences = [dzongkha]

    results = []

    for sentence in sentences:
        prompt = (
            "You are helping students pronounce "
            "spoken Bhutanese Dzongkha. "
            "Convert the supplied Dzongkha sentence "
            "into readable pronunciation using "
            "English alphabet letters only. "
            "Do not translate into English. "
            "Do not use Tibetan script. "
            "Do not use Wylie transliteration. "
            "Use Bhutanese spoken pronunciation. "
            "Preserve the meaning and word order. "
            "Output only the pronunciation text.\n\n"
            "Examples:\n"
            "སྐུ་གཟུགས་བཟང་པོ་ལགས། "
            "= Kuzuzangpo la\n"
            "བཀའ་དྲིན་ཆེ། "
            "= Kadrinche\n\n"
            "Additional verified examples:\n"
            + reference
        )

        try:
            roman = _groq(
                [
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": sentence,
                    },
                ],
                max_tokens=1800,
                temperature=0.1,
            )

            roman = roman.strip()

            # Remove accidental code fences.
            roman = re.sub(
                r"^```[a-zA-Z]*\s*|\s*```$",
                "",
                roman,
            ).strip()

            # Do not display Dzongkha script
            # inside the pronunciation field.
            if DZONGKHA_PATTERN.search(roman):
                return ""

            if not re.search(r"[A-Za-z]", roman):
                return ""

            results.append(roman)

        except Exception as exc:
            print(
                "Pronunciation error:",
                exc,
            )
            return ""

    return "\n".join(results)


# ============================================================
# CONVERSATION HISTORY
# ============================================================

def _history_messages(history):
    messages = []

    for turn in (history or [])[-10:]:
        role = turn.get("role")

        if role == "user":
            content = turn.get("english") or ""

        elif role == "assistant":
            content = turn.get("gloss") or ""

        else:
            continue

        if content:
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    return messages


# ============================================================
# MAIN TRANSLATION FUNCTION
# ============================================================

def translate(
    english: str,
    history=None,
    taught=None,
) -> dict:

    prompt = english.strip()

    if not prompt:
        raise RuntimeError(
            "Please enter a message."
        )

    key = re.sub(
        r"[.!?]+$",
        "",
        prompt.lower(),
    ).strip()

    # Use verified greeting.
    if key in KNOWN:
        dz, roman, gloss = KNOWN[key]

        return {
            "dzongkha": dz,
            "roman": roman,
            "gloss": gloss,
        }

    # Build verified phrase references.
    examples = []

    for row in (taught or [])[:12]:
        en = row.get("english", "")
        dz = row.get("dzongkha", "")

        if en and dz:
            examples.append(
                f"{en} -> {dz}"
            )

    reference = "\n".join(examples)

    # Reuse an approved phrase for exact matches.
    for row in (taught or []):
        saved_english = " ".join(
            row.get("english", "").lower().split()
        )

        current_english = " ".join(
            prompt.lower().split()
        )

        if saved_english == current_english:
            return {
                "dzongkha": row.get(
                    "dzongkha", ""
                ),
                "roman": row.get(
                    "roman", ""
                ),
                "gloss": row.get(
                    "gloss", prompt
                ),
            }

    # Step 1: Understand the question in English.
    system_prompt = (
        "You are Druk Kha, a helpful AI assistant "
        "for people in Bhutan. "
        "Answer the user's actual question in "
        "simple, clear English. "
        "Do not merely translate their question. "
        "Use short, natural sentences. "
        "Write entirely in English. "
        "Do not insert Dzongkha or Tibetan script. "
        "Avoid unusual punctuation, long paragraphs "
        "and complicated expressions. "
        "Provide accurate, useful answers. "
        "Keep simple questions concise."
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        *_history_messages(history),
        {
            "role": "user",
            "content": prompt,
        },
    ]

    english_answer = _groq(
        messages,
        max_tokens=1500,
    )

    # Step 2: Translate into Bhutanese Dzongkha.
    dzongkha = cst_translate(
        english_answer,
        reference,
    )

    # Step 3: Generate pronunciation.
    roman = romanize_dzongkha(
        dzongkha,
        reference,
    )

    # Step 4: Return all three fields.
    return {
        "dzongkha": dzongkha,
        "roman": roman,
        "gloss": english_answer,
    }
