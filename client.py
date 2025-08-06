import asyncio
import aiohttp
import json
import argparse

payload = {
    "prompt": "a super dooper weirdo oddly satisfying jelly castle scissors and tactile",
    "width": 1024,
    "height": 1024,
    "workflow_id": "flux-dev-workflow",
    "model": "flux1-dev-fp8.safetensors"
}

async def test_mcp_server(host="localhost"):
    url = f"http://{host}:9000/generate_image"
    try:
        async with aiohttp.ClientSession() as session:
            print("Connecting to HTTP MCP server...")
            async with session.post(url, json=payload) as response:
                response_data = await response.json()
                
                # Replace localhost with the actual host in image_url
                if "image_url" in response_data and host != "localhost":
                    response_data["image_url"] = response_data["image_url"].replace("localhost", host)
                
                print("Response from server:")
                print(json.dumps(response_data, indent=2))
    except Exception as e:
        print(f"HTTP error: {e}")

async def test_mcp_server_stream(host="localhost"):
    url = f"http://{host}:9000/generate_image_stream"
    try:
        async with aiohttp.ClientSession() as session:
            print("Connecting to HTTP MCP server with streaming...")
            async with session.post(url, json=payload) as response:
                print("Streaming response:")
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                            print(f"  {data}")
                            
                            # Replace localhost with the actual host in final result
                            if data.get('status') == 'complete' and host != "localhost":
                                result = data.get('result', {})
                                if "image_url" in result:
                                    result["image_url"] = result["image_url"].replace("localhost", host)
                                    print(f"  Updated URL: {result['image_url']}")
    except Exception as e:
        print(f"Streaming error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP server with HTTP")
    parser.add_argument("--tailscale", action="store_true", help="Use Tailscale address (100.75.77.33)")
    parser.add_argument("--host", type=str, help="Custom host address")
    parser.add_argument("--stream", action="store_true", help="Use streaming endpoint")
    args = parser.parse_args()
    
    host = "localhost"
    if args.tailscale:
        host = "100.75.77.33"
    elif args.host:
        host = args.host
    
    if args.stream:
        print(f"Testing MCP server with HTTP streaming at {host}:9000...")
        asyncio.run(test_mcp_server_stream(host))
    else:
        print(f"Testing MCP server with HTTP at {host}:9000...")
        asyncio.run(test_mcp_server(host))
