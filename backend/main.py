import sys
import os
import shutil
import time
import json

# Fix imports if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.runs.run_manager import create_run
from backend.query.expander import expand_query
from backend.llm.client import get_llm
from backend.harvester.client import get_harvester
from backend.graph.builder import build_graph
from backend.graph.centrality import compute_pagerank
from backend.graph.exporter import export_graph
from backend.config import LLM_PROVIDER, DATA_PROVIDER
from backend.papers.download import download_arxiv_pdf

from backend.rag.pipeline import embed_and_store

def run_pipeline(topic, update_status):

    run_id, run_path = create_run(topic)

    print("\nRun:", run_id)
    print("Topic:", topic)
    print("-" * 50)

    llm = get_llm()

    update_status("Expanding research queries")

    queries = expand_query(llm, topic)

    for q in queries:
        print("Query:", q)

    # Select data provider (arxiv or semantic)
    search_papers, get_references = get_harvester()

    papers = []
    reference_map = {}
    seen_papers = set()

    update_status("Searching papers")

    for q in queries:
        update_status(f"Searching: {q}")

        results = search_papers(q)

        for p in results:

            paper_id = p["id"]

            if paper_id in seen_papers:
                continue

            seen_papers.add(paper_id)

            papers.append(p)

    print("Total unique papers:", len(papers))

    if len(papers) == 0:
        print("No papers found. Exiting.")
        return

    update_status("Fetching references")
    update_status("Downloading research papers")

    for i, p in enumerate(papers):
        paper_id = p["id"]

        # Download PDF if using arXiv
        if "arxiv.org" in paper_id:
            update_status(f"Downloading paper {i+1}/{len(papers)}")
            pdf_path = download_arxiv_pdf(paper_id, run_path)
            p["pdf_path"] = pdf_path

        refs = get_references(paper_id)

        reference_map[paper_id] = refs
        time.sleep(1)
        
    update_status("Chunking and embedding papers")
    vector_db_path = embed_and_store(papers, run_path)
    print("Vector DB stored at:", vector_db_path)    

    update_status("Building research graph")

    G = build_graph(papers, reference_map)

    print("Nodes:", len(G.nodes))
    print("Edges:", len(G.edges))

    print("\nComputing PageRank...")

    G = compute_pagerank(G)

    export_graph(G, run_path)

    # Save run metadata
    run_info = {
        "run_id": run_id,
        "topic": topic,
        "llm_provider": LLM_PROVIDER,
        "paper_source": DATA_PROVIDER,
        "queries": queries,
        "papers_found": len(papers),
        "nodes": len(G.nodes),
        "edges": len(G.edges)
    }

    with open(f"{run_path}/run_info.json", "w") as f:
        json.dump(run_info, f, indent=2)

    update_status("Graph ready")
    print("\nGraph exported to frontend/graph.json")
    print("Run metadata saved.")
    print("-" * 50)

    return run_id, run_path


if __name__ == "__main__":

    run_pipeline("diffusion models for video generation", lambda m: print(f"STATUS: {m}"))
    
    
    
# uvicorn backend.server:app --reload    