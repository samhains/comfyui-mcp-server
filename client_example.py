#!/usr/bin/env python3
"""
Example client for calling ComfyUI MCP Server HTTP endpoints from any Python project.
"""

import requests
import json
import time
from typing import Optional, Dict, Any


class ComfyUIClient:
    """HTTP client for ComfyUI MCP Server"""
    
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url.rstrip('/')
    
    def generate_image(self, prompt: str, width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
        """Generate an image using the HTTP API
        
        Args:
            prompt: Text description of the image to generate
            width: Image width in pixels (optional)
            height: Image height in pixels (optional)
            
        Returns:
            dict: Contains 'image_url' on success or 'error' on failure
        """
        payload = {"prompt": prompt}
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
            
        response = requests.post(f"{self.base_url}/generate_image", json=payload)
        return response.json()
    
    def generate_video(self, prompt: str, audio_prompt: str, frame_length: Optional[int] = None, 
                      width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
        """Generate a video with audio using the HTTP API
        
        Args:
            prompt: Text description of the video content to generate
            audio_prompt: Text description of the audio/sound to generate
            frame_length: Number of frames for the video (optional)
            width: Video width in pixels (optional)
            height: Video height in pixels (optional)
            
        Returns:
            dict: Contains 'video_url' on success or 'error' on failure
        """
        payload = {
            "prompt": prompt,
            "audio_prompt": audio_prompt
        }
        if frame_length is not None:
            payload["frame_length"] = frame_length
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
            
        response = requests.post(f"{self.base_url}/generate_video", json=payload)
        return response.json()
    
    def generate_image_stream(self, prompt: str, width: Optional[int] = None, height: Optional[int] = None):
        """Generate an image with streaming progress updates
        
        Args:
            prompt: Text description of the image to generate
            width: Image width in pixels (optional)
            height: Image height in pixels (optional)
            
        Yields:
            dict: Progress updates and final result
        """
        payload = {"prompt": prompt}
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
            
        response = requests.post(
            f"{self.base_url}/generate_image_stream",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                yield data
    
    def generate_video_stream(self, prompt: str, audio_prompt: str, frame_length: Optional[int] = None,
                             width: Optional[int] = None, height: Optional[int] = None):
        """Generate a video with streaming progress updates
        
        Args:
            prompt: Text description of the video content to generate
            audio_prompt: Text description of the audio/sound to generate
            frame_length: Number of frames for the video (optional)
            width: Video width in pixels (optional)
            height: Video height in pixels (optional)
            
        Yields:
            dict: Progress updates and final result
        """
        payload = {
            "prompt": prompt,
            "audio_prompt": audio_prompt
        }
        if frame_length is not None:
            payload["frame_length"] = frame_length
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
            
        response = requests.post(
            f"{self.base_url}/generate_video_stream",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                yield data


# Example usage
if __name__ == "__main__":
    client = ComfyUIClient("http://localhost:9000")
    
    # Example 1: Generate an image
    print("Generating image...")
    result = client.generate_image("a beautiful sunset over mountains")
    if "image_url" in result:
        print(f"Image generated: {result['image_url']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Example 2: Generate a video
    print("\nGenerating video...")
    result = client.generate_video(
        prompt="a cat walking in a garden",
        audio_prompt="birds chirping, gentle footsteps on grass",
        width=1920,
        height=1080
    )
    if "video_url" in result:
        print(f"Video generated: {result['video_url']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Example 3: Generate with streaming updates
    print("\nGenerating image with streaming updates...")
    for update in client.generate_image_stream("anime girl in armor"):
        print(f"Status: {update.get('status')}, Message: {update.get('message', '')}")
        if update.get('status') == 'complete':
            result = update.get('result', {})
            if "image_url" in result:
                print(f"Final image: {result['image_url']}")
            break
        elif update.get('status') == 'error':
            print(f"Error: {update.get('error')}")
            break