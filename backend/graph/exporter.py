import json


def export_graph(G, run_path):
    nodes = []
    links = []

    for node, data in G.nodes(data=True):
        nodes.append({
            "id":        node,
            "title":     data.get("title", ""),
            "year":      data.get("year", 2024),
            "pagerank":  data.get("pagerank", 0),
            "role":      data.get("role", "peripheral"),
            "citations": data.get("citations", 0),
            "arxiv_id":  data.get("arxiv_id", ""),
        })

    for source, target in G.edges():
        links.append({"source": source, "target": target})

    with open(f"{run_path}/graph.json", "w") as f:
        json.dump({"nodes": nodes, "links": links}, f, indent=2)