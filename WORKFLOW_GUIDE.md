# Adding New Workflows to ComfyUI MCP Server

This guide explains how to add a new workflow to the ComfyUI MCP Server.

## Steps to Add a Workflow

### 1. Add the Workflow File
- Place your ComfyUI workflow JSON file in the `workflows/` directory
- Use a descriptive filename like `{workflow-name}-workflow.json`
- Example: `mmaudio-workflow.json`

### 2. Update tools.json
Add your new tool configuration to `tools.json`:

```json
{
  "tools": {
    "your_tool_name": {
      "description": "Description of what this tool does",
      "workflow_id": "your-workflow-name",
      "resolution": {
        "width": 768,
        "height": 512
      },
      "timeout": 600,
      "parameters": {
        "prompt": {
          "required": true,
          "type": "string",
          "description": "Text description of what to generate"
        }
      },
      "workflow_mapping": {
        "prompt": ["6", "text"]
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
    "mmaudio-workflow": {
        "prompt": ("6", "text")  # Maps to node "6", input "text"
    }
}
```

The mapping defines how parameters are passed to your workflow:
- Key: Parameter name (e.g., "prompt", "width", "height")
- Value: Tuple of (node_id, input_key) in your workflow JSON

### 4. Identify Node IDs and Input Keys
To find the correct node IDs and input keys:
1. Open your workflow JSON file
2. Find the node that should receive the parameter
3. Note the node's key (e.g., "6", "27", "83:75")
4. Note the input field name (e.g., "text", "width", "height")

### 5. Test the Integration
After making these changes:
1. Restart the server
2. Test the workflow through the API
3. Check logs for any errors

## Files That Need Updates

When adding a workflow, you need to update:
1. `workflows/{workflow-name}.json` - The workflow file itself
2. `tools.json` - Tool configuration and documentation
3. `comfyui_client.py` - Workflow mapping

## Example: MMAudio Workflow

The MMAudio workflow was added with these changes:
- File: `workflows/mmaudio-workflow.json`
- Config: `"workflow_id": "mmaudio-workflow"`
- Mapping: `"mmaudio-workflow": {"prompt": ("6", "text")}`