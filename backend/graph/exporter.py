import json


def export_graph(G, run_path):
    nodes = []
    links = []

    for node, data in G.nodes(data=True):
        nodes.append({
            "id":        node,
            "title":     data.get("title", ""),
            "abstract":  data.get("abstract", ""),
            "year":      data.get("year", 2024),
            "role":      data.get("role", "peripheral"),
            "citations": data.get("citations", 0),
            "arxiv_id":  data.get("arxiv_id", ""),
            "relevance_score": data.get("relevance_score", 0),
        })

    for source, target in G.edges():
        links.append({"source": source, "target": target})

    with open(f"{run_path}/graph.json", "w") as f:
        json.dump({"nodes": nodes, "links": links}, f, indent=2)