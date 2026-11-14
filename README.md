# Dzongkha English Chatbot

A small website where you type in English and the reply comes back in spoken Bhutanese Dzongkha, with the pronunciation and the English meaning under it.

The repository name stays `dzongkha-english-chatbot`.

## Run it

You need Python 3.10 or newer, and an [xAI API key](https://console.x.ai/).

```bash
git clone https://github.com/Probin1234/dzongkha-english-chatbot.git
cd dzongkha-english-chatbot
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
$env:XAI_API_KEY = "your-key"
streamlit run app.py
```

Mac or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
export XAI_API_KEY="your-key"
streamlit run app.py
```

Streamlit prints a local address, usually http://localhost:8501. Open that in the browser.

## Sign in

| Role | Email | Password |
|---|---|---|
| Admin | 03230235@gmail.com | admin101 |
| Test | test1@gmail.com | test101 |

You can also create a new account from the sign-in page. The admin desk lists accounts, recent replies, and phrases the admin has taught.

## What you can do

- Your English stays on the right. The Dzongkha stays on the left.
- Start a new chat. Older chats stay in the sidebar.
- Save a reply into your phrasebook.
- The grammar set (greetings, pronouns, and short sentences) is already in the phrasebook.

## How a reply is chosen

1. If the English matches a line an admin taught, or a line in the grammar set, that Dzongkha is used.
2. If the English matches the downloaded corpus, that Dzongkha is used.
3. Otherwise Grok 4.5 writes the answer. The closest corpus lines are sent with the question so the spelling can follow Bhutanese usage.

Everyday lines are fixed so they cannot drift:

- Hello is སྐུ་གཟུགས་བཟང་པོ་ལགས། (Kuzuzangpo la)
- You're welcome is རྗེམ་པ་ལེགས་སོ། (Jembalaekso)

The writing follows school spelling: a tsheg between syllables, a space between words, and a shad at the end of a sentence. Tibetan forms such as བཀའ་དྲིན་མེད། and ཐུགས་རྗེ་ཆེ། are rejected.

## Files

```
app.py                      pages: sign in, chat, phrasebook, admin
backend/database.py         accounts, chats, phrasebook
backend/translator.py       calls the model and checks the spelling
backend/textbook.py         grammar lines saved into every phrasebook
backend/dataset.py          looks up the corpus
data/opus_dz_en.tsv         577 English–Dzongkha lines
data/opus_dz_en.SOURCE.txt  where those lines came from
requirements.txt
```

Accounts and chats are stored in `data/druk.db`. That file is created on first run and is not part of the repository.

## Corpus

The parallel lines come from OPUS (Tiedemann, 2012): Ubuntu localization v14.10, GNOME localization v1, and the OPUS-100 English–Dzongkha set. They are Bhutanese Dzongkha, not Central Tibetan. See `data/opus_dz_en.SOURCE.txt`.
