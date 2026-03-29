import requests
import time

BASE_URL = "https://api.semanticscholar.org/graph/v1"


def search_papers(query, limit=5):

    url = f"{BASE_URL}/paper/search"

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,citationCount"
    }

    wait = 3

    for attempt in range(5):

        r = requests.get(url, params=params)

        if r.status_code == 200:

            data = r.json()

            papers = []

            for p in data.get("data", []):

                papers.append({
                    "id": p["paperId"],
                    "title": p["title"],
                    "year": p.get("year"),
                    "citations": p.get("citationCount", 0)
                })

            return papers

        if r.status_code == 429:

            print(f"Rate limit hit. Waiting {wait}s...")
            time.sleep(wait)
            wait *= 2
            continue

        print("Search failed:", r.status_code)
        return []

    return []


def get_references_batch(paper_ids):

    url = f"{BASE_URL}/paper/batch"

    params = {
        "fields": "references.paperId"
    }

    payload = {
        "ids": paper_ids
    }

    wait = 3

    for attempt in range(5):

        r = requests.post(url, params=params, json=payload)

        if r.status_code == 200:

            data = r.json()

            reference_map = {}

            for paper in data:

                paper_id = paper["paperId"]

                refs = []

                for ref in paper.get("references", []):

                    ref_id = ref.get("paperId")

                    if ref_id:
                        refs.append(ref_id)

                reference_map[paper_id] = refs

            return reference_map

        if r.status_code == 429:

            print(f"Rate limit hit during batch fetch. Waiting {wait}s...")
            time.sleep(wait)
            wait *= 2
            continue

        print("Batch reference fetch failed:", r.status_code)
        return {}

    return {}

def get_references(paper_id):
    """
    Wrapper so the rest of the system can request
    references for a single paper.
    Internally it calls the batch API.
    """

    result = get_references_batch([paper_id])

    return result.get(paper_id, [])