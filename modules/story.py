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
        self.story_data = self.load_story()
        self.current_node_key = 'start'
        self.current_node = self.story_data.get(self.current_node_key, {})
        self.image_cache = {}  # Cache generated images
        self.image_folder = image_folder

        # Initialize ImageGenerator
        self.image_generator = image_generator or ImageGenerator()

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

    def get_all_image_prompts(self) -> Dict[str, str]:
        """
        Extracts all image prompts from the story.

        Returns:
            A dictionary where keys are node keys and values are image prompts.
        """
        image_prompts = {}
        for node_key, node_data in self.story_data.items():
            if 'image_prompt' in node_data:
                image_prompts[node_key] = node_data['image_prompt']
        return image_prompts

    def set_generated_image(self, node_key: str, image_path: str):
        """
        Sets the generated image path for a specific node.
        """
        if node_key in self.story_data:
            self.story_data[node_key]['generated_image'] = image_path

    def get_generated_image(self, node_key: str) -> Optional[str]:
        """
        Gets the generated image path for a specific node.
        """
        image_path = self.story_data.get(node_key, {}).get('generated_image')
        if image_path and self.image_folder:
            return os.path.join(self.image_folder, os.path.basename(image_path))
        return image_path

    def is_end(self) -> bool:
        """
        Checks if the current node is an end node.
        """
        return self.current_node.get('end', False)
