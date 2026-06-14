import asyncio
import os
from backend.services.llm_provider import invoke

async def main():
    try:
        print("Testing Google Gemma model...")
        resp = await invoke("You are a test bot.", "Reply with 'OK'.", "google/gemma-2-9b-it:free", 10)
        print("Gemma Response:", resp)
    except Exception as e:
        print("Gemma Error:", type(e).__name__, str(e))

asyncio.run(main())
