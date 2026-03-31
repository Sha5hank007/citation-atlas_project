import networkx as nx
import datetime


def compute_pagerank(G):
    if len(G.nodes) == 0:
        return G

    # only run pagerank if we have edges
    if len(G.edges) > 0:
        pr = nx.pagerank(G, alpha=0.85)
        for node, score in pr.items():
            G.nodes[node]["pagerank"] = round(score, 5)
    else:
        # no edges — assign equal pagerank
        n = len(G.nodes)
        for node in G.nodes:
            G.nodes[node]["pagerank"] = round(1/n, 5)

    # assign roles by citation count — works without edges
    for node in G.nodes:
        citations = G.nodes[node].get("citations", 0)
        year      = int(G.nodes[node].get("year") or 2020)
        age       = 2025 - year

        existing = G.nodes[node].get("role", "")

        if citations > 5000 and age >= 3:
            role = "landmark"
        elif citations > 1000:
            role = "important"
        elif citations > 200:
            role = "bridge"
        elif age <= 2:
            role = "recent"
        else:
            role = "peripheral"

        # landmark always wins
        if role == "landmark":
            G.nodes[node]["role"] = "landmark"
        elif existing != "landmark":
            G.nodes[node]["role"] = role

    return G