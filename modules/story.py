# modules/story.py

import os
import json
import logging
from typing import Optional, Dict, Any, List, Union
from enum import Enum, auto
from typing import TYPE_CHECKING

from modules.common.types import NavigationDirection

if TYPE_CHECKING:
    from core.battle.battle_manager import BattleManager

from core.story.story_content import StoryContent
from core.story.story_node import StoryNode
from .image_generator import ImageGenerator

class StoryManager:
    """
    Manages story progression, content, and state.
    """

    def __init__(
        self,
        filepath: str,
        image_generator: ImageGenerator,
        image_folder: Optional[str] = None,
        ui_component: Optional[Any] = None,
        battle_manager: Optional['BattleManager'] = None
    ):
        self.filepath = filepath
        self.ui = ui_component
        self.image_generator = image_generator
        self.image_folder = image_folder
        self.battle_manager = battle_manager

        # Initialize state
        self.story_data = self.load_story()
        self.current_node_key = self.get_initial_node()
        self.current_node = self.story_data.get(self.current_node_key, {})
        self._current_content: Optional[StoryContent] = None

        # Navigation history
        self._history: List[tuple] = []
        self._history_index: int = -1

        # Track completed battles
        self.completed_battle_nodes = set()

        logging.info(f"StoryManager initialized with filepath: {filepath}")

    def load_story(self) -> Dict[str, Any]:
        """
        Load and validate the story JSON file.

        Returns:
            Dict[str, Any]: Validated story data
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                story_data = json.load(f)

            # Validate story data structure
            if not isinstance(story_data, dict):
                raise ValueError("Story data must be a dictionary")

            # Convert all string nodes to dict format for consistency
            validated_data = {}
            for key, node in story_data.items():
                if isinstance(node, str):
                    # Convert legacy string format to dict
                    validated_data[key] = {
                        "text": node,
                        "next": None
                    }
                elif isinstance(node, dict):
                    validated_data[key] = node
                else:
                    logging.warning(f"Invalid node type for key {key}: {type(node)}")
                    continue

            logging.info(f"Story loaded and validated: {len(validated_data)} nodes")
            return validated_data

        except Exception as e:
            logging.error(f"Error loading story: {e}")
            # Return minimal valid story data
            return {
                "start": {
                    "text": "Error loading story. Please check story file format.",
                    "end": True
                }
            }

    def get_initial_node(self) -> str:
        """
        Get the initial node of the story with improved node detection.
        
        Returns:
            str: Key of the first story node
        """
        try:
            if not self.story_data:
                raise ValueError("Story data is empty")

            # Check for standard start nodes
            if 'start' in self.story_data:
                return 'start'
                
            # Find the lowest numbered node if using nodeX format
            numbered_nodes = [
                node for node in self.story_data.keys() 
                if node.startswith('node') and node[4:].isdigit()
            ]
            
            if numbered_nodes:
                # Sort by node number and get the lowest
                lowest_node = sorted(
                    numbered_nodes,
                    key=lambda x: int(x[4:])  # Extract number from 'nodeX'
                )[0]
                logging.info(f"Starting with lowest numbered node: {lowest_node}")
                return lowest_node

            # Fallback to first available node
            first_node = next(iter(self.story_data))
            logging.info(f"Using first available node: {first_node}")
            return first_node

        except Exception as e:
            logging.error(f"Error finding initial node: {e}")
            raise ValueError("Could not determine initial story node")

    def display_story_segment(self) -> bool:
        """Display the current segment of the story with enhanced error handling."""
        try:
            if not self._validate_story_state():
                return False

            node = self.get_current_node()
            if not node:
                logging.error(f"Invalid node data for key: {self.current_node_key}")
                return False

            # Create node content
            content = self._create_node_content(node)
            if not content:
                logging.error("Failed to create node content")
                return False

            self._current_content = content

            # Update history if moving forward
            if self._history_index == len(self._history) - 1:
                self._history.append((self.current_node_key, content))
                self._history_index += 1

            # Update UI if available
            if self.ui:
                html_content = content.to_html()
                self.ui.story_display.set_page(
                    self.current_node_key,
                    html_content,
                    content.image_path
                )
                logging.info(f"Displayed story segment for node: {self.current_node_key}")

            return True

        except Exception as e:
            logging.error(f"Error displaying story segment: {e}")
            if self.ui:
                self.ui.story_display.append_text(
                    "<p style='color: red;'>Error loading story content. Please check the story file.</p>"
                )
            return False

    def _validate_story_state(self) -> bool:
        """Validate the current story state."""
        if not self.story_data:
            logging.error("No story data available")
            return False

        if not self.current_node_key:
            logging.error("No current node key set")
            return False

        if self.current_node_key not in self.story_data:
            logging.error(f"Invalid node key: {self.current_node_key}")
            return False

        return True

    def _create_node_content(self, node_data: Any) -> Optional[StoryContent]:
        """
        Create node content from node data with proper type checking and error handling.

        Args:
            node_data: Node data from story file

        Returns:
            Optional[StoryContent]: Created content or None if invalid
        """
        try:
            # Verify node_data is a dictionary
            if not isinstance(node_data, dict):
                if isinstance(node_data, str):
                    # Handle legacy format where node might be just text
                    return StoryContent(
                        text=node_data,
                        node_key=self.current_node_key
                    )
                logging.error(f"Invalid node data type: {type(node_data)}")
                return None

            # Create StoryNode from dictionary data
            node = StoryNode.from_dict(self.current_node_key, node_data)

            return StoryContent(
                text=node.text,
                node_key=self.current_node_key,
                image_path=self.get_generated_image(self.current_node_key),
                environment=node.environment,
                event=node.event,
                npc_info=node.npc_info,
                battle_info=node.battle_info,
                choices=node.choices
            )

        except Exception as e:
            logging.error(f"Error creating node content: {e}")
            # Return a basic content object with error message
            return StoryContent(
                text="Error loading story content. Please contact support.",
                node_key=self.current_node_key
            )

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
                html_content = content.to_html()
                self.ui.story_display.set_page(
                    self.current_node_key,
                    html_content,
                    content.image_path
                )

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

    def mark_battle_complete(self, node_key: str):
        """Mark a battle node as completed."""
        self.completed_battle_nodes.add(node_key)
        logging.info(f"Marked battle node {node_key} as completed")

    def next_story_segment(self) -> bool:
        """Progress to next story segment with battle integration."""
        try:
            current_node = self.get_current_node()

            # Handle battle nodes
            if "battle" in current_node and not current_node.get("battle_completed", False):
                battle_info = current_node["battle"]
                if self.battle_manager and self.battle_manager.start_battle(battle_info):
                    # Mark this battle as completed
                    current_node["battle_completed"] = True
                    self.mark_battle_complete(self.current_node_key)
                else:
                    return False  # Battle couldn't start

            # Normal story progression
            next_node = current_node.get('next')
            if next_node:
                try:
                    self.set_current_node(next_node)
                    return self.display_story_segment()
                except ValueError as e:
                    logging.error(f"Invalid next node: {e}")
                    return False

            return False

        except Exception as e:
            logging.error(f"Error in story progression: {e}")
            return False

    def set_battle_manager(self, battle_manager: 'BattleManager') -> None:
        """Set the battle manager after initialization."""
        self.battle_manager = battle_manager
        logging.info("Battle manager set in StoryManager")