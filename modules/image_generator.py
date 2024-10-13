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

from .constants import ASSETS_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageGenerator:
    def __init__(self, workflow_json: str = None, checkpoints_dir: str = None):
        self.workflow_json = workflow_json or self.default_workflow_json()
        self.image_cache = {}
        self.checkpoints_dir = checkpoints_dir or r"C:\StableDiffusion\ComfyUI_windows_portable_nvidia_cu121_or_cpu\ComfyUI_windows_portable\ComfyUI\models\checkpoints"

    def default_workflow_json(self) -> str:
        return """
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

    def enhance_prompt(self, prompt: str) -> str:
        enhanced_prompt = f"{prompt}, high detail, cinematic lighting"
        return enhanced_prompt

    def load_workflow_json(self) -> Dict[str, Any]:
        try:
            workflow = json.loads(self.workflow_json)
            logging.info("Workflow JSON loaded successfully.")
            return workflow
        except json.JSONDecodeError as e:
            logging.error(f"Failed to load workflow JSON. Error: {e}")
            return {}

    def modify_workflow(self, workflow: Dict[str, Any], enhanced_prompt: str):
        try:
            if "6" in workflow:
                workflow["6"]["inputs"]["text"] = enhanced_prompt
            else:
                logging.warning("Positive prompt node '6' not found in workflow.")

            if "3" in workflow:
                workflow["3"]["inputs"]["seed"] = random.randint(10**6, 10**7)
            else:
                logging.warning("KSampler node '3' not found in workflow.")

            ckpt_name = workflow.get("4", {}).get("inputs", {}).get("ckpt_name")
            if ckpt_name and not self.validate_checkpoint(ckpt_name):
                raise ValueError(f"Invalid checkpoint name: {ckpt_name}")
        except Exception as e:
            logging.error(f"Failed to modify workflow. Error: {e}")

    def validate_checkpoint(self, ckpt_name: str) -> bool:
        checkpoint_path = os.path.join(self.checkpoints_dir, ckpt_name)
        if os.path.isfile(checkpoint_path):
            logging.info(f"Checkpoint '{ckpt_name}' found in '{self.checkpoints_dir}'.")
            return True
        else:
            logging.error(f"Checkpoint '{ckpt_name}' not found in '{self.checkpoints_dir}'.")
            return False

    def open_websocket_connection(self):
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
        try:
            payload = {
                "prompt": workflow,
                "client_id": client_id
            }
            headers = {'Content-Type': 'application/json'}
            response = requests.post(f"http://{server_address}/prompt", json=payload, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            prompt_id = response_json.get('prompt_id')
            if prompt_id:
                logging.info(f"Prompt queued with ID: {prompt_id}")
                return prompt_id
            else:
                logging.error("No prompt_id returned in the response.")
                return None
        except requests.HTTPError as e:
            try:
                error_body = e.response.json()
                logging.error(f"HTTPError while queuing prompt: {e.response.status_code} - {e.response.reason}")
                logging.error(f"Response body: {error_body}")
            except ValueError:
                logging.error(f"HTTPError while queuing prompt: {e.response.status_code} - {e.response.reason}")
            return None
        except requests.RequestException as e:
            logging.error(f"RequestException while queuing prompt: {e}")
            return None
        except Exception as e:
            logging.error(f"Error while queuing prompt: {e}")
            return None

    def track_progress(self, ws: websocket.WebSocket, prompt_id: str):
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

                        if node is None and data.get('prompt_id') == prompt_id:
                            logging.info("Image generation completed.")
                            break
                else:
                    continue
        except Exception as e:
            logging.error(f"Error while tracking progress: {e}")

    def get_images(self, prompt_id: str, server_address: str) -> Optional[List[Dict[str, Any]]]:
        try:
            response = requests.get(f"http://{server_address}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()

            images = []
            for node_id, node_data in history.get(prompt_id, {}).get('outputs', {}).items():
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
        except requests.HTTPError as e:
            try:
                error_body = e.response.json()
                logging.error(f"HTTPError while fetching history: {e.response.status_code} - {e.response.reason}")
                logging.error(f"Response body: {error_body}")
            except ValueError:
                logging.error(f"HTTPError while fetching history: {e.response.status_code} - {e.response.reason}")
            return None
        except requests.RequestException as e:
            logging.error(f"RequestException while fetching history: {e}")
            return None
        except Exception as e:
            logging.error(f"Error while fetching history: {e}")
            return None

    def get_image(self, filename: str, subfolder: str, folder_type: str, server_address: str) -> Optional[bytes]:
        try:
            params = {
                'filename': filename,
                'subfolder': subfolder,
                'type': folder_type
            }
            response = requests.get(f"http://{server_address}/view", params=params)
            response.raise_for_status()
            return response.content
        except requests.HTTPError as e:
            try:
                error_body = e.response.json()
                logging.error(f"HTTPError while retrieving image {filename}: {e.response.status_code} - {e.response.reason}")
                logging.error(f"Response body: {error_body}")
            except ValueError:
                logging.error(f"HTTPError while retrieving image {filename}: {e.response.status_code} - {e.response.reason}")
            return None
        except requests.RequestException as e:
            logging.error(f"RequestException while retrieving image {filename}: {e}")
            return None
        except Exception as e:
            logging.error(f"Failed to retrieve image {filename}. Error: {e}")
            return None

    def save_image(self, images: List[Dict[str, Any]], prompt: str) -> Optional[str]:
        try:
            if not images:
                logging.error("No images to save.")
                return None

            image_info = images[0]
            image_data = image_info.get('image_data')
            image_type = image_info.get('type')
            filename = image_info.get('filename')

            if image_data:
                image = Image.open(BytesIO(image_data))

                image_dir = os.path.join(ASSETS_DIR, 'images', 'generated')
                os.makedirs(image_dir, exist_ok=True)
                image_filename = f"{hash(prompt)}_{filename}"
                image_path = os.path.join(image_dir, image_filename)

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
        except requests.HTTPError as e:
            try:
                error_body = e.response.json()
                logging.error(f"HTTPError while uploading image {name}: {e.response.status_code} - {e.response.reason}")
                logging.error(f"Response body: {error_body}")
            except ValueError:
                logging.error(f"HTTPError while uploading image {name}: {e.response.status_code} - {e.response.reason}")
            return None
        except requests.RequestException as e:
            logging.error(f"RequestException while uploading image {name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error uploading image: {e}")
            return None

    def generate_image(self, prompt: str) -> Optional[str]:
        if not self.is_image_generation_enabled():
            logging.info("Image generation is disabled in settings.")
            return None

        if prompt in self.image_cache:
            logging.info("Image retrieved from cache.")
            return self.image_cache[prompt]

        try:
            logging.info(f"Generating image for prompt: {prompt}")

            enhanced_prompt = self.enhance_prompt(prompt)
            workflow = self.load_workflow_json()
            self.modify_workflow(workflow, enhanced_prompt)
            ws, server_address, client_id = self.open_websocket_connection()
            prompt_id = self.queue_prompt(workflow, client_id, server_address)

            if not prompt_id:
                logging.error("Failed to queue prompt.")
                ws.close()
                return None

            self.track_progress(ws, prompt_id)
            images = self.get_images(prompt_id, server_address)
            image_path = self.save_image(images, prompt)
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

    def is_image_generation_enabled(self) -> bool:
        # Implement your logic to check if image generation is enabled
        # For example, read from a settings file or configuration
        # Here, we'll assume it's enabled by default
        return True

# End of ImageGenerator class

