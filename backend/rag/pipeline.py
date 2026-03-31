import os
try:
    import fitz
except ImportError:
    fitz = None
import chromadb
from sentence_transformers import SentenceTransformer

fitz.TOOLS.mupdf_display_errors(False)

model = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text(pdf_path):

    if fitz is None:
        raise RuntimeError("pymupdf (fitz) is not installed. Install with: pip install pymupdf")

    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    return text


def chunk_text(text, size=300, overlap=50):

    words = text.split()
    chunks = []

    for i in range(0, len(words), size - overlap):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)

    return chunks


def embed_and_store(papers, run_path):

    db_path = f"{run_path}/vector_db"

    os.makedirs(db_path, exist_ok=True)

    client = chromadb.PersistentClient(path=db_path)

    collection = client.get_or_create_collection("papers")

    ids = []
    docs = []
    metadatas = []

    for paper in papers:

        pdf_path = paper.get("pdf_path")

        if not pdf_path or not os.path.exists(pdf_path):
            continue

        text = extract_text(pdf_path)

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):

            ids.append(f"{paper['id']}_{i}")
            docs.append(chunk)
            metadatas.append({
                "paper_id": paper["id"],
                "title": paper.get("title", "")
            })

    if docs:

        embeddings = model.encode(docs)

        collection.add(
            documents=docs,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

    return db_path