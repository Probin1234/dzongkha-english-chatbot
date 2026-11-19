
"""Druk Kha - English to Bhutanese Dzongkha AI Chatbot.

Features:
- Immediate user-message display
- AI thinking/loading indicator
- Dzongkha response, pronunciation and English meaning
- Login and registration
- Chat history
- Phrasebook
- Admin dashboard
- Human review of suspected Tibetan-style expressions
"""

from __future__ import annotations

import html
import streamlit as st

from backend import database as db
from backend.dataset import pairs as corpus_pairs
from backend.translator import translate

# Requires backend/language_review.py from the previous step.
from backend import language_review as review


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Druk Kha",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Tibetan:wght@400;500;600&family=Source+Sans+3:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: "Source Sans 3", "Segoe UI", sans-serif;
}

#MainMenu, footer, [data-testid="stAppDeployButton"] {
    display: none;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1050px;
    padding-top: 1.5rem;
    padding-bottom: 7rem;
}

/* SIDEBAR */

section[data-testid="stSidebar"] {
    background: #141414;
    border-right: 1px solid #282828;
}

section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: transparent;
    border: 1px solid transparent;
    text-align: left;
}

section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: #262626;
}

section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: #c56a12;
    color: white;
    border: none;
}

/* BRAND */

.brand {
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: -0.03em;
}

.brand small {
    display: block;
    color: #e08a2c;
    font-size: 0.68rem;
    letter-spacing: 0.18em;
    font-weight: 700;
}

.lede {
    color: #aaa;
    line-height: 1.6;
}

.who {
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    color: #969696;
    font-weight: 700;
    margin: 0 0 0.5rem;
}

/* CHAT MESSAGES */

.turn {
    display: flex;
    width: 100%;
    margin: 1.1rem 0;
}

.turn.user {
    justify-content: flex-end;
}

.turn.bot {
    justify-content: flex-start;
}

/* USER MESSAGE - CHATGPT STYLE */

.turn.user .bubble {
    background: #303030;
    border: 1px solid #3b3b3b;
    border-radius: 22px;
    padding: 0.8rem 1.15rem;
    width: fit-content;
    max-width: 75%;
    overflow-wrap: anywhere;
}

.user-text {
    color: #f5f5f5;
    font-size: 1rem;
    line-height: 1.6;
    white-space: pre-wrap;
    margin: 0;
}

/* BOT RESPONSE */

.turn.bot .bubble {
    background: #1b1b1b;
    border: 1px solid #303030;
    border-radius: 17px;
    padding: 1.2rem 1.5rem;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    overflow-wrap: anywhere;
}

.reply-label {
    color: #e9e9e9;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 0.6rem;
}

