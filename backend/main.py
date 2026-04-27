import sys
import os
import json
import numpy as np
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.rag.pipeline import model
from backend.runs.run_manager import create_run
from backend.query.expander import expand_query
from backend.llm.client import get_llm
from backend.harvester.arxiv import search_papers_async
from backend.harvester.semantic_scholar import get_references_by_arxiv_id
from backend.graph.builder import build_graph
from backend.graph.roles import assign_roles
from backend.graph.exporter import export_graph
from backend.papers.download import download_pdf_from_url
from backend.rag.pipeline import embed_and_store


def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def download_batch(papers, papers_dir):
    if not papers:
        return []

    results = []

    with ThreadPoolExecutor(max_workers=min(4, len(papers))) as executor:
        futures = {
            executor.submit(download_pdf_from_url, p, papers_dir): p
            for p in papers
        }

        for future in as_completed(futures):
            p = futures[future]
            try:
                pdf_path = future.result()
                if pdf_path:
                    p["pdf_path"] = pdf_path
                    results.append(p)
                else:
                    print(f"Download failed: {p['title'][:50]}")
            except Exception as e:
                print("Error:", e)

    return results


# summary generator
def generate_summary(llm, topic, papers):

    # STEP 1: sort groups
    by_relevance = sorted(papers, key=lambda x: x.get("relevance_score", 0), reverse=True)
    by_citations = sorted(papers, key=lambda x: x.get("citations", 0), reverse=True)
    by_year      = sorted(papers, key=lambda x: x.get("year", 0), reverse=True)

    # STEP 2: pick from each group
    selected = []

    def add_papers(source, k):
        for p in source:
            if len(selected) >= k:
                break
            if p["id"] not in seen:
                selected.append(p)
                seen.add(p["id"])

    seen = set()

    # priority order
    add_papers(by_relevance, 6)
    add_papers(by_citations, 4)   # total grows to ~9
    add_papers(by_year, 12)       # total grows to ~12

    papers = selected[:12]

    context = ""
    for i, p in enumerate(papers):
        title = p.get("title", "").strip()
        abstract = (p.get("abstract") or "").strip()[:400]
        context += f"{i+1}. {title}\n{abstract}\n\n"

    prompt = f"""
You are summarizing a research field for a technical user.

Topic: {topic}

You are given a set of representative papers (titles + abstracts).

Your job is to extract STRUCTURE and INSIGHT, not repeat text.

Rules:
- Do NOT repeat paper titles
- Do NOT list every method blindly
- Merge similar ideas
- Keep it concise and easy to scan
- Avoid jargon overload where possible

Return output in this format:

Overview:
(2-3 lines explaining the field clearly)

Key Themes:
• short, clear bullets (max 5)

Major Approaches:
• group similar approaches together
• 1 line per approach

Trends:
• what is changing recently

Open Problems:
• concrete research gaps (most important)

Keep everything tight and readable.
"""

    summary = llm.generate(prompt)

    return summary


