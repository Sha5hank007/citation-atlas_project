from backend.config import DATA_PROVIDER

from backend.harvester.semantic_scholar import (
    search_papers as semantic_search,
    get_references as semantic_refs,
)

from backend.harvester.arxiv_api import (
    search_papers as arxiv_search,
    get_references as arxiv_refs,
)


def get_harvester():

    provider = DATA_PROVIDER.lower()

    if provider == "semantic":
        return semantic_search, semantic_refs

    if provider == "arxiv":
        return arxiv_search, arxiv_refs

    raise RuntimeError("Invalid DATA_PROVIDER")