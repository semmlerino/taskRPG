import os
import json
import logging
import random
import uuid
from typing import Dict, Any, Optional, List
import requests
from PIL import Image
from io import BytesIO
import websocket
from requests_toolbelt.multipart.encoder import MultipartEncoder

from modules.constants import ASSETS_DIR, STORIES_DIR

class ImageGenerator:
    """Handles image generation and validation."""
    
    def __init__(self, workflow_json: str = None, checkpoints_dir: str = None):
        self.workflow_json = workflow_json or self.default_workflow_json()
        self.image_cache = {}
        self.checkpoints_dir = checkpoints_dir or r"C:\StableDiffusion\ComfyUI_windows_portable_nvidia_cu121_or_cpu\ComfyUI_windows_portable\ComfyUI\models\checkpoints"
        logging.info("ImageGenerator initialized")

    def default_workflow_json(self) -> str:
        """Returns the default workflow JSON configuration."""
        return """
        {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 8,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": 8566257,
                    "steps": 50
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": 1024,
                    "width": 1024
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "masterpiece best quality"
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "bad hands"
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                }
            }
        }
        """

    def generate_missing_story_images(self, progress_dialog=None) -> List[str]:
        """Generate images for all stories that have missing images."""
        generated_images = []
        try:
            stories = self._get_available_stories()
            missing_images = self._get_missing_story_images(stories)
            
            if not missing_images:
                logging.info("No missing images to generate")
                return generated_images

            total_images = len(missing_images)
            current = 0

            if progress_dialog:
                progress_dialog.setMaximum(total_images)

            for story_name, image_info in missing_images:
                try:
                    if progress_dialog and progress_dialog.wasCanceled():
                        break

                    image_path = self.generate_image(
                        image_info['prompt'],
                        save_path=image_info['path']
                    )
                    
                    if image_path:
                        generated_images.append(image_path)
                        logging.info(f"Generated image for {story_name}: {image_path}")
                    
                    current += 1
                    if progress_dialog:
                        progress_dialog.setValue(current)
                        
                except Exception as e:
                    logging.error(f"Error generating image for {story_name}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error in generate_missing_story_images: {e}")

        return generated_images

    def _get_available_stories(self) -> List[tuple]:
        """Get list of available stories and their paths."""
        stories = []
        try:
            for filename in os.listdir(STORIES_DIR):
                if filename.endswith('.json'):
                    story_path = os.path.join(STORIES_DIR, filename)
                    story_name = os.path.splitext(filename)[0]
                    stories.append((story_name, story_path))
        except Exception as e:
            logging.error(f"Error getting available stories: {e}")
        return stories

    def _get_missing_story_images(self, stories: List[tuple]) -> List[tuple]:
        """Identify which story images need to be generated."""
        missing_images = []
        for story_name, story_path in stories:
            try:
                with open(story_path, 'r', encoding='utf-8') as f:
                    story_data = json.load(f)

                image_folder = os.path.join(ASSETS_DIR, 'images', story_name)
                os.makedirs(image_folder, exist_ok=True)

                for node_key, node_data in story_data.items():
                    if isinstance(node_data, dict) and 'image_prompt' in node_data:
                        image_path = os.path.join(image_folder, f"{node_key}.png")
                        
                        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                            missing_images.append((
                                story_name,
                                {
                                    'prompt': node_data['image_prompt'],
                                    'path': image_path,
                                    'node_key': node_key
                                }
                            ))
            except Exception as e:
                logging.error(f"Error processing story {story_name}: {e}")
                continue

        return missing_images

    def generate_image(self, prompt: str, save_path: Optional[str] = None) -> Optional[str]:
        """Generate an image if it doesn't already exist."""
        try:
            if not self.is_image_generation_enabled():
                logging.info("Image generation is disabled in settings.")
                return None

            # Normalize save path
            if save_path:
                save_path = os.path.abspath(save_path)
                
            # Check if image already exists
            if save_path and os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                if file_size > 0 and self._validate_image_file(save_path):
                    logging.info(f"Valid image already exists at {save_path}")
                    self.image_cache[prompt] = save_path
                    return save_path
                else:
                    logging.warning(f"Invalid or empty image file at {save_path}")
                    os.remove(save_path)

            # Check ComfyUI server connection
            if not self.validate_server_connection():
                logging.error("ComfyUI server not available")
                return None

            # Generate new image
            logging.info(f"Generating new image for prompt: {prompt}")
            
            enhanced_prompt = self.enhance_prompt(prompt)
            workflow = self.load_workflow_json()
            self.modify_workflow(workflow, enhanced_prompt)
            
            ws, server_address, client_id = self.open_websocket_connection()
            prompt_id = self.queue_prompt(workflow, client_id, server_address)

            if not prompt_id:
                logging.error("Failed to queue prompt")
                ws.close()
                return None

            self.track_progress(ws, prompt_id)
            images = self.get_images(prompt_id, server_address)
            
            if not images:
                logging.error("No images generated")
                ws.close()
                return None
                
            image_path = self.save_image(images, prompt, save_path)
            ws.close()

            if image_path and self._validate_image_file(image_path):
                self.image_cache[prompt] = image_path
                logging.info(f"Image successfully generated and saved at {image_path}")
                return image_path
            else:
                logging.error("Generated image validation failed")
                return None

        except Exception as e:
            logging.error(f"Error in generate_image: {e}")
            return None

    def _validate_image_file(self, path: str) -> bool:
        """Validate that a file is a valid image."""
        try:
            with Image.open(path) as img:
                img.verify()
            return True
        except Exception as e:
            logging.error(f"Image validation failed for {path}: {e}")
            return False

    def enhance_prompt(self, prompt: str) -> str:
        """Enhance the image generation prompt."""
        return f"{prompt}, high detail, cinematic lighting"

    def load_workflow_json(self) -> Dict[str, Any]:
        """Load and parse the workflow JSON."""
        try:
            workflow = json.loads(self.workflow_json)
            logging.info("Workflow JSON loaded successfully")
            return workflow
        except json.JSONDecodeError as e:
            logging.error(f"Failed to load workflow JSON: {e}")
            return {}

    def modify_workflow(self, workflow: Dict[str, Any], enhanced_prompt: str):
        """Modify the workflow with the enhanced prompt."""
        try:
            if "6" in workflow:
                workflow["6"]["inputs"]["text"] = enhanced_prompt
            if "3" in workflow:
                workflow["3"]["inputs"]["seed"] = random.randint(10**6, 10**7)

            ckpt_name = workflow.get("4", {}).get("inputs", {}).get("ckpt_name")
            if ckpt_name and not self.validate_checkpoint(ckpt_name):
                raise ValueError(f"Invalid checkpoint name: {ckpt_name}")
        except Exception as e:
            logging.error(f"Failed to modify workflow: {e}")

    def validate_checkpoint(self, ckpt_name: str) -> bool:
        """Validate the existence of a checkpoint file."""
        checkpoint_path = os.path.join(self.checkpoints_dir, ckpt_name)
        exists = os.path.isfile(checkpoint_path)
        if exists:
            logging.info(f"Checkpoint '{ckpt_name}' found")
        else:
            logging.error(f"Checkpoint '{ckpt_name}' not found")
        return exists

    def validate_server_connection(self) -> bool:
        """Validate connection to ComfyUI server."""
        try:
            response = requests.get('http://127.0.0.1:8188/system_stats')
            response.raise_for_status()
            logging.info("ComfyUI server connection validated")
            return True
        except Exception as e:
            logging.error(f"ComfyUI server connection failed: {e}")
            return False

    def open_websocket_connection(self):
        """Open a WebSocket connection to the ComfyUI server."""
        try:
            server_address = '127.0.0.1:8188'
            client_id = str(uuid.uuid4())
            ws = websocket.WebSocket()
            ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
            logging.info("WebSocket connection established")
            return ws, server_address, client_id
        except Exception as e:
            logging.error(f"Failed to establish WebSocket connection: {e}")
            raise

    def queue_prompt(self, workflow: Dict[str, Any], client_id: str, server_address: str) -> Optional[str]:
        """Queue a prompt for image generation."""
        try:
            payload = {
                "prompt": workflow,
                "client_id": client_id
            }
            response = requests.post(
                f"http://{server_address}/prompt",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            prompt_id = response.json().get('prompt_id')
            if prompt_id:
                logging.info(f"Prompt queued with ID: {prompt_id}")
                return prompt_id
            else:
                logging.error("No prompt_id returned")
                return None
        except Exception as e:
            logging.error(f"Error queuing prompt: {e}")
            return None

    def track_progress(self, ws: websocket.WebSocket, prompt_id: str):
        """Track the progress of image generation."""
        try:
            workflow = self.load_workflow_json()
            node_ids = list(workflow.keys())
            total_nodes = len(node_ids)
            finished_nodes = []

            while True:
                message = ws.recv()
                if not isinstance(message, str):
                    continue

                message_json = json.loads(message)
                message_type = message_json.get('type')

                if message_type == 'progress':
                    data = message_json.get('data', {})
                    current_step = data.get('value')
                    max_steps = data.get('max')
                    logging.info(f"Progress: Step {current_step}/{max_steps}")

                elif message_type in ('execution_cached', 'executing'):
                    data = message_json.get('data', {})
                    if message_type == 'executing' and data.get('prompt_id') == prompt_id and data.get('node') is None:
                        logging.info("Generation completed")
                        break

                    nodes = data.get('nodes', [data.get('node')] if data.get('node') else [])
                    for node in nodes:
                        if node and node not in finished_nodes:
                            finished_nodes.append(node)
                            logging.info(f"Progress: {len(finished_nodes)}/{total_nodes} nodes completed")

        except Exception as e:
            logging.error(f"Error tracking progress: {e}")
            raise

    def get_images(self, prompt_id: str, server_address: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve generated images from the server."""
        try:
            response = requests.get(f"http://{server_address}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()

            images = []
            outputs = history.get(prompt_id, {}).get('outputs', {})
            for node_id, node_data in outputs.items():
                if 'images' in node_data:
                    for image_info in node_data['images']:
                        image_type = image_info.get('type')
                        filename = image_info.get('filename')
                        subfolder = image_info.get('subfolder')

                        image_data = self.get_image(filename, subfolder, image_type, server_address)
                        if image_data:
                            images.append({
                                'filename': filename,
                                'type': image_type,
                                'image_data': image_data
                            })

            return images
        except Exception as e:
            logging.error(f"Error retrieving images: {e}")
            return None

    def get_image(self, filename: str, subfolder: str, folder_type: str, server_address: str) -> Optional[bytes]:
        """Retrieve a specific image from the server."""
        try:
            response = requests.get(
                f"http://{server_address}/view",
                params={
                    'filename': filename,
                    'subfolder': subfolder,
                    'type': folder_type
                }
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logging.error(f"Error retrieving image {filename}: {e}")
            return None

    def save_image(self, images: List[Dict[str, Any]], prompt: str, save_path: Optional[str] = None) -> Optional[str]:
        """Save generated images to disk."""
        try:
            if not images:
                logging.error("No images to save")
                return None

            image_info = images[0]
            image_data = image_info.get('image_data')
            
            if not image_data:
                logging.error("No image data found")
                return None

            image = Image.open(BytesIO(image_data))

            if save_path:
                image_path = save_path
            else:
                image_dir = os.path.join(ASSETS_DIR, 'images', 'generated')
                os.makedirs(image_dir, exist_ok=True)
                image_filename = f"{hash(prompt)}_{image_info.get('filename', 'image.png')}"
                image_path = os.path.join(image_dir, image_filename)

            # Ensure directory exists
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            image.save(image_path)
            logging.info(f"Image saved at {image_path}")
            return image_path

        except Exception as e:
            logging.error(f"Error saving image: {e}")
            return None

    def is_image_generation_enabled(self) -> bool:
        """Check if image generation is enabled in settings."""
        try:
            settings_file = os.path.join(
                os.path.dirname(ASSETS_DIR),
                'data',
                'settings.json'
            )
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                return settings.get('image_generation', True)
            return True  # Default to enabled if no settings file
        except Exception as e:
            logging.error(f"Error checking image generation settings: {e}")
            return True  # Default to enabled on error

    def clear_cache(self):
        """Clear the image cache."""
        self.image_cache.clear()
        logging.info("Image cache cleared")

    def cleanup(self):
        """Cleanup resources."""
        try:
            self.clear_cache()
            logging.info("ImageGenerator cleanup complete")
        except Exception as e:
            logging.error(f"Error during ImageGenerator cleanup: {e}")

    def __del__(self):
        """Cleanup when object is deleted."""
        self.cleanup()