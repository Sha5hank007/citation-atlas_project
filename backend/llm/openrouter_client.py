import requests
from backend.config import OPENROUTER_API_KEY


class OpenRouterClient:

    def generate(self, prompt):

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        }

        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        r = requests.post(url, headers=headers, json=payload)

        return r.json()["choices"][0]["message"]["content"]