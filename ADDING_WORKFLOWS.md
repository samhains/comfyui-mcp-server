# Adding New Workflows to ComfyUI MCP Server

This guide explains how to add a new workflow to the ComfyUI MCP Server. All the necessary changes are centralized to make this process as simple as possible.

## Overview

The ComfyUI MCP Server supports multiple workflows for different tasks (image generation, video generation, etc.). To add a new workflow, you need to update 3 files:

1. **Add the workflow JSON file** to the `workflows/` directory
2. **Add workflow mapping** to `comfyui_client.py`
3. **Update tool configuration** in `tools.json` (optional, if creating a new tool)

## Step-by-Step Process

### 1. Add Workflow JSON File

Place your ComfyUI workflow JSON file in the `workflows/` directory:

```bash
workflows/your-new-workflow.json
```

**Naming Convention**: Use kebab-case with descriptive names (e.g., `wan2.2-t2v-sd.json`, `flux-dev-workflow.json`)

### 2. Add Workflow Mapping

Edit `comfyui_client.py` and add your workflow mapping to the `WORKFLOW_MAPPINGS` dictionary:

```python
WORKFLOW_MAPPINGS = {
    # ... existing mappings ...
    "your-new-workflow": {
        "prompt": ("NODE_ID", "input_key"),
        "width": ("NODE_ID", "input_key"),
        "height": ("NODE_ID", "input_key"),
        # Add other parameters as needed
    }
}
```

**How to find node IDs and input keys:**
1. Open your workflow JSON file
2. Find the nodes that accept the parameters you want to expose
3. Use the node ID (the key in the JSON) and the input field name

**Example from wan2.2-t2v-sd workflow:**
```python
"wan2.2-t2v-sd": {
    "prompt": ("141", "value"),        # Node 141, input "value"
    "audio_prompt": ("147", "value"),  # Node 147, input "value"
    "width": ("143", "value"),         # Node 143, input "value"
    "height": ("144", "value"),        # Node 144, input "value"
    "frame_length": ("145", "value")   # Node 145, input "value"
}
```

### 3. Update Tool Configuration (if needed)

If you're creating a new tool or want to change which workflow a tool uses, edit `tools.json`:

```json
{
  "tools": {
    "your_tool_name": {
      "description": "Description of what this tool does",
      "workflow_id": "your-new-workflow",
      "parameters": {
        "prompt": {
          "required": true,
          "type": "string",
          "description": "Text description..."
        }
        // ... other parameters
      },
      "workflow_mapping": {
        "prompt": ["141", "value"],
        // ... other mappings (should match comfyui_client.py)
      }
    }
  }
}
```

**To switch an existing tool to a new workflow**, just change the `workflow_id`:
```json
"generate_video": {
  "workflow_id": "wan2.2-t2v-sd"  // Changed from "wan-2.2-t2v-hq"
}
```

### 4. Update Default Configuration (optional)

If your workflow should be the default for a tool, update `config.json`:

```json
{
  "video_generation": {
    "workflow": "your-new-workflow"
  }
}
```

## Testing Your Integration

1. **Start the server**:
   ```bash
   python server.py
   ```

2. **Test via HTTP endpoint**:
   ```bash
   curl -X POST http://localhost:9000/generate_video \
     -H "Content-Type: application/json" \
     -d '{"prompt": "test prompt"}'
   ```

3. **Check logs** for any errors related to node mapping or workflow loading

## Common Issues

### Missing Node IDs
- **Error**: `Node {id} not found in workflow`
- **Solution**: Double-check the node ID exists in your workflow JSON

### Wrong Input Keys
- **Error**: Workflow executes but parameters aren't applied
- **Solution**: Verify the input key names in the workflow JSON

### Workflow File Not Found
- **Error**: `FileNotFoundError` when loading workflow
- **Solution**: Ensure the workflow file is in `workflows/` directory with correct name

## Example: Adding a New Video Workflow

Let's say you want to add a new video workflow called `fast-video-gen.json`:

1. **Add workflow file**: `workflows/fast-video-gen.json`

2. **Add mapping to comfyui_client.py**:
```python
"fast-video-gen": {
    "prompt": ("10", "text"),
    "width": ("20", "width"),
    "height": ("20", "height")
}
```

3. **Update tools.json** (if you want to use this as the default video workflow):
```json
"generate_video": {
  "workflow_id": "fast-video-gen"
}
```

4. **Test the integration**

## Workflow Analysis Tips

To understand a workflow's structure:

1. **Look for primitive inputs** (nodes with `class_type: "PrimitiveInt"` or `"PrimitiveStringMultiline"`)
2. **Check node titles** in `_meta.title` for human-readable names like `"@PROMPT"`, `"@WIDTH"`
3. **Follow the data flow** to understand which nodes accept user inputs

## File Locations Summary

All workflow-related code is centralized in these locations:

- **Workflow files**: `workflows/*.json`
- **Workflow mappings**: `comfyui_client.py` → `WORKFLOW_MAPPINGS`
- **Tool definitions**: `tools.json` → `tools.{tool_name}.workflow_id`
- **Default configurations**: `config.json` → `video_generation.workflow`

This centralized approach makes it easy to add new workflows without touching the core server logic in `server.py`.