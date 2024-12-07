from __future__ import annotations

# Standard library imports
import os
import json
import logging
import random
import uuid
import time
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum, auto
from io import BytesIO
from pathlib import Path

# Third-party imports
from PIL import Image
import websocket
import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')


class ImageQuality(Enum):
    """Image quality presets."""
    DRAFT = auto()      # Quick generation, lower quality
    STANDARD = auto()   # Default balance
    HIGH = auto()       # Higher quality, slower
    ULTRA = auto()      # Maximum quality, slowest


@dataclass
class QualityPreset:
    """Quality preset configuration."""
    steps: int
    cfg: float
    denoise: float
    sampler: str
    scheduler: str
    width: int
    height: int

    @classmethod
    def get_preset(cls, quality: ImageQuality) -> 'QualityPreset':
        """Get settings for specified quality level."""
        presets = {
            ImageQuality.DRAFT: cls(
                steps=30,
                cfg=7.0,
                denoise=0.9,
                sampler="euler",
                scheduler="normal",
                width=896,
                height=896
            ),
            ImageQuality.STANDARD: cls(
                steps=50,
                cfg=7.0,
                denoise=0.95,
                sampler="dpmpp_2m",
                scheduler="karras",
                width=1024,
                height=1024
            ),
            ImageQuality.HIGH: cls(
                steps=75,
                cfg=7.5,
                denoise=0.97,
                sampler="dpmpp_2m",
                scheduler="karras",
                width=1152,
                height=1152
            ),
            ImageQuality.ULTRA: cls(
                steps=60,
                cfg=6.0,
                denoise=0.98,
                sampler="dpmpp_3m_sde",
                scheduler="karras",
                width=1216,
                height=832
            )
        }
        return presets.get(quality, presets[ImageQuality.STANDARD])


class PromptEnhancer:
    """Handles prompt enhancement and processing for SDXL."""

    def __init__(self):
        # Base prompt quality terms
        self.base_terms: Dict[str, List[str]] = {
            "technical": [
                "masterpiece",
                "best quality",
                "highly detailed",
                "sharp focus",
                "ultra high resolution",
                "8k uhd",
                "high detail"
            ],
            "medium": [
                "digital art",
                "concept art",
                "illustration",
                "painting",
                "artwork"
            ]
        }

        # Refiner-specific quality terms
        self.refiner_terms: Dict[str, List[str]] = {
            "style": [
                "cinematic",
                "photorealistic",
                "hyperrealistic",
                "octane render",
                "unreal engine 5"
            ],
            "lighting": [
                "professional lighting",
                "dramatic lighting",
                "volumetric lighting",
                "atmospheric",
                "cinematic lighting",
                "studio lighting",
                "dynamic lighting"
            ],
            "composition": [
                "trending on artstation",
                "award winning",
                "cinematic composition",
                "professional",
                "highly detailed"
            ]
        }

        # Negative terms for both base and refiner
        self.negative_terms: List[str] = [
            "bad hands",
            "text",
            "watermark",
            "signature",
            "blurry",
            "artifacting",
            "low quality",
            "worst quality",
            "jpeg artifacts",
            "distortion",
            "deformed",
            "mutation",
            "duplicate",
            "cropped",
            "out of frame",
            "extra limbs",
            "ugly",
            "poorly drawn face",
            "poorly drawn hands"
        ]

    def process_structured_prompt(self, prompt_data: Dict[str, str]) -> Tuple[str, str]:
        """Process structured SDXL prompt data."""
        try:
            # Extract components
            main_subject = prompt_data.get("main", "")
            style_info = prompt_data.get("style", "")
            details = prompt_data.get("details", "")
            quality_level = prompt_data.get("quality", "STANDARD")

            # Select quality terms based on quality level
            num_terms = {
                "DRAFT": 1,
                "STANDARD": 2,
                "HIGH": 3,
                "ULTRA": 4
            }.get(quality_level, 2)

            # Build base prompt (focused on subject and basic quality)
            base_technical = random.sample(self.base_terms["technical"], min(num_terms, len(self.base_terms["technical"])))
            base_medium = random.sample(self.base_terms["medium"], 1)
            
            base_components = [
                main_subject,
                ", ".join(base_technical),
                base_medium[0]
            ]
            base_prompt = ", ".join(filter(None, [x.strip() for x in base_components]))

            # Build refiner prompt (focused on style and details)
            style_terms = random.sample(self.refiner_terms["style"], min(num_terms, len(self.refiner_terms["style"])))
            lighting_terms = random.sample(self.refiner_terms["lighting"], min(num_terms, len(self.refiner_terms["lighting"])))
            composition_terms = random.sample(self.refiner_terms["composition"], min(num_terms, len(self.refiner_terms["composition"])))
            
            refiner_components = [
                main_subject,
                style_info,
                details,
                ", ".join(style_terms),
                ", ".join(lighting_terms),
                ", ".join(composition_terms)
            ]
            refiner_prompt = ", ".join(filter(None, [x.strip() for x in refiner_components]))

            # Combine prompts in SDXL format
            positive_prompt = f"{base_prompt} --s {refiner_prompt}"

            # Generate negative prompt
            negative_prompt = ", ".join(self.negative_terms)

            logger.debug(f"Processed SDXL prompt - Quality: {quality_level}")
            return positive_prompt, negative_prompt

        except Exception as e:
            logger.error(f"Error processing structured prompt: {e}")
            return main_subject, ", ".join(self.negative_terms)

    def enhance_legacy_prompt(self, prompt: str) -> Tuple[str, str]:
        """Enhance a legacy string prompt."""
        try:
            # Extract any style information in parentheses
            style_info = ""
            if "(" in prompt and ")" in prompt:
                main_part = prompt[:prompt.find("(")].strip()
                style_info = prompt[prompt.find("(")+1:prompt.find(")")].strip()
            else:
                main_part = prompt

            structured_prompt = {
                "main": main_part,
                "style": style_info if style_info else "digital art, concept art",
                "details": "detailed, sharp focus",
                "quality": "STANDARD"
            }
            return self.process_structured_prompt(structured_prompt)
        except Exception as e:
            logger.error(f"Error enhancing legacy prompt: {e}")
            return prompt, ", ".join(self.negative_terms)


