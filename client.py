import asyncio
import websockets
import json
import argparse

payload = {
    "tool": "generate_image",
    "params": json.dumps({
        "prompt": "an english mastiff dog sitting on a large boulder, bright shiny day",
        "width": 1024,
        "height": 1024,
        "workflow_id": "flux-dev-workflow",
        "model": "flux1-dev-fp8.safetensors"
    })
}

async def test_mcp_server(host="localhost"):
    uri = f"ws://{host}:9000"
    try:
        async with websockets.connect(uri) as ws:
            print("Connected to MCP server")
            await ws.send(json.dumps(payload))
            response = await ws.recv()
            print("Response from server:")
            print(json.dumps(json.loads(response), indent=2))
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP server with WebSocket")
    parser.add_argument("--tailscale", action="store_true", help="Use Tailscale address (100.75.77.33)")
    parser.add_argument("--host", type=str, help="Custom host address")
    args = parser.parse_args()
    
    host = "localhost"
    if args.tailscale:
        host = "100.75.77.33"
    elif args.host:
        host = args.host
    
    print(f"Testing MCP server with WebSocket at {host}:9000...")
    asyncio.run(test_mcp_server(host))