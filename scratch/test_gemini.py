import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    print(f"API key: {api_key}")
    
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-exp"]
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": "Hello, write a 3 word response."}]}],
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                print(f"\nModel: {model}")
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Failed for {model}: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
