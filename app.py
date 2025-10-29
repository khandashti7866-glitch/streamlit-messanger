# app.py
import sqlite3
from datetime import datetime
import streamlit as st
from typing import List, Tuple

# ---------- DB helpers ----------
DB_PATH = "messages.db"

@st.experimental_singleton
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            content TEXT NOT NULL,
            ts TEXT NOT NULL
        )
        """
    )
    conn.commit()

def add_message(sender: str, receiver: str, content: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (sender, receiver, content, ts) VALUES (?, ?, ?, ?)",
        (sender, receiver, content, datetime.utcnow().isoformat()),
    )
    conn.commit()

def get_conversations_for_user(username: str) -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT CASE
            WHEN sender = ? THEN receiver
            ELSE sender
        END as contact
        FROM messages
        WHERE sender = ? OR receiver = ?
        """,
        (username, username, username)
    )
    rows = cur.fetchall()
    contacts = [row["contact"] for row in rows]
    contacts.sort()
    return contacts

def get_messages(user_a: str, user_b: str) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM messages
        WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        ORDER BY id ASC
        """,
        (user_a, user_b, user_b, user_a)
    )
    return cur.fetchall()

# ---------- UI ----------
st.set_page_config(page_title="Simple Messenger", layout="wide")
init_db()

st.sidebar.title("Simple Messenger")
username = st.sidebar.text_input("Your username (login)", value=st.session_state.get("username", ""))
if username:
    st.session_state["username"] = username

if not username:
    st.sidebar.info("Enter your username to start. You can use any name (no password).")
    st.stop()

# New contact box
new_contact = st.sidebar.text_input("Start chat with (username)", value="")
if st.sidebar.button("Add / Open chat"):
    if new_contact and new_contact != username:
        # add a tiny placeholder if no messages exist yet so contact appears
        add_message(username, new_contact, "[Started conversation]")
        st.experimental_rerun()

st.sidebar.markdown("---")
contacts = get_conversations_for_user(username)
selected_contact = st.sidebar.radio("Chats", options=contacts if contacts else ["No conversations"], index=0 if contacts else 0)

# Main chat area
st.title(f"Chat — {username}")
col1, col2 = st.columns([3, 1])

with col1:
    if not contacts:
        st.info("No conversations yet. Use the sidebar to start a chat.")
    else:
        contact = selected_contact
        st.header(f"Chat with {contact}")

        messages = get_messages(username, contact)
        # Display messages
        for m in messages:
            sender = m["sender"]
            content = m["content"]
            ts = m["ts"]
            # simple styling: right align your messages
            if sender == username:
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:flex-end; margin:6px 0;">
                      <div style="max-width:75%; background:#DCF8C6; padding:8px 12px; border-radius:12px;">
                        <div style="font-size:14px;">{st._cc.escape_html(content)}</div>
                        <div style="font-size:11px; opacity:0.6; text-align:right;">{ts.split('T')[0]} {ts.split('T')[1][:8]} UTC</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:flex-start; margin:6px 0;">
                      <div style="max-width:75%; background:#FFFFFF; padding:8px 12px; border-radius:12px; border:1px solid #e6e6e6;">
                        <div style="font-size:14px;"><b>{st._cc.escape_html(sender)}</b>: {st._cc.escape_html(content)}</div>
                        <div style="font-size:11px; opacity:0.6;">{ts.split('T')[0]} {ts.split('T')[1][:8]} UTC</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        # Message input
        with st.form(key="send_form", clear_on_submit=True):
            msg = st.text_area("Write a message", height=80, placeholder="Type your message here...")
            send = st.form_submit_button("Send")
            if send and msg.strip():
                add_message(username, contact, msg.strip())
                # after send, rerun to update chat
                st.experimental_rerun()

with col2:
    st.subheader("Conversation details")
    if contacts:
        st.write(f"Chatting with: **{contact}**")
        st.write(f"Total messages in this chat: **{len(messages)}**")
        last_msg = messages[-1]["ts"] if messages else "—"
        st.write(f"Last message: **{last_msg}**")
    st.markdown("---")
    st.subheader("Actions")
    if st.button("Refresh"):
        st.experimental_rerun()
    if st.button("Delete conversation"):
        if contacts:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM messages WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)",
                (username, contact, contact, username),
            )
            conn.commit()
            st.success("Conversation deleted.")
            st.experimental_rerun()

st.markdown("---")
st.caption("This is a simple local messenger demo. For multi-user real-time messaging across devices, deploy with a real backend and websockets or a messaging service.")
