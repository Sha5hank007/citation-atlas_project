import requests
import aiohttp
import asyncio
import time
import os
import re

BASE_URL = "https://api.semanticscholar.org/graph/v1"
API_KEY  = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
HEADERS  = {"x-api-key": API_KEY} if API_KEY else {}


def _normalize_arxiv_id(arxiv_id):
    if not arxiv_id:
        return arxiv_id
    return re.sub(r"v\d+$", "", arxiv_id)


def resolve_paper_id_by_arxiv(arxiv_id):
    if not arxiv_id:
        return None

    arxiv_id = _normalize_arxiv_id(arxiv_id)
    print(f"Resolving Semantic Scholar paper for arXiv:{arxiv_id}")

    url = f"{BASE_URL}/paper/ARXIV:{arxiv_id}"
    params = {"fields": "paperId"}
    wait = 3

    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=48)
            if r.status_code == 200:
                return r.json().get("paperId")

            if r.status_code == 429:
                print(f"Rate limit resolving arXiv id, waiting {wait}s...")
                time.sleep(wait)
                wait *= 2
                continue

            if r.status_code == 404:
                break

            print(f"Semantic Scholar resolve failed: {r.status_code}")
            return None

        except Exception as e:
            print(f"Resolve error: {e}")
            return None

    url = f"{BASE_URL}/paper/search"
    params = {
        "query": f"arXiv:{arxiv_id}",
        "limit": 1,
        "fields": "paperId,externalIds"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=48)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return data[0].get("paperId")
    except Exception as e:
        print(f"Resolve fallback error: {e}")

    return None


def get_references_by_arxiv_id(arxiv_id, min_citations=1000):
    paper_id = resolve_paper_id_by_arxiv(arxiv_id)
    if not paper_id:
        print(f"Could not resolve Semantic Scholar paper for arXiv:{arxiv_id}")
        return []
    return get_references(paper_id, min_citations=min_citations)


def search_papers(query, limit=5):
    print(f"Searching: {query}")
    url    = f"{BASE_URL}/paper/search"
    params = {
        "query":  query,
        "limit":  limit,
        "fields": (
            "paperId,title,abstract,year,citationCount,"
            "externalIds,openAccessPdf"
        )
    }

    wait = 3
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=48)

            if r.status_code == 200:
                papers = []
                for p in r.json().get("data", []):
                    arxiv_id = (p.get("externalIds") or {}).get("ArXiv")
                    pdf_url  = (p.get("openAccessPdf") or {}).get("url")

                    papers.append({
                        "id":        p["paperId"],
                        "arxiv_id":  arxiv_id,
                        "pdf_url":   pdf_url,  # future fallback
                        "title":     p.get("title", ""),
                        "abstract":  p.get("abstract", ""), 
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


async def resolve_paper_id_by_arxiv_async(arxiv_id, session=None):
    """Async version of resolve_paper_id_by_arxiv"""
    if not arxiv_id:
        return None

    arxiv_id = _normalize_arxiv_id(arxiv_id)
    print(f"Resolving Semantic Scholar paper for arXiv:{arxiv_id}")

    url = f"{BASE_URL}/paper/ARXIV:{arxiv_id}"
    params = {"fields": "paperId"}
    wait = 3

    should_close_session = session is None
    if session is None:
        session = aiohttp.ClientSession(headers=HEADERS)

    try:
        for attempt in range(5):
            try:
                async with session.get(url, params=params, timeout=48) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("paperId")

                    if response.status == 429:
                        print(f"Rate limit resolving arXiv id, waiting {wait}s...")
                        await asyncio.sleep(wait)
                        wait *= 2
                        continue

                    if response.status == 404:
                        break

                    print(f"Semantic Scholar resolve failed: {response.status}")
                    return None

            except Exception as e:
                print(f"Resolve error: {e}")
                return None

        # Fallback search
        url = f"{BASE_URL}/paper/search"
        params = {
            "query": f"arxiv:{arxiv_id}",
            "fields": "paperId",
            "limit": 1
        }

        for attempt in range(3):
            try:
                async with session.get(url, params=params, timeout=48) as response:
                    if response.status == 200:
                        data = await response.json()
                        papers = data.get("data", [])
                        if papers:
                            return papers[0].get("paperId")
                        break

                    if response.status == 429:
                        print(f"Rate limit search, waiting {wait}s...")
                        await asyncio.sleep(wait)
                        wait *= 2
                        continue

            except Exception as e:
                print(f"Search error: {e}")
                return None

    finally:
        if should_close_session:
            await session.close()

    return None


def get_references(paper_id, min_citations=1000):
    print(f"Fetching refs for {paper_id[:20]}...")
    url    = f"{BASE_URL}/paper/{paper_id}"
    params = {
        "fields": (
            "references,references.paperId,references.title,"
            "references.abstract," 
            "references.year,references.citationCount,"
            "references.externalIds,references.openAccessPdf"
        )
    }

    wait = 3
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=48)

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
                    pdf_url  = (ref.get("openAccessPdf") or {}).get("url")

                    refs.append({
                        "id":        ref.get("paperId", ""),
                        "arxiv_id":  arxiv_id,
                        "pdf_url":   pdf_url,  # 🔥 future use
                        "title":     ref.get("title", ""),
                        "abstract":  ref.get("abstract", ""), 
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

