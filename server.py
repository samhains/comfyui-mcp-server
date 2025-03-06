import asyncio
import json
import logging
import websockets
from mcp.server.fastmcp import FastMCP
from comfyui_client import ComfyUIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCP_Server")

mcp = FastMCP("ComfyUI_MCP_Server")
comfyui_client = ComfyUIClient("http://localhost:8188")

@mcp.tool()
def generate_image(params: str) -> dict:
    logger.info(f"Received request with params: {params}")
    try:
        param_dict = json.loads(params)
        prompt = param_dict["prompt"]
        width = param_dict.get("width", 512)
        height = param_dict.get("height", 512)
       # In generate_image function:
        image_path = comfyui_client.generate_image(prompt, width, height)
        image_url = image_path  # Already includes full URL with /view
        logger.info(f"Returning image URL: {image_url}")
        return {"image_url": image_url}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

async def handle_websocket(websocket, path):
    logger.info("WebSocket client connected")
    try:
        async for message in websocket:
            request = json.loads(message)
            logger.info(f"Received message: {request}")
            if request.get("tool") == "generate_image":
                result = generate_image(request.get("params", ""))
                await websocket.send(json.dumps(result))
            else:
                await websocket.send(json.dumps({"error": "Unknown tool"}))
    except websockets.ConnectionClosed:
        logger.info("WebSocket client disconnected")

async def main():
    logger.info("Starting MCP server on ws://localhost:9000...")
    async with websockets.serve(handle_websocket, "localhost", 9000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())