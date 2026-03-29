import networkx as nx


def compute_pagerank(G):

    pr = nx.pagerank(G)

    for node, score in pr.items():

        G.nodes[node]["pagerank"] = score

    return G