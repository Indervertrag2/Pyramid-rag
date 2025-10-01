import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.ollama_client import OllamaClient

async def test_ollama():
    """Test Ollama directly"""
    client = OllamaClient()

    # Test health check
    health = await client.check_health()
    print("Health check:", health)

    # Test generate_response
    print("\nTesting generate_response...")
    response = await client.generate_response(
        query="Hallo, wie geht es dir?",
        context="",
        temperature=0.7
    )
    print(f"Response: {response}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(test_ollama())