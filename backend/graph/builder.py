import networkx as nx


def build_graph(papers, reference_map):

    G = nx.DiGraph()

    for paper in papers:

        G.add_node(
            paper["id"],
            title=paper.get("title", ""),
            year=paper.get("year", 2024),
            citations=paper.get("citations", 0)
        )

    for paper_id, refs in reference_map.items():

        for ref in refs:

            if ref in G.nodes:

                G.add_edge(paper_id, ref)

    return G