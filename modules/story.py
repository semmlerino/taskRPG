# modules/story.py

import os
import json
import logging
import shutil
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from enum import Enum, auto
import re
from json.decoder import JSONDecodeError

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
        image_generator: Optional['ImageGenerator'] = None,
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

        # Reset all history and state
        self.reset_state()

        # Initialize character manager only if image generator is available
        self.character_manager = CharacterManager(filepath, image_generator) if image_generator else None
        
        logging.info(f"StoryManager initialized with filepath: {filepath}")

    def load_story(self) -> Dict[str, Any]:
        """
        Load and validate the story JSON file.

        Returns:
            Dict[str, Any]: Validated story data
        """
        try:
            logging.info(f"Loading story from: {self.filepath}")
            story_data = self._robust_json_load(self.filepath)

            # Validate story data structure
            if not isinstance(story_data, dict):
                raise ValueError("Story data must be a dictionary")

            # Log story structure
            logging.info(f"Story keys: {list(story_data.keys())}")
            for key, node in story_data.items():
                if isinstance(node, dict):
                    logging.info(f"Node {key} content: {list(node.keys())}")

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
            logging.info(f"Displaying story segment for node: {self.current_node_key}")
            if not self._validate_story_state():
                return False

            node = self.get_current_node()
            if not node:
                logging.error(f"Invalid node data for key: {self.current_node_key}")
                return False

            logging.info(f"Node data: {node}")
            # Create node content
            content = self._create_node_content(node)
            if not content:
                logging.error("Failed to create node content")
                return False

            logging.info(f"Created content: text={content.text[:100]}..., battle_info={content.battle_info}")

            # Handle image persistence with validation
            # Only attempt image handling if image generator is available
            if self.image_generator:
                current_image = self.get_generated_image(self.current_node_key)
                if current_image:
                    self._last_valid_image = current_image
                elif not self._last_valid_image or not os.path.isfile(self._last_valid_image):
                    self._next_valid_image = self._find_next_valid_image(self.current_node_key)
                    if not self._next_valid_image:
                        # Use a default placeholder image if no valid images are found
                        default_image = os.path.join(os.path.dirname(self.filepath), 'assets', 'images', 'placeholder.png')
                        if os.path.isfile(default_image):
                            self._last_valid_image = default_image

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
                logging.info("Updating UI with content")
                self.ui.story_display.set_page(content)
                logging.info(f"UI updated for node: {self.current_node_key}")

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

            # Extract text and battle information
            text = node_data.get('text', '')
            battle_info = None
            
            # Handle battle node
            if 'enemy' in node_data:
                battle_info = {
                    'enemy': node_data['enemy'],
                    'message': node_data.get('message', text)
                }
                logging.info(f"Created battle info: {battle_info}")

            # Create StoryNode from dictionary data
            node = StoryNode.from_dict(self.current_node_key, {
                **node_data,
                'battle': battle_info
            })

            content = StoryContent(
                text=text,
                node_key=self.current_node_key,
                image_path=self.get_generated_image(self.current_node_key),
                environment=node.environment,
                event=node.event,
                npc_info=node.npc_info,
                battle_info=battle_info,
                choices=node.choices,
                image_prompt=node.image_prompt
            )

            logging.info(f"Created content for node {self.current_node_key}")
            logging.info(f"Text: {text[:100]}...")
            logging.info(f"Battle info: {battle_info}")
            return content

        except Exception as e:
            logging.error(f"Error creating node content: {e}")
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
                self.ui.story_display.set_page(content)
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
        """Get the path to a generated image for a node, validating its existence."""
        if not self.image_folder or not node_key:
            return None
            
        image_path = os.path.join(self.image_folder, f"{node_key}.png")
        return image_path if os.path.isfile(image_path) else None

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

            # Handle battle nodes only if battle manager is available
            if self.battle_manager:
                battle_info = None
                # Check for battle node in either format
                if "battle" in current_node:
                    battle_info = current_node["battle"]
                elif "enemy" in current_node:
                    # Convert old format to battle info
                    battle_info = {
                        "enemy": current_node["enemy"],
                        "message": current_node.get("message", current_node.get("text", ""))
                    }
                
                if battle_info and not current_node.get("battle_completed", False):
                    if self.battle_manager.start_battle(battle_info):
                        # Mark this battle as completed
                        current_node["battle_completed"] = True
                        self.mark_battle_complete(self.current_node_key)
                        # If this is the last node, return True to indicate successful progression
                        if not current_node.get('next'):
                            return True
                    return False  # Battle in progress or couldn't start
            elif "battle" in current_node or "enemy" in current_node:
                # Skip battle if battle manager is not available
                logging.warning("Battle system not available, skipping battle node")
                if current_node.get('next'):
                    self.set_current_node(current_node['next'])
                    return self.display_story_segment()
                return True

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

    def _find_next_valid_image(self, start_node_key: str) -> Optional[str]:
        """Find the next valid image in the story, checking file existence."""
        current_key = start_node_key
        visited = set()

        while current_key and current_key not in visited:
            visited.add(current_key)
            node = self.story_data.get(current_key, {})
            next_key = node.get('next')
            
            # Check if image exists for this node
            image = self.get_generated_image(current_key)
            if image:
                return image
                
            current_key = next_key

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

    def _robust_json_load(self, filepath: str) -> Dict[str, Any]:
        """
        Load a JSON file with robust error handling and automatic fixes.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Dict[str, Any]: The parsed JSON data
        """
        logging.info(f"Attempting to load JSON with robust error handling: {filepath}")
        
        # First attempt: Standard JSON loading
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logging.warning(f"Initial JSON parse failed: {str(e)}. Attempting fixes...")
            
            # Read the file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply fixes to common JSON problems
            fixed_content = self._fix_json_content(content, e)
            
            try:
                # Try to parse the fixed content
                return json.loads(fixed_content)
            except json.JSONDecodeError as e2:
                logging.error(f"Failed to parse JSON even after fixes: {str(e2)}")
                
                # Create a backup of the original file
                backup_path = filepath + ".backup"
                if not os.path.exists(backup_path):
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logging.info(f"Created backup of original file at {backup_path}")
                
                # Overwrite the original file with the fixed content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                logging.info(f"Overwrote original file with fixed content at {filepath}")
                
                # Return a minimal valid story
                return {
                    "start": {
                        "text": f"Error loading story. Please check story file format. Original error: {str(e)}",
                        "end": True
                    }
                }
    
    def _fix_json_content(self, content: str, error: json.JSONDecodeError) -> str:
        """
        Apply fixes to JSON content to handle common errors.
        
        Args:
            content: The JSON content as a string
            error: The JSONDecodeError that occurred
            
        Returns:
            str: Fixed JSON content
        """
        # Extract line and column information from the error
        error_line = error.lineno
        error_col = error.colno
        error_msg = str(error)
        
        logging.info(f"Attempting to fix JSON error on line {error_line}, column {error_col}: {error_msg}")
        
        # Split content into lines for processing
        lines = content.split('\n')
        
        # Common character replacements for problematic characters
        replacements = {
            '—': '-',  # Replace em dash with hyphen
            ''': "'",  # Replace curly single quotes
            ''': "'",
            '"': '"',  # Replace curly double quotes
            '"': '"',
            '…': '...',  # Replace ellipsis
            '\u2028': ' ',  # Line separator
            '\u2029': ' '   # Paragraph separator
        }
        
        # Handle specific error types
        if "Expecting ',' delimiter" in error_msg:
            # Direct fix for missing comma errors
            if error_line > 0 and error_line <= len(lines):
                line = lines[error_line - 1]
                # If the error is at the beginning of a line, check the previous line
                if error_col <= 1 and error_line > 1:
                    prev_line = lines[error_line - 2]
                    # Add comma at the end of the previous line if it doesn't end with a comma
                    if not prev_line.rstrip().endswith(',') and not prev_line.rstrip().endswith('{') and not prev_line.rstrip().endswith('['):
                        lines[error_line - 2] = prev_line.rstrip() + ','
                        logging.info(f"Added missing comma at the end of line {error_line - 1}")
                else:
                    # Insert comma at the error position
                    before = line[:error_col - 1]
                    after = line[error_col - 1:]
                    if not before.endswith(',') and not before.endswith('{') and not before.endswith('['):
                        lines[error_line - 1] = before + ',' + after
                        logging.info(f"Added missing comma at position {error_col} in line {error_line}")
        
        # Apply fixes based on common patterns
        fixed_lines = []
        for i, line in enumerate(lines):
            fixed_line = line
            
            # Apply character replacements
            for char, replacement in replacements.items():
                fixed_line = fixed_line.replace(char, replacement)
            
            # Fix unterminated strings (especially near line breaks)
            if i + 1 == error_line and '"' in fixed_line:
                # Count quotes to see if we have an odd number (indicating unterminated string)
                quote_count = fixed_line.count('"')
                if quote_count % 2 == 1:
                    fixed_line = fixed_line + '"'
            
            # Fix missing commas after closing brackets or quotes
            if (re.search(r'"\s*}$', fixed_line) or re.search(r'"\s*$', fixed_line)) and i < len(lines) - 1:
                next_line = lines[i+1].strip()
                if next_line and next_line[0] not in [',', '}', ']']:
                    fixed_line = fixed_line + ','
            
            # Fix other common JSON syntax issues
            if ":" in fixed_line and not re.search(r'".*:.*"', fixed_line):
                # Ensure proper quoting of property names (but avoid fixing already quoted content)
                fixed_line = re.sub(r'(\w+):', r'"\1":', fixed_line)
                
            fixed_lines.append(fixed_line)
        
        # Join the fixed lines back together
        fixed_content = '\n'.join(fixed_lines)
        
        # Additional fixes for specific error patterns
        if "Expecting ',' delimiter" in error_msg:
            # Try to fix missing commas using regex patterns
            fixed_content = re.sub(r'"\s*\n\s*"', '",\n"', fixed_content)
            fixed_content = re.sub(r'}\s*\n\s*"', '},\n"', fixed_content)
            fixed_content = re.sub(r']\s*\n\s*"', '],\n"', fixed_content)
        
        # If the error was near special characters, attempt further fixes
        if "got 'undefined'" in error_msg or "Invalid control character" in error_msg:
            # Apply additional repairs to the JSON string
            fixed_content = self._additional_json_fixes(fixed_content)
        
        # Try to validate if the fix worked
        try:
            json.loads(fixed_content)
            logging.info("JSON fix successful!")
            return fixed_content
        except json.JSONDecodeError as e:
            logging.warning(f"First fix attempt failed: {str(e)}. Trying more aggressive fixes...")
            
            # If we still have errors, try more aggressive fixes
            if "Expecting ',' delimiter" in str(e):
                # More aggressive comma fixing
                fixed_content = self._fix_missing_commas(fixed_content)
            
            # Final validation
            try:
                json.loads(fixed_content)
                logging.info("Aggressive JSON fix successful!")
            except json.JSONDecodeError as e2:
                logging.error(f"Could not fix JSON after multiple attempts: {str(e2)}")
        
        return fixed_content
    
    def _fix_missing_commas(self, content: str) -> str:
        """
        Apply more aggressive fixes for missing commas in JSON.
        
        Args:
            content: JSON content string
            
        Returns:
            str: Fixed JSON content
        """
        # Pattern to find places where commas are likely missing between elements
        # This looks for patterns like "value""key" or "value"{ or "value"[
        patterns = [
            (r'(["}\]])\s*(["{\[])', r'\1,\2'),  # Add comma between values and new elements
            (r'(["}\]])\s*\n\s*(["{\[])', r'\1,\n\2'),  # Add comma between values and new elements with newlines
            (r'(["}\]])\s*\n\s*(["])', r'\1,\n\2'),  # Add comma between string values with newlines
        ]
        
        fixed_content = content
        for pattern, replacement in patterns:
            fixed_content = re.sub(pattern, replacement, fixed_content)
        
        # Try to fix the entire structure by parsing and re-serializing
        try:
            # Try to load the JSON to see if our fixes worked
            parsed = json.loads(fixed_content)
            # If successful, re-serialize with proper formatting
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            # If we still can't parse it, return our best attempt
            return fixed_content
    
    def _additional_json_fixes(self, content: str) -> str:
        """
        Apply additional fixes for complex JSON errors.
        
        Args:
            content: JSON content string
            
        Returns:
            str: Fixed JSON content
        """
        # Remove control characters
        fixed_content = re.sub(r'[\x00-\x1F\x7F]', '', content)
        
        # Fix unescaped backslashes in strings
        fixed_content = re.sub(r'(?<!\\)\\(?!["\\\/bfnrtu])', r'\\\\', fixed_content)
        
        # Fix unescaped quotes in strings
        in_string = False
        result = []
        i = 0
        while i < len(fixed_content):
            char = fixed_content[i]
            if char == '"' and (i == 0 or fixed_content[i-1] != '\\'):
                in_string = not in_string
            elif char == '"' and in_string and fixed_content[i-1] != '\\':
                # Escape the quote
                result.append('\\')
            result.append(char)
            i += 1
        
        return ''.join(result)

    def reset_state(self):
        """Reset all story state and history."""
        # Navigation history
        self._history: List[tuple] = []
        self._history_index: int = -1

        # Track completed battles
        self.completed_battle_nodes = set()

        # Reset image tracking
        self._last_valid_image = None
        self._next_valid_image = None

        # Reset current content
        self._current_content = None
