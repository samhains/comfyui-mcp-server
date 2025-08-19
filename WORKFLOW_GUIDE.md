# Adding New Workflows to ComfyUI MCP Server

This guide explains how to add a new workflow to the ComfyUI MCP Server.

## ⚠️ CRITICAL: Output Node Handling

**ALWAYS use hardcoded output node IDs from your workflow - NEVER use dynamic searching!**

The output node configuration in `tools.json` must match exactly what's in your workflow:

```json
"output_node": {
  "node_id": "9",
  "class_type": "SaveImage", 
  "title": "SAVE_IMAGE",
  "output_type": "image"
}
```

## ⚠️ CRITICAL: Image Loading 

**Standard ComfyUI `LoadImage` nodes do NOT support URLs!**

For workflows that need to load images from URLs:
- ✅ **Use `LoadImageFromUrlOrPath` nodes** (requires custom node installation)  
- ❌ **Do NOT use standard `LoadImage` nodes with URLs**

## Steps to Add a Workflow

### 1. Add the Workflow File
- Place your ComfyUI workflow JSON file in the `workflows/` directory
- Use a descriptive filename like `{workflow-name}.json` 
- Example: `flux-2-redux.json`

### 2. Update tools.json
Add your new tool configuration to `tools.json`:

```json
{
  "tools": {
    "remix_image": {
      "description": "Generates images using 2 input images with Flux Redux style conditioning through ComfyUI",
      "workflow_id": "flux-2-redux",
      "parameters": {
        "image1_url": {
          "required": true,
          "type": "string",
          "description": "URL to the first reference image for style conditioning"
        },
        "image2_url": {
          "required": true,
          "type": "string", 
          "description": "URL to the second reference image for style conditioning"
        },
        "width": {
          "required": false,
          "type": "integer",
          "description": "Image width in pixels"
        },
        "height": {
          "required": false,
          "type": "integer",
          "description": "Image height in pixels"
        }
      },
      "workflow_mapping": {
        "description": "Maps parameters to ComfyUI workflow nodes",
        "image1_url": ["69", "url_or_path"],
        "image2_url": ["70", "url_or_path"],
        "width": ["62", "value"],
        "height": ["65", "value"]
      },
      "output_node": {
        "node_id": "9",
        "class_type": "SaveImage",
        "title": "SAVE_IMAGE",
        "output_type": "image"
      }
    }
  }
}
```

### 3. Add Workflow Mapping
In `comfyui_client.py`, add a mapping entry to `WORKFLOW_MAPPINGS`:

```python
WORKFLOW_MAPPINGS = {
    # ... existing mappings ...
    "flux-2-redux": {
        "image1_url": ("69", "url_or_path"),
        "image2_url": ("70", "url_or_path"),
        "width": ("62", "value"),
        "height": ("65", "value")
    }
}
```

The mapping defines how parameters are passed to your workflow:
- Key: Parameter name (e.g., "image1_url", "width", "height")
- Value: Tuple of (node_id, input_key) in your workflow JSON

### 4. Add Server Method
In `server.py`, add the MCP tool function:

```python
@mcp.tool()
def remix_image(params: dict) -> dict:
    """Generate an image using 2 input images with Flux Redux through ComfyUI"""
    logger.info(f"Received remix image request with params: {params}")
    try:
        param_dict = params
        
        # Required parameters
        image1_url = param_dict["image1_url"]
        image2_url = param_dict["image2_url"]
        
        # Optional parameters
        width = param_dict.get("width")
        height = param_dict.get("height")
        
        # Use global comfyui_client
        image_url = comfyui_client.remix_image(
            image1_url=image1_url,
            image2_url=image2_url,
            width=width,
            height=height
        )
        
        logger.info(f"Returning remix image URL: {image_url}")
        return {"image_url": image_url}
        
    except KeyError as e:
        missing_param = str(e).strip("'")
        error_msg = f"Missing required parameter: {missing_param}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}
```

### 5. Add Client Method
In `comfyui_client.py`, add the client method:

