import requests
from backend.config import OPENROUTER_API_KEY


class OpenRouterClient:

    def generate(self, prompt):

        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=20)

            if r.status_code != 200:
                print("OpenRouter HTTP ERROR:", r.status_code, r.text)
                return ""

            data = r.json()

            return data["choices"][0]["message"]["content"]

        except Exception as e:
            print("OpenRouter ERROR:", str(e))
            return ""