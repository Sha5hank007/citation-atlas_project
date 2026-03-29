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

        r = requests.post(url, headers=headers, json=payload)

        data = r.json()

        return data["choices"][0]["message"]["content"]