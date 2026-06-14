import asyncio
from backend.services.llm_provider import invoke

async def main():
    try:
        print("Testing Planner model...")
        resp = await invoke("You are a test bot.", "Reply with 'OK'.", "meta-llama/llama-3.3-70b-instruct:free", 10)
        print("Planner Response:", resp)
    except Exception as e:
        print("Planner Error:", type(e).__name__, str(e))

asyncio.run(main())
