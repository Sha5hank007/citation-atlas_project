import requests
import xml.etree.ElementTree as ET


def search_papers(query, limit=5):

    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results={limit}"

    r = requests.get(url)

    root = ET.fromstring(r.text)

    papers = []

    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):

        paper_id = entry.find("{http://www.w3.org/2005/Atom}id").text
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        published = entry.find("{http://www.w3.org/2005/Atom}published").text[:4]

        papers.append({
            "id": paper_id,
            "title": title.strip(),
            "year": published,
            "citations": 0
        })

    return papers


def get_references(paper_id):

    # arXiv API does not provide citation graph
    return []