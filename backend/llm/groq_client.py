import aiohttp
import asyncio
from backend.config import GROQ_API_KEY


class GroqClient:

    def generate(self, prompt):
        # Synchronous version - check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a new thread for sync call
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._generate_async(prompt))
                return future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self._generate_async(prompt))

    async def generate_async(self, prompt):
        # New async version
        return await self._generate_async(prompt)

    async def _generate_async(self, prompt):
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

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload, timeout=20) as response:
                    if response.status != 200:
                        print("LLM HTTP ERROR:", response.status, await response.text())
                        return ""

                    data = await response.json()

                    if "choices" not in data:
                        print("LLM ERROR RESPONSE:", data)
                        return ""

                    return data["choices"][0]["message"]["content"]

            except Exception as e:
                print("LLM REQUEST FAILED:", str(e))
                return ""