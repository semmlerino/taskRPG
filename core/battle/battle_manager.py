# core/battle/battle_manager.py

import os
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Protocol, List, TYPE_CHECKING, Dict, Any, Union
from enum import Enum, auto
import random

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRect
from PyQt5.QtCore import QTimer

# Core game system imports
from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.players.player import Player
from modules.battle.enemy import Enemy
from modules.battle.battle_state import BattleState
from modules.ui.components.compact_battle_window import CompactBattleWindow

# Type hints for UI components
if TYPE_CHECKING:
    from PyQt5.QtWidgets import QStatusBar, QLabel, QApplication
    from modules.ui.components.story_display import StoryDisplay
    from modules.ui.components.enemy_panel import EnemyPanel
    from modules.ui.components.action_buttons import ActionButtons
    from modules.ui.components.player_panel import PlayerPanel
    from modules.ui.main_window import TaskRPG

# At the top of the file, add debug logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

class BattleEvent(Enum):
    """Battle system events."""
    BATTLE_START = auto()
    BATTLE_END = auto()
    ATTACK_PERFORMED = auto()
    STATE_CHANGED = auto()
    ENEMY_DEFEATED = auto()

class BattleManager:
    """
    Unified battle management system handling both core logic and UI coordination.
    """

    def __init__(self, task_manager: TaskManager, player: Player):
        """
        Initialize the battle manager.
        
        Args:
            task_manager: Task management system
            player: Player instance
        """
        self.task_manager = task_manager
        self.player = player
        self.battle_state = BattleState()
        self.current_enemy: Optional[Enemy] = None
        self.paused: bool = False

        # UI update callbacks
        self.on_battle_start: Optional[Callable] = None
        self.on_battle_end: Optional[Callable] = None
        self.on_attack: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_victory: Optional[Callable] = None

        # UI Components (set by UI layer)
        self.story_display: Optional['StoryDisplay'] = None
        self.enemy_panel: Optional['EnemyPanel'] = None
        self.action_buttons: Optional['ActionButtons'] = None
        self.player_panel: Optional['PlayerPanel'] = None
        self.status_bar: Optional['QStatusBar'] = None
        self.main_window: Optional['TaskRPG'] = None
        self.compact_window: Optional['CompactBattleWindow'] = None
        self.tasks_left_label: Optional['QLabel'] = None

        logging.info("BattleManager initialized")

    def _initialize_enemy_hp(self, task: Task) -> int:
        """
        Initialize enemy HP based on task count.
        Args:
            task (Task): The task object containing min/max counts
        Returns:
            int: The calculated HP value
        """
        hp = task.get_hp()
        logging.debug(f"Initializing enemy HP for task '{task.name}': {hp}")
        return hp

    def start_battle(self, battle_info: dict) -> bool:
        """
        Start a new battle with a randomly selected active task.
        
        Args:
            battle_info (dict): Dictionary containing battle configuration with:
                - enemy: Name of the enemy (from story)
                - message: Battle start message
            
        Returns:
            bool: True if battle started successfully, False otherwise
        """
        try:
            # Debug log to see what's in battle_info
            logging.debug(f"Received battle_info: {battle_info}")
            
            # Get a random active task from the task manager
            task = self.task_manager.get_random_active_task()
            if not task:
                logging.warning("No active task available for battle")
                return False
                
            # Get enemy name from the correct key in battle_info
            enemy_name = battle_info.get('enemy') or battle_info.get('enemy_name')
            if not enemy_name:
                logging.warning("No enemy name provided in battle_info")
                enemy_name = f"Task: {task.name}"
            
            logging.debug(f"Using enemy_name: {enemy_name}")
            
            # Calculate initial HP based on task parameters
            initial_hp = self._initialize_enemy_hp(task)
            
            # Create new enemy instance with all required parameters
            self.current_enemy = Enemy(
                name=enemy_name,                                      # Use the enemy name from story
                task_name=task.name,                                  # Name of the task
                task_description=task.description or                  # Use task description if available
                           f"Complete {task.name} task",          # Or create default description
                max_hp=initial_hp,                                    # Maximum HP from task count
                current_hp=initial_hp                                 # Current HP starts at maximum
            )
            
            # Update battle state
            self.battle_state.enemy_hp = initial_hp
            self.battle_state.is_active = True
            
            # Update all UI elements with new battle information
            self._update_battle_ui()
            return True
            
        except Exception as e:
            logging.error(f"Failed to start battle: {e}")
            return False

    def perform_attack(self, is_heavy: bool = False) -> bool:
        """Perform an attack."""
        try:
            logging.debug(f"Attempting {'heavy' if is_heavy else 'normal'} attack")
            
            if not self._validate_attack():
                logging.warning("Attack validation failed - Current state: "
                              f"battle_active={self.battle_state.is_active}, "
                              f"enemy_exists={self.current_enemy is not None}, "
                              f"paused={self.paused}")
                return False

            # Log pre-attack state
            logging.debug(f"Pre-attack state - Enemy: {self.current_enemy.name}, "
                         f"HP: {self.current_enemy.current_hp}/{self.current_enemy.max_hp}")

            # Calculate damage
            if is_heavy:
                damage = random.randint(2, 4)
                logging.debug(f"Heavy attack damage rolled: {damage}")
            else:
                damage = 1
                logging.debug("Normal attack damage: 1")

            # Update enemy HP
            old_hp = self.current_enemy.current_hp
            self.current_enemy.take_damage(damage)
            new_hp = self.current_enemy.current_hp
            
            logging.debug(f"HP change: {old_hp} -> {new_hp} (damage: {damage})")

            # Update battle state
            self.battle_state.enemy_hp = new_hp
            logging.debug(f"Battle state HP updated: {self.battle_state.enemy_hp}")

            # Update UI
            self._update_ui_after_attack(is_heavy)
            logging.debug("UI updated after attack")

            # Check for victory
            if self.current_enemy.is_defeated():
                logging.debug("Enemy defeated - handling victory")
                self._handle_victory()
                return True

            return True

        except Exception as e:
            logging.error(f"Error performing attack: {str(e)}", exc_info=True)
            return False

    def toggle_pause(self) -> None:
        """Toggle the pause state of the battle."""
        try:
            self.paused = not self.paused
            status = "paused" if self.paused else "resumed"

            # Update UI pause state
            if self.action_buttons:
                self.action_buttons.setEnabled(not self.paused)
            if self.compact_window:
                self.compact_window.setEnabled(not self.paused)

            self._update_status(f"Battle {status}")
            logging.info(f"Battle {status}")

        except Exception as e:
            logging.error(f"Error toggling pause: {e}")

    def show_compact_mode(self) -> None:
        """Show compact battle window in top right corner."""
        try:
            if not self.compact_window:
                # Import here to avoid circular import
                from modules.ui.components.compact_battle_window import CompactBattleWindow
                self.compact_window = CompactBattleWindow()
                
                # Get the screen geometry
                screen = QApplication.primaryScreen()
                screen_geo = screen.availableGeometry()
                
                # Calculate position for top right corner
                # Leave a small margin from the edges
                margin = 10
                x = screen_geo.width() - self.compact_window.width() - margin
                y = margin  # Position at top with margin
                
                self.compact_window.move(x, y)
                logging.info(f"Positioning compact window at: ({x}, {y})")

                # Ensure current_enemy is an Enemy instance before updating
                if self.current_enemy and hasattr(self.current_enemy, 'name'):
                    self.compact_window.update_display(self.current_enemy)
                self.compact_window.show()
                self.compact_window.raise_()  # Bring window to front
                logging.info(f"Compact window shown at position: {self.compact_window.pos()}")

        except Exception as e:
            logging.error(f"Error showing compact window: {e}")

    def hide_compact_mode(self) -> None:
        """Hide compact battle window."""
        try:
            if self.compact_window:
                self.compact_window.close()
                self.compact_window.deleteLater()
                self.compact_window = None
                logging.info("Compact battle window hidden")

        except Exception as e:
            logging.error(f"Error hiding compact window: {e}")

    def update_tasks_left(self) -> None:
        """Update the tasks left display."""
        try:
            if self.current_enemy and self.tasks_left_label:
                current_hp = self.battle_state.enemy_hp
                tasks_left = max(0, current_hp)
                self.tasks_left_label.setText(str(tasks_left))

                # Update compact window if it exists
                if self.compact_window:
                    self.compact_window.update_tasks(tasks_left)
                    
            logging.debug(f"Tasks left updated: {self.battle_state.enemy_hp}")
            
        except Exception as e:
            logging.error(f"Error updating tasks left: {e}")

    def _validate_attack(self) -> bool:
        """Validate attack conditions."""
        validation_results = {
            "battle_active": self.battle_state.is_active,
            "enemy_exists": self.current_enemy is not None,
            "not_paused": not self.paused,
            "has_hp_attribute": hasattr(self.current_enemy, 'current_hp') if self.current_enemy else False
        }
        
        logging.debug(f"Attack validation results: {validation_results}")
        
        if not validation_results["battle_active"]:
            logging.warning("Attack validation failed: No active battle")
            return False
        if not validation_results["enemy_exists"]:
            logging.warning("Attack validation failed: No current enemy")
            return False
        if not validation_results["not_paused"]:
            logging.warning("Attack validation failed: Battle is paused")
            return False
        if not validation_results["has_hp_attribute"]:
            logging.error("Attack validation failed: Enemy missing current_hp attribute")
            return False
            
        logging.debug("Attack validation passed")
        return True

    def _handle_victory(self) -> None:
        """Handle victory with complete update chain."""
        try:
            logging.debug("Processing victory")
            
            # Calculate XP
            xp_gained = max(10, self.current_enemy.max_hp * 2)
            logging.debug(f"Calculated XP gain: {xp_gained}")
            
            # Award XP
            old_xp = self.player.stats.experience
            self.player.gain_experience(xp_gained)
            new_xp = self.player.stats.experience
            
            logging.debug(f"Player XP change: {old_xp} -> {new_xp}")
            
            # Update battle state
            self.battle_state.xp_gained = xp_gained
            self.battle_state.is_active = False
            self.current_enemy = None
            
            # Hide compact window if it exists
            if self.compact_window:
                self.hide_compact_mode()
            
            # Ensure main window is visible and focused
            if self.main_window:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                
                # Use a timer to force focus after a short delay
                QTimer.singleShot(100, lambda: (
                    self.main_window.show(),
                    self.main_window.raise_(),
                    self.main_window.activateWindow()
                ))
            
            logging.debug("Battle state updated for victory")
            
            # Update UI
            self._update_ui_for_victory(xp_gained)
            logging.debug("UI updated for victory")
            
            # Trigger callbacks
            if self.on_victory:
                logging.debug("Triggering victory callback")
                self.on_victory()
            if self.on_battle_end:
                logging.debug("Triggering battle end callback")
                self.on_battle_end()

        except Exception as e:
            logging.error(f"Error handling victory: {str(e)}")

    def _validate_battle_start(self) -> bool:
        """
        Validate battle start conditions.
        
        Returns:
            bool: True if battle can start
        """
        if self.battle_state.is_active:
            logging.warning("Battle already in progress")
            self._update_status("Battle already in progress")
            return False
        if self.paused:
            logging.warning("Cannot start battle while paused")
            self._update_status("Game is paused")
            return False
        return True

    def _update_ui_for_battle_start(self, battle_info: Dict[str, Any]) -> None:
        """Update UI for battle start."""
        if self.enemy_panel:
            self.enemy_panel.update_panel(self.current_enemy)
        if self.action_buttons:
            self.action_buttons.show_attack_buttons()
        if self.story_display:
            message = battle_info.get("message", "A new enemy appears!")
            self.story_display.append_text(f"<p><i>{message}</i></p>")
        if self.compact_window:
            self.compact_window.update_display(self.current_enemy)
        self._update_status("Battle started!")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI after attack."""
        if self.enemy_panel:
            self.enemy_panel.update_panel(self.current_enemy)
        if self.compact_window:
            self.compact_window.update_display(self.current_enemy)
        
        # Update tasks left display
        self.update_tasks_left()

        attack_type = "Heavy attack" if was_heavy else "Attack"
        self._update_status(f"{attack_type} landed!")

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI for victory."""
        if self.story_display:
            self.story_display.append_text(
                f"<p>Victory! You gained <b>{xp_gained}</b> XP!</p>"
            )
        if self.enemy_panel:
            self.enemy_panel.update_panel(None)
        if self.action_buttons:
            self.action_buttons.hide_attack_buttons()
            self.action_buttons.next_button.show()
        if self.player_panel:
            self.player_panel.update_panel()
        self._update_status("Victory! Story continues...")

    def _update_status(self, message: str) -> None:
        """Update status bar if available."""
        if self.status_bar:
            self.status_bar.showMessage(message)

    def is_in_battle(self) -> bool:
        """Check if currently in battle."""
        try:
            # First check if we have the basic requirements for a battle
            if not self.battle_state.is_active or not self.current_enemy:
                logging.debug("Battle check failed: No active battle state or no enemy")
                return False
                
            # Safely check HP
            current_hp = getattr(self.battle_state, 'enemy_hp', None)
            if current_hp is None:
                logging.debug("Battle check failed: enemy_hp is None")
                return False
                
            battle_active = current_hp > 0
            
            logging.debug(f"Battle state check - Active: {self.battle_state.is_active}, "
                         f"Enemy exists: {self.current_enemy is not None}, "
                         f"HP: {current_hp}")
            return battle_active
            
        except Exception as e:
            logging.error(f"Error checking battle state: {e}")
            return False

    def get_current_enemy(self) -> Optional[Enemy]:
        """
        Get current enemy.
        
        Returns:
            Optional[Enemy]: Current enemy or None
        """
        return self.current_enemy

    def set_ui_components(self, 
                         story_display: 'StoryDisplay',
                         enemy_panel: 'EnemyPanel',
                         action_buttons: 'ActionButtons',
                         player_panel: 'PlayerPanel',
                         status_bar: 'QStatusBar',
                         tasks_left_label: 'QLabel',
                         main_window: 'TaskRPG') -> None:
        """
        Set all UI component references for battle system.
        
        Args:
            story_display: Story display component
            enemy_panel: Enemy stats panel
            action_buttons: Battle action buttons
            player_panel: Player stats panel
            status_bar: Status bar for messages
            tasks_left_label: Label showing remaining tasks
            main_window: Main window reference
        """
        try:
            self.story_display = story_display
            self.enemy_panel = enemy_panel
            self.action_buttons = action_buttons
            self.player_panel = player_panel
            self.status_bar = status_bar
            self.tasks_left_label = tasks_left_label
            self.main_window = main_window
            
            # Connect UI signals
            if self.action_buttons:
                self.action_buttons.attack_clicked.connect(
                    lambda: self.perform_attack(is_heavy=False)
                )
                self.action_buttons.heavy_attack_clicked.connect(
                    lambda: self.perform_attack(is_heavy=True)
                )
            
            logging.info("UI components set for battle manager")
            
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")
            self._update_status("Error initializing battle system")

    def connect_signals(self, hotkey_listener) -> None:
        """
        Connect battle-related hotkey signals.
        
        Args:
            hotkey_listener: Global hotkey listener instance
        """
        try:
            # Connect attack hotkeys
            hotkey_listener.normal_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=False)
            )
            hotkey_listener.heavy_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=True)
            )
            hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
            
            logging.info("Battle hotkeys connected")
            
        except Exception as e:
            logging.error(f"Error connecting battle signals: {e}")

    def cleanup(self) -> None:
        """Clean up battle resources."""
        try:
            # Hide compact window
            self.hide_compact_mode()
            
            # Reset battle state
            self.battle_state = BattleState()
            self.current_enemy = None
            self.paused = False
            
            # Clear UI state
            if self.enemy_panel:
                self.enemy_panel.update_panel(None)
            if self.action_buttons:
                self.action_buttons.hide_attack_buttons()
            if self.tasks_left_label:
                self.tasks_left_label.setText("0")
                
            logging.info("Battle manager cleanup complete")
            
        except Exception as e:
            logging.error(f"Error during battle manager cleanup: {e}")
            
    def register_callbacks(self,
                          on_battle_start: Optional[Callable] = None,
                          on_battle_end: Optional[Callable] = None,
                          on_attack: Optional[Callable] = None,
                          on_state_change: Optional[Callable] = None,
                          on_victory: Optional[Callable] = None) -> None:
        """
        Register callback functions for battle events.
        
        Args:
            on_battle_start: Called when battle starts
            on_battle_end: Called when battle ends
            on_attack: Called when attack performed
            on_state_change: Called when battle state changes
            on_victory: Called on victory
        """
        self.on_battle_start = on_battle_start
        self.on_battle_end = on_battle_end
        self.on_attack = on_attack
        self.on_state_change = on_state_change
        self.on_victory = on_victory
        
        logging.debug("Battle callbacks registered")

    def end_battle(self) -> None:
        """End the current battle."""
        try:
            logging.debug("Ending battle")
            self.battle_state.is_active = False
            self.current_enemy = None
            self.battle_state.enemy_hp = 0
            
            # Hide compact window if it exists
            if self.compact_window:
                self.hide_compact_mode()
            
            # Reset battle state
            self.current_enemy = None
            self.in_battle = False
            
            # Ensure main window is visible and focused
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            
            # Force focus to the main window
            QTimer.singleShot(100, lambda: (
                self.main_window.raise_(),
                self.main_window.activateWindow()
            ))
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")

    def _update_battle_ui(self) -> None:
        """
        Update all UI components with current battle state.
        
        This method is responsible for:
        - Updating the enemy panel with current enemy stats
        - Refreshing the compact window display
        - Updating the tasks remaining counter
        - Showing attack buttons
        - Setting the status bar message
        
        Each UI component is checked for existence before updating to prevent errors.
        """
        try:
            # Update the main enemy panel showing enemy stats and HP bar
            # This panel is typically in the main window
            if hasattr(self, 'enemy_panel') and self.enemy_panel:
                self.enemy_panel.update_panel(self.current_enemy)
                logging.debug("Enemy panel updated")
                
            # Update the compact floating window if it exists
            # This is the small window that can be positioned anywhere on screen
            if hasattr(self, 'compact_window') and self.compact_window:
                self.compact_window.update_display(self.current_enemy)
                logging.debug("Compact window updated")
                
            # Update the counter showing remaining tasks/HP
            # This is typically shown in both main and compact windows
            if hasattr(self, 'update_tasks_left'):
                self.update_tasks_left()
                logging.debug("Tasks left counter updated")
                
            # Show the attack buttons for battle interaction
            # These buttons allow the player to perform actions
            if hasattr(self, 'action_buttons') and self.action_buttons:
                self.action_buttons.show_attack_buttons()
                logging.debug("Attack buttons displayed")
                
            # Update the status bar with battle information
            # This provides feedback to the player about the current state
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage("Battle started!")
                logging.debug("Status bar message set")
                
            logging.debug(f"Battle UI successfully updated for enemy: {self.current_enemy.name}")
            
        except Exception as e:
            # Log any errors that occur during UI updates
            logging.error(f"Error updating battle UI: {e}")
            # Include the full error traceback for debugging
            logging.debug(f"Full error details:", exc_info=True)