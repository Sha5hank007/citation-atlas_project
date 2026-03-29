import json
import time


def log_llm_call(run_path, data):

    log_file = f"{run_path}/logs/llm_calls.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(data) + "\n")