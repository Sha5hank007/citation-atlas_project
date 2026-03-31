import sys
import os
import time
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.runs.run_manager import create_run
from backend.query.expander import expand_query
from backend.llm.client import get_llm
from backend.harvester.semantic_scholar import search_papers, get_references
from backend.graph.builder import build_graph
from backend.graph.centrality import compute_pagerank
from backend.graph.exporter import export_graph
from backend.config import LLM_PROVIDER
from backend.papers.download import download_arxiv_pdf
from backend.rag.pipeline import embed_and_store


def run_pipeline(topic, update_status):

    run_id, run_path = create_run(topic)
    print("\nRun:", run_id)
    print("Topic:", topic)
    print("-" * 50)

    llm = get_llm()

    # ── Step 1: expand queries ────────────────────────────────────────
    update_status("Expanding research queries")
    queries = expand_query(llm, topic)
    for q in queries:
        print("Query:", q)

    # ── Step 2: search seed papers ────────────────────────────────────
    update_status("Searching papers")
    seen_ids    = set()
    seed_papers = []

    for q in queries:
        update_status(f"Searching: {q}")
        results = search_papers(q, limit=8)
        for p in results:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                seed_papers.append(p)
        time.sleep(1)

    print(f"Seed papers found: {len(seed_papers)}")

    # ── Step 3: fetch references ──────────────────────────────────────
    update_status("Fetching references")
    reference_map = {}

    for i, p in enumerate(seed_papers):
        update_status(f"Fetching refs {i+1}/{len(seed_papers)}: {p['title'][:40]}")
        refs = get_references(p["id"], min_citations=2000)
        reference_map[p["id"]] = refs
        time.sleep(1)

    total_refs = sum(len(v) for v in reference_map.values())
    print(f"Total refs fetched: {total_refs}")

    # deduplicate refs
    seen_ref_ids = set()
    all_refs     = []
    for refs in reference_map.values():
        for ref in refs:
            if ref["id"] not in seen_ref_ids:
                seen_ref_ids.add(ref["id"])
                all_refs.append(ref)

    print(f"Unique refs: {len(all_refs)}")
    
    # hard cap — never download more than 30 ref papers
    all_refs = sorted(all_refs, key=lambda x: x["citations"], reverse=True)[:30]
    print(f"Refs after cap: {len(all_refs)}")

    # ── Step 4: download seed PDFs ────────────────────────────────────
    update_status("Downloading seed PDFs")
    seed_with_pdf = []

    for i, p in enumerate(seed_papers):
        arxiv_id = p.get("arxiv_id")
        if not arxiv_id:
            print(f"No ArXiv ID: {p['title'][:50]}")
            continue
        update_status(f"Seed {i+1}/{len(seed_papers)}: {p['title'][:40]}")
        pdf_path = download_arxiv_pdf(arxiv_id, run_path)
        if pdf_path:
            p["pdf_path"] = pdf_path
            seed_with_pdf.append(p)
        else:
            print(f"Failed: {p['title'][:50]}")
        time.sleep(1)

    print(f"Seed with PDF: {len(seed_with_pdf)}")

    # ── Step 5: download ref PDFs ─────────────────────────────────────
    update_status("Downloading reference PDFs")
    refs_with_pdf = []

    for i, ref in enumerate(all_refs):
        arxiv_id = ref.get("arxiv_id")
        if not arxiv_id:
            continue
        update_status(f"Ref {i+1}/{len(all_refs)}: {ref['title'][:40]}")
        pdf_path = download_arxiv_pdf(arxiv_id, run_path)
        if pdf_path:
            ref["pdf_path"] = pdf_path
            refs_with_pdf.append(ref)
        else:
            print(f"Ref failed: {ref['title'][:50]}")
        time.sleep(1)

    print(f"Refs with PDF: {len(refs_with_pdf)}")

    # combine
    all_papers_with_pdf = seed_with_pdf + refs_with_pdf
    print(f"Total papers with PDF: {len(all_papers_with_pdf)}")

    if len(all_papers_with_pdf) == 0:
        update_status("Failed — no papers downloaded")
        return

    # attach pdf_path back to reference_map dicts
    pdf_path_by_id = {p["id"]: p["pdf_path"] for p in all_papers_with_pdf}
    for paper_id in reference_map:
        for ref in reference_map[paper_id]:
            if ref["id"] in pdf_path_by_id:
                ref["pdf_path"] = pdf_path_by_id[ref["id"]]

    # ── Step 6: embed ─────────────────────────────────────────────────
    update_status("Embedding papers")
    vector_db_path = embed_and_store(all_papers_with_pdf, run_path)
    print("Vector DB:", vector_db_path)

    # ── Step 7: build graph ───────────────────────────────────────────
    update_status("Building graph")

    node_ids            = {p["id"] for p in all_papers_with_pdf}
    ref_keys_in_nodes   = sum(1 for pid in reference_map if pid in node_ids)
    refs_with_pdf_count = sum(
        1 for refs in reference_map.values()
        for r in refs if r.get("pdf_path")
    )
    print(f"reference_map keys that are nodes: {ref_keys_in_nodes}")
    print(f"refs with pdf_path: {refs_with_pdf_count}")

    G = build_graph(all_papers_with_pdf, reference_map)
    print(f"Nodes: {len(G.nodes)}  Edges: {len(G.edges)}")

    G = compute_pagerank(G)
    export_graph(G, run_path)

    # ── Step 8: save run info ─────────────────────────────────────────
    run_info = {
        "run_id":       run_id,
        "topic":        topic,
        "llm_provider": LLM_PROVIDER,
        "queries":      queries,
        "papers_found": len(all_papers_with_pdf),
        "nodes":        len(G.nodes),
        "edges":        len(G.edges),
    }
    with open(f"{run_path}/run_info.json", "w") as f:
        json.dump(run_info, f, indent=2)

    update_status("complete")
    print("\nDone.")
    print("-" * 50)

    return run_id, run_path


if __name__ == "__main__":
    run_pipeline(
        "diffusion models for video generation",
        lambda m: print(f"STATUS: {m}")
    )


# uvicorn backend.server:app --reload