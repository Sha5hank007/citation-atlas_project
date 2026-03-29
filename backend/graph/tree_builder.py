def build_tree(seed_paper, reference_map, paper_map):

    def expand(paper_id, depth=2):

        if depth == 0:
            return None

        node = {
            "id": paper_id,
            "name": paper_map[paper_id]["title"],
            "children": []
        }

        for ref in reference_map.get(paper_id, []):

            if ref in paper_map:

                child = expand(ref, depth - 1)

                if child:
                    node["children"].append(child)

        return node

    return expand(seed_paper)