async def run_pipeline_async(topic, update_status, run_id=None, run_path=None):
    """Optimized async version of run_pipeline"""

    if run_id is None or run_path is None:
        run_id, run_path = create_run(topic)

    papers_dir = os.path.join(run_path, "papers")
    os.makedirs(papers_dir, exist_ok=True)

    print("\nRun:", run_id)
    print("Topic:", topic)
    print("-" * 50)

    llm = get_llm()

    # ── Step 1: expand queries ────────────────────────────────────────
    update_status("Expanding research queries")
    queries = expand_query(llm, topic)
    for q in queries:
        print("Query:", q)

    # ── Step 2: search seed papers on ArXiv (PARALLEL) ─────────────────
    update_status("Searching seed papers on ArXiv")
    seen_ids = set()
    seed_papers = []

    async with aiohttp.ClientSession() as session:
        # Search all queries concurrently
        search_tasks = [
            search_papers_async(q, limit=8, session=session)
            for q in queries
        ]

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for results in search_results:
            if isinstance(results, Exception):
                print(f"Search error: {results}")
                continue
            for p in results:
                if p["id"] and p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    seed_papers.append(p)

    print(f"Seed papers found: {len(seed_papers)}")

    # ── Step 3: download seed PDFs ────────────────────────────────────
    update_status("Downloading seed PDFs")
    seed_with_pdf = download_batch(seed_papers, papers_dir)
    print(f"Seed with PDF: {len(seed_with_pdf)}")

    # ── Step 4: fetch references for papers with PDFs ───────────────────────
    # Only downloaded papers with an arXiv id are eligible for reference fetching.
    update_status("Fetching references")
    reference_map = {}

    pdf_seeds_with_arxiv = [p for p in seed_with_pdf if p.get("arxiv_id")]
    skipped = len(seed_with_pdf) - len(pdf_seeds_with_arxiv)
    if skipped:
        print(f"Skipping {skipped} downloaded seed papers with no arXiv ID")

    for i, p in enumerate(pdf_seeds_with_arxiv):
        update_status(f"Fetching refs {i+1}/{len(pdf_seeds_with_arxiv)}: {p['title'][:40]}")
        refs = get_references_by_arxiv_id(p["arxiv_id"], min_citations=10)
        reference_map[p["id"]] = refs

    total_refs = sum(len(v) for v in reference_map.values())
    print(f"Total refs fetched: {total_refs}")

    # deduplicate refs
    seen_ref_ids = set()
    all_refs = []
    for refs in reference_map.values():
        for ref in refs:
            if ref["id"] not in seen_ref_ids:
                seen_ref_ids.add(ref["id"])
                all_refs.append(ref)

    print(f"Unique refs: {len(all_refs)}")

    # hard cap — never download more than 30 ref papers
    all_refs = sorted(all_refs, key=lambda x: x["citations"], reverse=True)[:30]
    print(f"Refs after cap: {len(all_refs)}")

    # ── Step 5: download ref PDFs ─────────────────────────────────────
    update_status("Downloading reference PDFs")
    refs_with_pdf = download_batch(all_refs, papers_dir)
    print(f"Refs with PDF: {len(refs_with_pdf)}")

    # Rest of the pipeline remains the same...
    all_papers_with_pdf = seed_with_pdf + refs_with_pdf
    print(f"Total papers with PDF: {len(all_papers_with_pdf)}")

    if len(all_papers_with_pdf) == 0:
        print("❌ No PDFs downloaded — stopping pipeline")
        return {
            "success": False,
            "error": "no pdf papers found"
        }

    pdf_path_by_id = {p["id"]: p["pdf_path"] for p in all_papers_with_pdf}
    for paper_id in reference_map:
        for ref in reference_map[paper_id]:
            if ref["id"] in pdf_path_by_id:
                ref["pdf_path"] = pdf_path_by_id[ref["id"]]

    update_status("Embedding papers")
    vector_db_path = embed_and_store(all_papers_with_pdf, run_path)
    update_status(f"Vector DB: {vector_db_path}")

    # ── Step 6.5: compute relevance scores ───────────────────────────
    update_status("Computing relevance")

    query_vec = model.encode([topic])[0]

    for p in all_papers_with_pdf:
        text = p.get("title", "") + " " + (p.get("abstract") or "")

        if not text.strip():
            p["relevance_score"] = 0
            continue

        paper_vec = model.encode([text])[0]
        sim = cosine(query_vec, paper_vec)
        p["relevance_score"] = float(sim)

    max_score = max((p["relevance_score"] for p in all_papers_with_pdf), default=1)

    if max_score > 0:
        for p in all_papers_with_pdf:
            p["relevance_score"] /= max_score

    # ── Step 7: build graph ──────────────────────────────────────────
    update_status("Building citation graph")
    G = build_graph(all_papers_with_pdf, reference_map)

    # ── Step 8: assign roles ─────────────────────────────────────────
    update_status("Assigning paper roles")
    G = assign_roles(G)

    # ── Step 9: export graph ────────────────────────────────────────
    update_status("Exporting graph")
    export_graph(G, run_path)

    # ── Step 10: generate summary ───────────────────────────────────
    update_status("Generating summary")
    summary = generate_summary(llm, topic, all_papers_with_pdf)

    with open(f"{run_path}/summary.json", "w") as f:
        json.dump({"summary": summary}, f, indent=2)

    run_info = {
        "run_id": run_id,
        "topic": topic,
        "papers_found": len(all_papers_with_pdf),
        "nodes": len(G.nodes),
        "edges": len(G.edges),
    }

    with open(f"{run_path}/run_info.json", "w") as f:
        json.dump(run_info, f, indent=2)

    return {
        "success": True,
        "run_id": run_id,
        "run_path": run_path
    }


# uvicorn backend.server:app --reload