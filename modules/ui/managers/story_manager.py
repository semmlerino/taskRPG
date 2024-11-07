# modules/ui/managers/story_manager.py

import os
import json
import logging
import random
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto

from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication, QProgressDialog
from PyQt6.QtCore import Qt

from modules.constants import STORIES_DIR, ASSETS_DIR
from modules.ui.dialogs.story_selection_dialog import StorySelectionDialog
from modules.story import StoryManager as CoreStoryManager
from modules.core.error_handler import ErrorSeverity, ErrorContext
from modules.core.state_manager import GameState
from modules.utils.qt_helpers import ensure_qt_application

@dataclass
class StoryNodeContent:
    """Represents the content of a story node."""
    text: str
    image_path: Optional[str] = None
    environment: Optional[str] = None
    event: Optional[str] = None
    npc_info: Optional[Dict] = None
    battle_info: Optional[Dict] = None
    choices: Optional[list] = None

class NavigationDirection(Enum):
    FORWARD = auto()
    BACKWARD = auto()

class StoryManager:
    """Manages story loading, navigation, and display in the UI."""
    
    def __init__(self, main_window):
        ensure_qt_application()
        logging.info("Initializing UI StoryManager")
        self.main_window = main_window
        self.core_manager: Optional[CoreStoryManager] = None
        self.story_image_folder: Optional[str] = None
        self._current_content: Optional[StoryNodeContent] = None
        self._history: list = []
        self._history_index: int = -1
        
        # Register with state manager
        self.main_window.state_manager.add_listener(self._handle_state_change)
        
        # Register resource cleanup
        self._register_resources()

    def _register_resources(self):
        """Register story-related resources for cleanup."""
        try:
            if hasattr(self.main_window, 'resource_manager'):
                self.main_window.resource_manager.register_resource(
                    "story_content",
                    lambda: self._current_content,
                    lambda x: self._cleanup_content(x) if x else None
                )
                self.main_window.resource_manager.register_resource(
                    "story_images",
                    lambda: self.story_image_folder,
                    lambda x: self._cleanup_images(x) if x else None
                )
                logging.info("Story resources registered successfully")
        except Exception as e:
            logging.error(f"Error registering story resources: {e}")

    def select_story(self) -> bool:
        """Prompt user to select and initialize a story."""
        try:
            dialog = StorySelectionDialog(self.main_window)
            if dialog.exec_() != QDialog.Accepted:
                logging.info("Story selection cancelled")
                self._show_no_story_message()
                return False

            return self._initialize_story(dialog.selected_story)
            
        except Exception as e:
            self._handle_story_error(e, "select_story")
            return False

    def _initialize_story(self, story_path: str) -> bool:
        """Initialize the selected story and its resources."""
        try:
            if not os.path.exists(story_path):
                raise FileNotFoundError(f"Story file not found: {story_path}")

            story_name = os.path.splitext(os.path.basename(story_path))[0]
            self.story_image_folder = os.path.join(ASSETS_DIR, 'images', story_name)
            
            # Ensure directories exist
            os.makedirs(self.story_image_folder, exist_ok=True)
            
            # Initialize core manager
            self.core_manager = CoreStoryManager(
                story_path,
                image_generator=self.main_window.image_manager.image_generator,
                image_folder=self.story_image_folder
            )
            
            # Initialize images
            self._initialize_images()
            
            # Display initial segment
            success = self.display_story_segment()
            if success:
                self.main_window.state_manager.transition_state(
                    GameState.STORY,
                    {'story_name': story_name}
                )
            
            return success
            
        except Exception as e:
            self._handle_story_error(e, "initialize_story")
            return False

    def _initialize_images(self):
        """Initialize and verify story images."""
        try:
            image_prompts = self.get_all_image_prompts()
            if not image_prompts:
                logging.info("No image prompts found in story")
                return

            # Show progress dialog
            progress = QProgressDialog(
                "Initializing story images...",
                "Cancel",
                0,
                len(image_prompts),
                self.main_window
            )
            progress.setWindowModality(Qt.WindowModal)
            
            for i, (node_key, prompt) in enumerate(image_prompts.items()):
                if progress.wasCanceled():
                    break
                    
                progress.setValue(i)
                QApplication.processEvents()
                
                self._ensure_node_image(node_key, prompt)
                
            progress.setValue(len(image_prompts))
            
        except Exception as e:
            self._handle_story_error(e, "initialize_images")

    def _ensure_node_image(self, node_key: str, prompt: str):
        """Ensure image exists for a story node."""
        try:
            image_path = os.path.join(self.story_image_folder, f"{node_key}.png")
            if not os.path.exists(image_path):
                self.main_window.image_manager.generate_image(prompt, image_path)
                
        except Exception as e:
            logging.error(f"Error ensuring image for node {node_key}: {e}")

    def display_story_segment(self) -> bool:
        """Display the current segment of the story."""
        try:
            if not self._validate_story_state():
                return False

            # Get current node data
            node = self.core_manager.get_current_node()
            node_key = self.core_manager.current_node_key
            
            # Create node content
            content = self._create_node_content(node)
            if not content:
                return False
                
            # Store current content
            self._current_content = content
            
            # Update history if moving forward
            if self._history_index == len(self._history) - 1:
                self._history.append((node_key, content))
                self._history_index += 1
            
            # Display content
            self._display_content(content)
            
            # Handle node type
            self._handle_node_type(node)
            
            return True
            
        except Exception as e:
            self._handle_story_error(e, "display_story_segment")
            return False

    def _validate_story_state(self) -> bool:
        """Validate current story state."""
        if not self.core_manager:
            logging.error("No core story manager initialized")
            return False
            
        if self.main_window.battle_manager.battle_state.enemy:
            logging.error("Cannot display story during battle")
            return False
            
        return True

    def _create_node_content(self, node: Dict) -> Optional[StoryNodeContent]:
        """Create node content from node data."""
        try:
            if not isinstance(node, dict):
                raise ValueError(f"Invalid node data type: {type(node)}")
                
            return StoryNodeContent(
                text=self.core_manager.get_text(),
                image_path=self.core_manager.get_generated_image(
                    self.core_manager.current_node_key
                ),
                environment=node.get('environment'),
                event=node.get('event'),
                npc_info=node.get('npc'),
                battle_info=node.get('battle'),
                choices=node.get('choices')
            )
            
        except Exception as e:
            self._handle_story_error(e, "create_node_content")
            return None

    def _display_content(self, content: StoryNodeContent):
        """Display node content in UI."""
        try:
            html_content = self._generate_html_content(content)
            
            self.main_window.story_display.set_page(
                self.core_manager.current_node_key,
                html_content,
                content.image_path
            )
            
        except Exception as e:
            self._handle_story_error(e, "display_content")

    def _generate_html_content(self, content: StoryNodeContent) -> str:
        """Generate HTML content from node content."""
        html_parts = [f"<p>{content.text}</p>"]
        
        if content.environment:
            html_parts.append(f"<p><i>Environment:</i> {content.environment}</p>")
            
        if content.event:
            html_parts.append(f"<p><i>Event:</i> {content.event}</p>")
            
        if content.npc_info:
            html_parts.extend(self._generate_npc_html(content.npc_info))
            
        if content.battle_info:
            html_parts.extend(self._generate_battle_html(content.battle_info))
            
        return "\n".join(html_parts)

    def _generate_npc_html(self, npc_info: Dict) -> list:
        """Generate HTML content for NPC dialogue."""
        html_parts = []
        if isinstance(npc_info, list):
            for npc in npc_info:
                html_parts.append(self._format_npc_dialogue(npc))
        elif isinstance(npc_info, dict):
            html_parts.append(self._format_npc_dialogue(npc_info))
        return html_parts

    def _format_npc_dialogue(self, npc: Dict) -> str:
        """Format individual NPC dialogue."""
        name = npc.get("name", "Unknown NPC")
        dialogue = npc.get("dialogue", "")
        return f"<p><b>{name} says:</b> \"{dialogue}\"</p>"

    def _generate_battle_html(self, battle_info: Dict) -> list:
        """Generate HTML content for battle information."""
        html_parts = []
        message = battle_info.get("message", "An enemy appears!")
        enemy_name = battle_info.get("enemy", "Unknown Enemy")
        
        if task := self.main_window.task_manager.get_random_active_task():
            html_parts.extend([
                f"<p><i>{message}</i></p>",
                f"<p>To defeat the <b>{enemy_name}</b>, you need to complete ",
                f"the task: <b>{task['name']}</b></p>"
            ])
            
        return html_parts

    def _handle_node_type(self, node: Dict):
        """Handle different node types."""
        try:
            if self.core_manager.is_end():
                self._handle_end_node()
            elif node.get('choices'):
                self._handle_choice_node(node['choices'])
            elif node.get('battle'):
                self._handle_battle_node(node['battle'])
            else:
                self._handle_regular_node()
                
        except Exception as e:
            self._handle_story_error(e, "handle_node_type")

    def _handle_end_node(self):
        """Handle end node logic."""
        try:
            self.main_window.story_display.append_text("<br><b>The End.</b><br>")
            self.main_window.action_buttons.hide_attack_buttons()
            self.main_window.settings_button.setEnabled(False)
            
            self.main_window.state_manager.transition_state(
                GameState.END,
                {'completed': True}
            )
            
        except Exception as e:
            self._handle_story_error(e, "handle_end_node")

    def _handle_choice_node(self, choices: list):
        """Handle choice node logic."""
        try:
            self.main_window.choices_panel.display_choices(choices, self.make_choice)
            self.main_window.action_buttons.next_button.setEnabled(False)
            self.main_window.hotkey_listener.set_next_story_enabled(False)
            
            self.main_window.state_manager.transition_state(
                GameState.CHOICE,
                {'choices': choices}
            )
            
        except Exception as e:
            self._handle_story_error(e, "handle_choice_node")

    def _handle_battle_node(self, battle_info: Dict):
        """Handle battle node logic."""
        try:
            task = self.main_window.task_manager.get_random_active_task()
            if not task:
                raise ValueError("No active tasks available for battle")

            self.main_window.battle_manager.generate_enemy(
                battle_info.get("enemy", "Unknown Enemy"),
                task['name'],
                random.randint(task['min'], task['max'])
            )
            
        except Exception as e:
            self._handle_story_error(e, "handle_battle_node")

    def _handle_regular_node(self):
        """Handle regular (non-battle, non-choice) node."""
        try:
            self.main_window.action_buttons.hide_attack_buttons()
            self.main_window.action_buttons.next_button.setEnabled(True)
            self.main_window.hotkey_listener.set_next_story_enabled(True)
            
        except Exception as e:
            self._handle_story_error(e, "handle_regular_node")

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
            
            # Display content without adding to history
            self._display_content(content)
            self._update_navigation_state()
            
            return True
            
        except Exception as e:
            self._handle_story_error(e, "navigate")
            return False

    def _can_navigate(self, direction: NavigationDirection) -> bool:
        """Check if navigation in given direction is possible."""
        if direction == NavigationDirection.FORWARD:
            return self._history_index < len(self._history) - 1
        else:
            return self._history_index > 0

    def _update_navigation_state(self):
        """Update navigation button states."""
        try:
            can_go_back = self._history_index > 0
            can_go_forward = self._history_index < len(self._history) - 1
            
            self.main_window.story_display.back_button.setEnabled(can_go_back)
            self.main_window.story_display.forward_button.setEnabled(can_go_forward)
            
        except Exception as e:
            logging.error(f"Error updating navigation state: {e}")

    def make_choice(self, choice: Dict[str, Any]):
        """Handle player's choice selection."""
        try:
            if not isinstance(choice, dict):
                raise ValueError(f"Invalid choice type: {type(choice)}")

            if next_node := choice.get('next'):
                self.main_window.choices_panel.clear_choices()
                self.core_manager.set_current_node(next_node)
                self.display_story_segment()
                
            self.main_window.state_manager.transition_state(
                GameState.STORY,
                {'choice_made': choice}
            )
            
        except Exception as e:
            self._handle_story_error(e, "make_choice")

    def next_story_segment(self):
        """Proceed to the next segment of the story."""
        try:
            if not self._can_proceed():
                return

            current_node = self.get_current_node()
            if not current_node:
                return

            if next_node := current_node.get('next'):
                self.core_manager.set_current_node(next_node)
                self.display_story_segment()
            else:
                self._show_story_end_message()
                
        except Exception as e:
            self._handle_story_error(e, "next_story_segment")

    def _can_proceed(self) -> bool:
        """Check if story can proceed to next segment."""
        if not self.main_window.isActiveWindow():
            return False
            
        if self.main_window.battle_manager.battle_state.enemy:
            self._show_battle_in_progress_message()
            return False
            
        if not self.main_window.action_buttons.next_button.isEnabled():
            return False
            
        return True

    def get_current_node(self) -> Dict[str, Any]:
        """Get current node data from core manager."""
        try:
            if not self.core_manager:
                logging.warning("No core manager available")
                return {}
            
            node = self.core_manager.get_current_node()
            if not isinstance(node, dict):
                logging.error(f"Invalid node data type: {type(node)}")
                return {}
                
            return node
            
        except Exception as e:
            self._handle_story_error(e, "get_current_node")
            return {}

    def _handle_state_change(self, old_state: GameState, new_state: GameState, state_data: dict):
        """Handle game state changes."""
        try:
            if new_state == GameState.STORY:
                self._handle_story_state(state_data)
            elif new_state == GameState.END:
                self._handle_end_state(state_data)
                
        except Exception as e:
            self._handle_story_error(e, "handle_state_change")

    def _handle_story_state(self, state_data: dict):
        """Handle transition to story state."""
        try:
            if state_data.get('error_recovery'):
                self._handle_error_recovery()
                
        except Exception as e:
            logging.error(f"Error handling story state: {e}")

    def _handle_end_state(self, state_data: dict):
        """Handle transition to end state."""
        try:
            if state_data.get('completed'):
                self._show_completion_message()
                
        except Exception as e:
            logging.error(f"Error handling end state: {e}")

    def _handle_error_recovery(self):
        """Handle recovery from errors."""
        try:
            self._current_content = None
            self.main_window.story_display.clear_history()
            self.display_story_segment()
            
        except Exception as e:
            logging.error(f"Error during error recovery: {e}")

    def _handle_story_error(self, error: Exception, operation: str):
        """Handle story-related errors with proper recovery."""
        try:
            context = self.main_window.error_handler.create_context(
                "StoryManager",
                operation,
                {'current_node': self.current_node_key},
                ErrorSeverity.MEDIUM
            )
            
            # Log the error
            logging.error(f"Story error in {operation}: {error}")
            
            # Attempt recovery based on error type
            if isinstance(error, (IOError, OSError)):
                self._handle_io_error(error, context)
            elif isinstance(error, ValueError):
                self._handle_value_error(error, context)
            else:
                self._handle_generic_error(error, context)
                
        except Exception as recovery_error:
            logging.critical(f"Error recovery failed: {recovery_error}")
            self.main_window.close()

    def _handle_io_error(self, error: Exception, context: ErrorContext):
        """Handle IO-related errors."""
        # Try to reload from backup or default story
        if self.load_backup_story():
            logging.info("Successfully recovered using backup story")
            return
            
        # If backup fails, try to reset to initial state
        self.reset_to_initial_state()

    def _handle_value_error(self, error: Exception, context: ErrorContext):
        """Handle validation errors."""
        # Try to fix invalid state
        if self.validate_and_fix_state():
            logging.info("Successfully fixed invalid story state")
            return
            
        # If fix fails, reset to last known good state
        self.reset_to_last_checkpoint()

    def _handle_generic_error(self, error: Exception, context: ErrorContext):
        """Handle unknown errors."""
        # Save current state for recovery
        self.save_recovery_point()
        
        # Reset to initial state
        self.reset_to_initial_state()

    def _show_no_story_message(self):
        """Show message when no story is selected."""
        QMessageBox.information(
            self.main_window,
            "No Story Selected",
            "No story selected. Exiting the game."
        )

    def _show_battle_in_progress_message(self):
        """Show message when trying to proceed during battle."""
        QMessageBox.information(
            self.main_window,
            "Battle In Progress",
            "You must defeat the current enemy before proceeding!"
        )

    def _show_story_end_message(self):
        """Show message at story end."""
        QMessageBox.information(
            self.main_window,
            "End of Story",
            "You have reached the end of the story."
        )

    def _show_completion_message(self):
        """Show story completion message."""
        QMessageBox.information(
            self.main_window,
            "Story Complete",
            "Congratulations! You have completed the story!"
        )

    def cleanup(self):
        """Clean up story manager resources."""
        try:
            logging.info("Cleaning up story manager")
            self._cleanup_content(self._current_content)
            self._cleanup_images(self.story_image_folder)
            self._history.clear()
            self._history_index = -1
            self.core_manager = None
            self.main_window.story_display.clear_history()
            self.main_window.choices_panel.clear_choices()
            
        except Exception as e:
            logging.error(f"Error during story manager cleanup: {e}")

    def _cleanup_content(self, content: Optional[StoryNodeContent]):
        """Clean up story content resources."""
        if content:
            content.image_path = None
            
    def _cleanup_images(self, image_folder: Optional[str]):
        """Clean up generated images."""
        if image_folder and os.path.exists(image_folder):
            try:
                for filename in os.listdir(image_folder):
                    if filename.endswith('.png'):
                        os.remove(os.path.join(image_folder, filename))
            except Exception as e:
                logging.error(f"Error cleaning up images: {e}")