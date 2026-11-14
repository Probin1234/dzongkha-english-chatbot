"""Druk Kha. Streamlit chat. English in, Bhutanese Dzongkha out."""

from __future__ import annotations

import html
import streamlit as st

from backend import database as db
from backend.dataset import pairs as corpus_pairs
from backend.translator import translate

st.set_page_config(page_title="Druk Kha", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Tibetan:wght@600&family=Source+Sans+3:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: "Source Sans 3", "Segoe UI", sans-serif; }
#MainMenu, footer, [data-testid="stAppDeployButton"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 820px; padding-top: 1.6rem; padding-bottom: 7rem; }
section[data-testid="stSidebar"] { background: #141414; border-right: 1px solid #262626; }
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background: transparent; border: 1px solid transparent; text-align: left; font-weight: 500;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover { background: #222; }
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
  background: #c56a12; border: none; color: #fff;
}
.brand { font-weight: 700; font-size: 1.25rem; letter-spacing: -0.03em; }
.brand small { display: block; color: #e08a2c; font-size: 0.68rem; letter-spacing: 0.18em; font-weight: 700; }
.lede { color: #a3a3a3; line-height: 1.5; }
.dzo { font-family: "Noto Serif Tibetan", serif; font-size: 1.65rem; line-height: 1.85; margin: 0.15rem 0 0.45rem; white-space: pre-wrap; }
.line { color: #cfcfcf; margin: 0.2rem 0; white-space: pre-wrap; font-size: 0.95rem; }
.line b { color: #fff; font-weight: 600; }
.turn { display: flex; width: 100%; margin: 1rem 0 0.25rem; }
.turn.user { justify-content: flex-end; }
.turn.bot { justify-content: flex-start; }
.bubble { max-width: min(80%, 580px); }
.turn.user .bubble {
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 18px 18px 4px 18px;
  padding: 0.65rem 0.95rem 0.75rem;
}
.turn.bot .bubble { padding-right: 0.4rem; }
.who { font-size: 0.68rem; letter-spacing: 0.12em; color: #8d8d8d; margin: 0 0 0.3rem; font-weight: 600; }
.turn.user .who { text-align: right; }
.empty { padding-top: 8vh; }
.card {
  border: 1px solid #2c2c2c;
  background: #1b1b1b;
  border-radius: 16px;
  padding: 1rem 1.1rem;
  margin: 0.7rem 0;
}
.gate { max-width: 440px; margin: 8vh auto 0; }
[data-testid="stForm"] {
  background: #1b1b1b;
  border: 1px solid #2e2e2e;
  border-radius: 16px;
  padding: 0.6rem 1rem 1rem;
}
[data-testid="stChatInput"] { padding-bottom: 0.6rem; }
</style>
""",
    unsafe_allow_html=True,
)


def boot() -> None:
    db.init_db()
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("view", "chat")
    st.session_state.setdefault("chat_id", None)


def account(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}


def gate() -> None:
    st.markdown(
        '<div class="gate"><div class="brand"><small>BHUTAN</small>Druk Kha</div>'
        '<p class="lede">Write in English. The answer is spoken Bhutanese Dzongkha, then the pronunciation, then the meaning.</p></div>',
        unsafe_allow_html=True,
    )
    mode = st.radio("Account", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed")
    if mode == "Sign in":
        with st.form("login"):
            email = st.text_input("Email", placeholder="you@email.com")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", use_container_width=True)
        if go:
            row = db.authenticate(email, password)
            if row is None:
                st.error("Email or password is wrong.")
            else:
                st.session_state.user = account(row)
                st.session_state.chat_id = None
                st.session_state.view = "chat"
                st.rerun()
        st.markdown(
            f'<p class="lede">Admin<br><code>{db.ADMIN_EMAIL}</code> · {db.ADMIN_PASSWORD}<br>'
            f'Test<br><code>{db.TEST_EMAIL}</code> · {db.TEST_PASSWORD}</p>',
            unsafe_allow_html=True,
        )
        return

    with st.form("signup"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        again = st.text_input("Confirm password", type="password")
        go = st.form_submit_button("Create account", use_container_width=True)
    if go:
        if password != again:
            st.error("Those passwords do not match.")
            return
        error = db.create_user(name, email, password)
        if error:
            st.error(error)
            return
        st.session_state.user = account(db.authenticate(email, password))
        st.session_state.chat_id = None
        st.rerun()


def sidebar(user: dict) -> None:
    with st.sidebar:
        st.markdown('<div class="brand"><small>BHUTAN</small>Druk Kha</div>', unsafe_allow_html=True)
        st.caption(user["name"])
        st.caption(f"{len(corpus_pairs())} Dzongkha lines loaded for spelling")
        if st.button("New chat", use_container_width=True, type="primary"):
            st.session_state.chat_id = None
            st.session_state.view = "chat"
            st.rerun()
        if st.button("Phrasebook", use_container_width=True):
            st.session_state.view = "phrases"
            st.rerun()
        if user["role"] == "admin" and st.button("Admin desk", use_container_width=True):
            st.session_state.view = "admin"
            st.rerun()
        st.markdown('<p class="who">CHATS</p>', unsafe_allow_html=True)
        chats = db.list_chats(user["id"])
        if not chats:
            st.caption("No chats yet.")
        for chat in chats:
            active = chat["id"] == st.session_state.chat_id and st.session_state.view == "chat"
            label = f"●  {chat['title']}" if active else chat["title"]
            cols = st.columns([5, 1])
            if cols[0].button(label, key=f"open-{chat['id']}", use_container_width=True):
                st.session_state.chat_id = chat["id"]
                st.session_state.view = "chat"
                st.rerun()
            if cols[1].button("×", key=f"del-{chat['id']}", help="Delete chat"):
                db.delete_chat(chat["id"], user["id"])
                if st.session_state.chat_id == chat["id"]:
                    st.session_state.chat_id = None
                st.rerun()
        st.divider()
        if st.button("Log out", use_container_width=True):
            st.session_state.user = None
            st.session_state.chat_id = None
            st.rerun()


def show_answer(dzongkha: str, roman: str, gloss: str) -> None:
    parts = [f'<p class="dzo">{html.escape(dzongkha)}</p>']
    if roman:
        parts.append(f'<p class="line"><b>Pronunciation</b><br>{html.escape(roman)}</p>')
    if gloss:
        parts.append(f'<p class="line"><b>Meaning</b><br>{html.escape(gloss)}</p>')
    st.markdown(
        '<div class="turn bot"><div class="bubble"><p class="who">DRUK KHA</p>'
        + "".join(parts)
        + "</div></div>",
        unsafe_allow_html=True,
    )


def show_user(text: str) -> None:
    st.markdown(
        '<div class="turn user"><div class="bubble"><p class="who">YOU</p>'
        f'<p style="margin:0">{html.escape(text)}</p></div></div>',
        unsafe_allow_html=True,
    )


def send(user: dict, text: str) -> None:
    text = text.strip()
    if not text:
        return
    history = []
    if st.session_state.chat_id:
        history = db.get_messages(st.session_state.chat_id, user["id"])
    try:
        result = translate(text, history, db.glossary())
    except RuntimeError as exc:
        st.session_state.error = str(exc)
        return
    if st.session_state.chat_id is None:
        title = text if len(text) <= 42 else text[:42].rstrip() + "…"
        st.session_state.chat_id = db.create_chat(user["id"], title)
    chat_id = st.session_state.chat_id
    db.add_message(chat_id, "user", english=text)
    db.add_message(
        chat_id,
        "assistant",
        english=text,
        dzongkha=result["dzongkha"],
        roman=result["roman"],
        gloss=result["gloss"],
    )
    st.session_state.error = None


def chat(user: dict) -> None:
    rows = []
    if st.session_state.chat_id:
        rows = db.get_messages(st.session_state.chat_id, user["id"])
    saved = {item["dzongkha"] for item in db.list_phrases(user["id"])}
    if not rows:
        st.markdown(
            '<div class="empty"><p class="dzo">སྐུ་གཟུགས་བཟང་པོ་ལགས།</p>'
            "<p class=\"lede\">Kuzuzangpo la. Ask a question, or ask for a poem. "
            "Your words stay on the right. Dzongkha stays on the left.</p></div>",
            unsafe_allow_html=True,
        )
        picks = ["Hello", "How are you?", "Write a short poem about a flower", "How much is this?"]
        cols = st.columns(2)
        for index, label in enumerate(picks):
            if cols[index % 2].button(label, use_container_width=True):
                send(user, label)
                st.rerun()
    else:
        for row in rows:
            if row["role"] == "user":
                show_user(row["english"] or "")
                continue
            show_answer(row["dzongkha"], row["roman"] or "", row["gloss"] or "")
            already = row["dzongkha"] in saved
            save, _rest = st.columns([1, 3])
            if save.button(
                "Saved" if already else "Save to phrasebook",
                key=f"save-{row['id']}",
                disabled=already,
            ):
                db.save_phrase(
                    user["id"],
                    row["english"] or "",
                    row["dzongkha"],
                    row["roman"] or "",
                    row["gloss"] or "",
                )
                st.rerun()
    if st.session_state.get("error"):
        st.error(st.session_state.error)
    prompt = st.chat_input("Write in English")
    if prompt:
        send(user, prompt)
        st.rerun()


def phrasebook(user: dict) -> None:
    st.markdown('<div class="brand"><small>SAVED</small>Phrasebook</div>', unsafe_allow_html=True)
    items = db.list_phrases(user["id"])
    book = [item for item in items if item.get("kind") == "textbook"]
    mine = [item for item in items if item.get("kind") != "textbook"]
    st.markdown(
        f'<p class="lede">The grammar set is saved here ({len(book)} lines). '
        "Your own saves are underneath.</p>",
        unsafe_allow_html=True,
    )
    st.markdown('<p class="who">FROM THE GRAMMAR</p>', unsafe_allow_html=True)
    _phrase_cards(user, book, allow_remove=False)
    st.markdown('<p class="who">YOURS</p>', unsafe_allow_html=True)
    if not mine:
        st.markdown(
            '<div class="card"><p class="lede">Nothing of yours yet. In a chat, press Save to phrasebook.</p></div>',
            unsafe_allow_html=True,
        )
        return
    _phrase_cards(user, mine, allow_remove=True)


def _phrase_cards(user: dict, items: list, allow_remove: bool) -> None:
    for item in items:
        st.markdown(
            '<div class="card">'
            f'<p class="who">{html.escape(item["english"] or "")}</p>'
            f'<p class="dzo">{html.escape(item["dzongkha"])}</p>'
            f'<p class="line"><b>Pronunciation</b><br>{html.escape(item["roman"] or "")}</p>'
            f'<p class="line"><b>Meaning</b><br>{html.escape(item["gloss"] or "")}</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        if allow_remove and st.button("Remove", key=f"drop-{item['id']}"):
            db.delete_phrase(item["id"], user["id"])
            st.rerun()


def admin(user: dict) -> None:
    st.markdown('<div class="brand"><small>ADMIN</small>Desk</div>', unsafe_allow_html=True)
    numbers = db.stats()
    one, two, three = st.columns(3)
    one.metric("People", numbers["users"])
    two.metric("Chats", numbers["chats"])
    three.metric("Replies", numbers["replies"])

    st.subheader("Accounts")
    people = db.list_users()
    st.dataframe(
        [{"Name": p["name"], "Email": p["email"], "Role": p["role"], "Joined": p["created_at"]} for p in people],
        use_container_width=True,
        hide_index=True,
    )
    students = [p for p in people if p["role"] != "admin"]
    if students:
        labels = {f"{p['name']} · {p['email']}": p["id"] for p in students}
        picked = st.selectbox("Remove a student account", list(labels))
        if st.button("Delete this account"):
            error = db.delete_user(labels[picked], user["id"])
            if error:
                st.error(error)
            else:
                st.success("Removed.")
                st.rerun()

    st.subheader("Teach a phrase")
    st.caption("Saved here, this English line always gets your Dzongkha. Use real spelling, not ཀུ་ཟུ་བཟང་པོ།.")
    with st.form("teach"):
        english = st.text_input("English")
        dzongkha = st.text_input("Dzongkha")
        roman = st.text_input("Pronunciation")
        gloss = st.text_input("Meaning")
        if st.form_submit_button("Save phrase"):
            error = db.add_glossary(english, dzongkha, roman, gloss)
            if error:
                st.error(error)
            else:
                st.success("Saved.")
                st.rerun()
    taught = db.glossary()
    if taught:
        st.dataframe(taught, use_container_width=True, hide_index=True)

    st.subheader("Recent replies")
    recent = db.recent_replies()
    if recent:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.caption("No replies yet.")


def main() -> None:
    boot()
    user = st.session_state.user
    if not user:
        gate()
        return
    sidebar(user)
    if st.session_state.view == "admin" and user["role"] == "admin":
        admin(user)
    elif st.session_state.view == "phrases":
        phrasebook(user)
    else:
        chat(user)


main()
