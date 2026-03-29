import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")


def query_db(question, db_path, paper_ids=None, top_k=10):

    client = chromadb.PersistentClient(path=db_path)

    try:
        collection = client.get_collection("papers")
    except Exception:
        collection = client.get_or_create_collection("papers")

    q_embedding = model.encode(question)

    if paper_ids and len(paper_ids) > 0:

        # Count how many chunks exist for these papers
        available = collection.get(
            where={"paper_id": {"$in": list(paper_ids)}}
        )
        total = len(available["documents"])

        if total == 0:
            return [], []

        n = min(top_k, total)   # ← the fix

        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=n,
            where={"paper_id": {"$in": list(paper_ids)}},  # ← filter inside chromadb
            include=["documents", "metadatas"]
        )

    else:
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=top_k,
            include=["documents", "metadatas"]
        )

    docs  = results.get("documents", [[]])[0] or []
    metas = results.get("metadatas",  [[]])[0] or []

    return docs, metas