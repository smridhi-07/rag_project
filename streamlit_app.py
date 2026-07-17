"""
Streamlit frontend for WebFi — a RAG chatbot for website content.
"""

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="WebFi", page_icon=None, layout="centered")

st.markdown(
    """
    <style>
    .webfi-header h1 {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
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
    except requests.RequestException:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "Sorry, I couldn't connect to the app just now. Please try again in a moment.",
                "sources": [],
                "follow_ups": [],
            }
        )


# --- Sidebar: crawl a new site + pick which site to chat with ---
with st.sidebar:
    st.header("Add a website")
    url = st.text_input("Website URL", placeholder="https://example.com/docs")
    max_pages = st.slider("How many pages to read (max)", min_value=1, max_value=50, value=10)
    single_page = st.checkbox(
        "Just this one page",
        help="Turn this on to read only the exact page above. Leave it off to explore the whole site (up to the limit set by the slider)."
    )

    if st.button("Add to WebFi", type="primary"):
        if not url:
            st.error("Please enter a website URL first.")
        else:
            with st.spinner("Reading the site... this can take a little while"):
                try:
                    response = requests.post(
                        f"{API_URL}/sites",
                        json={"url": url, "max_pages": max_pages, "single_page": single_page},
                        timeout=300,
                    )
                    response.raise_for_status()
                    data = response.json()

                    pages = data["pages_indexed"]
                    skipped = data["skipped_robots"]
                    failed = data["failed"]

                    if pages > 0:
                        st.success(f"Added {pages} page(s) to WebFi. You can start asking questions now.")
                        if skipped > 0 or failed > 0:
                            st.caption(f"({skipped + failed} page(s) on this site couldn't be read.)")
                    elif skipped > 0 and single_page:
                        st.error(
                            "Can't access this site — it doesn't allow this kind of reading, "
                            "even for a single page. This is the site's own choice, not something WebFi can work around."
                        )
                    elif skipped > 0:
                        st.warning(
                            "This site doesn't allow it to be read this way. "
                            "Try turning on 'Just this one page' and adding the exact page you want instead."
                        )
                    else:
                        st.warning("Nothing readable was found at that address. Double-check the URL and try again.")

                except requests.RequestException:
                    st.error("Couldn't reach the app right now. Please try again in a moment.")

    st.divider()

    st.subheader("Ask about")
    try:
        sites_resp = requests.get(f"{API_URL}/sites/list", timeout=5).json()
        available_sites = sites_resp.get("sites", [])
        backend_ok = True
    except requests.RequestException:
        available_sites = []
        backend_ok = False

    site_options = ["All added sites"] + available_sites
    selected_site = st.selectbox("Focus your questions on:", site_options)

    st.divider()
    if backend_ok:
        try:
            status = requests.get(f"{API_URL}/", timeout=5).json()
            count = status["chunks_indexed"]
            st.caption(f"WebFi currently knows about {count} piece(s) of content.")
        except requests.RequestException:
            backend_ok = False

    if not backend_ok:
        st.caption("WebFi isn't running right now. Please start the app and refresh this page.")

# --- Main chat area ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("sources"):
            with st.expander("Where this came from"):
                for src in message["sources"]:
                    st.write(src)

if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    follow_ups = st.session_state.messages[-1].get("follow_ups", [])
    if follow_ups:
        st.caption("You might also ask:")
        cols = st.columns(len(follow_ups))
        for col, fq in zip(cols, follow_ups):
            if col.button(fq, key=f"fu_{fq}"):
                st.session_state.pending_question = fq

question = st.chat_input("Ask a question about the sites you've added...")

if question:
    st.session_state.pending_question = question

if st.session_state.pending_question:
    q = st.session_state.pending_question
    st.session_state.pending_question = None
    site_arg = None if selected_site == "All added sites" else selected_site
    with st.spinner("Thinking..."):
        ask_question(q, site_arg)
    st.rerun()