.dzo {
    font-family: "Noto Serif Tibetan", serif;
    font-size: 1.22rem;
    font-weight: 400;
    line-height: 1.9;
    color: #f5f5f5;
    margin: 0.2rem 0 0.8rem;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.line {
    font-size: 0.94rem;
    line-height: 1.75;
    color: #c9c9c9;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 0;
}

.line b {
    color: white;
}

.reply-divider {
    height: 1px;
    background: #343434;
    margin: 1.1rem 0;
}

/* LOADING INDICATOR */

.thinking {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 1rem 0.5rem;
    color: #bdbdbd;
    font-size: 0.92rem;
}

.thinking-dots {
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.thinking-dots span {
    width: 7px;
    height: 7px;
    background: #d98b39;
    border-radius: 50%;
    animation: thinking-pulse 1.2s infinite ease-in-out;
}

.thinking-dots span:nth-child(2) {
    animation-delay: 0.2s;
}

.thinking-dots span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes thinking-pulse {
    0%, 60%, 100% {
        opacity: 0.3;
        transform: scale(0.8);
    }
    30% {
        opacity: 1;
        transform: scale(1.15);
    }
}

/* PHRASEBOOK AND FORMS */

.card {
    border: 1px solid #303030;
    background: #1b1b1b;
    border-radius: 16px;
    padding: 1rem 1.1rem;
    margin: 0.7rem 0;
}

.gate {
    max-width: 440px;
    margin: 8vh auto 0;
}

[data-testid="stForm"] {
    background: #1b1b1b;
    border: 1px solid #303030;
    border-radius: 16px;
    padding: 0.6rem 1rem 1rem;
}

[data-testid="stChatInput"] {
    padding-bottom: 0.6rem;
}

/* MOBILE */

@media (max-width: 768px) {
    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    .turn.user .bubble {
        max-width: 90%;
    }

    .turn.bot .bubble {
        padding: 1rem;
    }

    .dzo {
        font-size: 1.05rem;
        line-height: 1.9;
    }

    .line {
        font-size: 0.88rem;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# INITIALIZE APPLICATION
# ============================================================

def boot():
    db.init_db()
    review.init_review()

    st.session_state.setdefault("user", None)
    st.session_state.setdefault("view", "chat")
    st.session_state.setdefault("chat_id", None)
    st.session_state.setdefault("pending_message", None)
    st.session_state.setdefault("error", None)


def account(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
    }


# ============================================================
# LOGIN AND SIGNUP
# ============================================================

def gate():
    st.markdown(
        '<div class="gate">'
        '<div class="brand">'
        '<small>BHUTAN</small>Druk Kha'
        '</div>'
        '<p class="lede">'
        'Write in English and receive answers in Bhutanese '
        'Dzongkha with pronunciation and English meaning.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Account",
        ["Sign in", "Create account"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "Sign in":
        with st.form("login"):
            email = st.text_input(
                "Email",
                placeholder="you@email.com",
            )
            password = st.text_input(
                "Password",
                type="password",
            )
            go = st.form_submit_button(
                "Sign in",
                use_container_width=True,
            )

        if go:
            row = db.authenticate(email, password)

            if row is None:
                st.error("Email or password is wrong.")
            else:
                st.session_state.user = account(row)
                st.session_state.chat_id = None
                st.session_state.pending_message = None
                st.session_state.view = "chat"
                st.rerun()

        return

    with st.form("signup"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input(
            "Password",
            type="password",
        )
        again = st.text_input(
            "Confirm password",
            type="password",
        )

        go = st.form_submit_button(
            "Create account",
            use_container_width=True,
        )

    if go:
        if password != again:
            st.error("Those passwords do not match.")
            return

        error = db.create_user(
            name,
            email,
            password,
        )

        if error:
            st.error(error)
            return

        row = db.authenticate(email, password)

        st.session_state.user = account(row)
        st.session_state.chat_id = None
        st.session_state.pending_message = None
        st.session_state.view = "chat"
        st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

def sidebar(user):
    with st.sidebar:
        st.markdown(
            '<div class="brand">'
            '<small>BHUTAN</small>Druk Kha'
            '</div>',
            unsafe_allow_html=True,
        )

        st.caption(user["name"])

        st.caption(
            f"{len(corpus_pairs())} Dzongkha lines "
            "loaded for spelling"
        )

        if st.button(
            "New chat",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.chat_id = None
            st.session_state.pending_message = None
            st.session_state.error = None
            st.session_state.view = "chat"
            st.rerun()

        if st.button(
            "Phrasebook",
            use_container_width=True,
        ):
            st.session_state.pending_message = None
            st.session_state.view = "phrases"
            st.rerun()

        if user["role"] == "admin":
            if st.button(
                "Admin desk",
                use_container_width=True,
            ):
                st.session_state.pending_message = None
                st.session_state.view = "admin"
                st.rerun()

        st.markdown(
            '<p class="who">CHATS</p>',
            unsafe_allow_html=True,
        )

        chats = db.list_chats(user["id"])

        if not chats:
            st.caption("No chats yet.")

        for chat_item in chats:
            active = (
                chat_item["id"] == st.session_state.chat_id
                and st.session_state.view == "chat"
            )

            label = chat_item["title"]

            if active:
                label = "●  " + label

            cols = st.columns([5, 1])

            if cols[0].button(
                label,
                key=f"open-{chat_item['id']}",
                use_container_width=True,
            ):
                st.session_state.chat_id = chat_item["id"]
                st.session_state.pending_message = None
                st.session_state.view = "chat"
                st.rerun()

            if cols[1].button(
                "×",
                key=f"del-{chat_item['id']}",
                help="Delete chat",
            ):
                db.delete_chat(
                    chat_item["id"],
                    user["id"],
                )

                if (
                    st.session_state.chat_id
                    == chat_item["id"]
                ):
                    st.session_state.chat_id = None

                st.rerun()

        st.divider()

        if st.button(
            "Log out",
            use_container_width=True,
        ):
            st.session_state.user = None
            st.session_state.chat_id = None
            st.session_state.pending_message = None
            st.rerun()


# ============================================================
# CHAT MESSAGE DESIGN
# ============================================================

def show_user(text):
    safe_text = html.escape(text)

    st.markdown(
        '<div class="turn user">'
        '<div class="bubble">'
        f'<p class="user-text">{safe_text}</p>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )



def show_answer(dzongkha, roman, gloss):
    """Display all three chatbot response sections."""

    import re

    pronunciation = (roman or "").strip()

    # Reject Dzongkha script in pronunciation.
    if re.search(r"[\u0F00-\u0FFF]", pronunciation):
        pronunciation = ""

    if not pronunciation:
        pronunciation = (
            "Pronunciation unavailable. "
            "This response needs pronunciation review."
        )

    parts = [
        '<div class="reply-label">Dzongkha Response</div>',
        f'<div class="dzo">{html.escape(dzongkha or "")}</div>',

        '<div class="reply-divider"></div>',
        '<div class="reply-label">Pronunciation</div>',
        f'<div class="line">{html.escape(pronunciation)}</div>',
    ]

    if gloss:
        parts.extend([
            '<div class="reply-divider"></div>',
            '<div class="reply-label">English Meaning</div>',
            f'<div class="line">{html.escape(gloss)}</div>',
        ])

    st.markdown(
        '<div class="turn bot">'
        '<div class="bubble">'
        '<p class="who">DRUK KHA</p>'
        + "".join(parts)
        + '</div></div>',
        unsafe_allow_html=True,
    )

def show_thinking():
    """Animated thinking indicator."""

    st.markdown(
        """
        <div class="thinking">
            <div class="thinking-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span>Druk Kha is thinking...</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PROCESS AND SAVE MESSAGE
# ============================================================

def send(user, text):
    """Generate the response and save it to chat history."""

    text = text.strip()

    if not text:
        return False

    history = []

    if st.session_state.chat_id:
        history = db.get_messages(
            st.session_state.chat_id,
            user["id"],
        )

    try:
        result = translate(
            text,
            history,
            db.glossary(),
        )

    except Exception as exc:
        st.session_state.error = str(exc)
        return False

    # Flag suspicious language without blocking the reply.
    try:
        review.inspect_and_queue(text, result)
    except Exception:
        # A review-system error should not break chatting.
        pass

    if st.session_state.chat_id is None:
        title = text

        if len(title) > 42:
            title = title[:42].rstrip() + "…"

        st.session_state.chat_id = db.create_chat(
            user["id"],
            title,
        )

    chat_id = st.session_state.chat_id

    db.add_message(
        chat_id,
        "user",
        english=text,
    )

    db.add_message(
        chat_id,
        "assistant",
        english=text,
        dzongkha=result["dzongkha"],
        roman=result["roman"],
        gloss=result["gloss"],
    )

    st.session_state.error = None

    return True


# ============================================================
# CHAT PAGE
# ============================================================

def chat(user):
    rows = []

    if st.session_state.chat_id:
        rows = db.get_messages(
            st.session_state.chat_id,
            user["id"],
        )

    saved = {
        item["dzongkha"]
        for item in db.list_phrases(user["id"])
    }

    pending = st.session_state.get("pending_message")

    # Empty conversation.
    if not rows and not pending:
        st.markdown(
            '<div style="padding-top:8vh">'
            '<p class="dzo">'
            'སྐུ་གཟུགས་བཟང་པོ་ལགས།'
            '</p>'
            '<p class="lede">'
            'Kuzuzangpo la. Ask me anything in English.'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        suggestions = [
            "Hello",
            "How are you?",
            "What is machine learning?",
            "Write a short poem about Bhutan",
        ]

        cols = st.columns(2)

        for index, label in enumerate(suggestions):
            if cols[index % 2].button(
                label,
                use_container_width=True,
            ):
                st.session_state.pending_message = label
                st.session_state.error = None
                st.rerun()

    # Existing chat history.
    for row in rows:
        if row["role"] == "user":
            show_user(row["english"] or "")
            continue

        show_answer(
            row["dzongkha"] or "",
            row["roman"] or "",
            row["gloss"] or "",
        )

        already = row["dzongkha"] in saved

        save_col, _ = st.columns([1, 3])

        if save_col.button(
            "Saved" if already else "Save to phrasebook",
            key=f"save-{row['id']}",
            disabled=already,
        ):
            db.save_phrase(
                user["id"],
                row["english"] or "",
                row["dzongkha"] or "",
                row["roman"] or "",
                row["gloss"] or "",
            )
            st.rerun()

    # Chat input.
    # Disabled while a message is being processed.
    prompt = st.chat_input(
        "Write in English",
        disabled=bool(pending),
    )

    if prompt and not pending:
        st.session_state.pending_message = prompt
        st.session_state.error = None
        st.rerun()

    # IMPORTANT:
    # Display the user message BEFORE running the AI.
    pending = st.session_state.get("pending_message")

    if pending:
        show_user(pending)

        # Render a visible loading indicator.
        loading_area = st.empty()

        with loading_area.container():
            show_thinking()

        # This can take several seconds because
        # Groq, CST and pronunciation run sequentially.
        try:
            success = send(user, pending)
        finally:
            loading_area.empty()
            st.session_state.pending_message = None

        if success:
            st.rerun()

        # Keep the failed question visible on this render.
        if st.session_state.get("error"):
            st.error(st.session_state.error)

    elif st.session_state.get("error"):
        st.error(st.session_state.error)


# ============================================================
# PHRASEBOOK
# ============================================================

def phrasebook(user):
    st.markdown(
        '<div class="brand">'
        '<small>SAVED</small>Phrasebook'
        '</div>',
        unsafe_allow_html=True,
    )

    items = db.list_phrases(user["id"])

    book = [
        item
        for item in items
        if item.get("kind") == "textbook"
    ]

    mine = [
        item
        for item in items
        if item.get("kind") != "textbook"
    ]

    st.markdown(
        f'<p class="lede">'
        f'The grammar set contains {len(book)} saved lines. '
        'Your own phrases are shown below.'
        '</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="who">FROM THE GRAMMAR</p>',
        unsafe_allow_html=True,
    )

    _phrase_cards(user, book, allow_remove=False)

    st.markdown(
        '<p class="who">YOUR SAVED PHRASES</p>',
        unsafe_allow_html=True,
    )

    if not mine:
        st.info("No personal phrases saved yet.")
        return

    _phrase_cards(user, mine, allow_remove=True)


def _phrase_cards(user, items, allow_remove):
    for item in items:
        english = html.escape(item["english"] or "")
        dzongkha = html.escape(item["dzongkha"] or "")
        roman = html.escape(item["roman"] or "")
        gloss = html.escape(item["gloss"] or "")

        st.markdown(
            '<div class="card">'
            f'<p class="who">{english}</p>'
            f'<p class="dzo">{dzongkha}</p>'
            f'<p class="line"><b>Pronunciation</b></p>'
            f'<p class="line">{roman}</p>'
            '<div class="reply-divider"></div>'
            f'<p class="line"><b>Meaning</b></p>'
            f'<p class="line">{gloss}</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        if allow_remove:
            if st.button(
                "Remove",
                key=f"drop-{item['id']}",
            ):
                db.delete_phrase(
                    item["id"],
                    user["id"],
                )
                st.rerun()


# ============================================================
# LANGUAGE REVIEW PANEL
# ============================================================

def language_review_panel():
    st.subheader("Dzongkha Language Review")

    st.caption(
        "Review expressions that may contain "
        "Tibetan-style wording. A flag does not "
        "automatically mean the sentence is incorrect."
    )

    items = review.pending_reviews()

    if not items:
        st.success("No pending language reviews.")
        return

    st.info(
        f"{len(items)} response(s) awaiting review."
    )

    for item in items:
        with st.expander(
            f"Review #{item['id']}: "
            f"{item['english'][:60]}"
        ):
            st.write("**English question**")
            st.write(item["english"])

            st.write("**Generated Dzongkha**")
            st.write(item["dzongkha"])

            st.write("**Reason for review**")
            st.warning(item["reason"])

            with st.form(
                f"review_form_{item['id']}"
            ):
                corrected = st.text_area(
                    "Correct Bhutanese Dzongkha",
                    value=item["dzongkha"],
                )

                roman = st.text_area(
                    "English-letter pronunciation",
                    value=item["roman"],
                )

                gloss = st.text_area(
                    "English meaning",
                    value=item["gloss"],
                )

                approve = st.form_submit_button(
                    "Approve correction"
                )

                dismiss = st.form_submit_button(
                    "Dismiss flag"
                )

            if approve:
                error = review.approve_correction(
                    item["id"],
                    corrected,
                    roman,
                    gloss,
                )

                if error:
                    st.error(error)
                else:
                    st.success(
                        "Correction approved and saved."
                    )
                    st.rerun()

            if dismiss:
                review.dismiss_review(item["id"])
                st.rerun()


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def admin(user):
    st.markdown(
        '<div class="brand">'
        '<small>ADMIN</small>Desk'
        '</div>',
        unsafe_allow_html=True,
    )

    numbers = db.stats()

    one, two, three = st.columns(3)

    one.metric("People", numbers["users"])
    two.metric("Chats", numbers["chats"])
    three.metric("Replies", numbers["replies"])

    st.subheader("Accounts")

    people = db.list_users()

    st.dataframe(
        [
            {
                "Name": p["name"],
                "Email": p["email"],
                "Role": p["role"],
                "Joined": p["created_at"],
            }
            for p in people
        ],
        use_container_width=True,
        hide_index=True,
    )

    students = [
        p for p in people
        if p["role"] != "admin"
    ]

    if students:
        labels = {
            f"{p['name']} · {p['email']}": p["id"]
            for p in students
        }

        picked = st.selectbox(
            "Remove a student account",
            list(labels),
        )

        if st.button("Delete this account"):
            error = db.delete_user(
                labels[picked],
                user["id"],
            )

            if error:
                st.error(error)
            else:
                st.success("Account removed.")
                st.rerun()

    st.divider()

    # TEACH PHRASES
    st.subheader("Teach a Phrase")

    st.caption(
        "Add verified Bhutanese Dzongkha phrases "
        "to the chatbot's knowledge base."
    )

    with st.form("teach"):
        english = st.text_input("English")
        dzongkha = st.text_input("Dzongkha")
        roman = st.text_input(
            "English-letter pronunciation"
        )
        gloss = st.text_input("English meaning")

        if st.form_submit_button("Save phrase"):
            error = db.add_glossary(
                english,
                dzongkha,
                roman,
                gloss,
            )

            if error:
                st.error(error)
            else:
                st.success("Phrase saved.")
                st.rerun()

    taught = db.glossary()

    if taught:
        st.dataframe(
            taught,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # LANGUAGE REVIEW
    language_review_panel()

    st.divider()

    # RECENT RESPONSES
    st.subheader("Recent Replies")

    recent = db.recent_replies()

    if recent:
        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No replies yet.")


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    boot()

    user = st.session_state.user

    if not user:
        gate()
        return

    sidebar(user)

    if (
        st.session_state.view == "admin"
        and user["role"] == "admin"
    ):
        admin(user)

    elif st.session_state.view == "phrases":
        phrasebook(user)

    else:
        chat(user)


if __name__ == "__main__":
    main()