import requests
import time
import os

BASE_URL = "https://api.semanticscholar.org/graph/v1"
API_KEY  = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
HEADERS  = {"x-api-key": API_KEY} if API_KEY else {}


def search_papers(query, limit=5):
    print(f"Searching: {query}")
    url    = f"{BASE_URL}/paper/search"
    params = {
        "query":  query,
        "limit":  limit,
        "fields": "paperId,title,year,citationCount,externalIds"
    }

    wait = 3
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)

            if r.status_code == 200:
                papers = []
                for p in r.json().get("data", []):
                    arxiv_id = (p.get("externalIds") or {}).get("ArXiv")
                    papers.append({
                        "id":        p["paperId"],
                        "arxiv_id":  arxiv_id,
                        "title":     p.get("title", ""),
                        "year":      p.get("year") or 2024,
                        "citations": p.get("citationCount", 0),
                    })
                return papers

            if r.status_code == 429:
                print(f"Rate limit, waiting {wait}s...")
                time.sleep(wait)
                wait *= 2
                continue

            print(f"Search failed: {r.status_code}")
            return []

        except Exception as e:
            print(f"Search error: {e}")
            return []

    return []


def get_references(paper_id, min_citations=1000):
    print(f"Fetching refs for {paper_id[:20]}...")
    url    = f"{BASE_URL}/paper/{paper_id}"
    params = {
        "fields": "references,references.paperId,references.title,"
                  "references.year,references.citationCount,references.externalIds"
    }

    wait = 3
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)

            if r.status_code == 200:
                data     = r.json()
                refs_raw = data.get("references") or []
                refs     = []

                for ref in refs_raw:
                    if not ref:
                        continue
                    citations = ref.get("citationCount") or 0
                    if citations < min_citations:
                        continue
                    arxiv_id = (ref.get("externalIds") or {}).get("ArXiv")
                    if not arxiv_id:
                        continue
                    refs.append({
                        "id":        ref.get("paperId", ""),
                        "arxiv_id":  arxiv_id,
                        "title":     ref.get("title", ""),
                        "year":      ref.get("year") or 2020,
                        "citations": citations,
                    })

                print(f"  Got {len(refs)} refs (after filter)")
                return refs

            if r.status_code == 429:
                print(f"Rate limit, waiting {wait}s...")
                time.sleep(wait)
                wait *= 2
                continue

            print(f"Ref fetch failed: {r.status_code}")
            return []

        except Exception as e:
            print(f"Error fetching refs for {paper_id}: {e}")
            return []

    return []