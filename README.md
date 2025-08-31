# ComfyUI MCP Server

A lightweight Python-based MCP (Model Context Protocol) server that interfaces with a local [ComfyUI](https://github.com/comfyanonymous/ComfyUI) instance to generate images and videos programmatically via AI agent requests.

## Overview

This project enables AI agents to send generation requests to ComfyUI using the MCP protocol. It supports:

### 🎨 Image Generation
- **Tool**: `generate_image`
- **Workflow**: `image_qwen_image` (Qwen-Image)
- **Parameters**: `prompt`, `width`, `height`

### 🎬 Video Generation  
- **Tool**: `generate_video`
- **Workflow**: `wan2.2-t2v-sd` (WAN 2.2 Text-to-Video + MMAudio)
- **Parameters**: `prompt`, `audio_prompt`, `frame_length`, `width`, `height`

### 🎭 3-Image Style Video Generation
- **Tool**: `generate_3_image_video`
- **Workflow**: `flux-3-redux-wan2.2-i2v-sd` (Flux Redux + WAN 2.2 I2V + MMAudio)
- **Parameters**: `image1_url`, `image2_url`, `image3_url`, `prompt`, `audio_prompt`, `frame_length`, `width`, `height`

All tools support both MCP protocol and HTTP API endpoints.

## Prerequisites

- **Python 3.10+**
- **ComfyUI**: Installed and running locally (e.g., on `localhost:8188`).
- **Dependencies**: `requests`, `websockets`, `mcp` (install via pip).

## Setup

1. **Clone the Repository**:
   git clone <your-repo-url>
   cd comfyui-mcp-server

2. **Install Dependencies**:

   pip install requests websockets mcp


3. **Start ComfyUI**:
- Install ComfyUI (see [ComfyUI docs](https://github.com/comfyanonymous/ComfyUI)).
- Run it on port 8188:
  ```
  cd <ComfyUI_dir>
  python main.py --port 8188
  ```

4. **Prepare Workflows**:
- Place API-format workflow files (e.g., `basic_api_test.json`) in the `workflows/` directory.
- Export workflows from ComfyUI’s UI with “Save (API Format)” (enable dev mode in settings).

## Usage

### MCP Server Mode
```bash
python server.py
```
Runs the MCP server for use with MCP-compatible clients.

### HTTP API Mode  
```bash
python server.py --http
```
Starts HTTP server on `http://localhost:9000` with these endpoints:

- `POST /generate_image` - Image generation
- `POST /generate_video` - Video generation  
- `POST /generate_3_image_video` - 3-image style video generation
- `POST /generate_image_stream` - Streaming image generation (SSE)
- `POST /generate_video_stream` - Streaming video generation (SSE)
- `GET /health` - Health check

### Example HTTP Requests

**Image Generation:**
```bash
curl -X POST http://localhost:9000/generate_image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat in space", "width": 1024, "height": 1024}'
```

**Video Generation:**
```bash
curl -X POST http://localhost:9000/generate_video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat walking in a garden", "audio_prompt": "birds chirping"}'
```

**3-Image Video Generation:**
```bash
curl -X POST http://localhost:9000/generate_3_image_video \
  -H "Content-Type: application/json" \
  -d '{
    "image1_url": "https://example.com/img1.jpg",
    "image2_url": "https://example.com/img2.jpg", 
    "image3_url": "https://example.com/img3.jpg",
    "width": 1920,
    "height": 1080,
    "frame_length": 150
  }'
```

## Project Structure

- `server.py`: MCP server with WebSocket transport and lifecycle support.
- `comfyui_client.py`: Interfaces with ComfyUI’s API, handles workflow queuing.
- `client.py`: Test client for sending MCP requests.
- `workflows/`: Directory for API-format workflow JSON files.

## Recent Fixes (2025-08-18)

🔧 **Fixed `generate_3_image_video` Output Node Issue**
- **Problem**: ComfyUI workflow was completing but not returning video files due to missing output node configuration
- **Error**: `"No output node with video found: {'173': {'value': [4.0]}}"`
- **Solution**: Added explicit output configuration to `flux-3-redux-wan2.2-i2v-sd.json` workflow to mark node "125" (VHS_VideoCombine/SAVE_VIDEO) as an output node
- **Result**: The 3-image video generation tool now properly saves and returns MP4 files

## Configuration

The server uses `config.json` and `tools.json` for configuration:
- **config.json**: ComfyUI server settings, resolutions, and general parameters
- **tools.json**: Tool definitions, workflow mappings, and parameter specifications

## Required Models

Ensure these models are installed in your ComfyUI `models/` directory:
- **Qwen Image UNet**: `qwen_image_fp8_e4m3fn.safetensors`
- **Qwen CLIP**: `qwen_2.5_vl_7b_fp8_scaled.safetensors`
- **Qwen VAE**: `qwen_image_vae.safetensors`
- **Qwen Lora**: `Qwen-Image-Lightning-8steps-V1.0.safetensors`
- (If switching back to Flux) **Checkpoint**: `flux1-dev-fp8.safetensors`
- (If switching back to Flux) **CLIP**: `umt5_xxl_fp8_e4m3fn_scaled.safetensors`
- **WAN Models**: WAN 2.2 text-to-video and image-to-video models
- **MMAudio**: Audio generation models for video soundtracks

## Contributing

Feel free to submit issues or PRs to enhance flexibility (e.g., dynamic node mapping, progress streaming).

## License

Apache License
