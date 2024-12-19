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
import datetime
import copy
import shutil
from PyQt5.QtWidgets import QApplication

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
                width=1216,
                height=832
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
        # Basic quality terms
        self.quality_terms = [
            "masterpiece",
            "best quality",
            "highly detailed",
            "sharp focus",
            "professional"
        ]

        # Negative terms
        self.negative_terms = [
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
        """Process structured prompt data."""
        try:
            # Extract components
            main_subject = prompt_data.get("main", "")
            style_info = prompt_data.get("style", "")
            details = prompt_data.get("details", "")

            # Build positive prompt
            components = [
                main_subject,
                style_info,
                details,
                ", ".join(random.sample(self.quality_terms, 2))
            ]
            positive_prompt = ", ".join(filter(None, [x.strip() for x in components]))

            # Generate negative prompt
            negative_prompt = ", ".join(self.negative_terms)

            logger.debug(f"Processed prompt")
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
                "style": style_info if style_info else "digital art",
                "details": "detailed, sharp focus",
            }
            return self.process_structured_prompt(structured_prompt)
        except Exception as e:
            logger.error(f"Error enhancing legacy prompt: {e}")
            return prompt, ", ".join(self.negative_terms)


class ImageGenerator:
    """Enhanced image generator with SDXL support."""

    def _validate_and_prepare_workflow(self, workflow: Dict[str, Any], prompt: str = "", negative_prompt: str = "") -> Dict[str, Any]:
        """Validate and prepare the workflow with the given prompts."""
        try:
            # Find the CLIP Text Encode node for the prompt
            prompt_node = None
            for node_id, node in workflow.items():
                if node["class_type"] == "CLIPTextEncode":
                    prompt_node = node_id
                    break

            if not prompt_node:
                logger.error("No CLIPTextEncode node found in workflow")
                return workflow

            # Update the prompt text
            workflow[prompt_node]["inputs"]["text"] = prompt

            return workflow

        except Exception as e:
            logger.error(f"Error in _validate_and_prepare_workflow: {e}")
            return workflow

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
        self.ws = None  # Initialize WebSocket connection as None

        # Initialize components
        self.image_cache = {}
        self.prompt_enhancer = PromptEnhancer()

        # Load settings to get selected workflow
        settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'settings.json')
        selected_workflow = "newFluxWorkflow"  # Default to newFluxWorkflow
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    selected_workflow = settings.get('selected_workflow', "newFluxWorkflow")
                    logger.info(f"Found workflow in settings: {selected_workflow}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

        # Initialize workflow
        if workflow_json is not None:
            logger.info("Using provided workflow_json")
            self.original_workflow_json = workflow_json
            self.workflow_json = self._validate_and_prepare_workflow(workflow_json)
        else:
            # Try to load selected workflow file
            workflow_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'workflows',
                f"{selected_workflow}.json"
            )
            logger.info(f"Attempting to load workflow from: {workflow_file}")
            try:
                if os.path.exists(workflow_file):
                    with open(workflow_file, 'r', encoding='utf-8') as f:
                        loaded_workflow = json.load(f)
                        # Store the loaded workflow before validation
                        self.original_workflow_json = loaded_workflow
                        # Now validate and prepare it
                        self.workflow_json = self._validate_and_prepare_workflow(self.original_workflow_json)
                        logger.info(f"Successfully loaded and validated workflow from {workflow_file}")
                        # Log the model nodes
                        for node_id, node in self.workflow_json.items():
                            if node.get("class_type") in ["UNETLoader", "DualCLIPLoader", "VAELoader"]:
                                logger.info(f"Model node {node_id}: {node['class_type']} - {node['inputs']}")
                else:
                    logger.warning(f"Selected workflow file not found: {workflow_file}")
                    # Try to load newFluxWorkflow as fallback
                    fallback_file = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'workflows',
                        "newFluxWorkflow.json"
                    )
                    if os.path.exists(fallback_file):
                        with open(fallback_file, 'r', encoding='utf-8') as f:
                            self.workflow_json = json.load(f)
                        logger.info("Falling back to newFluxWorkflow")
                    else:
                        self.workflow_json = self.default_workflow_json()
                        logger.info("Falling back to default workflow")
            except Exception as e:
                logger.error(f"Error loading workflow file: {e}")
                self.workflow_json = self.default_workflow_json()
                logger.info("Falling back to default workflow due to error")

        logger.info(f"ImageGenerator initialized with quality: {quality.name} and workflow: {selected_workflow}")

    def scan_story_for_missing_images(self, story_data: Dict[str, Any], story_name: str) -> List[Tuple[str, str]]:
        """Scan story for missing images using project structure."""
        missing_images = []
        logging.info(f"Scanning story '{story_name}' for missing images")

        try:
            # Create the story's image directory if it doesn't exist
            image_dir = os.path.join(ASSETS_DIR, 'images', story_name)
            os.makedirs(image_dir, exist_ok=True)
            logging.info(f"Using image directory: {image_dir}")

            # Scan story nodes
            total_nodes = 0
            missing_count = 0
            for node_key, node_data in story_data.items():
                if isinstance(node_data, dict) and 'image_prompt' in node_data:
                    total_nodes += 1
                    image_path = os.path.join(image_dir, f"{node_key}.png")
                    prompt = node_data['image_prompt']

                    # Check existence and validity
                    if not os.path.exists(image_path) or not self._validate_image_file(image_path):
                        missing_count += 1
                        logging.info(f"Found missing image - ID: {node_key}")
                        logging.debug(f"Prompt: {prompt}")
                        logging.debug(f"Target path: {image_path}")
                        missing_images.append((prompt, image_path))

            logging.info(f"Found {missing_count} missing images out of {total_nodes} total in '{story_name}'")
            return missing_images

        except Exception as e:
            logging.error(f"Error scanning for missing images: {str(e)}", exc_info=True)
            return []

    def generate_missing_story_images(self, story_data, story_name, progress_dialog=None):
        """Generate missing images for a story."""
        logging.info(f"Starting image generation for story: {story_name}")
        try:
            logging.info("Scanning for missing images...")
            missing_images = self.scan_story_for_missing_images(story_data, story_name)
            if not missing_images:
                logging.info("No missing images found")
                return []

            generated_images = []
            total_images = len(missing_images)
            logging.info(f"Found {total_images} missing images to generate")

            for i, (prompt, image_path) in enumerate(missing_images):
                logging.info(f"\n{'='*50}")
                logging.info(f"Processing image {i+1}/{total_images}")
                logging.info(f"Prompt: {prompt}")
                logging.info(f"Target path: {os.path.basename(image_path)}")

                if progress_dialog and progress_dialog.wasCanceled():
                    logging.warning("Image generation cancelled by user")
                    break

                if progress_dialog:
                    status_msg = f"Generating image {i + 1} of {total_images}..."
                    logging.info(f"Updating progress dialog: {status_msg}")
                    progress_dialog.setLabelText(status_msg)
                    progress_dialog.setValue(i)
                    QApplication.processEvents()
                    logging.debug("Events processed after progress update")

                try:
                    logging.info("Starting individual image generation")
                    generated_path = self.generate_image(prompt, image_path)
                    if generated_path:
                        logging.info(f"Successfully generated image: {generated_path}")
                        generated_images.append(generated_path)
                        if progress_dialog:
                            QApplication.processEvents()
                            logging.debug("Events processed after successful generation")
                    else:
                        logging.error("Image generation returned None")
                except Exception as e:
                    logging.error(f"Error generating image {image_path}: {str(e)}", exc_info=True)
                    continue

                logging.debug("Processing events after iteration")
                if progress_dialog:
                    QApplication.processEvents()

            if progress_dialog and not progress_dialog.wasCanceled():
                logging.info("Updating final progress")
                progress_dialog.setValue(total_images)
                QApplication.processEvents()

            logging.info(f"Generation complete. Successfully generated {len(generated_images)} images")
            return generated_images

        except Exception as e:
            logging.error(f"Error in generate_missing_story_images: {str(e)}", exc_info=True)
            raise
        finally:
            logging.info("Cleaning up resources...")
            self.cleanup_websocket()
            if progress_dialog:
                QApplication.processEvents()
            logging.info("Cleanup complete")

    def cleanup_websocket(self):
        """Clean up WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logging.debug(f"Error closing WebSocket: {str(e)}")
            finally:
                self.ws = None

    def generate_image(self, prompt, output_path):
        """Generate a single image."""
        logging.info(f"\nStarting image generation for: {output_path}")
        logging.info(f"Using prompt: {prompt}")
        
        try:
            logging.info("Initializing WebSocket")
            if not self.init_websocket():
                raise RuntimeError("Failed to initialize WebSocket")
            
            logging.info("Preparing workflow")
            workflow = self.prepare_workflow(prompt)
            if not workflow:
                logging.error("Failed to prepare workflow")
                return None

            # Queue the prompt
            queue_msg = {
                "prompt": workflow,
                "client_id": self.client_id
            }

            logging.info("Queueing prompt...")
            response = requests.post(
                f"{self.server_url}/prompt",
                json=queue_msg,
                timeout=10
            )
            if response.status_code != 200:
                logging.error(f"Failed to queue prompt: {response.text}")
                raise RuntimeError(f"Failed to queue prompt: {response.status_code}")
            
            prompt_id = response.json().get('prompt_id')
            if not prompt_id:
                logging.error("No prompt_id in response")
                raise RuntimeError("No prompt_id in response")
            
            logging.info(f"Prompt queued successfully with ID: {prompt_id}")

            # Wait for execution to complete
            while True:
                try:
                    message = self.ws.recv()
                    if isinstance(message, str):
                        data = json.loads(message)
                        if data['type'] == 'executing':
                            node_info = data.get('data', {})
                            if node_info.get('node') is None and node_info.get('prompt_id') == prompt_id:
                                logging.info("Execution completed")
                                break
                    QApplication.processEvents()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    logging.error(f"Error receiving message: {str(e)}")
                    raise

            # Get results from history
            logging.info("Fetching results from history")
            history_response = requests.get(f"{self.server_url}/history/{prompt_id}")
            if history_response.status_code != 200:
                logging.error(f"Failed to get history: {history_response.text}")
                raise RuntimeError("Failed to get history")

            history_data = history_response.json()
            node_outputs = history_data.get(prompt_id, {}).get('outputs', {})
            
            # Find and save the first image
            for node_id, output in node_outputs.items():
                if 'images' in output and output['images']:
                    image_info = output['images'][0]
                    params = {
                        "filename": image_info["filename"],
                        "subfolder": image_info.get("subfolder", ""),
                        "type": image_info.get("type", "")
                    }
                    
                    image_response = requests.get(
                        f"{self.server_url}/view",
                        params=params
                    )
                    
                    if image_response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(image_response.content)
                        logging.info(f"Image saved to {output_path}")
                        return output_path

            logging.error("No image found in output")
            return None

        except Exception as e:
            logging.error(f"Error in generate_image: {str(e)}", exc_info=True)
            return None
        finally:
            self.cleanup_websocket()
            QApplication.processEvents()

    def init_websocket(self):
        """Initialize WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
        
        try:
            # Generate a client ID that will be used for the entire session
            self.client_id = str(uuid.uuid4())
            ws_url = f"ws://{self.server_url.split('://')[-1]}/ws?clientId={self.client_id}"
            logging.info(f"Connecting to WebSocket at {ws_url}")
            
            self.ws = websocket.WebSocket()
            self.ws.connect(ws_url)
            self.ws.settimeout(1.0)  # 1 second timeout
            logging.info("WebSocket connection established successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize WebSocket: {str(e)}", exc_info=True)
            self.ws = None
            return False

    def prepare_workflow(self, prompt):
        """Prepare the workflow for image generation."""
        try:
            # Use the stored workflow_json instead of loading it again
            if not hasattr(self, 'workflow_json') or not self.workflow_json:
                logger.error("No workflow available")
                return None
                
            # Validate prompt
            if not prompt or not isinstance(prompt, str):
                logger.error(f"Invalid prompt: {prompt}")
                return None
                
            # Make a copy of the workflow to avoid modifying the original
            workflow = copy.deepcopy(self.workflow_json)
            
            # Find the SaveImage node and ensure it has proper metadata
            for node_id, node in workflow.items():
                if node["class_type"] == "SaveImage":
                    if "inputs" not in node:
                        node["inputs"] = {}
                    # Add metadata to include workflow information
                    node["inputs"]["metadata"] = {
                        "workflow": self.original_workflow_json,
                        "prompt": prompt,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    logger.info(f"Added metadata to SaveImage node {node_id}")
                    
            # Find the CLIP Text Encode node and update its prompt
            prompt_updated = False
            for node_id, node in workflow.items():
                if node["class_type"] == "CLIPTextEncode":
                    # Update the prompt text
                    node["inputs"]["text"] = prompt
                    logger.info(f"Updated prompt in node {node_id}: {prompt}")
                    prompt_updated = True
                    break
                    
            if not prompt_updated:
                logger.error("No CLIPTextEncode node found in workflow")
                return None
                
            # Ensure UNETLoader is using fp8_e4m3fn weight type
            for node_id, node in workflow.items():
                if node["class_type"] == "UNETLoader":
                    node["inputs"]["weight_dtype"] = "fp8_e4m3fn"
                    logger.info(f"Set UNETLoader weight_dtype to fp8_e4m3fn in node {node_id}")
                    
            # Validate CLIP models
            for node_id, node in workflow.items():
                if node["class_type"] == "DualCLIPLoader":
                    if node["inputs"]["clip_name1"] != "t5xxl_fp8_e4m3fn.safetensors" or node["inputs"]["clip_name2"] != "clip_l.safetensors":
                        logger.warning(f"CLIP models in workflow may not match optimal configuration")
                        
            return workflow
            
        except Exception as e:
            logger.error(f"Error preparing workflow: {e}")
            return None

    def get_image_from_history(self, client_id: str):
        """Get the generated image from the history."""
        try:
            # Get the history
            history = self.get_images("history", self.server_url)
            if not history:
                logger.error("No history found")
                return None

            # Get the image data
            for entry in history:
                if entry.get("client_id") == client_id:
                    image_data = entry.get("image_data")
                    if image_data:
                        return image_data

            logger.error("No image data found for client ID")
            return None
            
        except Exception as e:
            logger.error(f"Error getting image from history: {e}")
            return None

    def save_image(self, image_data, output_path):
        """Save the generated image to disk."""
        try:
            # Create a temporary file to validate image data before saving
            temp_path = os.path.join(os.path.dirname(output_path), f"temp.png")
            with open(temp_path, 'wb') as f:
                f.write(image_data)

            # Validate image data
            try:
                with Image.open(temp_path) as img:
                    # Basic validation
                    if img.size[0] <= 0 or img.size[1] <= 0:
                        raise ValueError("Invalid image dimensions")

                    # Check image mode
                    if img.mode not in ['RGB', 'RGBA']:
                        logger.warning(f"Unexpected image mode: {img.mode}, converting to RGB")
                        img = img.convert('RGB')

                    # Save the validated image
                    img.save(output_path, "PNG", optimize=True)
                    logger.info(f"Image saved to: {output_path}")

                    # Verify the saved image
                    if not os.path.exists(output_path):
                        raise FileNotFoundError("Saved image file not found")

                    with Image.open(output_path) as saved_img:
                        if saved_img.size != (img.size[0], img.size[1]):
                            raise ValueError("Saved image dimensions don't match original")

                    return output_path

            except Exception as e:
                logger.error(f"Image validation/saving failed: {e}")
                return None

        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {e}")

    def _cleanup_temp_files(self, prompt_id: str) -> None:
        """Clean up any temporary files created during image generation."""
        try:
            # Clean up temporary image file if it exists
            temp_path = os.path.join(os.getcwd(), f"temp_{prompt_id}.png")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Removed temporary file: {temp_path}")

            # Clean up any ComfyUI temporary files
            if hasattr(self, 'checkpoints_dir') and self.checkpoints_dir:
                temp_dir = os.path.join(os.path.dirname(self.checkpoints_dir), 'temp')
                if os.path.exists(temp_dir):
                    for filename in os.listdir(temp_dir):
                        if prompt_id in filename:
                            try:
                                os.remove(os.path.join(temp_dir, filename))
                                logger.debug(f"Removed ComfyUI temp file: {filename}")
                            except Exception as e:
                                logger.warning(f"Failed to remove temp file {filename}: {e}")

        except Exception as e:
            logger.warning(f"Error during temp file cleanup: {e}")

    def get_generated_image(self, node_key: str, story_name: str) -> Optional[str]:
        """Get the path to a generated image for a specific story node."""
        try:
            image_path = os.path.join(ASSETS_DIR, 'images', story_name, f"{node_key}.png")
            if os.path.exists(image_path):
                # Validate image file
                try:
                    with Image.open(image_path) as img:
                        # Basic validation
                        if img.size[0] > 0 and img.size[1] > 0:
                            return image_path
                        else:
                            logger.warning(f"Invalid image dimensions for {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to validate image {image_path}: {e}")
                    # Remove corrupted image
                    try:
                        os.remove(image_path)
                        logger.info(f"Removed corrupted image: {image_path}")
                    except:
                        pass
            return None
        except Exception as e:
            logger.error(f"Error getting generated image: {e}")
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

            # Use the loaded workflow instead of default
            workflow = self.workflow_json.copy()

            # Find nodes by class type
            clip_node = None
            latent_node = None
            for node_id, node in workflow.items():
                class_type = node.get("class_type", "")
                
                # Find CLIPTextEncode node - in Flux workflow we only have one
                if class_type == "CLIPTextEncode":
                    clip_node = node_id
                
                # Find EmptyLatentImage node
                elif class_type == "EmptyLatentImage":
                    latent_node = node_id

            # Update prompt in the CLIP node
            if not clip_node:
                raise ValueError("No CLIPTextEncode node found in workflow")

            workflow[clip_node]["inputs"]["text"] = positive_prompt

            # Update dimensions if needed based on prompt
            if isinstance(prompt_data, dict) and latent_node:
                width, height = self._get_dimensions_for_prompt(prompt_data.get("main", ""), preset)
                workflow[latent_node]["inputs"]["width"] = width
                workflow[latent_node]["inputs"]["height"] = height

            # Log workflow details for debugging
            node_list = [node_id for node_id in workflow.keys()]
            logger.info(f"Using workflow with nodes: {node_list}")

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

    def load_workflow_json(self) -> Dict[str, Any]:
        """Load and parse the workflow JSON."""
        try:
            # The workflows folder is at the root level, not in modules
            workflow_path = os.path.join(os.path.dirname(__file__), "..", "..", "workflows", "Flux.json")
            logger.info(f"Loading workflow from: {workflow_path}")
            
            if not os.path.exists(workflow_path):
                logger.error(f"Workflow file not found: {workflow_path}")
                return self.default_workflow_json()
                
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
                
            # Log workflow structure
            logger.info("Loaded workflow structure:")
            for node_id, node in workflow.items():
                logger.info(f"Node {node_id}: {node.get('class_type')} - {node.get('_meta', {}).get('title', 'No title')}")
                
            return workflow
            
        except Exception as e:
            logger.error(f"Error loading workflow JSON: {e}")
            logger.info("Falling back to default workflow")
            return self.default_workflow_json()

    def default_workflow_json(self) -> Dict[str, Any]:
        """Returns the default workflow configuration matching flux.json."""
        return {
            "11": {
                "inputs": {
                    "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                    "clip_name2": "clip_l.safetensors",
                    "type": "flux"
                },
                "class_type": "DualCLIPLoader",
                "is_changed": False,  # Tell ComfyUI to cache this
                "_meta": {
                    "title": "DualCLIPLoader"
                }
            },
            "12": {
                "inputs": {
                    "unet_name": "flux_schnell.sft",
                    "weight_dtype": "fp8_e4m3fn_fast"
                },
                "class_type": "UNETLoader",
                "is_changed": False,  # Tell ComfyUI to cache this
                "_meta": {
                    "title": "Load Diffusion Model"
                }
            },
            "10": {
                "inputs": {
                    "vae_name": "ae.safetensors"
                },
                "class_type": "VAELoader",
                "is_changed": False,  # Tell ComfyUI to cache this
                "_meta": {
                    "title": "Load VAE"
                }
            },
            "6": {
                "inputs": {
                    "text": "masterpiece, best quality",
                    "speak_and_recognation": True,
                    "clip": ["11", 1]  # Use output 1 for cached state
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "5": {
                "inputs": {
                    "width": 1728,
                    "height": 1152,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {
                    "title": "Empty Latent Image"
                }
            },
            "25": {
                "inputs": {
                    "noise_seed": 619906050193391
                },
                "class_type": "RandomNoise",
                "_meta": {
                    "title": "RandomNoise"
                }
            },
            "16": {
                "inputs": {
                    "sampler_name": "euler"
                },
                "class_type": "KSamplerSelect",
                "_meta": {
                    "title": "KSamplerSelect"
                }
            },
            "17": {
                "inputs": {
                    "scheduler": "simple",
                    "steps": 4,
                    "denoise": 1,
                    "model": ["12", 1]  # Use output 1 for cached state
                },
                "class_type": "BasicScheduler",
                "_meta": {
                    "title": "BasicScheduler"
                }
            },
            "22": {
                "inputs": {
                    "model": ["12", 1],  # Use output 1 for cached state
                    "conditioning": ["6", 0]
                },
                "class_type": "BasicGuider",
                "_meta": {
                    "title": "BasicGuider"
                }
            },
            "13": {
                "inputs": {
                    "noise": ["25", 0],
                    "guider": ["22", 0],
                    "sampler": ["16", 0],
                    "sigmas": ["17", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "SamplerCustomAdvanced",
                "_meta": {
                    "title": "SamplerCustomAdvanced"
                }
            },
            "8": {
                "inputs": {
                    "samples": ["13", 0],
                    "vae": ["10", 1]  # Use output 1 for cached state
                },
                "class_type": "VAEDecode",
                "_meta": {
                    "title": "VAE Decode"
                }
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage",
                "_meta": {
                    "title": "Save Image"
                }
            }
        }

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

    def validate_server_connection(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """Validate connection to ComfyUI server with retry logic."""
        logging.info("Validating ComfyUI server connection...")
        for attempt in range(max_retries):
            try:
                logging.debug(f"Connection attempt {attempt + 1}/{max_retries}")
                response = requests.get(f"{self.server_url}/system_stats", timeout=5)
                response.raise_for_status()
                logging.info("ComfyUI server connection validated successfully")
                return True
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    logging.warning(f"ComfyUI server connection attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"ComfyUI server connection failed after {max_retries} attempts: {str(e)}")
        return False
