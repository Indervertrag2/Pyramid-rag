import asyncio
import httpx
import json

async def test_mcp():
    """Test the MCP endpoint directly"""

    # First, let's login to get a token
    async with httpx.AsyncClient() as client:
        # Login
        login_response = await client.post(
            "http://localhost:18000/api/v1/auth/login",
            json={
                "email": "admin@pyramid-computer.de",
                "password": "admin123"
            }
        )

        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            print(login_response.text)
            return

        token = login_response.json()["access_token"]
        print(f"Got token: {token[:20]}...")

        # Now test the MCP endpoint
        mcp_response = await client.post(
            "http://localhost:18000/api/v1/mcp/message?session_id=test-session-123",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "role": "user",
                "content": "Hallo, wie geht es dir?"
            }
        )

        print(f"MCP Response Status: {mcp_response.status_code}")
        if mcp_response.status_code == 200:
            print(f"MCP Response: {json.dumps(mcp_response.json(), indent=2)}")
        else:
            print(f"Error: {mcp_response.text}")

if __name__ == "__main__":
    asyncio.run(test_mcp())