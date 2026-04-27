import requests
import os

def download_pdf_from_url(paper, papers_dir):

    filename = make_safe_filename(paper)
    path = os.path.join(papers_dir, filename)

    # already downloaded
    if os.path.exists(path):
        return path

    arxiv_id = paper.get("arxiv_id")
    pdf_url  = paper.get("pdf_url")

    # Step 1: Try ArXiv FIRST
    if arxiv_id:
        arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        if try_download(arxiv_url, path):
            return path

    # Step 2: Fallback to provided PDF URL
    if pdf_url:
        if try_download(pdf_url, path):
            return path

    # Step 3: Give up
    print(
        f"Download failed: {paper.get('title','')[:60]} "
        f"(arxiv={arxiv_id}, pdf_url={pdf_url})"
    )
    return None


def try_download(url, path):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, timeout=50, headers=headers, allow_redirects=True)
        if r.status_code != 200:
            return False

        content_type = (r.headers.get("content-type") or "").lower()
        body = r.content

        if "pdf" in content_type or body.startswith(b"%PDF"):
            with open(path, "wb") as f:
                f.write(body)
            return True

    except Exception:
        pass

    return False


def make_safe_filename(paper):
    paper_id = paper.get("id", "unknown")
    title = paper.get("title", "")

    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
    safe_title = safe_title.replace(" ", "_")[:50]

    if not safe_title:
        return f"{paper_id}.pdf"

    return f"{paper_id}_{safe_title}.pdf"