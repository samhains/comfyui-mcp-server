import asyncio
import json
import logging
from typing import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import uvicorn
from mcp.server.fastmcp import FastMCP
from comfyui_client import ComfyUIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCP_Server")

# Global ComfyUI client (fallback since context isn't available)
comfyui_client = ComfyUIClient("http://100.75.77.33:8188")

# Define application context (for future use)
class AppContext:
    def __init__(self, comfyui_client: ComfyUIClient):
        self.comfyui_client = comfyui_client

# Lifespan management (placeholder for future context support)
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle"""
    logger.info("Starting MCP server lifecycle...")
    try:
        # Startup: Could add ComfyUI health check here in the future
        logger.info("ComfyUI client initialized globally")
        yield AppContext(comfyui_client=comfyui_client)
    finally:
        # Shutdown: Cleanup (if needed)
        logger.info("Shutting down MCP server")

# Initialize FastMCP with lifespan
mcp = FastMCP("ComfyUI_MCP_Server", lifespan=app_lifespan)

# Define the image generation tool
@mcp.tool()
def generate_image(params: str) -> dict:
    """Generate an image using ComfyUI"""
    logger.info(f"Received request with params: {params}")
    try:
        param_dict = json.loads(params)
        prompt = param_dict["prompt"]
        width = param_dict.get("width", 512)
        height = param_dict.get("height", 512)
        workflow_id = param_dict.get("workflow_id", "basic_api_test")
        model = param_dict.get("model", None)

        # Use global comfyui_client (since mcp.context isn’t available)
        image_url = comfyui_client.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            workflow_id=workflow_id,
            model=model
        )
        logger.info(f"Returning image URL: {image_url}")
        return {"image_url": image_url}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

# Create FastAPI app for HTTP endpoints
app = FastAPI(title="ComfyUI MCP Server")

@app.post("/generate_image")
async def generate_image_http(params: dict):
    """HTTP endpoint for image generation"""
    logger.info(f"Received HTTP request with params: {params}")
    try:
        result = generate_image(json.dumps(params))
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

@app.post("/generate_image_stream")
async def generate_image_stream(params: dict):
    """SSE endpoint for streaming image generation progress"""
    logger.info(f"Received SSE request with params: {params}")
    
    async def event_stream():
        try:
            # Send initial status
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing image generation...'})}\n\n"
            
            # Generate image (this will still use polling internally)
            result = generate_image(json.dumps(params))
            
            # Send progress updates (can be enhanced to show actual ComfyUI progress)
            yield f"data: {json.dumps({'status': 'processing', 'message': 'Generating image...'})}\n\n"
            
            # Send final result
            yield f"data: {json.dumps({'status': 'complete', 'result': result})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

# Health check endpoint
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