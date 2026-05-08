"""Streamlit UI."""
import streamlit as st
import requests
import json
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Email RAG Chatbot", layout="wide")
st.title("📧 Email + Attachment RAG Chatbot")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_debug" not in st.session_state:
    st.session_state.last_debug = None


def fetch_threads():
    try:
        r = requests.get(f"{API_URL}/threads", timeout=5)
        return r.json()["threads"]
    except Exception as e:
        st.error(f"Cannot reach API at {API_URL}. Is it running? Error: {e}")
        return []


# ===== Sidebar =====
with st.sidebar:
    st.header("⚙️ Settings")

    threads = fetch_threads()
    thread_options = {f"{t['thread_id']}: {t['subject'][:40]}": t["thread_id"]
                      for t in threads}

    if thread_options:
        selected = st.selectbox("Select Thread", list(thread_options.keys()))
        selected_tid = thread_options[selected]

        if st.session_state.thread_id != selected_tid:
            # Start or switch session
            if st.session_state.session_id is None:
                resp = requests.post(f"{API_URL}/start_session",
                                     json={"thread_id": selected_tid}).json()
                st.session_state.session_id = resp["session_id"]
            else:
                requests.post(f"{API_URL}/switch_thread",
                              json={"session_id": st.session_state.session_id,
                                    "thread_id": selected_tid})
            st.session_state.thread_id = selected_tid
            st.session_state.messages = []
            st.session_state.last_debug = None
            st.rerun()

    search_outside = st.checkbox("🔍 Search outside thread", value=False)

    if st.button("🔄 Reset Session"):
        if st.session_state.session_id:
            requests.post(f"{API_URL}/reset_session",
                          json={"session_id": st.session_state.session_id})
        st.session_state.messages = []
        st.session_state.last_debug = None
        st.rerun()

    st.divider()

    # Debug panel
    with st.expander("🔍 Debug Panel", expanded=True):
        if st.session_state.last_debug:
            d = st.session_state.last_debug
            st.markdown("**Rewritten query:**")
            st.code(d["rewrite"])

            st.markdown("**Top retrieved chunks:**")
            for r in d["retrieved"][:5]:
                page_str = f", p.{r['page_no']}" if r.get("page_no") else ""
                st.markdown(
                    f"- `{r['chunk_id']}` ({r['type']}, msg={r['message_id']}{page_str}) "
                    f"score={r['score']:.2f}"
                )

            st.markdown("**Citations used:**")
            for c in d["citations"]:
                if c["type"] == "pdf":
                    st.markdown(f"- 📄 [msg: {c['message_id']}, page: {c['page']}]")
                else:
                    st.markdown(f"- ✉️ [msg: {c['message_id']}]")

            st.markdown(f"**Latency:** {d['latency_ms']} ms")
        else:
            st.info("Ask a question to see debug info")

# ===== Main chat =====
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about this email thread..."):
    if not st.session_state.session_id:
        st.error("Please select a thread first")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{API_URL}/ask",
                    json={
                        "session_id": st.session_state.session_id,
                        "text": prompt,
                        "search_outside_thread": search_outside
                    },
                    timeout=60
                ).json()
                answer = resp["answer"]
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.last_debug = resp
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")