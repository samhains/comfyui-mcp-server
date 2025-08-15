import requests
import json
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComfyUIClient")

WORKFLOW_MAPPINGS = {
    "basic_api_test": {
        "prompt": ("6", "text"),
        "width": ("5", "width"),
        "height": ("5", "height"),
        "model": ("4", "ckpt_name")
    },
    "flux-dev-workflow": {
        "prompt": ("6", "text"),
        "width": ("27", "width"),
        "height": ("27", "height"),
        "model": ("30", "ckpt_name")
    },
    "wan-2.2-t2v-api": {
        "prompt": ("6", "text"),
        "width": ("59", "width"),
        "height": ("59", "height")
    },
    "mmaudio-workflow": {
        "prompt": ("6", "text"),
        "audio_prompt": ("83:75", "prompt"),
        "frame_length": ("59", "length"),
        "width": ("59", "width"),
        "height": ("59", "height")
    },
    "wan-2.2-t2v-hq": {
        "prompt": ("141", "value"),
        "audio_prompt": ("147", "value"),
        "width": ("143", "value"),
        "height": ("144", "value"),
        "frame_length": ("145", "value")
    }
}

DEFAULT_MAPPING = WORKFLOW_MAPPINGS["basic_api_test"]

class ComfyUIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.available_models = self._get_available_models()

    def _get_available_models(self):
        """Fetch list of available checkpoint models from ComfyUI"""
        try:
            response = requests.get(f"{self.base_url}/object_info/CheckpointLoaderSimple")
            if response.status_code != 200:
                logger.warning("Failed to fetch model list; using default handling")
                return []
            data = response.json()
            models = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
            logger.info(f"Available models: {models}")
            return models
        except Exception as e:
            logger.warning(f"Error fetching models: {e}")
            return []

    def generate_image(self, prompt, width, height, workflow_id="basic_api_test", model=None, timeout=300):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            workflow_file = os.path.join(script_dir, "workflows", f"{workflow_id}.json")
            with open(workflow_file, "r") as f:
                workflow = json.load(f)

            # Get the appropriate mapping for this workflow
            mapping = WORKFLOW_MAPPINGS.get(workflow_id, DEFAULT_MAPPING)
            logger.info(f"Using mapping for workflow {workflow_id}: {mapping}")

            params = {"prompt": prompt, "width": width, "height": height}
            if model:
                # Validate or correct model name
                if model.endswith("'"):  # Strip accidental quote
                    model = model.rstrip("'")
                    logger.info(f"Corrected model name: {model}")
                if self.available_models and model not in self.available_models:
                    raise Exception(f"Model '{model}' not in available models: {self.available_models}")
                params["model"] = model

            for param_key, value in params.items():
                if param_key in mapping:
                    node_id, input_key = mapping[param_key]
                    if node_id not in workflow:
                        raise Exception(f"Node {node_id} not found in workflow {workflow_id}")
                    workflow[node_id]["inputs"][input_key] = value

            logger.info(f"Submitting workflow {workflow_id} to ComfyUI...")
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
            if response.status_code != 200:
                raise Exception(f"Failed to queue workflow: {response.status_code} - {response.text}")

            prompt_id = response.json()["prompt_id"]
            logger.info(f"Queued workflow with prompt_id: {prompt_id}")

            max_attempts = timeout  # Use timeout from config
            for _ in range(max_attempts):
                history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
                if history.get(prompt_id):
                    outputs = history[prompt_id]["outputs"]
                    logger.info("Workflow outputs: %s", json.dumps(outputs, indent=2))
                    image_node = next((nid for nid, out in outputs.items() if "images" in out), None)
                    if not image_node:
                        raise Exception(f"No output node with images found: {outputs}")
                    image_filename = outputs[image_node]["images"][0]["filename"]
                    image_url = f"{self.base_url}/view?filename={image_filename}&subfolder=&type=output"
                    logger.info(f"Generated image URL: {image_url}")
                    return image_url
                time.sleep(1)
            raise Exception(f"Workflow {prompt_id} didn’t complete within {max_attempts} seconds")

        except FileNotFoundError:
            raise Exception(f"Workflow file '{workflow_file}' not found")
        except KeyError as e:
            raise Exception(f"Workflow error - invalid node or input: {e}")
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API error: {e}")

    def generate_video(self, prompt, width=None, height=None, audio_prompt=None, frame_length=None, workflow_id=None, timeout=600):
        try:
            # Load config to get default workflow if none specified
            if workflow_id is None:
                config_path = os.path.join(os.path.dirname(__file__), "config.json")
                with open(config_path, 'r') as f:
                    config = json.load(f)
                workflow_id = config["video_generation"]["workflow"]
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            workflow_file = os.path.join(script_dir, "workflows", f"{workflow_id}.json")
            with open(workflow_file, "r") as f:
                workflow = json.load(f)

            # Get the appropriate mapping for this workflow
            mapping = WORKFLOW_MAPPINGS.get(workflow_id, DEFAULT_MAPPING)
            logger.info(f"Using mapping for workflow {workflow_id}: {mapping}")

            params = {"prompt": prompt}
            if width is not None:
                params["width"] = width
            if height is not None:
                params["height"] = height
            if audio_prompt:
                params["audio_prompt"] = audio_prompt
            if frame_length:
                params["frame_length"] = frame_length

            for param_key, value in params.items():
                if param_key in mapping:
                    node_id, input_key = mapping[param_key]
                    if node_id not in workflow:
                        raise Exception(f"Node {node_id} not found in workflow {workflow_id}")
                    workflow[node_id]["inputs"][input_key] = value
            
            # Calculate dynamic audio duration for mmaudio workflow
            if workflow_id == "mmaudio-workflow":
                try:
                    # Get video parameters from workflow nodes
                    frame_count = workflow.get("59", {}).get("inputs", {}).get("length", 181)
                    
                    # Use base generation rate (16fps) for duration calculation
                    # With 32fps output and 2x RIFE interpolation, this maintains original timing
                    base_fps = 16
                    duration = frame_count / base_fps
                    
                    logger.info(f"Calculated audio duration: {frame_count} frames ÷ {base_fps} fps (base rate) = {duration} seconds")
                    
                    # Update audio duration in MMAudioSampler node
                    if "83:75" in workflow:
                        workflow["83:75"]["inputs"]["duration"] = duration
                        logger.info(f"Set MMAudioSampler duration to {duration} seconds")
                except Exception as e:
                    logger.warning(f"Failed to calculate dynamic duration, using default: {e}")

            logger.info(f"Submitting video workflow {workflow_id} to ComfyUI...")
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
            if response.status_code != 200:
                raise Exception(f"Failed to queue workflow: {response.status_code} - {response.text}")

            prompt_id = response.json()["prompt_id"]
            logger.info(f"Queued video workflow with prompt_id: {prompt_id}")

            max_attempts = timeout  # Use timeout from config
            for _ in range(max_attempts):
                history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
                if history.get(prompt_id):
                    outputs = history[prompt_id]["outputs"]
                    logger.info("Video workflow outputs: %s", json.dumps(outputs, indent=2))
                    # Look for video output node - check "images", "gifs", and "filenames" arrays
                    video_node = None
                    for node_id, output in outputs.items():
                        if "images" in output and any(item["filename"].endswith(".mp4") for item in output["images"]):
                            video_node = node_id
                            break
                        elif "gifs" in output and any(item["filename"].endswith(".mp4") for item in output["gifs"]):
                            video_node = node_id
                            break
                        elif "filenames" in output and any(item["filename"].endswith(".mp4") for item in output["filenames"]):
                            video_node = node_id
                            break
                    if not video_node:
                        raise Exception(f"No output node with video found: {outputs}")
                    
                    # Video can be in "images", "gifs", or "filenames" array
                    if "images" in outputs[video_node]:
                        video_data = outputs[video_node]["images"][0]
                    elif "gifs" in outputs[video_node]:
                        video_data = outputs[video_node]["gifs"][0]
                    else:
                        video_data = outputs[video_node]["filenames"][0]
                    video_filename = video_data["filename"]
                    subfolder = video_data.get("subfolder", "")
                    video_url = f"{self.base_url}/view?filename={video_filename}&subfolder={subfolder}&type=output"
                    logger.info(f"Generated video URL: {video_url}")
                    return video_url
                time.sleep(1)
            raise Exception(f"Video workflow {prompt_id} didn't complete within {max_attempts} seconds")

        except FileNotFoundError:
            raise Exception(f"Workflow file '{workflow_file}' not found")
        except KeyError as e:
            raise Exception(f"Workflow error - invalid node or input: {e}")
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API error: {e}")