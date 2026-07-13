from app.crawler.fetcher import fetch_page
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import embed_texts, embed_text
from app.retrieval.vector_store import VectorStore
from app.generation.llm import generate_answer

# fetch + chunk + embed + store (same as before)
page = fetch_page("https://docs.python.org/3/tutorial/introduction.html")
chunks = chunk_text(page.text, page.url, page.title)
embeddings = embed_texts([c.text for c in chunks])

store = VectorStore(path="test_store.json")
store.add(chunks, embeddings)

# retrieve
question = "How do I write a comment in Python?"
question_vec = embed_text(question)
results = store.search(question_vec, top_k=3)

context_chunks = [chunk.text for chunk, score in results]

# generate
answer = generate_answer(question, context_chunks)

print(f"Question: {question}\n")
print(f"Answer:\n{answer}")