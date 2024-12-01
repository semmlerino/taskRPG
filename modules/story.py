# modules/story.py

import os
import json
import logging
import shutil
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from enum import Enum, auto

from modules.common.types import NavigationDirection
from core.story.story_content import StoryContent
from core.story.story_node import StoryNode
from modules.characters.character_manager import CharacterManager

# Use TYPE_CHECKING for circular imports
if TYPE_CHECKING:
    from modules.battle.battle_manager import BattleManager
    from modules.image_generator import ImageGenerator

class StoryManager:
    """
    Manages story progression, content, and state.
    """

    def __init__(
        self,
        filepath: str,
        image_generator: 'ImageGenerator',
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

        # Add after the __init__ method initialization
        self._last_valid_image = None
        self._next_valid_image = None

        # Initialize character manager
        self.character_manager = CharacterManager(filepath, image_generator)
        
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

            # Handle image persistence
            current_image = self.get_generated_image(self.current_node_key)
            if current_image:
                self._last_valid_image = current_image
            elif not self._last_valid_image:
                self._next_valid_image = self._find_next_valid_image(self.current_node_key)

            # Use the most appropriate image
            content.image_path = current_image or self._last_valid_image or self._next_valid_image

            self._current_content = content

            # Log history state before update
            logging.info(f"History before update - Index: {self._history_index}, Size: {len(self._history)}")

            # If we're not at the end of history, truncate the future history
            if self._history_index < len(self._history) - 1:
                self._history = self._history[:self._history_index + 1]
                logging.info("Truncated future history")

            # Add new node to history
            self._history.append((self.current_node_key, content))
            self._history_index = len(self._history) - 1
            
            # Log history state after update
            logging.info(f"History after update - Index: {self._history_index}, Size: {len(self._history)}")

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
            # Log current state before navigation
            logging.info(f"Attempting navigation {direction.name}")
            logging.info(f"Current history index: {self._history_index}")
            logging.info(f"History size: {len(self._history)}")
            logging.info(f"Available history nodes: {[key for key, _ in self._history]}")

            if not self._can_navigate(direction):
                logging.info(f"Cannot navigate {direction.name}")
                return False

            # Update index
            if direction == NavigationDirection.FORWARD:
                self._history_index += 1
            else:
                self._history_index -= 1

            # Get content from history
            node_key, content = self._history[self._history_index]
            logging.info(f"Retrieved node {node_key} from history at index {self._history_index}")
            
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
                logging.info(f"Updated display with node: {node_key}")

            return True

        except Exception as e:
            logging.error(f"Error during navigation: {e}", exc_info=True)
            return False

    def _can_navigate(self, direction: NavigationDirection) -> bool:
        """Check if navigation in given direction is possible."""
        try:
            if direction == NavigationDirection.FORWARD:
                can_nav = self._history_index < len(self._history) - 1
            else:
                can_nav = self._history_index > 0
            
            # Add detailed debug info
            logging.info(f"Navigation check - Direction: {direction.name}")
            logging.info(f"Current history index: {self._history_index}")
            logging.info(f"History length: {len(self._history)}")
            logging.info(f"Can navigate {direction.name}: {can_nav}")
            
            return can_nav
        except Exception as e:
            logging.error(f"Error checking navigation possibility: {e}")
            return False

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
                    # If this is the last node, return True to indicate successful progression
                    if not current_node.get('next'):
                        return True
                return False  # Battle in progress or couldn't start

            # Normal story progression
            next_node = current_node.get('next')
            if next_node:
                try:
                    self.set_current_node(next_node)
                    return self.display_story_segment()
                except ValueError as e:
                    logging.error(f"Invalid next node: {e}")
                    return False
            
            # No next node available
            logging.info("Reached end of story branch")
            return True

        except Exception as e:
            logging.error(f"Error in story progression: {e}")
            return False

    def set_battle_manager(self, battle_manager: 'BattleManager') -> None:
        """Set the battle manager after initialization."""
        self.battle_manager = battle_manager
        logging.info("Battle manager set in StoryManager")

    def generate_node_image(self, node_data: Dict[str, Any], node_key: str) -> Optional[str]:
        """Generate an image for the current story node."""
        try:
            if not self.image_generator:
                return None

            # Determine if this node has character-aware image generation
            if isinstance(node_data.get("image_prompt"), dict) and "characters" in node_data:
                # Generate scene with character consistency
                image_path = os.path.join(self.image_folder, f"{node_key}.png")
                return self.image_generator.generate_scene_with_characters(
                    scene_data=node_data,
                    character_manager=self.character_manager,
                    save_path=image_path
                )
            else:
                # Fall back to standard image generation
                prompt = node_data.get("image_prompt", "")
                if not prompt:
                    return None
                    
                image_path = os.path.join(self.image_folder, f"{node_key}.png")
                return self.image_generator.generate_image(prompt, save_path=image_path)

        except Exception as e:
            logging.error(f"Error generating node image: {e}")
            return None

    def _find_next_valid_image(self, current_node_key: str) -> Optional[str]:
        try:
            # Start from next node
            next_key = self.story_data[current_node_key].get('next')
            while next_key and next_key in self.story_data:
                node = self.story_data[next_key]
                if 'image_prompt' in node:
                    image_path = self.get_generated_image(next_key)
                    if image_path:
                        return image_path
                next_key = node.get('next')
            return None
        except Exception as e:
            logging.error(f"Error finding next valid image: {e}")
            return None

    def initialize_story_characters(self):
        """Initialize all characters defined in the story."""
        try:
            # Get character definitions from story data
            characters = self.story_data.get("characters", {})
            
            for char_name, char_data in characters.items():
                if not self.character_manager.get_character(char_name):
                    # Add character if they don't exist
                    self.character_manager.add_character(
                        name=char_name,
                        description=char_data.get("description", ""),
                        traits=char_data.get("traits", {})
                    )
            
            logging.info(f"Initialized {len(characters)} story characters")
            
        except Exception as e:
            logging.error(f"Error initializing story characters: {e}")

    def move_to_completed(self) -> bool:
        """
        Move the current story file and its associated images to the oldstories folder.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.filepath or not os.path.exists(self.filepath):
                logging.error("No valid story file path to move")
                return False

            # Create oldstories directory structure
            oldstories_dir = os.path.join(os.path.dirname(os.path.dirname(self.filepath)), 'oldstories')
            old_images_dir = os.path.join(oldstories_dir, 'images')
            
            logging.info(f"Creating oldstories directories: {oldstories_dir}")
            os.makedirs(oldstories_dir, exist_ok=True)
            os.makedirs(old_images_dir, exist_ok=True)

            # Get the story filename and name
            story_filename = os.path.basename(self.filepath)
            story_name = os.path.splitext(story_filename)[0]
            
            # Move story file
            new_filepath = os.path.join(oldstories_dir, story_filename)
            logging.info(f"Moving story file from {self.filepath} to {new_filepath}")
            
            if os.path.exists(new_filepath):
                logging.warning(f"Story already exists in oldstories, removing: {new_filepath}")
                os.remove(new_filepath)
                
            shutil.move(self.filepath, new_filepath)
            logging.info(f"Successfully moved story file to: {new_filepath}")

            # Move associated images if they exist
            if self.image_folder and os.path.exists(self.image_folder):
                old_image_folder = os.path.join(old_images_dir, story_name)
                logging.info(f"Moving images from {self.image_folder} to {old_image_folder}")
                
                if os.path.exists(old_image_folder):
                    logging.warning(f"Image folder already exists, removing: {old_image_folder}")
                    shutil.rmtree(old_image_folder)
                    
                shutil.move(self.image_folder, old_image_folder)
                logging.info(f"Successfully moved images to: {old_image_folder}")
                self.image_folder = old_image_folder

            # Update filepath
            self.filepath = new_filepath
            return True

        except Exception as e:
            logging.error(f"Error moving story to completed: {e}", exc_info=True)
            return False
