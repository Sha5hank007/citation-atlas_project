import requests
import os


def download_arxiv_pdf(arxiv_id, run_path):
    """
    arxiv_id: bare id like "1706.03762" or "2301.07041v2"
    """
    # strip version suffix if present e.g. 1706.03762v5 → 1706.03762
    bare = arxiv_id.split("v")[0]

    pdf_url  = f"https://arxiv.org/pdf/{bare}.pdf"
    save_dir = f"{run_path}/papers"
    os.makedirs(save_dir, exist_ok=True)
    save_path = f"{save_dir}/{bare}.pdf"

    # skip if already downloaded
    if os.path.exists(save_path):
        return save_path

    try:
        r = requests.get(pdf_url, timeout=15)
        if r.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return save_path
        else:
            print(f"PDF download failed {bare}: status {r.status_code}")
            return None

    except Exception as e:
        print(f"PDF download error {bare}: {e}")
        return None