# modules/story.py

import os
import json
import logging
import random
from typing import Dict, Any, Optional, List
from PIL import Image

from modules.constants import STORIES_DIR, ASSETS_DIR
from modules.image_generator import ImageGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StoryManager:
    def __init__(self, filepath: str, image_generator: Optional[ImageGenerator] = None, image_folder: str = None):
        self.filepath = filepath
        logging.info(f"Initializing StoryManager with filepath: {filepath}")
        
        self.story_data = self.load_story()
        self.current_node_key = self.get_initial_node()
        self.current_node = self.story_data.get(self.current_node_key, {})
        self.image_cache = {}
        self.image_folder = image_folder
        
        logging.info(f"Story loaded. Initial node: {self.current_node_key}")
        logging.info(f"Image folder set to: {self.image_folder}")

        # Initialize ImageGenerator
        self.image_generator = image_generator or ImageGenerator()

    def load_story(self) -> Dict[str, Any]:
        """
        Loads the story JSON file from the given filepath.
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                story = json.load(f)
            logging.info(f"Story loaded from {self.filepath}")
            logging.info(f"Story contains {len(story)} nodes")
            return story
        except FileNotFoundError:
            logging.error(f"Story file not found at {self.filepath}")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {self.filepath}: {e}")
            return {}

    def get_initial_node(self) -> str:
        """
        Gets the initial node of the story.
        """
        if not self.story_data:
            raise ValueError("Story data is empty")
            
        # Priority 1: Check for 'start' node
        if 'start' in self.story_data:
            logging.info("Using 'start' as initial node")
            return 'start'
        
        # Priority 2: Check for 'node1' node
        elif 'node1' in self.story_data:
            logging.info("Using 'node1' as initial node")
            return 'node1'
        
        # Priority 3: Use the first node in the story data
        else:
            first_node = next(iter(self.story_data))
            logging.info(f"No 'start' or 'node1' found. Using first available node: '{first_node}'")
            return first_node

    def set_current_node(self, node_key: str):
        """
        Sets the current node in the story based on the node_key.
        """
        self.current_node_key = node_key
        self.current_node = self.story_data.get(self.current_node_key, {})
        logging.info(f"Current node set to '{self.current_node_key}'")

    def get_current_node(self) -> Dict[str, Any]:
        """Retrieves the current node in the story."""
        return self.current_node

    def get_text(self) -> str:
        """Retrieves the narrative text from the current node."""
        return self.current_node.get('text', '')

    def get_image_prompt(self) -> Optional[str]:
        """Retrieves the image prompt from the current node."""
        return self.current_node.get('image_prompt')

    def get_choices(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves the choices available in the current node."""
        return self.current_node.get('choices')

    def get_environment(self) -> Optional[str]:
        """Retrieves the environment description."""
        return self.current_node.get('environment')

    def get_npc(self) -> Optional[Dict[str, Any]]:
        """Retrieves the NPC details."""
        return self.current_node.get('npc')

    def get_event(self) -> Optional[str]:
        """Retrieves event descriptions."""
        return self.current_node.get('event')

    def get_battle_info(self) -> Optional[Dict[str, Any]]:
        """Retrieves battle information."""
        return self.current_node.get('battle')

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Retrieves player stats."""
        return self.current_node.get('stats')

    def get_quests(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves quest information."""
        return self.current_node.get('quests')

    def get_inventory(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves inventory information."""
        return self.current_node.get('inventory')

    def get_all_image_prompts(self) -> Dict[str, str]:
        """
        Extracts all image prompts from the story.
        """
        image_prompts = {}
        for node_key, node_data in self.story_data.items():
            if 'image_prompt' in node_data:
                image_prompts[node_key] = node_data['image_prompt']
                logging.info(f"Found image prompt for node {node_key}")
        
        logging.info(f"Total image prompts found: {len(image_prompts)}")
        return image_prompts

    def get_generated_image(self, node_key: str) -> Optional[str]:
        """Gets the generated image path for a specific node."""
        try:
            # First check if this node exists
            if node_key not in self.story_data:
                logging.error(f"Node {node_key} not found in story data")
                return None
            
            # Construct image path
            image_filename = f"{node_key}.png"
            if self.image_folder:
                image_path = os.path.join(self.image_folder, image_filename)
                logging.info(f"Looking for image at: {image_path}")
                
                if os.path.exists(image_path):
                    logging.info(f"Found image at: {image_path}")
                    # Verify image is readable
                    try:
                        with open(image_path, 'rb') as f:
                            f.read(1024)  # Try to read first 1KB
                        return image_path
                    except Exception as e:
                        logging.error(f"Image file exists but is not readable: {e}")
                else:
                    logging.error(f"Image file does not exist: {image_path}")
                    # List directory contents for debugging
                    if os.path.exists(self.image_folder):
                        files = os.listdir(self.image_folder)
                        logging.info(f"Files in image folder: {files}")
                    else:
                        logging.error(f"Image folder does not exist: {self.image_folder}")
            else:
                logging.error("No image folder specified")
                
            return None
        except Exception as e:
            logging.error(f"Error getting generated image: {e}")
            return None

    def set_generated_image(self, node_key: str, image_path: str):
        """Sets the generated image path for a specific node."""
        try:
            if node_key in self.story_data:
                self.story_data[node_key]['generated_image'] = image_path
                logging.info(f"Set generated image for node {node_key}: {image_path}")
            else:
                logging.warning(f"Attempted to set image for non-existent node: {node_key}")
        except Exception as e:
            logging.error(f"Error setting generated image: {e}")

    def is_end(self) -> bool:
        """Checks if the current node is an end node."""
        return self.current_node.get('end', False)

    def verify_image_paths(self):
        """Verifies all image paths in the story."""
        if not self.image_folder:
            logging.error("No image folder specified")
            return
            
        logging.info(f"Verifying images in folder: {self.image_folder}")
        
        if not os.path.exists(self.image_folder):
            logging.error(f"Image folder does not exist: {self.image_folder}")
            return
            
        # Get all image files in the folder
        existing_images = set(os.listdir(self.image_folder))
        logging.info(f"Found {len(existing_images)} files in image folder")
        
        # Check each node that should have an image
        for node_key, node_data in self.story_data.items():
            if 'image_prompt' in node_data:
                expected_filename = f"{node_key}.png"
                if expected_filename in existing_images:
                    logging.info(f"Found image for node {node_key}: {expected_filename}")
                else:
                    logging.warning(f"Missing image for node {node_key}")

