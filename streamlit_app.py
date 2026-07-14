"""
Streamlit frontend for WebFi — a RAG chatbot for website content.
"""

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="WebFi", page_icon=None, layout="centered")

# --- Sticky header so the title stays visible while scrolling chat history ---
st.markdown(
    """
    <style>
    .webfi-header {
        position: sticky;
        top: 0;
        background-color: var(--background-color, #0e1117);
        z-index: 999;
        padding: 0.75rem 0;
        border-bottom: 1px solid rgba(250, 250, 250, 0.1);
        margin-bottom: 1rem;
    }
    .webfi-header h1 {
        margin: 0;
        font-size: 1.6rem;
    }
    </style>
    <div class="webfi-header">
        <h1>WebFi</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def ask_question(question: str, site_filter: str | None):
    st.session_state.messages.append({"role": "user", "content": question})

    payload = {"question": question, "top_k": 3}
    if site_filter and site_filter != "All indexed sites":
        payload["site"] = site_filter

    try:
        response = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": data["answer"],
                "sources": data.get("sources", []),
                "follow_ups": data.get("follow_ups", []),
            }
        )
    except requests.RequestException as e:
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Couldn't reach the backend: {e}", "sources": [], "follow_ups": []}
        )


# --- Sidebar: crawl a new site + pick which site to chat with ---
with st.sidebar:
    st.header("Index a website")
    url = st.text_input("Website URL", placeholder="https://example.com/docs")
    max_pages = st.slider("Max pages to crawl", min_value=1, max_value=50, value=10)
    single_page = st.checkbox("Only this exact page (skip sitemap/link crawling)")

    if st.button("Crawl & Index"):
        if not url:
            st.error("Enter a URL first.")
        else:
            with st.spinner("Crawling and indexing... this can take a while"):
                try:
                    response = requests.post(
                        f"{API_URL}/sites",
                        json={"url": url, "max_pages": max_pages, "single_page": single_page},
                        timeout=300,
                    )
                    response.raise_for_status()
                    data = response.json()
                    st.success(
                        f"Indexed {data['pages_indexed']} pages "
                        f"({data['chunks_added']} chunks). "
                        f"Skipped (robots.txt): {data['skipped_robots']}, "
                        f"Failed: {data['failed']}"
                    )
                except requests.RequestException as e:
                    st.error(f"Failed to reach the API: {e}")

    st.divider()

    st.subheader("Ask about")
    try:
        sites_resp = requests.get(f"{API_URL}/sites/list", timeout=5).json()
        available_sites = sites_resp.get("sites", [])
    except requests.RequestException:
        available_sites = []

    site_options = ["All indexed sites"] + available_sites
    selected_site = st.selectbox("Scope your questions to:", site_options)

    st.divider()
    try:
        status = requests.get(f"{API_URL}/", timeout=5).json()
        st.caption(f"Currently indexed: {status['chunks_indexed']} chunks")
    except requests.RequestException:
        st.caption("Backend not reachable — is uvicorn running?")

# --- Main chat area ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for src in message["sources"]:
                    st.write(src)

# show follow-up buttons after the most recent assistant message only
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    follow_ups = st.session_state.messages[-1].get("follow_ups", [])
    if follow_ups:
        st.caption("Follow-up questions:")
        cols = st.columns(len(follow_ups))
        for col, fq in zip(cols, follow_ups):
            if col.button(fq, key=f"fu_{fq}"):
                st.session_state.pending_question = fq

question = st.chat_input("Ask a question about the indexed content...")

if question:
    st.session_state.pending_question = question

if st.session_state.pending_question:
    q = st.session_state.pending_question
    st.session_state.pending_question = None
    with st.spinner("Thinking..."):
        ask_question(q, selected_site)
    st.rerun()