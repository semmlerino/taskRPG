# modules/story.py

import os
import json
import random
import logging
from typing import Dict, List, Optional
from .constants import STORY_LINEAR_FILE, STORY_ADVANCED_FILE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class StoryManager:
    """
    Manages the dynamic storyline, loading from an external file.
    Supports branching paths based on player choices.
    """
    def __init__(self, filepath: str = STORY_LINEAR_FILE):
        self.filepath = filepath
        self.story_data = self.load_story()
        self.current_node = "start"

    def load_story(self) -> Dict:
        """Loads the storyline from a JSON file or returns default segments."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    story = json.load(f)
                logging.info(f"Story loaded from {self.filepath}.")
                return story
            except Exception as e:
                logging.error(f"Failed to load story from {self.filepath}. Using default story. Error: {e}")
        logging.info("Using default story segments.")
        return {"start": {"text": "Default story segment.", "choices": []}}

    def get_current_node(self) -> Dict:
        """Returns the current node's data."""
        return self.story_data.get(self.current_node, {})

    def set_current_node(self, node_id: str):
        """Sets the current node to the specified node_id."""
        if node_id in self.story_data:
            self.current_node = node_id
            logging.info(f"Moved to node: {self.current_node}")
        else:
            logging.error(f"Node '{node_id}' does not exist in the story.")
            raise ValueError(f"Node '{node_id}' does not exist in the story.")

    def get_choices(self) -> Optional[List[Dict]]:
        """Returns the list of choices for the current node, if any."""
        node = self.get_current_node()
        return node.get("choices", None)

    def get_battle_info(self) -> Optional[Dict]:
        """Returns battle information if the current node initiates a battle."""
        node = self.get_current_node()
        return node.get("battle", None)

    def get_text(self) -> str:
        """Returns the narrative text of the current node."""
        node = self.get_current_node()
        return node.get("text", "")

    def is_end(self) -> bool:
        """Checks if the current node is the end of the story."""
        node = self.get_current_node()
        return len(node.get("choices", [])) == 0 and "battle" not in node
