import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComfyUIClient")

DYNAMIC_MAPPING = {
    "prompt": (6, "text"),
    "width": (5, "width"),
    "height": (5, "height")
}

class ComfyUIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def generate_image(self, prompt, width, height):
        try:
            with open("workflows/basic_api_test.json", "r") as f:
                workflow = json.load(f)

            for param_key, (node_id, input_key) in DYNAMIC_MAPPING.items():
                value = locals()[param_key]
                if str(node_id) not in workflow:
                    raise Exception(f"Node {node_id} not found in workflow")
                workflow[str(node_id)]["inputs"][input_key] = value

            logger.info("Submitting workflow to ComfyUI...")
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
            if response.status_code != 200:
                raise Exception(f"Failed to queue workflow: {response.status_code} - {response.text}")

            prompt_id = response.json()["prompt_id"]
            logger.info(f"Queued workflow with prompt_id: {prompt_id}")

            max_attempts = 30
            for _ in range(max_attempts):
                history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
                if history.get(prompt_id):
                    outputs = history[prompt_id]["outputs"]
                    logger.info("Workflow outputs: %s", json.dumps(outputs, indent=2))
                    if "9" not in outputs or "images" not in outputs["9"]:
                        raise Exception(f"Output node '9' missing or has no images: {outputs}")
                    image_filename = outputs["9"]["images"][0]["filename"]
                    # Use /view endpoint for ComfyUI image access
                    image_url = f"{self.base_url}/view?filename={image_filename}&subfolder=&type=output"
                    logger.info(f"Generated image URL: {image_url}")
                    return image_url
                time.sleep(1)
            raise Exception(f"Workflow {prompt_id} didn’t complete within {max_attempts} seconds")

        except FileNotFoundError:
            raise Exception("Workflow file 'workflows/basic_api_test.json' not found")
        except KeyError as e:
            raise Exception(f"Workflow error - invalid node or input: {e}")
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API error: {e}")