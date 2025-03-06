import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComfyUIClient")

class ComfyUIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def generate_image(self, prompt, width, height):
        try:
            with open("workflows/basic.json", "r") as f:
                workflow = json.load(f)

            # Map nodes by ID
            nodes = {node["id"]: node for node in workflow["nodes"]}
            logger.info("Available node IDs: %s", list(nodes.keys()))

            # Update workflow with parameters
            if 6 not in nodes:
                raise Exception("Node 6 not found in workflow")
            nodes[6]["widgets_values"][0] = prompt  # Positive prompt
            if 5 not in nodes:
                raise Exception("Node 5 not found in workflow")
            nodes[5]["widgets_values"][0] = width   # Latent width
            nodes[5]["widgets_values"][1] = height  # Latent height

            # Queue the workflow
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"Failed to queue workflow: {response.status_code} - {error_detail}")

            prompt_id = response.json()["prompt_id"]
            logger.info(f"Queued workflow with prompt_id: {prompt_id}")

            # Poll for completion
            max_attempts = 30
            for _ in range(max_attempts):
                history = requests.get(f"{self.base_url}/history/{prompt_id}").json()
                if history.get(prompt_id):
                    outputs = history[prompt_id]["outputs"]
                    if "9" not in outputs or "images" not in outputs["9"]:
                        raise Exception(f"Output node '9' missing or has no images: {outputs}")
                    image_path = outputs["9"]["images"][0]["filename"]
                    return f"output/{image_path}"
                time.sleep(1)
            raise Exception(f"Workflow {prompt_id} didn’t complete within {max_attempts} seconds")

        except FileNotFoundError:
            raise Exception("Workflow file 'workflows/basic.json' not found")
        except KeyError as e:
            raise Exception(f"Workflow error - invalid node or input: {e}")
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API error: {e}")