import asyncio
import os
from backend.services.llm_provider import invoke

async def main():
    try:
        print("Testing Llama 3.2 3B model...")
        resp = await invoke("You are a test bot.", "Reply with 'OK'.", "meta-llama/llama-3.2-3b-instruct:free", 10)
        print("Response:", resp)
    except Exception as e:
        print("Error:", type(e).__name__, str(e))

asyncio.run(main())
