"""
Image generation module for TaskRPG.
Handles SDXL integration with ComfyUI for story image generation.
"""

from __future__ import annotations

# Standard library imports
import os
import json
import logging
import random
import uuid
import time
from typing import Dict, Any, Optional, List, Tuple, Union
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
                steps=100,
                cfg=8.0,
                denoise=0.98,
                sampler="dpmpp_2m_sde",
                scheduler="karras",
                width=1280,
                height=1280
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
        quality: ImageQuality = ImageQuality.STANDARD,
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

    def default_workflow_json(self) -> Dict[str, Any]:
        """Returns the default workflow configuration."""
        preset = QualityPreset.get_preset(self.quality)
        
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": preset.cfg,
                    "denoise": preset.denoise,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": preset.sampler,
                    "scheduler": preset.scheduler,
                    "seed": random.randint(10**6, 10**7),
                    "steps": preset.steps
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
                    "height": preset.height,
                    "width": preset.width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "masterpiece best quality"  # Will be replaced with actual prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": ", ".join(self.prompt_enhancer.negative_terms)
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
            logger.info("WebSocket connection established")
            return ws, self.server_url, client_id
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            raise

    def queue_prompt(self, workflow: Dict[str, Any], client_id: str, server_address: str) -> Optional[str]:
        """Queue a prompt for image generation."""
        try:
            payload = {
                "prompt": workflow,
                "client_id": client_id
            }
            response = requests.post(
                f"{server_address}/prompt",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            prompt_id = response.json().get('prompt_id')
            if prompt_id:
                logger.info(f"Prompt queued with ID: {prompt_id}")
                return prompt_id
            else:
                logger.error("No prompt_id returned")
                return None
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None

    def track_progress(self, ws: websocket.WebSocket, prompt_id: str):
        """Track the progress of image generation."""
        try:
            workflow = self.load_workflow_json()
            node_ids = list(workflow.keys())
            total_nodes = len(node_ids)
            finished_nodes = []
            
            timeout = time.time() + 300  # 5 minute timeout

            while time.time() < timeout:
                try:
                    message = ws.recv()
                    if not isinstance(message, str):
                        continue

                    message_json = json.loads(message)
                    message_type = message_json.get('type')

                    if message_type == 'progress':
                        data = message_json.get('data', {})
                        current_step = data.get('value')
                        max_steps = data.get('max')
                        logger.info(f"Progress: Step {current_step}/{max_steps}")

                    elif message_type in ('execution_cached', 'executing'):
                        data = message_json.get('data', {})
                        if message_type == 'executing' and data.get('prompt_id') == prompt_id and data.get('node') is None:
                            logger.info("Generation completed")
                            break

                        nodes = data.get('nodes', [data.get('node')] if data.get('node') else [])
                        for node in nodes:
                            if node and node not in finished_nodes:
                                finished_nodes.append(node)
                                logger.info(f"Progress: {len(finished_nodes)}/{total_nodes} nodes completed")

                except websocket.WebSocketTimeoutException:
                    continue

            if time.time() >= timeout:
                raise TimeoutError("Image generation timed out")

        except Exception as e:
            logger.error(f"Error tracking progress: {e}")
            raise

    def generate_missing_story_images(self, progress_dialog=None) -> List[str]:
        """Generate images for all stories that have missing images."""
        generated_images = []
        try:
            # Validate server first
            logger.info("Checking ComfyUI server connection...")
            if not self.validate_server_connection():
                logger.error("ComfyUI server not available - aborting image generation")
                return generated_images

            logger.info("Getting list of missing images...")
            missing_images = self._get_missing_story_images()
            
            if not missing_images:
                logger.info("No missing images to generate")
                return generated_images

            total_images = len(missing_images)
            logger.info(f"Found {total_images} images to generate")
            current = 0

            if progress_dialog:
                progress_dialog.setMaximum(total_images)
                logger.info("Progress dialog initialized")

            for story_name, image_info in missing_images:
                try:
                    if progress_dialog and progress_dialog.wasCanceled():
                        logger.info("Image generation canceled by user")
                        break

                    logger.info(f"Processing image for story '{story_name}' node '{image_info['node_key']}'")
                    prompt_data = image_info['prompt']
                    
                    # Log the prompt data
                    logger.info(f"Prompt data: {json.dumps(prompt_data, indent=2)}")

                    if isinstance(prompt_data, str):
                        logger.info("Converting legacy string prompt to structured format")
                        prompt_data = {
                            "main": prompt_data,
                            "style": "digital art, best quality",
                            "details": "detailed, sharp focus",
                            "quality": "STANDARD"
                        }

                    # Generate workflow and log it
                    logger.info("Generating workflow...")
                    workflow = self.generate_workflow(prompt_data)
                    logger.info(f"Workflow generated: {json.dumps(workflow, indent=2)}")
                    
                    # Generate the image
                    logger.info(f"Generating image to path: {image_info['path']}")
                    image_path = self.queue_and_generate(
                        workflow,
                        save_path=image_info['path']
                    )
                    
                    if image_path:
                        generated_images.append(image_path)
                        logger.info(f"Successfully generated image: {image_path}")
                    else:
                        logger.error(f"Failed to generate image for {story_name} - {image_info['node_key']}")
                    
                    current += 1
                    if progress_dialog:
                        progress_dialog.setValue(current)
                        logger.info(f"Progress updated: {current}/{total_images}")
                        
                except Exception as e:
                    logger.error(f"Error generating image for {story_name}: {e}", exc_info=True)
                    continue

            logger.info(f"Image generation complete. Generated {len(generated_images)} images")
            return generated_images

        except Exception as e:
            logger.error(f"Error in generate_missing_story_images: {e}", exc_info=True)
            return generated_images

    def _get_missing_story_images(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Identify which story images need to be generated."""
        missing_images = []
        try:
            # Get the correct stories directory from TaskRPG
            stories_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'stories'
            )
            
            logger.info(f"Checking for missing images in stories directory: {stories_dir}")
            
            if not os.path.exists(stories_dir):
                logger.error(f"Stories directory not found: {stories_dir}")
                return missing_images

            # Create assets/images directory if it doesn't exist
            assets_dir = os.path.join(
                os.path.dirname(stories_dir),
                'assets',
                'images'
            )
            os.makedirs(assets_dir, exist_ok=True)
            logger.info(f"Ensuring assets directory exists: {assets_dir}")

            # Check each story file
            for filename in os.listdir(stories_dir):
                if not filename.endswith('.json'):
                    continue
                    
                story_path = os.path.join(stories_dir, filename)
                story_name = os.path.splitext(filename)[0]
                
                logger.info(f"Processing story file: {story_name}")
                
                try:
                    with open(story_path, 'r', encoding='utf-8') as f:
                        story_data = json.load(f)

                    image_folder = os.path.join(assets_dir, story_name)
                    os.makedirs(image_folder, exist_ok=True)
                    logger.info(f"Image folder for story: {image_folder}")

                    for node_key, node_data in story_data.items():
                        if isinstance(node_data, dict) and 'image_prompt' in node_data:
                            image_path = os.path.join(image_folder, f"{node_key}.png")
                            logger.info(f"Checking image for node {node_key}: {image_path}")
                            
                            if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                                logger.info(f"Missing image found for node {node_key}")
                                missing_images.append((
                                    story_name,
                                    {
                                        'prompt': node_data['image_prompt'],
                                        'path': image_path,
                                        'node_key': node_key
                                    }
                                ))
                                
                except Exception as e:
                    logger.error(f"Error processing story {story_name}: {e}")
                    continue

            logger.info(f"Found {len(missing_images)} missing images")
            for story_name, info in missing_images:
                logger.info(f"Missing image: {story_name} - {info['node_key']}")
            return missing_images

        except Exception as e:
            logger.error(f"Error getting missing story images: {e}", exc_info=True)
            return missing_images

    def get_images(self, prompt_id: str, server_address: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve generated images from the server."""
        try:
            response = requests.get(
                f"{server_address}/history/{prompt_id}",
                timeout=30
            )
            response.raise_for_status()
            history = response.json()

            images = []
            outputs = history.get(prompt_id, {}).get('outputs', {})
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
            workflow["6"]["inputs"]["text"] = positive_prompt
            workflow["7"]["inputs"]["text"] = negative_prompt
            
            # Update dimensions if needed based on prompt
            if isinstance(prompt_data, dict):
                width, height = self._get_dimensions_for_prompt(prompt_data.get("main", ""), preset)
                workflow["5"]["inputs"]["width"] = width
                workflow["5"]["inputs"]["height"] = height
            
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

    def queue_and_generate(self, workflow: Dict[str, Any], save_path: Optional[str] = None) -> Optional[str]:
        """Queue and generate an image using the provided workflow."""
        try:
            if not self.validate_server_connection():
                logger.error("ComfyUI server not available")
                return None

            ws, server_address, client_id = self.open_websocket_connection()
            
            try:
                prompt_id = self.queue_prompt(workflow, client_id, server_address)
                if not prompt_id:
                    logger.error("Failed to queue prompt")
                    return None

                self.track_progress(ws, prompt_id)
                
                images = self.get_images(prompt_id, server_address)
                if not images:
                    logger.error("No images generated")
                    return None

                image_path = self.save_image(images, prompt_id, save_path)
                if image_path and self._validate_image_file(image_path):
                    logger.info(f"Image generated successfully: {image_path}")
                    return image_path
                    
                return None

            finally:
                ws.close()

        except Exception as e:
            logger.error(f"Error in queue_and_generate: {e}")
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

    def _validate_image_file(self, path: str) -> bool:
        """Validate that a file is a valid image."""
        try:
            with Image.open(path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.error(f"Image validation failed for {path}: {e}")
            return False

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