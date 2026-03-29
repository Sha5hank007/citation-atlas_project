import requests
import os


def download_arxiv_pdf(arxiv_url, run_path):

    arxiv_id = arxiv_url.split("/")[-1]

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    save_dir = f"{run_path}/papers"

    os.makedirs(save_dir, exist_ok=True)

    save_path = f"{save_dir}/{arxiv_id}.pdf"

    try:

        r = requests.get(pdf_url)

        with open(save_path, "wb") as f:
            f.write(r.content)

        return save_path

    except Exception as e:

        print("PDF download failed:", e)

        return None