```python
def remix_image(self, image1_url, image2_url, width=None, height=None):
    """Generate image using 2 input images with Flux Redux style conditioning"""
    try:
        workflow_id = "flux-2-redux"
        
        # Load workflow
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_file = os.path.join(script_dir, "workflows", f"{workflow_id}.json")
        with open(workflow_file, "r") as f:
            workflow = json.load(f)

        # Get the appropriate mapping for this workflow
        mapping = WORKFLOW_MAPPINGS.get(workflow_id, DEFAULT_MAPPING)
        logger.info(f"Using mapping for workflow {workflow_id}: {mapping}")

        # Prepare parameters with defaults
        params = {
            "image1_url": image1_url,
            "image2_url": image2_url,
            "width": width or 720,
            "height": height or 720
        }

        # Apply parameters to workflow nodes
        for param_key, value in params.items():
            if param_key in mapping:
                node_id, input_key = mapping[param_key]
                if node_id not in workflow:
                    raise Exception(f"Node {node_id} not found in workflow {workflow_id}")
                workflow[node_id]["inputs"][input_key] = value
                logger.info(f"Set {param_key} -> node {node_id}[{input_key}] = {value}")

        # Submit workflow and wait for results
        response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
        if response.status_code != 200:
            raise Exception(f"Failed to queue workflow: {response.status_code} - {response.text}")

        prompt_id = response.json()["prompt_id"]
        logger.info(f"Queued remix image workflow with prompt_id: {prompt_id}")

        # Wait for completion and get results using HARDCODED output node
        while True:
            history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
            if history.get(prompt_id):
                outputs = history[prompt_id]["outputs"]
                logger.info("Remix image workflow outputs: %s", json.dumps(outputs, indent=2))
                
                # Use the configured output node from tools.json (node 9 = SAVE_IMAGE)
                output_node_id = "9"
                if output_node_id not in outputs:
                    raise Exception(f"Output node {output_node_id} not found in outputs: {outputs}")
                
                image_data = outputs[output_node_id]["images"][0]
                image_filename = image_data["filename"]
                subfolder = image_data.get("subfolder", "")
                image_url = f"{self.base_url}/view?filename={image_filename}&subfolder={subfolder}&type=output"
                
                logger.info(f"Generated remix image URL: {image_url}")
                return image_url
                
            time.sleep(1)

    except Exception as e:
        raise Exception(f"Error generating remix image: {e}")
```

### 6. Identify Node IDs and Input Keys
To find the correct node IDs and input keys:
1. Open your workflow JSON file
2. Find the node that should receive the parameter
3. Note the node's key (e.g., "69", "70", "62")
4. Note the input field name (e.g., "url_or_path", "value")

For the flux-2-redux workflow:
- Node 69: `LoadImageFromUrlOrPath` with `url_or_path` input (@IMAGE_1)
- Node 70: `LoadImageFromUrlOrPath` with `url_or_path` input (@IMAGE_2)  
- Node 62: `PrimitiveInt` with `value` input (@WIDTH)
- Node 65: `PrimitiveInt` with `value` input (@HEIGHT)
- Node 9: `SaveImage` output node (SAVE_IMAGE)

### 7. Test the Integration
After making these changes:
1. Restart the server
2. Test the workflow through the API
3. Check logs for parameter mapping confirmation
4. Verify output node detection works

## Complete Checklist: ALL Files That Need Updates

When adding a workflow, you MUST update these 4 files in this order:

### 1. `workflows/{workflow-name}.json`
- **Location**: Root directory `/workflows/` folder
- **Action**: Place your ComfyUI workflow JSON file
- **Naming**: Use format `{workflow-name}.json` (e.g., `flux-2-redux.json`)

### 2. `tools.json` 
- **Location**: Root directory `/tools.json`
- **Action**: Add complete tool definition with:
  - Tool name and description
  - All parameters (required/optional)
  - Workflow mapping (parameter → node mappings)  
  - **CRITICAL**: Output node specification
- **Section**: Add to `"tools": { ... }` object

### 3. `comfyui_client.py`
- **Location**: Root directory `/comfyui_client.py`
- **Actions Required**:
  - **A. Add workflow mapping** to `WORKFLOW_MAPPINGS` dictionary
  - **B. Add client method** to `ComfyUIClient` class

### 4. `server.py`
- **Location**: Root directory `/server.py`  
- **Actions Required**:
  - **A. Add MCP tool function** with `@mcp.tool()` decorator
  - **B. Add HTTP endpoint** for API access

## Detailed Update Instructions

### FILE 1: `workflows/{workflow-name}.json`
```bash
# Simply copy your ComfyUI workflow JSON file to:
workflows/flux-2-redux.json
```

### FILE 2: `tools.json` - ADD TOOL DEFINITION
**Location**: Find the `"tools": {` section and add your tool:

```json
{
  "tools": {
    "your_tool_name": {
      "description": "What this tool does",
      "workflow_id": "your-workflow-name",
      "parameters": {
        "param1": {
          "required": true,
          "type": "string",
          "description": "Description of param1"
        },
        "param2": {
          "required": false, 
          "type": "integer",
          "description": "Description of param2"
        }
      },
      "workflow_mapping": {
        "description": "Maps parameters to ComfyUI workflow nodes",
        "param1": ["node_id", "input_key"],
        "param2": ["node_id", "input_key"]
      },
      "output_node": {
        "node_id": "X",
        "class_type": "SaveImage",
        "title": "SAVE_IMAGE", 
        "output_type": "image"
      }
    }
  }
}
```

### FILE 3A: `comfyui_client.py` - ADD WORKFLOW MAPPING  
**Location**: Find `WORKFLOW_MAPPINGS = {` dictionary and add:

```python
WORKFLOW_MAPPINGS = {
    # ... existing mappings ...
    "your-workflow-name": {
        "param1": ("node_id", "input_key"),
        "param2": ("node_id", "input_key")
    }
}
```

### FILE 3B: `comfyui_client.py` - ADD CLIENT METHOD
**Location**: Add method to `ComfyUIClient` class:

