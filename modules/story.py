# modules/story.py

import os
import json
import logging
import random
import uuid
from typing import Dict, Any, Optional, List
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError
import requests
from PIL import Image
from io import BytesIO
import websocket
from requests_toolbelt.multipart.encoder import MultipartEncoder  # For uploading images

from .constants import STORIES_DIR, ASSETS_DIR

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class StoryManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.story_data = self.load_story()
        self.current_node_key = 'start'
        self.current_node = self.story_data.get(self.current_node_key, {})
        self.image_cache = {}  # Cache generated images

    # --------------------- Story Management Methods ---------------------

    def load_story(self) -> Dict[str, Any]:
        """
        Loads the story JSON file from the given filepath.
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                story = json.load(f)
            logging.info(f"Story loaded from {self.filepath}.")
            return story
        except FileNotFoundError:
            logging.error(f"Story file not found at {self.filepath}.")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {self.filepath}: {e}")
            return {}

    def set_current_node(self, node_key: str):
        """
        Sets the current node in the story based on the node_key.
        """
        self.current_node_key = node_key
        self.current_node = self.story_data.get(self.current_node_key, {})
        logging.info(f"Current node set to '{self.current_node_key}'.")

    def get_current_node(self) -> Dict[str, Any]:
        """
        Retrieves the current node in the story.
        """
        return self.current_node

    def get_text(self) -> str:
        """
        Retrieves the narrative text from the current node.
        """
        return self.current_node.get('text', '')

    def get_image_prompt(self) -> Optional[str]:
        """
        Retrieves the image prompt from the current node, if available.
        """
        return self.current_node.get('image_prompt')

    def get_choices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the choices available in the current node.
        """
        return self.current_node.get('choices')

    def get_environment(self) -> Optional[str]:
        """
        Retrieves the environment description from the current node, if available.
        """
        return self.current_node.get('environment')

    def get_npc(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the Non-Player Character (NPC) details from the current node, if available.
        """
        return self.current_node.get('npc')

    def get_event(self) -> Optional[str]:
        """
        Retrieves any event descriptions from the current node, if available.
        """
        return self.current_node.get('event')

    def get_items(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the list of items from the current node, if available.
        """
        return self.current_node.get('items')

    def get_battle_info(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves battle information from the current node, if available.
        """
        return self.current_node.get('battle')

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the player's stats from the current node, if available.
        """
        return self.current_node.get('stats')

    def get_quests(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the list of quests from the current node, if available.
        """
        return self.current_node.get('quests')

    def get_inventory(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the player's inventory from the current node, if available.
        """
        return self.current_node.get('inventory')

    # --------------------- Image Generation Methods ---------------------

    def is_image_generation_enabled(self) -> bool:
        """
        Checks if image generation is enabled in settings.
        """
        # Implement your logic to check if image generation is enabled
        # For example, read from a settings file or configuration
        # Here, we'll assume it's enabled by default
        return True

    def enhance_prompt(self, prompt: str) -> str:
        """
        Enhances the given prompt with additional descriptors or modifiers.
        """
        # Implement your prompt enhancement logic here
        # For example, adding styles, quality descriptors, etc.
        enhanced_prompt = f"{prompt}, high detail, cinematic lighting"
        return enhanced_prompt

    def generate_image(self, prompt: str) -> Optional[str]:
        """
        Generates an image based on the provided prompt using ComfyUI's API.
        """
        if not self.is_image_generation_enabled():
            logging.info("Image generation is disabled in settings.")
            return None

        if prompt in self.image_cache:
            logging.info("Image retrieved from cache.")
            return self.image_cache[prompt]

        try:
            logging.info(f"Generating image for prompt: {prompt}")

            # Optionally enhance the prompt
            enhanced_prompt = self.enhance_prompt(prompt)

            # Load the base workflow JSON
            workflow = self.load_workflow_json()

            # Modify the workflow with the new prompt and seed
            self.modify_workflow(workflow, enhanced_prompt)

            # Establish WebSocket connection
            ws, server_address, client_id = self.open_websocket_connection()

            # Queue the prompt
            prompt_id = self.queue_prompt(workflow, client_id, server_address)

            if not prompt_id:
                logging.error("Failed to queue prompt.")
                ws.close()
                return None

            # Track progress
            self.track_progress(ws, prompt_id)

            # Retrieve images
            images = self.get_images(prompt_id, server_address)

            # Save images
            image_path = self.save_image(images, prompt)

            # Close WebSocket
            ws.close()

            if image_path:
                self.image_cache[prompt] = image_path
                logging.info(f"Image generated and saved at {image_path}.")
                return image_path
            else:
                logging.error("Image generation failed: No image path returned.")
                return None

        except Exception as e:
            logging.error(f"Failed to generate image for prompt '{prompt}'. Error: {e}")
            return None

    def load_workflow_json(self) -> Dict[str, Any]:
        """
        Loads the predefined workflow JSON.
        """
        # Define your workflow JSON here or load from a file
        # For this example, we'll define it based on the provided prompt_text
        prompt_text = """
        {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 8,
                    "denoise": 1,
                    "latent_image": [
                        "5",
                        0
                    ],
                    "model": [
                        "4",
                        0
                    ],
                    "negative": [
                        "7",
                        0
                    ],
                    "positive": [
                        "6",
                        0
                    ],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": 8566257,
                    "steps": 20
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
                    "height": 512,
                    "width": 512
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": [
                        "4",
                        1
                    ],
                    "text": "masterpiece best quality girl"
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": [
                        "4",
                        1
                    ],
                    "text": "bad hands"
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": [
                        "3",
                        0
                    ],
                    "vae": [
                        "4",
                        2
                    ]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": [
                        "8",
                        0
                    ]
                }
            }
        }
        """
        try:
            workflow = json.loads(prompt_text)
            logging.info("Workflow JSON loaded successfully.")
            return workflow
        except json.JSONDecodeError as e:
            logging.error(f"Failed to load workflow JSON. Error: {e}")
            return {}

    def modify_workflow(self, workflow: Dict[str, Any], enhanced_prompt: str):
        """
        Modify the workflow JSON with the new prompt and a random seed.
        """
        try:
            # Find the positive prompt node (assumed to be node "6")
            if "6" in workflow:
                workflow["6"]["inputs"]["text"] = enhanced_prompt
            else:
                logging.warning("Positive prompt node '6' not found in workflow.")

            # Find the KSampler node (assumed to be node "3")
            if "3" in workflow:
                workflow["3"]["inputs"]["seed"] = random.randint(10**6, 10**7)
            else:
                logging.warning("KSampler node '3' not found in workflow.")
        except Exception as e:
            logging.error(f"Failed to modify workflow. Error: {e}")

    def open_websocket_connection(self):
        """
        Establishes a WebSocket connection to ComfyUI and returns the connection, server address, and client ID.
        """
        try:
            server_address = '127.0.0.1:8188'
            client_id = str(uuid.uuid4())

            ws = websocket.WebSocket()
            ws.connect(f"ws://{server_address}/ws?clientId={client_id}")

            logging.info("WebSocket connection established.")
            return ws, server_address, client_id
        except Exception as e:
            logging.error(f"Failed to establish WebSocket connection. Error: {e}")
            raise e

    def queue_prompt(self, workflow: Dict[str, Any], client_id: str, server_address: str) -> Optional[str]:
        """
        Sends a prompt to ComfyUI's /prompt endpoint and returns the prompt_id.
        """
        try:
            payload = {
                "prompt": workflow,
                "client_id": client_id
            }
            headers = {'Content-Type': 'application/json'}
            data = json.dumps(payload).encode('utf-8')
            req = urllib_request.Request(f"http://{server_address}/prompt", data=data, headers=headers)
            with urllib_request.urlopen(req) as response:
                response_data = response.read()
                response_json = json.loads(response_data)
                prompt_id = response_json.get('prompt_id')
                if prompt_id:
                    logging.info(f"Prompt queued with ID: {prompt_id}")
                    return prompt_id
                else:
                    logging.error("No prompt_id returned in the response.")
                    return None
        except HTTPError as e:
            # Read and log the response body for more details
            error_body = e.read().decode('utf-8')
            logging.error(f"HTTPError while queuing prompt: {e.code} - {e.reason}")
            logging.error(f"Response body: {error_body}")
            return None
        except URLError as e:
            logging.error(f"URLError while queuing prompt: {e.reason}")
            return None
        except Exception as e:
            logging.error(f"Error while queuing prompt: {e}")
            return None

    def track_progress(self, ws: websocket.WebSocket, prompt_id: str):
        """
        Tracks the progress of the image generation via WebSocket.
        """
        try:
            workflow = self.load_workflow_json()
            node_ids = list(workflow.keys())
            total_nodes = len(node_ids)
            finished_nodes = []

            while True:
                message = ws.recv()
                if isinstance(message, str):
                    message_json = json.loads(message)
                    message_type = message_json.get('type')

                    if message_type == 'progress':
                        data = message_json.get('data', {})
                        current_step = data.get('value')
                        max_steps = data.get('max')
                        logging.info(f"In K-Sampler -> Step: {current_step} of: {max_steps}")

                    elif message_type == 'execution_cached':
                        data = message_json.get('data', {})
                        nodes = data.get('nodes', [])
                        for node in nodes:
                            if node not in finished_nodes:
                                finished_nodes.append(node)
                                logging.info(f"Progress: {len(finished_nodes)} / {total_nodes} Tasks done")

                    elif message_type == 'executing':
                        data = message_json.get('data', {})
                        node = data.get('node')
                        if node and node not in finished_nodes:
                            finished_nodes.append(node)
                            logging.info(f"Progress: {len(finished_nodes)} / {total_nodes} Tasks done")

                        # Check if execution is done
                        if node is None and data.get('prompt_id') == prompt_id:
                            logging.info("Image generation completed.")
                            break
                else:
                    continue
        except Exception as e:
            logging.error(f"Error while tracking progress: {e}")

    def get_images(self, prompt_id: str, server_address: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves generated images from ComfyUI via the /history/{prompt_id} endpoint.
        """
        try:
            response = urllib_request.urlopen(f"http://{server_address}/history/{prompt_id}")
            history = json.loads(response.read())

            images = []
            for node_id, node_data in history.get(prompt_id, {}).get('outputs', {}).items():
                if 'images' in node_data:
                    for image_info in node_data['images']:
                        image_type = image_info.get('type')
                        filename = image_info.get('filename')
                        subfolder = image_info.get('subfolder')

                        # Fetch the image data
                        image_data = self.get_image(filename, subfolder, image_type, server_address)
                        if image_data:
                            images.append({
                                'filename': filename,
                                'type': image_type,
                                'image_data': image_data
                            })

            return images
        except HTTPError as e:
            logging.error(f"HTTPError while fetching history: {e.code} - {e.reason}")
            return None
        except URLError as e:
            logging.error(f"URLError while fetching history: {e.reason}")
            return None
        except Exception as e:
            logging.error(f"Error while fetching history: {e}")
            return None

    def get_image(self, filename: str, subfolder: str, folder_type: str, server_address: str) -> Optional[bytes]:
        """
        Retrieves an image from ComfyUI via the /view endpoint.
        """
        try:
            params = {
                'filename': filename,
                'subfolder': subfolder,
                'type': folder_type
            }
            query_string = urllib_request.urlencode(params)
            url = f"http://{server_address}/view?{query_string}"
            with urllib_request.urlopen(url) as response:
                return response.read()
        except Exception as e:
            logging.error(f"Failed to retrieve image {filename}. Error: {e}")
            return None

    def save_image(self, images: List[Dict[str, Any]], prompt: str) -> Optional[str]:
        """
        Saves the first image from the images list to the assets directory.
        """
        try:
            if not images:
                logging.error("No images to save.")
                return None

            # For simplicity, take the first image
            image_info = images[0]
            image_data = image_info.get('image_data')
            image_type = image_info.get('type')
            filename = image_info.get('filename')

            if image_data:
                image = Image.open(BytesIO(image_data))

                # Define the output directory and filename
                image_dir = os.path.join(ASSETS_DIR, 'images', 'generated')
                os.makedirs(image_dir, exist_ok=True)
                # Use a unique filename based on prompt hash and original filename
                image_filename = f"{hash(prompt)}_{filename}"
                image_path = os.path.join(image_dir, image_filename)

                # Save the image
                image.save(image_path)
                logging.info(f"Image saved at {image_path}")
                return image_path
            else:
                logging.error("No image data found.")
                return None

        except Exception as e:
            logging.error(f"Failed to save image. Error: {e}")
            return None

    def upload_image(self, input_path: str, name: str, server_address: str, image_type: str = "input", overwrite: bool = False) -> Optional[bytes]:
        """
        Uploads an image to ComfyUI via the /upload/image endpoint.
        """
        try:
            with open(input_path, 'rb') as file:
                encoder = MultipartEncoder(
                    fields={
                        'image': (name, file, 'image/png'),
                        'type': image_type,
                        'overwrite': str(overwrite).lower()
                    }
                )
                headers = {'Content-Type': encoder.content_type}
                response = requests.post(f"http://{server_address}/upload/image", data=encoder, headers=headers)
                if response.status_code == 200:
                    logging.info(f"Image {name} uploaded successfully.")
                    return response.content
                else:
                    logging.error(f"Failed to upload image. Status code: {response.status_code}")
                    logging.error(f"Response body: {response.text}")
                    return None
        except Exception as e:
            logging.error(f"Error uploading image: {e}")
            return None

    # You can add more methods here as needed for your application

# --------------------- End of modules/story.py ---------------------
