# ComfyUI MCP Server

A lightweight Python-based MCP (Model Context Protocol) server that interfaces with a local [ComfyUI](https://github.com/comfyanonymous/ComfyUI) instance to generate images programmatically via AI agent requests.

## Overview

This project enables AI agents to send image generation requests to ComfyUI using the MCP protocol over WebSocket. It supports:
- Fixed workflow selection (`flux-dev-workflow.json`).
- Dynamic parameters: `prompt`, `width`, and `height` (defaults to 1024x1024).
- Returns image URLs served by ComfyUI.

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

1. **Run the MCP Server**:
   python server.py

- Listens on `ws://localhost:9000`.

2. **Test with the Client**:
   python client.py

- Sends a sample request: `"a dog wearing sunglasses"` using the hardcoded flux-dev workflow.
- Output example:
  ```
  Response from server:
  {
    "image_url": "http://localhost:8188/view?filename=ComfyUI_00001_.png&subfolder=&type=output"
  }
  ```

3. **Custom Requests**:
- Modify `client.py`'s `payload` to change `prompt`, `width`, and `height` parameters.
- Example:
  ```
  "params": json.dumps({
      "prompt": "a cat in space",
      "width": 768,
      "height": 1024
  })
  ```
- If width/height are omitted, they default to 1024x1024.

## Project Structure

- `server.py`: MCP server with WebSocket transport and lifecycle support.
- `comfyui_client.py`: Interfaces with ComfyUI’s API, handles workflow queuing.
- `client.py`: Test client for sending MCP requests.
- `workflows/`: Directory for API-format workflow JSON files.

## Notes

- The workflow uses `flux1-dev-fp8.safetensors` model which must exist in `<ComfyUI_dir>/models/checkpoints/`.
- The MCP SDK lacks native WebSocket transport; this uses a custom implementation.
- Model and other workflow parameters are hardcoded in the `flux-dev-workflow.json` file, except for prompt, width, and height which can be customized.
- Successfully tested with anime-style image generation including Golden Boy art style characters.

## Planned Features

- **Video Generation**: `generate_video_from_image` functionality to create videos from generated or uploaded images.

## Contributing

Feel free to submit issues or PRs to enhance flexibility (e.g., dynamic node mapping, progress streaming).

## License

Apache License