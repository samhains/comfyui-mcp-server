import json
import logging
import os
from typing import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
from mcp.server.fastmcp import FastMCP
from comfyui_client import ComfyUIClient, TOOLS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCP_Server")

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()

# Global ComfyUI client
comfyui_client = ComfyUIClient(config["server"]["comfyui_url"])

# Lifespan management
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    logger.info("Starting MCP server lifecycle...")
    try:
        yield
    finally:
        logger.info("Shutting down MCP server")

# Initialize FastMCP
mcp = FastMCP("ComfyUI_MCP_Server", lifespan=app_lifespan)

# --- Auto-register MCP tools from tools.json ---

def _create_mcp_handler(tool_name: str, tool_def: dict):
    """Create a generic MCP tool handler for a given tool definition."""
    output_type = tool_def.get("output", {}).get("type", "image")
    result_key = "video_url" if output_type == "video" else "image_url"

    def handler(params: dict) -> dict:
        logger.info(f"[{tool_name}] params: {params}")
        try:
            result_url = comfyui_client.execute_workflow(tool_name, params)
            logger.info(f"[{tool_name}] result: {result_url}")
            return {result_key: result_url}
        except KeyError as e:
            error_msg = f"Missing required parameter: {str(e).strip(chr(39))}"
            logger.error(f"[{tool_name}] {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            logger.error(f"[{tool_name}] Error: {e}")
            return {"error": str(e)}

    handler.__name__ = tool_name
    handler.__doc__ = tool_def["description"]
    return handler

for _tool_name, _tool_def in TOOLS.items():
    mcp.tool()(_create_mcp_handler(_tool_name, _tool_def))

# --- FastAPI HTTP server ---

app = FastAPI(title="ComfyUI MCP Server")

def _create_http_handler(tool_name: str):
    """Create a generic HTTP endpoint handler."""
    mcp_handler = _create_mcp_handler(tool_name, TOOLS[tool_name])

    async def handler(params: dict):
        logger.info(f"[HTTP:{tool_name}] params: {params}")
        return mcp_handler(params)

    handler.__name__ = f"{tool_name}_http"
    return handler

for _tool_name in TOOLS:
    app.post(f"/{_tool_name}")(_create_http_handler(_tool_name))

# --- SSE streaming endpoints (unique logic, kept explicit) ---

@app.post("/generate_image_stream")
async def generate_image_stream(params: dict):
    """SSE endpoint for streaming image generation progress"""
    async def event_stream():
        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing image generation...'})}\n\n"
            handler = _create_mcp_handler("generate_image", TOOLS["generate_image"])
            result = handler(params)
            yield f"data: {json.dumps({'status': 'processing', 'message': 'Generating image...'})}\n\n"
            yield f"data: {json.dumps({'status': 'complete', 'result': result})}\n\n"
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"})

@app.post("/generate_video_stream")
async def generate_video_stream(params: dict):
    """SSE endpoint for streaming video generation progress"""
    async def event_stream():
        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing video generation...'})}\n\n"
            handler = _create_mcp_handler("generate_video", TOOLS["generate_video"])
            result = handler(params)
            yield f"data: {json.dumps({'status': 'processing', 'message': 'Generating video...'})}\n\n"
            yield f"data: {json.dumps({'status': 'complete', 'result': result})}\n\n"
        except Exception as e:
            logger.error(f"Error in video stream: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"})

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ComfyUI MCP Server"}

if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        logger.info("Starting HTTP MCP server on http://0.0.0.0:9000...")
        uvicorn.run(app, host="0.0.0.0", port=9000)
    else:
        logger.info("Starting MCP server...")
        mcp.run()
