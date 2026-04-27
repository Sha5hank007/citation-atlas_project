import datetime


def assign_roles(G):
    """
    Assign roles to nodes based on citations and recency.
    No graph-based centrality is used.
    """

    if len(G.nodes) == 0:
        return G

    import datetime
    current_year = datetime.datetime.now().year

    for node in G.nodes:
        citations = G.nodes[node].get("citations", 0)
        year      = int(G.nodes[node].get("year") or current_year)
        age       = current_year - year

        existing = G.nodes[node].get("role", "")

        # 🔥 RECENT FIRST
        if age <= 2:
            role = "recent"

        elif citations > 5000 and age >= 3:
            role = "landmark"

        elif citations > 1000:
            role = "important"

        elif citations > 200:
            role = "moderate"  

        else:
            role = "peripheral"

        # landmark override
        if role == "landmark":
            G.nodes[node]["role"] = "landmark"
        elif existing != "landmark":
            G.nodes[node]["role"] = role

    return G