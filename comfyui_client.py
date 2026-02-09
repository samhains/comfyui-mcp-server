import requests
import json
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComfyUIClient")


def _load_tools():
    """Load tool definitions from tools.json (single source of truth)."""
    tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools.json")
    with open(tools_path, "r") as f:
        return json.load(f).get("tools", {})


def _build_workflow_specs(tools: dict) -> dict:
    """Build WORKFLOW_SPECS from tools.json definitions."""
    specs = {}
    for tool_name, tool_def in tools.items():
        workflow_id = tool_def["workflow_id"]
        params = {}
        for param_name, param_def in tool_def.get("parameters", {}).items():
            if "node_id" in param_def and "input_key" in param_def:
                params[param_name] = (param_def["node_id"], param_def["input_key"])
        specs[workflow_id] = {
            "params": params,
            "output": tool_def.get("output", {"type": "image"}),
        }
    return specs


# Build specs once at module load
TOOLS = _load_tools()
WORKFLOW_SPECS = _build_workflow_specs(TOOLS)


def _apply_params_to_workflow(workflow: dict, workflow_id: str, params: dict):
    spec = WORKFLOW_SPECS.get(workflow_id, {})
    mapping = spec.get("params", {})
    logger.info(f"Using mapping for workflow {workflow_id}: {mapping}")
    for param_key, value in params.items():
        if param_key in mapping:
            node_id, input_key = mapping[param_key]
            if node_id not in workflow:
                raise Exception(f"Node {node_id} not found in workflow {workflow_id}")
            workflow[node_id]["inputs"][input_key] = value


def _extract_output_url(base_url: str, outputs: dict, workflow_id: str):
    spec = WORKFLOW_SPECS.get(workflow_id, {})
    out_spec = spec.get("output", {})
    node_id = out_spec.get("node_id")
    output_type = out_spec.get("type", "image")

    if node_id:
        if node_id not in outputs:
            raise Exception(f"Output node {node_id} not found in outputs: {outputs}")
        node_out = outputs[node_id]
        if output_type == "image" and "images" in node_out:
            data = node_out["images"][0]
        elif output_type == "video":
            if "images" in node_out:
                data = node_out["images"][0]
            elif "gifs" in node_out:
                data = node_out["gifs"][0]
            elif "filenames" in node_out:
                data = node_out["filenames"][0]
            else:
                raise Exception(f"No video output found in node {node_id}: {node_out}")
        else:
            key = next((k for k in ("images", "gifs", "filenames") if k in node_out), None)
            if not key:
                raise Exception(f"No recognizable outputs in node {node_id}: {node_out}")
            data = node_out[key][0]
    else:
        # Fallback: first node with images
        image_node = next((nid for nid, out in outputs.items() if "images" in out), None)
        if not image_node:
            raise Exception(f"No output node with images found: {outputs}")
        data = outputs[image_node]["images"][0]

    filename = data["filename"]
    subfolder = data.get("subfolder", "")
    return f"{base_url}/view?filename={filename}&subfolder={subfolder}&type=output"


class ComfyUIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def execute_workflow(self, tool_name: str, params: dict) -> str:
        """Generic workflow executor. Loads tool def from tools.json, applies params, submits, polls, returns output URL.

        Args:
            tool_name: Key in tools.json (e.g. "generate_i2v")
            params: User-provided parameters (required + optional)

        Returns:
            str: URL to the generated output file
        """
        tool_def = TOOLS.get(tool_name)
        if not tool_def:
            raise Exception(f"Unknown tool: {tool_name}")

        workflow_id = tool_def["workflow_id"]
        param_defs = tool_def.get("parameters", {})

        # Validate required params
        for param_name, param_def in param_defs.items():
            if param_def.get("required") and param_name not in params:
                raise KeyError(param_name)

        # Build final params: user value > default > skip
        final_params = {}
        for param_name, param_def in param_defs.items():
            if param_name in params:
                final_params[param_name] = params[param_name]
            elif "default" in param_def:
                final_params[param_name] = param_def["default"]
            # else: skip — let workflow's baked-in value stand

        # Load workflow
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workflow_file = os.path.join(script_dir, "workflows", f"{workflow_id}.json")
        with open(workflow_file, "r") as f:
            workflow = json.load(f)

        _apply_params_to_workflow(workflow, workflow_id, final_params)

        # Submit
        logger.info(f"Submitting {tool_name} workflow ({workflow_id}) to ComfyUI...")
        response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
        if response.status_code != 200:
            raise Exception(f"Failed to queue workflow: {response.status_code} - {response.text}")

        prompt_id = response.json()["prompt_id"]
        logger.info(f"Queued {tool_name} with prompt_id: {prompt_id}")

        # Poll for completion
        while True:
            history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
            if history.get(prompt_id):
                outputs = history[prompt_id]["outputs"]
                logger.info(f"{tool_name} outputs: %s", json.dumps(outputs, indent=2))
                result_url = _extract_output_url(self.base_url, outputs, workflow_id)
                logger.info(f"{tool_name} result URL: {result_url}")
                return result_url
            time.sleep(1)
