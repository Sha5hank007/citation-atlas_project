import requests
import aiohttp
import asyncio
import time
import xml.etree.ElementTree as ET

BASE_URL = "http://export.arxiv.org/api/query"


def normalize_text(text):
    if not text:
        return ""
    return " ".join(text.strip().split())


def parse_entry(entry):
    ns = "{http://www.w3.org/2005/Atom}"
    arxiv_id = ""
    arxiv_url = entry.find(ns + "id")
    if arxiv_url is not None and arxiv_url.text:
        arxiv_id = arxiv_url.text.strip().split("/abs/")[-1]

    title = normalize_text(entry.find(ns + "title").text if entry.find(ns + "title") is not None else "")
    abstract = normalize_text(entry.find(ns + "summary").text if entry.find(ns + "summary") is not None else "")
    published = entry.find(ns + "published")
    year = 2024
    if published is not None and published.text:
        try:
            year = int(published.text.strip()[:4])
        except ValueError:
            pass

    return {
        "id":       arxiv_id,
        "arxiv_id": arxiv_id,
        "pdf_url":  f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        "title":    title,
        "abstract": abstract,
        "year":     year,
        "citations": 0,
    }


def search_papers(query, limit=5):
    print(f"Searching ArXiv: {query}")
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    wait = 3
    for attempt in range(5):
        try:
            r = requests.get(BASE_URL, params=params, timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                papers = [parse_entry(entry) for entry in entries if entry is not None]
                return papers

            print(f"ArXiv search failed: {r.status_code}")
            return []

        except Exception as e:
            print(f"ArXiv search error: {e}")
            time.sleep(wait)
            wait *= 2
            continue

    return []


async def search_papers_async(query, limit=5, session=None):
    """Async version of search_papers"""
    print(f"Searching ArXiv: {query}")
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    should_close_session = session is None
    if session is None:
        session = aiohttp.ClientSession()

    try:
        wait = 3
        for attempt in range(5):
            try:
                async with session.get(BASE_URL, params=params, timeout=15) as response:
                    if response.status == 200:
                        text = await response.text()
                        root = ET.fromstring(text)
                        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                        papers = [parse_entry(entry) for entry in entries if entry is not None]
                        return papers

                    print(f"ArXiv search failed: {response.status}")
                    return []

            except Exception as e:
                print(f"ArXiv search error: {e}")
                await asyncio.sleep(wait)
                wait *= 2
                continue

        return []

    finally:
        if should_close_session:
            await session.close()
