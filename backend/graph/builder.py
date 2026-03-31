import networkx as nx


def build_graph(papers, reference_map):
    G = nx.DiGraph()

    # add all papers that have a pdf as nodes
    for paper in papers:
        if not paper.get("pdf_path"):
            continue
        G.add_node(
            paper["id"],
            title=paper.get("title", ""),
            year=int(paper.get("year") or 2024),
            citations=paper.get("citations", 0),
            arxiv_id=paper.get("arxiv_id", ""),
            role="seed"
        )

    print(f"Nodes added: {len(G.nodes)}")

    # add edges — both nodes must be in graph
    edge_count = 0
    for paper_id, refs in reference_map.items():
        if paper_id not in G.nodes:
            continue
        for ref in refs:
            ref_id = ref.get("id", "")
            if ref_id and ref_id in G.nodes:
                G.add_edge(paper_id, ref_id)
                edge_count += 1

    print(f"Edges added: {edge_count}")
        
    return G