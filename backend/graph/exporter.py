import json


def export_graph(G, run_path):

    nodes = []
    links = []

    for node, data in G.nodes(data=True):

        nodes.append({
            "id": node,
            "title": data.get("title", ""),
            "year": data.get("year", 2024),
            "pagerank": data.get("pagerank", 0)
        })

    for source, target in G.edges():

        links.append({
            "source": source,
            "target": target
        })

    graph_data = {
        "nodes": nodes,
        "links": links
    }

    with open(f"{run_path}/graph.json", "w") as f:
        json.dump(graph_data, f, indent=2)