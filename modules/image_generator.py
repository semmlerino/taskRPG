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
    """Handles prompt enhancement and processing."""

    def __init__(self):
        self.quality_terms: Dict[str, List[str]] = {
            "technical": [
                "masterpiece",
                "best quality",
                "highly detailed",
                "sharp focus",
                "ultra high resolution",
                "8k uhd",
                "high detail"
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
            "render": [
                "octane render",
                "unreal engine 5",
                "trending on artstation",
                "cinematic composition",
                "concept art",
                "digital art"
            ]
        }

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
            "cropped"
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

            # Build quality enhancements
            technical = random.sample(self.quality_terms["technical"], min(num_terms, len(self.quality_terms["technical"])))
            lighting = random.sample(self.quality_terms["lighting"], min(num_terms, len(self.quality_terms["lighting"])))
            render = random.sample(self.quality_terms["render"], min(num_terms, len(self.quality_terms["render"])))

            # Combine all components
            components = [
                main_subject,
                style_info,
                details,
                ", ".join(technical),
                ", ".join(lighting),
                ", ".join(render)
            ]

            # Clean up and combine
            positive_prompt = ", ".join(filter(None, [x.strip() for x in components]))

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
            structured_prompt = {
                "main": prompt,
                "style": "digital art, concept art",
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
            response = requests.post(
                f"{server_address}/prompt",
                json={"prompt": workflow, "client_id": client_id},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('prompt_id')
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None

    def track_progress(self, ws: websocket.WebSocket, prompt_id: str):
        """Track the progress of image generation."""
        try:
            timeout = time.time() + 300  # 5 minute timeout
            while time.time() < timeout:
                try:
                    message = ws.recv()
                    if not isinstance(message, str):
                        continue

                    message_json = json.loads(message)
                    if message_json.get('type') == 'executing' and \
                       message_json.get('data', {}).get('node') is None:
                        break

                except websocket.WebSocketTimeoutException:
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
            workflow["nodes"][1]["inputs"]["text"] = positive_prompt
            workflow["nodes"][2]["inputs"]["text"] = negative_prompt

            # Update dimensions if needed based on prompt
            if isinstance(prompt_data, dict):
                width, height = self._get_dimensions_for_prompt(prompt_data.get("main", ""), preset)
                workflow["nodes"][4]["inputs"]["width"] = width
                workflow["nodes"][4]["inputs"]["height"] = height

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

    def default_workflow_json(self) -> Dict[str, Any]:
        """Returns the default workflow configuration."""
        preset = QualityPreset.get_preset(self.quality)

        return {
            "nodes": [
                {
                    "id": "base_model",
                    "type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": "sd_xl_base_1.0.safetensors"
                    }
                },
                {
                    "id": "positive_prompt",
                    "type": "CLIPTextEncode",
                    "inputs": {
                        "text": "",
                        "clip": "base_model.CLIP"
                    }
                },
                {
                    "id": "negative_prompt",
                    "type": "CLIPTextEncode",
                    "inputs": {
                        "text": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
                        "clip": "base_model.CLIP"
                    }
                },
                {
                    "id": "sampler",
                    "type": "KSampler",
                    "inputs": {
                        "model": "base_model.model",
                        "positive": "positive_prompt.CONDITIONING",
                        "negative": "negative_prompt.CONDITIONING",
                        "latent_image": "empty_latent.LATENT",
                        "steps": preset.steps,
                        "cfg": preset.cfg,
                        "sampler_name": preset.sampler,
                        "scheduler": preset.scheduler,
                        "denoise": preset.denoise,
                        "seed": random.randint(0, 0xffffffffffffffff)
                    }
                },
                {
                    "id": "empty_latent",
                    "type": "EmptyLatentImage",
                    "inputs": {
                        "width": preset.width,
                        "height": preset.height,
                        "batch_size": 1
                    }
                },
                {
                    "id": "decoder",
                    "type": "VAEDecode",
                    "inputs": {
                        "samples": "sampler.LATENT",
                        "vae": "base_model.VAE"
                    }
                },
                {
                    "id": "save_image",
                    "type": "SaveImage",
                    "inputs": {
                        "images": "decoder.IMAGE",
                        "filename_prefix": "output"
                    }
                }
            ]
        }

    def generate_image_with_character(
        self,
        prompt: str,
        character_image_path: str,
        save_path: Optional[str] = None,
        ip_adapter_weight: float = 0.8
    ) -> str:
        """Generate an image while maintaining character consistency using IP-Adapter."""
        
        # Start with the default workflow
        workflow = self.default_workflow_json()
        
        # Add IP-Adapter nodes
        workflow["nodes"].extend([
            {
                "id": "ip_adapter_loader",
                "type": "IPAdapterLoader",
                "inputs": {
                    "image": character_image_path,
                    "model": "ip-adapter_sd15.safetensors"
                }
            },
            {
                "id": "ip_adapter_apply",
                "type": "IPAdapterApply",
                "inputs": {
                    "model": workflow["nodes"][0]["outputs"]["model"],
                    "ip_adapter": "ip_adapter_loader.ip_adapter",
                    "weight": ip_adapter_weight
                }
            }
        ])
        
        # Update the KSampler node to use the IP-Adapter output
        for node in workflow["nodes"]:
            if node["type"] == "KSampler":
                node["inputs"]["model"] = "ip_adapter_apply.output"
        
        # Generate the image
        return self.queue_and_generate(workflow, save_path)

    def generate_scene_with_characters(
        self,
        scene_data: Dict[str, Any],
        character_manager: 'CharacterManager',
        save_path: Optional[str] = None
    ) -> str:
        """Generate a scene with multiple characters while maintaining visual consistency."""
        
        # Extract scene information
        image_prompt = scene_data["image_prompt"]
        focus_character = image_prompt.get("focus_character")
        secondary_characters = image_prompt.get("secondary_characters", [])
        
        # Build the complete scene prompt
        scene_prompt = image_prompt["scene"]
        
        # Add character actions to the prompt
        character_actions = image_prompt.get("character_actions", {})
        for char_name, action in character_actions.items():
            character = character_manager.get_character(char_name)
            if character:
                char_desc = f"{character.description} {action}"
                scene_prompt += f", {char_desc}"
        
        # Start with the default workflow
        workflow = self.default_workflow_json()
        
        # Add IP-Adapter nodes for each character
        ip_adapter_nodes = []
        for idx, char_name in enumerate([focus_character] + secondary_characters):
            if not char_name:
                continue
                
            character = character_manager.get_character(char_name)
            if not character:
                continue
            
            # Adjust weights based on character focus
            weight = 0.8 if char_name == focus_character else 0.5
            
            # Add loader and apply nodes for this character
            loader_id = f"ip_adapter_loader_{idx}"
            apply_id = f"ip_adapter_apply_{idx}"
            
            ip_adapter_nodes.extend([
                {
                    "id": loader_id,
                    "type": "IPAdapterLoader",
                    "inputs": {
                        "image": character.reference_image_path,
                        "model": "ip-adapter_sd15.safetensors"
                    }
                },
                {
                    "id": apply_id,
                    "type": "IPAdapterApply",
                    "inputs": {
                        "model": "base_model.model" if idx == 0 else f"ip_adapter_apply_{idx-1}.output",
                        "ip_adapter": f"{loader_id}.ip_adapter",
                        "weight": weight
                    }
                }
            ])
        
        # Add IP-Adapter nodes to workflow
        workflow["nodes"].extend(ip_adapter_nodes)
        
        # Update the KSampler node to use the final IP-Adapter output
        if ip_adapter_nodes:
            last_apply_node = f"ip_adapter_apply_{len(ip_adapter_nodes)//2 - 1}.output"
            for node in workflow["nodes"]:
                if node["type"] == "KSampler":
                    node["inputs"]["model"] = last_apply_node
        
        # Update the prompt
        for node in workflow["nodes"]:
            if node["type"] == "CLIPTextEncode" and "positive" in node["id"]:
                node["inputs"]["text"] = scene_prompt
        
        # Generate the image
        return self.queue_and_generate(workflow, save_path)

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