class ImageGenerator:
    """Enhanced image generator with SDXL support."""

    def __init__(
        self,
        workflow_json: Optional[Dict[str, Any]] = None,
        checkpoints_dir: Optional[str] = None,
        # Change default quality to ULTRA
        quality: ImageQuality = ImageQuality.ULTRA,
        server_address: str = "127.0.0.1",
        server_port: int = 8188
    ):
        """Initialize the image generator."""
        self.quality = quality
        self.checkpoints_dir = checkpoints_dir
        self.server_address = server_address
        self.server_port = server_port
        self.server_url = f"http://{server_address}:{server_port}"
        self.ws_url = f"ws://{server_address}:{server_port}/ws"

        # Initialize components
        self.image_cache = {}
        self.prompt_enhancer = PromptEnhancer()

        # Initialize workflow
        self.workflow_json = workflow_json if workflow_json is not None else self.default_workflow_json()

        logger.info(f"ImageGenerator initialized with quality: {quality.name}")

    def scan_story_for_missing_images(self, story_data: Dict[str, Any], story_name: str) -> List[Tuple[str, str]]:
        """Scan story for missing images using project structure."""
        missing_images = []

        try:
            # Use project image path structure
            image_dir = os.path.join(ASSETS_DIR, 'images', story_name)
            os.makedirs(image_dir, exist_ok=True)

            # Scan story nodes
            for node_key, node_data in story_data.items():
                if isinstance(node_data, dict) and 'image_prompt' in node_data:
                    image_path = os.path.join(image_dir, f"{node_key}.png")

                    # Check existence and validity
                    if not os.path.exists(image_path) or not self._validate_image_file(image_path):
                        missing_images.append((node_key, node_data['image_prompt']))

            logger.info(f"Found {len(missing_images)} missing images in '{story_name}'")
            return missing_images

        except Exception as e:
            logger.error(f"Error scanning for missing images: {e}")
            return []

    def generate_missing_story_images(self, story_data: Dict[str, Any], story_name: str, 
                                    progress_dialog=None) -> List[str]:
        """Generate missing story images using project structure."""
        generated_images = []

        try:
            # Skip if ComfyUI not available
            if not self.validate_server_connection():
                logger.error("ComfyUI server not available")
                return []

            # Get missing images
            missing_images = self.scan_story_for_missing_images(story_data, story_name)

            if not missing_images:
                return []

            # Update progress dialog
            if progress_dialog:
                progress_dialog.setMaximum(len(missing_images))

            # Generate images
            for idx, (node_key, image_prompt) in enumerate(missing_images):
                try:
                    if progress_dialog:
                        if progress_dialog.wasCanceled():
                            break
                        progress_dialog.setValue(idx)
                        progress_dialog.setLabelText(f"Generating image {idx + 1}/{len(missing_images)}")

                    # Generate image
                    image_path = self.generate_image(image_prompt)

                    if image_path:
                        # Move to project structure location
                        final_path = os.path.join(
                            ASSETS_DIR,
                            'images',
                            story_name,
                            f"{node_key}.png"
                        )

                        # Ensure directory exists
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)

                        # Move file
                        os.rename(image_path, final_path)
                        generated_images.append(final_path)

                except Exception as e:
                    logger.error(f"Error generating image for node {node_key}: {e}")
                    continue

            return generated_images

        except Exception as e:
            logger.error(f"Error generating story images: {e}")
            return []

    def generate_image(self, prompt: Union[str, Dict[str, str]], save_path: Optional[str] = None) -> Optional[str]:
        """Generate a single image."""
        try:
            # Generate workflow for the prompt
            workflow = self.generate_workflow(prompt)
            return self.queue_and_generate(workflow, save_path)
        except Exception as e:
            logger.error(f"Error in image generation: {e}")
            return None

    def validate_server_connection(self) -> bool:
        """Validate connection to ComfyUI server."""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=5)
            response.raise_for_status()
            logger.info("ComfyUI server connection validated")
            return True
        except Exception as e:
            logger.error(f"ComfyUI server connection failed: {e}")
            return False

    def open_websocket_connection(self) -> Tuple[websocket.WebSocket, str, str]:
        """Open a WebSocket connection to the ComfyUI server."""
        try:
            client_id = str(uuid.uuid4())
            ws = websocket.WebSocket()
            ws.connect(f"{self.ws_url}?clientId={client_id}")
            return ws, self.server_url, client_id
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            raise

    def queue_prompt(self, workflow: Dict[str, Any], client_id: str, server_address: str) -> Optional[str]:
        """Queue a prompt for image generation."""
        try:
            # Prepare the request payload
            payload = {
                "prompt": workflow,
                "client_id": client_id,
                "extra_data": {
                    "required_outputs": ["9"]  # Save Image node
                }
            }

            # Send the request
            response = requests.post(
                f"{server_address}/prompt",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            # Extract and validate prompt_id
            data = response.json()
            prompt_id = data.get('prompt_id')
            if not prompt_id:
                logger.error("No prompt_id in response")
                return None

            logger.info(f"Successfully queued prompt with ID: {prompt_id}")
            return prompt_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error queuing prompt: {e}")
            return None
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None

    def track_progress(self, ws: websocket.WebSocket, prompt_id: str):
        """Track the progress of image generation."""
        try:
            timeout = time.time() + 300  # 5 minute timeout
            ws.settimeout(1.0)  # 1 second timeout for each receive

            while time.time() < timeout:
                try:
                    message = ws.recv()
                    if not message:
                        continue

                    if not isinstance(message, str):
                        logger.warning(f"Received non-string message: {type(message)}")
                        continue

                    message_json = json.loads(message)
                    msg_type = message_json.get('type')
                    data = message_json.get('data', {})

                    if msg_type == 'executing':
                        node_id = data.get('node', None)
                        if node_id:
                            logger.debug(f"Processing node {node_id}")
                        else:
                            logger.info("Image generation completed")
                            return

                    elif msg_type == 'progress':
                        value = data.get('value', 0)
                        max_value = data.get('max', 100)
                        logger.debug(f"Progress: {value}/{max_value}")

                    elif msg_type == 'error':
                        error_msg = data.get('message', 'Unknown error')
                        logger.error(f"Server error: {error_msg}")
                        raise RuntimeError(f"Server error: {error_msg}")

                except websocket.WebSocketTimeoutException:
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in message: {e}")
                    continue

            if time.time() >= timeout:
                raise TimeoutError("Image generation timed out")

        except Exception as e:
            logger.error(f"Error tracking progress: {e}")
            raise

    def queue_and_generate(self, workflow: Dict[str, Any], save_path: Optional[str] = None) -> Optional[str]:
        """Queue and generate an image using the provided workflow."""
        try:
            if not self.validate_server_connection():
                return None

            ws, server_address, client_id = self.open_websocket_connection()

            try:
                prompt_id = self.queue_prompt(workflow, client_id, server_address)
                if not prompt_id:
                    return None

                self.track_progress(ws, prompt_id)

                images = self.get_images(prompt_id, server_address)
                if not images:
                    return None

                image_path = self.save_image(images, prompt_id, save_path)
                if image_path and self._validate_image_file(image_path):
                    return image_path

                return None

            finally:
                ws.close()

        except Exception as e:
            logger.error(f"Error in queue_and_generate: {e}")
            return None

    def get_images(self, prompt_id: str, server_address: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve generated images from the server."""
        try:
            response = requests.get(
                f"{server_address}/history/{prompt_id}",
                timeout=30
            )
            response.raise_for_status()

            history = response.json()
            outputs = history.get(prompt_id, {}).get('outputs', {})

            images = []
            for node_id, node_data in outputs.items():
                if 'images' in node_data:
                    for image_info in node_data['images']:
                        image_data = self.get_image(
                            image_info.get('filename'),
                            image_info.get('subfolder', ''),
                            image_info.get('type', ''),
                            server_address
                        )
                        if image_data:
                            images.append({
                                'filename': image_info.get('filename'),
                                'image_data': image_data
                            })

            return images

        except Exception as e:
            logger.error(f"Error retrieving images: {e}")
            return None

    def get_image(self, filename: str, subfolder: str, folder_type: str, server_address: str) -> Optional[bytes]:
        """Retrieve a specific image from the server."""
        try:
            response = requests.get(
                f"{server_address}/view",
                params={
                    'filename': filename,
                    'subfolder': subfolder,
                    'type': folder_type
                },
                timeout=30
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error retrieving image {filename}: {e}")
            return None

    def save_image(self, images: List[Dict[str, Any]], prompt_id: str, save_path: Optional[str] = None) -> Optional[str]:
        """Save generated images to disk."""
        try:
            if not images:
                logger.error("No images to save")
                return None

            image_data = images[0].get('image_data')
            if not image_data:
                logger.error("No image data found")
                return None

            image = Image.open(BytesIO(image_data))

            if save_path:
                image_path = save_path
            else:
                # Generate path based on prompt ID if no path specified
                image_dir = os.path.join(
                    os.path.dirname(self.checkpoints_dir),
                    'outputs',
                    prompt_id
                )
                os.makedirs(image_dir, exist_ok=True)
                image_path = os.path.join(image_dir, f"{prompt_id}.png")

            # Ensure directory exists
            os.makedirs(os.path.dirname(image_path), exist_ok=True)

            image.save(image_path, "PNG")
            logger.info(f"Image saved at {image_path}")
            return image_path

        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None

    def generate_workflow(self, prompt_data: Union[str, Dict[str, str]]) -> Dict[str, Any]:
        """Generate complete workflow for image generation."""
        try:
            # Process prompt based on type
            if isinstance(prompt_data, str):
                positive_prompt, negative_prompt = self.prompt_enhancer.enhance_legacy_prompt(prompt_data)
            else:
                positive_prompt, negative_prompt = self.prompt_enhancer.process_structured_prompt(prompt_data)

            # Get current preset
            preset = QualityPreset.get_preset(self.quality)

            # Start with default workflow
            workflow = self.default_workflow_json()

            # Update prompts
            workflow["3"]["inputs"]["text"] = positive_prompt
            workflow["4"]["inputs"]["text"] = negative_prompt

            # Update dimensions if needed based on prompt
            if isinstance(prompt_data, dict):
                width, height = self._get_dimensions_for_prompt(prompt_data.get("main", ""), preset)
                workflow["2"]["inputs"]["width"] = width
                workflow["2"]["inputs"]["height"] = height

            # Update node references
            workflow["5"]["inputs"]["latent_image"] = ["2", 0]
            workflow["5"]["inputs"]["model"] = ["1", 0]
            workflow["5"]["inputs"]["negative"] = ["4", 0]
            workflow["5"]["inputs"]["positive"] = ["3", 0]
            workflow["3"]["inputs"]["clip"] = ["1", 1]
            workflow["4"]["inputs"]["clip"] = ["1", 1]
            workflow["6"]["inputs"]["samples"] = ["5", 0]
            workflow["6"]["inputs"]["vae"] = ["1", 2]
            workflow["7"]["inputs"]["images"] = ["6", 0]

            logger.info(f"Generated workflow with quality {self.quality.name}")
            return workflow

        except Exception as e:
            logger.error(f"Error generating workflow: {e}")
            raise

    def _get_dimensions_for_prompt(self, prompt: str, preset: QualityPreset) -> Tuple[int, int]:
        """Determine appropriate dimensions based on prompt content."""
        prompt_lower = prompt.lower()

        if "landscape" in prompt_lower or "wide" in prompt_lower:
            # Landscape orientation (3:2)
            return (int(preset.width * 1.5), preset.height)
        elif "portrait" in prompt_lower or "character" in prompt_lower:
            # Portrait orientation (2:3)
            return (preset.width, int(preset.height * 1.5))
        else:
            # Square default
            return (preset.width, preset.height)

    def _validate_image_file(self, image_path: str) -> bool:
        """Validate if an image file exists and is not corrupted."""
        try:
            if not os.path.exists(image_path):
                return False
                
            # Try to open and verify the image
            with Image.open(image_path) as img:
                img.verify()
            return True
            
        except Exception as e:
            logger.debug(f"Image validation failed for {image_path}: {e}")
            return False

    def default_workflow_json(self) -> Dict[str, Any]:
        """Returns the default workflow configuration."""
        preset = QualityPreset.get_preset(self.quality)

        return {
            "1": {  # Base model loader
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            "2": {  # Empty latent image
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": preset.height,
                    "width": preset.width
                }
            },
            "3": {  # Positive prompt encoder
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["1", 1],
                    "text": ""  # Will be filled with positive prompt
                }
            },
            "4": {  # Negative prompt encoder
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["1", 1],
                    "text": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"
                }
            },
            "5": {  # KSampler
                "class_type": "KSampler",
                "inputs": {
                    "cfg": preset.cfg,
                    "denoise": preset.denoise,
                    "latent_image": ["2", 0],  # From empty latent
                    "model": ["1", 0],  # From base model
                    "negative": ["4", 0],  # From negative prompt
                    "positive": ["3", 0],  # From positive prompt
                    "sampler_name": preset.sampler,
                    "scheduler": preset.scheduler,
                    "seed": random.randint(0, 0xffffffffffffffff),
                    "steps": preset.steps
                }
            },
            "6": {  # VAE decode
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],  # From KSampler
                    "vae": ["1", 2]  # From base model VAE
                }
            },
            "7": {  # Save image
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "output",
                    "images": ["6", 0]  # From VAE decode
                }
            }
        }

    def generate_image_with_character(
        self,
        prompt: str,
        character_image_path: str,
        save_path: Optional[str] = None,
        ip_adapter_weight: float = 0.8
    ) -> Optional[str]:
        """Generate an image while maintaining character consistency using IP-Adapter."""
        try:
            # Start with the default workflow
            workflow = self.default_workflow_json()
            
            # Add IP-Adapter nodes
            workflow.update({
                "8": {  # Load image for IP-Adapter
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": character_image_path
                    }
                },
                "9": {  # IP-Adapter model loader
                    "class_type": "IPAdapterModelLoader",
                    "inputs": {
                        "model_name": "ip-adapter_sd15.safetensors"
                    }
                },
                "10": {  # Apply IP-Adapter
                    "class_type": "IPAdapterApply",
                    "inputs": {
                        "model": ["1", 0],  # Base model output
                        "ip_adapter": ["9", 0],  # IP-Adapter model
                        "image": ["8", 0],  # Reference image
                        "weight": ip_adapter_weight
                    }
                }
            })
            
            # Update KSampler to use IP-Adapter output
            workflow["5"]["inputs"]["model"] = ["10", 0]
            
            # Generate the image
            return self.queue_and_generate(workflow, save_path)

        except Exception as e:
            logger.error(f"Error in generate_image_with_character: {e}")
            return None

    def generate_scene_with_characters(
        self,
        prompt_data: Dict[str, str],
        characters: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """Generate a scene with multiple characters while maintaining visual consistency.
        
        Args:
            prompt_data: Dictionary containing prompt information (main, style, details, quality)
            characters: List of character dictionaries, each containing:
                - character: Dict with name, description, and reference_image
                - weight: Float indicating IP adapter weight for this character
            output_path: Optional path to save the generated image
        """
        try:
            # Start with the default workflow
            workflow = self.default_workflow_json()
            
            # Process the prompt
            positive_prompt, negative_prompt = self.prompt_enhancer.process_structured_prompt(prompt_data)
            
            # Update the positive and negative prompts
            workflow["3"]["inputs"]["text"] = positive_prompt
            workflow["4"]["inputs"]["text"] = negative_prompt
            
            # Add nodes for each character's IP adapter
            current_node_id = 8  # Start after our basic nodes
            previous_model = "1"  # Start with base model output
            
            for char_data in characters:
                character = char_data["character"]
                weight = char_data["weight"]
                
                # Add LoadImage node for character
                workflow[str(current_node_id)] = {
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": character["reference_image"]
                    }
                }
                
                # Add IPAdapterModelLoader node
                workflow[str(current_node_id + 1)] = {
                    "class_type": "IPAdapterModelLoader",
                    "inputs": {
                        "model_name": "ip-adapter_sd15.safetensors"
                    }
                }
                
                # Add IPAdapterApply node
                workflow[str(current_node_id + 2)] = {
                    "class_type": "IPAdapterApply",
                    "inputs": {
                        "model": [previous_model, 0],
                        "ip_adapter": [str(current_node_id + 1), 0],
                        "image": [str(current_node_id), 0],
                        "weight": weight
                    }
                }
                
                # Update for next iteration
                previous_model = str(current_node_id + 2)
                current_node_id += 3
            
            # Update KSampler to use the final IP-Adapter output
            workflow["5"]["inputs"]["model"] = [previous_model, 0]
            
            # Generate the image
            return self.queue_and_generate(workflow, output_path)

        except Exception as e:
            logger.error(f"Error in generate_scene_with_characters: {e}")
            return None

    def load_workflow_json(self) -> Dict[str, Any]:
        """Load and parse the workflow JSON."""
        try:
            if isinstance(self.workflow_json, str):
                return json.loads(self.workflow_json)
            return self.workflow_json
        except json.JSONDecodeError as e:
            logger.error(f"Failed to load workflow JSON: {e}")
            return {}

    def clear_cache(self):
        """Clear the image cache."""
        self.image_cache.clear()
        logger.info("Image cache cleared")

    def cleanup(self):
        """Clean up resources."""
        self.clear_cache()
        logger.info("ImageGenerator cleanup complete")

    def __del__(self):
        """Cleanup when object is deleted."""
        self.cleanup()