```python
def your_tool_name(self, param1, param2=None):
    """Description of what this method does"""
    try:
        workflow_id = "your-workflow-name"
        
        # Load workflow
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_file = os.path.join(script_dir, "workflows", f"{workflow_id}.json")
        with open(workflow_file, "r") as f:
            workflow = json.load(f)

        # Get mapping
        mapping = WORKFLOW_MAPPINGS.get(workflow_id, DEFAULT_MAPPING)
        logger.info(f"Using mapping for workflow {workflow_id}: {mapping}")

        # Prepare parameters
        params = {
            "param1": param1,
            "param2": param2 or default_value
        }

        # Apply parameters to workflow nodes
        for param_key, value in params.items():
            if param_key in mapping:
                node_id, input_key = mapping[param_key]
                if node_id not in workflow:
                    raise Exception(f"Node {node_id} not found in workflow {workflow_id}")
                workflow[node_id]["inputs"][input_key] = value
                logger.info(f"Set {param_key} -> node {node_id}[{input_key}] = {value}")

        # Submit workflow
        response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
        if response.status_code != 200:
            raise Exception(f"Failed to queue workflow: {response.status_code} - {response.text}")

        prompt_id = response.json()["prompt_id"]
        logger.info(f"Queued workflow with prompt_id: {prompt_id}")

        # Wait for completion - USE HARDCODED OUTPUT NODE
        while True:
            history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
            if history.get(prompt_id):
                outputs = history[prompt_id]["outputs"]
                logger.info("Workflow outputs: %s", json.dumps(outputs, indent=2))
                
                # CRITICAL: Use hardcoded output node from tools.json
                output_node_id = "X"  # Replace X with your actual output node ID
                if output_node_id not in outputs:
                    raise Exception(f"Output node {output_node_id} not found in outputs: {outputs}")
                
                # For IMAGE outputs:
                image_data = outputs[output_node_id]["images"][0]
                image_filename = image_data["filename"]
                subfolder = image_data.get("subfolder", "")
                result_url = f"{self.base_url}/view?filename={image_filename}&subfolder={subfolder}&type=output"
                
                # For VIDEO outputs:
                # video_data = outputs[output_node_id]["gifs"][0]  # or "images" or "filenames"
                # video_filename = video_data["filename"]
                # result_url = f"{self.base_url}/view?filename={video_filename}&subfolder=&type=output"
                
                logger.info(f"Generated result URL: {result_url}")
                return result_url
                
            time.sleep(1)

    except Exception as e:
        raise Exception(f"Error: {e}")
```

### FILE 4A: `server.py` - ADD MCP TOOL FUNCTION
**Location**: Add before the FastAPI app creation:

```python
@mcp.tool()
def your_tool_name(params: dict) -> dict:
    """Description of what this tool does
    
    Args:
        params: Dictionary containing:
            - param1 (required): Description
            - param2 (optional): Description
    
    Returns:
        dict: Contains 'image_url' or 'video_url' on success or 'error' on failure
    """
    logger.info(f"Received request with params: {params}")
    try:
        param_dict = params
        
        # Required parameters
        param1 = param_dict["param1"]
        
        # Optional parameters  
        param2 = param_dict.get("param2")
        
        # Call client method
        result_url = comfyui_client.your_tool_name(
            param1=param1,
            param2=param2
        )
        
        logger.info(f"Returning result URL: {result_url}")
        return {"image_url": result_url}  # or "video_url" for videos
        
    except KeyError as e:
        missing_param = str(e).strip("'")
        error_msg = f"Missing required parameter: {missing_param}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}
```

### FILE 4B: `server.py` - ADD HTTP ENDPOINT  
**Location**: Add after the other `@app.post` endpoints:

```python
@app.post("/your_tool_name")
async def your_tool_name_http(params: dict):
    """HTTP endpoint for your tool"""
    logger.info(f"Received HTTP request with params: {params}")
    try:
        result = your_tool_name(params)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}
```

## Working Example: flux-2-redux Workflow

The flux-2-redux workflow was successfully added with these changes:

### File Structure:
- **Workflow**: `workflows/flux-2-redux.json`
- **Tool ID**: `remix_image` 
- **Workflow ID**: `flux-2-redux`

### Key Nodes:
- **Node 69**: `LoadImageFromUrlOrPath` (@IMAGE_1) - `url_or_path` parameter
- **Node 70**: `LoadImageFromUrlOrPath` (@IMAGE_2) - `url_or_path` parameter  
- **Node 62**: `PrimitiveInt` (@WIDTH) - `value` parameter
- **Node 65**: `PrimitiveInt` (@HEIGHT) - `value` parameter
- **Node 9**: `SaveImage` (SAVE_IMAGE) - **OUTPUT NODE**

### Mapping Configuration:
```python
"flux-2-redux": {
    "image1_url": ("69", "url_or_path"),
    "image2_url": ("70", "url_or_path"),
    "width": ("62", "value"), 
    "height": ("65", "value")
}
```

### Output Node Configuration:
```json
"output_node": {
  "node_id": "9",
  "class_type": "SaveImage",
  "title": "SAVE_IMAGE", 
  "output_type": "image"
}
```

This workflow successfully handles URL-based image loading and produces reliable image outputs using hardcoded node references.