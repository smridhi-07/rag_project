# WebFi

A retrieval-augmented generation (RAG) chatbot that reads a website and answers questions grounded in its actual content with source citations and follow-up suggestions.

WebFi indexes a site by combining two discovery methods: sitemap parsing and link-following to build as complete a picture of the content as possible, while strictly respecting each site's `robots.txt` rules, including newer directives that specifically govern AI/RAG-style access. 

Crawled pages are cleaned of navigation, ads, and boilerplate before being chunked, embedded, and stored for retrieval.

---

## What it does

- **Crawls a website** — using sitemap discovery and link-following (combined), while respecting `robots.txt`
- **Chunks and embeds** the page content locally (no API cost for this step)
- **Stores** everything in a lightweight vector store with similarity search
- **Answers questions** using an LLM (via Groq), grounded *only* in the retrieved content — it won't make things up
- **Cites its sources** — every answer links back to the page(s) it came from
- **Suggests follow-up questions** based on what's actually in the indexed content
- **Scopes answers to a specific site** if you've indexed more than one
- **Extracts and stores page links**, so you can ask things like "what links are on this page?"

---
## Tech stack

| Layer | Tool |
|---|---|
| Backend API | FastAPI |
| Crawling | `requests`, `BeautifulSoup`, `trafilatura` |
| Embeddings | `sentence-transformers` (runs locally, no API key needed) |
| Vector store | Custom file-backed store (numpy-based similarity search) |
| LLM | Groq (Llama 3.3 70B) |
| Frontend | Streamlit |
| Testing | Pytest |

## Project structure

```
PROJECTAI/
├── app/
│   ├── crawler/        # sitemap discovery, page fetching, crawl orchestration
│   ├── ingestion/       # chunking and embedding
│   ├── retrieval/       # vector store + similarity search
│   ├── generation/      # LLM prompting and answer generation
│   └── main.py          # FastAPI app and endpoints
├── tests/               # pytest test suite
├── streamlit_app.py     # frontend
└── requirements.txt
```

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root with:
```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

## Running it

You need two terminals running at the same time:

**Terminal 1 — backend:**
```bash
uvicorn app.main:app --reload
```

**Terminal 2 — frontend:**
```bash
streamlit run streamlit_app.py
```

Then open the Streamlit URL it gives you (usually `http://localhost:8501`).

## Usage

1. In the sidebar, enter a website URL and click **Add to WebFi**
2. Choose whether to index just that one page, or let it explore linked pages too (up to a page limit)
3. Once indexed, pick which site to focus your questions on (or search across everything you've added)
4. Ask a question — you'll get a grounded answer with sources, and a few follow-up questions to keep exploring

## Running tests

```bash
pytest tests/ -v
```
