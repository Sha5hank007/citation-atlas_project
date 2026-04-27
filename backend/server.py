import sys
import os
import json
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Body
from pydantic import BaseModel

from backend.main import run_pipeline_async
from backend.rag.query import query_db
from backend.llm.client import get_llm

current_run = None
current_vector_db = None  # set this when vector DB is initialized


class AskRequest(BaseModel):
    question: str
    paper_id: str | None = None
    paper_ids: list[str] | None = None


app = FastAPI()

status = {
    "step": "idle",
    "message": ""
}

def update_status(msg, step="running"):
    status["message"] = msg
    status["step"] = step

# serve frontend folder
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


@app.get("/graph")
def graph():
    if not current_run:
         return {"error": "no active run"}

    path = f"runs/{current_run}/graph.json"
    if not os.path.exists(path):
        return {"nodes": [], "links": []}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/status")
def get_status():
    return status


from backend.runs.run_manager import create_run

@app.post("/run_pipeline")
def run(topic: str):

    
    run_id, run_path = create_run(topic)

    async def task():
        global current_run, current_vector_db

        try:
            status["step"] = "running"
            status["message"] = "Starting pipeline"

            await run_pipeline_async(topic, update_status, run_id, run_path)

            current_run = run_id
            current_vector_db = f"{run_path}/vector_db"

            status["step"] = "complete"
            status["message"] = "Graph ready"

        except Exception as e:
            print("Pipeline error:", e)
            status["step"] = "error"
            status["message"] = str(e)
        

    import asyncio
    
    def run_async_task():
        asyncio.run(task())
    
    thread = threading.Thread(target=run_async_task)
    thread.start()

    # return run_id to frontend
    return {"run_id": run_id}

@app.get("/summary")
def get_summary(run_id: str):
    path = f"runs/{run_id}/summary.json"

    if not os.path.exists(path):
        return {"summary": ""}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/ask")
def ask(payload: dict = Body(...)):

    question = payload.get("question")
    paper_ids = payload.get("paper_ids", [])

    docs, metas = query_db(
        question,
        current_vector_db,
        paper_ids=paper_ids,
        top_k=8
    )

    if len(docs) == 0:
        return {"error": "No relevant chunks found for selected papers"}

    llm = get_llm()

    # limit context size for LLM
    context = "\n\n".join(docs[:5])

    prompt = f"""
Answer clearly using ONLY the context.

Context:
{context}

Question:
{question}

- Use bullet points
- Be concise
"""

    answer = llm.generate(prompt)
    if not answer or not answer.strip():
        answer = "LLM failed to generate a response. Please try again."

    source_papers = list(set([
        m.get("paper_id") for m in metas if m and m.get("paper_id")
    ]))

    return {
        "answer": answer,
        "chunks_used": len(docs),
        "chunks": docs,
        "source_papers": source_papers
    }

@app.get("/runs")
def list_runs():

    runs = []

    for r in os.listdir("runs"):

        info_path = f"runs/{r}/run_info.json"

        if os.path.exists(info_path):
            with open(info_path) as f:
                info = json.load(f)

            runs.append({
                "id": r,
                "label": info.get("topic", r) + " (" + r.split("__")[-1] + ")"
            })
        else:
            runs.append({
                "id": r,
                "label": r
            })

    runs.sort(key=lambda x: x["id"], reverse=True)
    
    return runs


@app.post("/load_run")
def load_run(run_id: str):
    global current_run, current_vector_db

    current_run = run_id
    current_vector_db = f"runs/{run_id}/vector_db"

    return {"status": "loaded"}