import requests
from backend.config import GROQ_API_KEY


class GroqClient:

    def generate(self, prompt):

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=20)

            # 🔥 handle HTTP errors
            if r.status_code != 200:
                print("LLM HTTP ERROR:", r.status_code, r.text)
                return ""

            data = r.json()

            # handle missing "choices"
            if "choices" not in data:
                print("LLM ERROR RESPONSE:", data)
                return ""

            return data["choices"][0]["message"]["content"]

        except Exception as e:
            print("LLM REQUEST FAILED:", str(e))
            return ""