import requests
from backend.config import GEMINI_API_KEY


class GeminiClient:

    def generate(self, prompt):

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        try:
            r = requests.post(url, json=payload, timeout=20)

            if r.status_code != 200:
                print("Gemini HTTP ERROR:", r.status_code, r.text)
                return ""

            data = r.json()

            return data["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as e:
            print("Gemini ERROR:", str(e))
            return ""