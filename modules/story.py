import os
import json
import logging
from typing import Optional, Dict, Any, List, Union
from enum import Enum, auto
from core.story.story_content import StoryContent
from .image_generator import ImageGenerator

class NavigationDirection(Enum):
    """Enum for navigation directions."""
    FORWARD = auto()
    BACKWARD = auto()

class StoryManager:
    """
    Manages story progression, content, and state.
    """
    def __init__(self, filepath: str, image_generator: ImageGenerator, 
                 image_folder: Optional[str] = None, ui_component: Optional[Any] = None):
        self.filepath = filepath
        self.ui = ui_component
        self.image_generator = image_generator
        self.image_folder = image_folder

        # Initialize state
        self.story_data = self.load_story()
        self.current_node_key = self.get_initial_node()
        self.current_node = self.story_data.get(self.current_node_key, {})
        self._current_content: Optional[StoryContent] = None

        # Navigation history
        self._history: List[tuple] = []
        self._history_index: int = -1

        logging.info(f"StoryManager initialized with filepath: {filepath}")

    def load_story(self) -> Dict[str, Any]:
        """Load and parse the story JSON file."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                story = json.load(f)
            logging.info(f"Story loaded successfully from {self.filepath}")
            return story
        except Exception as e:
            logging.error(f"Error loading story: {e}")
            return {}

    def get_initial_node(self) -> str:
        """Get the initial node of the story."""
        if not self.story_data:
            raise ValueError("Story data is empty")

        if 'start' in self.story_data:
            return 'start'
        elif 'node1' in self.story_data:
            return 'node1'
        else:
            return next(iter(self.story_data))

    def display_story_segment(self) -> bool:
        """Display the current segment of the story."""
        try:
            if not self._validate_story_state():
                return False

            node = self.get_current_node()
            content = self._create_node_content(node)
            if not content:
                return False

            self._current_content = content

            # Update history if moving forward
            if self._history_index == len(self._history) - 1:
                self._history.append((self.current_node_key, content))
                self._history_index += 1

            # Update UI if available
            if self.ui:
                self._update_ui_display(content)

            return True

        except Exception as e:
            logging.error(f"Error displaying story segment: {e}")
            return False

    def _validate_story_state(self) -> bool:
        """Validate the current story state."""
        if not self.story_data:
            logging.error("No story data available")
            return False

        if not self.current_node:
            logging.error("No current node available")
            return False

        return True

    def _create_node_content(self, node: Dict) -> Optional[StoryContent]:
        """Create node content from node data."""
        try:
            return StoryContent(
                text=self.get_text(),
                node_key=self.current_node_key,
                image_path=self.get_generated_image(self.current_node_key),
                environment=self.get_environment(),
                event=self.get_event(),
                npc_info=self.get_npc(),
                battle_info=self.get_battle_info(),
                choices=self.get_choices()
            )
        except Exception as e:
            logging.error(f"Error creating node content: {e}")
            return None

    def _update_ui_display(self, content: StoryContent):
        """Update UI with node content."""
        if not self.ui:
            return

        try:
            html_content = content.to_html()
            self.ui.story_display.set_page(
                self.current_node_key,
                html_content,
                content.image_path
            )
        except Exception as e:
            logging.error(f"Error updating UI display: {e}")

    def navigate(self, direction: NavigationDirection) -> bool:
        """Navigate through story history."""
        try:
            if not self._can_navigate(direction):
                return False

            if direction == NavigationDirection.FORWARD:
                self._history_index += 1
            else:
                self._history_index -= 1

            node_key, content = self._history[self._history_index]
            self.current_node_key = node_key
            self.current_node = self.story_data[node_key]
            self._current_content = content

            if self.ui:
                self._update_ui_display(content)

            return True

        except Exception as e:
            logging.error(f"Error during navigation: {e}")
            return False

    def _can_navigate(self, direction: NavigationDirection) -> bool:
        """Check if navigation in given direction is possible."""
        if direction == NavigationDirection.FORWARD:
            return self._history_index < len(self._history) - 1
        else:
            return self._history_index > 0

    # Getter methods for node content
    def get_text(self) -> str:
        """Get narrative text from current node."""
        return self.current_node.get('text', '')

    def get_environment(self) -> Optional[str]:
        """Get environment description from current node."""
        return self.current_node.get('environment')

    def get_npc(self) -> Optional[Dict]:
        """Get NPC information from current node."""
        return self.current_node.get('npc')

    def get_event(self) -> Optional[str]:
        """Get event description from current node."""
        return self.current_node.get('event')

    def get_battle_info(self) -> Optional[dict]:
        """Extract battle information from current node."""
        try:
            if not self.current_node or 'battle' not in self.current_node:
                return None
                
            battle_data = self.current_node['battle']
            if isinstance(battle_data, dict):
                logging.info(f"Found battle data: {battle_data}")
                return battle_data
                
            logging.warning("Battle data found but in incorrect format")
            return None
            
        except Exception as e:
            logging.error(f"Error getting battle info: {e}")
            return None

    def get_choices(self) -> Optional[List]:
        """Get choices from current node."""
        return self.current_node.get('choices')

    def get_current_node(self) -> Dict[str, Any]:
        """Get current node data."""
        return self.current_node

    def get_generated_image(self, node_key: str) -> Optional[str]:
        """Gets the path to a generated image for a node."""
        if not self.image_folder:
            return None

        image_path = os.path.join(self.image_folder, f"{node_key}.png")
        return os.path.abspath(image_path) if os.path.exists(image_path) else None

    def get_all_image_prompts(self) -> Dict[str, str]:
        """Get all image prompts from story nodes."""
        prompts = {}
        for node_key, node_data in self.story_data.items():
            if isinstance(node_data, dict) and 'image_prompt' in node_data:
                prompts[node_key] = node_data['image_prompt']
        return prompts

    def set_current_node(self, node_key: str):
        """Set current node in story."""
        if node_key not in self.story_data:
            raise ValueError(f"Invalid node key: {node_key}")

        self.current_node_key = node_key
        self.current_node = self.story_data[node_key]

    def set_generated_image(self, node_key: str, image_path: str):
        """Sets the generated image path for a node."""
        if image_path and os.path.exists(image_path):
            self.image_generator.cache_image(node_key, image_path)

    def is_end(self) -> bool:
        """Check if current node is an end node."""
        return self.current_node.get('end', False)

    def cleanup(self):
        """Clean up story manager resources."""
        try:
            logging.info("Cleaning up story manager")
            self._cleanup_content(self._current_content)
            self._clear_cache()
            self._history.clear()
            self._history_index = -1
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def _clear_cache(self):
        """Clear the image cache."""
        self.image_generator.clear_cache()

    def _cleanup_content(self, content: Optional[StoryContent]):
        """Clean up story content resources."""
        if content and content.image_path:
            # If we're using node keys as cache keys
            self.image_generator.remove_from_cache(content.node_key)
            content.image_path = None
