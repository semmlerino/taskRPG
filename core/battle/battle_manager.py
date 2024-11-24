# core/battle/battle_manager.py
"""
This is the obsolete battle manager, which is being consolidated into a single file into the modules one.
"""

from dataclasses import dataclass
from typing import Optional
import logging

import os
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Protocol, List, TYPE_CHECKING, Dict, Any, Union
from enum import Enum, auto
import random
import time

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRect, QTimer, Qt

from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.players.player import Player
from modules.ui.components.compact_battle_window import CompactBattleWindow
from modules.battle.battle_manager import Enemy

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QStatusBar, QLabel, QApplication
    from modules.ui.components.story_display import StoryDisplay
    from modules.ui.components.enemy_panel import EnemyPanel
    from modules.ui.components.action_buttons import ActionButtons
    from modules.ui.components.player_panel import PlayerPanel
    from modules.ui.main_window import TaskRPG

class BattleEvent(Enum):
    """Battle system events."""
    BATTLE_START = auto()
    BATTLE_END = auto()
    ATTACK_PERFORMED = auto()
    STATE_CHANGED = auto()
    ENEMY_DEFEATED = auto()

@dataclass
class BattleState:
    """
    Represents the current state of a battle.
    
    Attributes:
        is_active: Whether a battle is currently in progress
        enemy_name: Name of current enemy
        enemy_hp: Current enemy HP
        enemy_max_hp: Maximum enemy HP
        task_name: Name of associated task
        last_attack_type: Type of last attack performed
        xp_gained: Amount of XP gained in battle
        turns_taken: Number of turns in battle
        attacks_performed: Number of attacks performed
    """
    is_active: bool = False
    enemy_name: Optional[str] = None
    enemy_hp: Optional[int] = None
    enemy_max_hp: Optional[int] = None
    task_name: Optional[str] = None
    last_attack_type: Optional[str] = None
    xp_gained: int = 0
    turns_taken: int = 0
    attacks_performed: int = 0

    def __post_init__(self):
        """Validate state after initialization."""
        if self.enemy_hp is not None and self.enemy_max_hp is not None:
            self.enemy_hp = max(0, min(self.enemy_hp, self.enemy_max_hp))

class BattleManager:
    """Unified battle management system handling both core logic and UI coordination."""
    
    def __init__(self, task_manager: TaskManager, player: Player):
        self.task_manager = task_manager
        self.player = player
        self.battle_state = BattleState()
        self.current_enemy: Optional[Enemy] = None
        self.paused: bool = False

        # UI Components (set by UI layer)
        self.story_display: Optional['StoryDisplay'] = None
        self.enemy_panel: Optional['EnemyPanel'] = None
        self.action_buttons: Optional['ActionButtons'] = None
        self.player_panel: Optional['PlayerPanel'] = None
        self.status_bar: Optional['QStatusBar'] = None
        self.main_window: Optional['TaskRPG'] = None
        self.compact_window: Optional['CompactBattleWindow'] = None
        self.tasks_left_label: Optional['QLabel'] = None

        # Callbacks
        self.on_battle_start: Optional[Callable] = None
        self.on_battle_end: Optional[Callable] = None
        self.on_attack: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_victory: Optional[Callable] = None

        logging.info("BattleManager initialized")

    def start_battle(self, battle_info: dict) -> bool:
        """Start a new battle."""
        try:
            logging.debug(f"Starting battle with info: {battle_info}")
            
            if not self._validate_battle_start():
                return False

            # Get random active task
            task = self.task_manager.get_random_active_task()
            if not task:
                logging.warning("No active task available for battle")
                return False

            # Initialize enemy
            enemy_name = battle_info.get('enemy') or battle_info.get('enemy_name')
            if not enemy_name:
                enemy_name = f"Task: {task.name}"

            initial_hp = self._initialize_enemy_hp(task)
            
            self.current_enemy = Enemy(
                name=enemy_name,
                task_name=task.name,
                task_description=task.description or f"Complete {task.name} task",
                max_hp=initial_hp,
                current_hp=initial_hp
            )
            
            # Update battle state
            self.battle_state.enemy_hp = initial_hp
            self.battle_state.is_active = True
            
            # Update UI
            self._update_battle_ui()
            
            # Ensure window state is appropriate
            if self.main_window and self.main_window.isFullScreen():
                self.main_window.releaseKeyboard()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to start battle: {e}")
            return False

    def perform_attack(self, is_heavy: bool = False) -> bool:
        """Perform an attack."""
        try:
            if not self._validate_attack():
                return False

            damage = random.randint(2, 4) if is_heavy else 1
            
            # Update enemy HP
            old_hp = self.current_enemy.current_hp
            self.current_enemy.take_damage(damage)
            new_hp = self.current_enemy.current_hp
            
            # Update battle state
            self.battle_state.enemy_hp = new_hp
            
            # Update UI
            self._update_ui_after_attack(is_heavy)
            
            # Check for victory
            if self.current_enemy.is_defeated():
                self._handle_victory()
                
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            return False

    def cleanup(self):
        """Clean up battle resources."""
        try:
            # Hide compact window
            self.hide_compact_mode()
            
            # Reset battle state
            self.battle_state = BattleState()
            self.current_enemy = None
            self.paused = False
            
            # Release any held keyboard focus
            if self.main_window:
                self.main_window.releaseKeyboard()
            
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

    def show_compact_mode(self) -> None:
        """Show compact battle window."""
        try:
            if not self.compact_window and self.is_in_battle():
                self.compact_window = CompactBattleWindow()
                
                screen = QApplication.primaryScreen()
                screen_geo = screen.availableGeometry()
                
                margin = 10
                x = screen_geo.width() - self.compact_window.width() - margin
                y = margin
                
                self.compact_window.move(x, y)
                
                if self.current_enemy:
                    self.compact_window.update_display(self.current_enemy)
                self.compact_window.show()
                self.compact_window.raise_()
                
                logging.info("Compact battle window shown")
                
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

    def toggle_pause(self) -> None:
        """Toggle battle pause state."""
        try:
            self.paused = not self.paused
            status = "paused" if self.paused else "resumed"

            if self.action_buttons:
                self.action_buttons.setEnabled(not self.paused)
            
            if self.compact_window:
                self.compact_window.update_pause_state(self.paused)
                if not self.paused:
                    self.compact_window.update_display(self.current_enemy)

            self._update_status(f"Battle {status}")
            
        except Exception as e:
            logging.error(f"Error toggling pause: {e}")

    def _validate_attack(self) -> bool:
        """Validate attack conditions."""
        validation_results = {
            "battle_active": self.battle_state.is_active,
            "enemy_exists": self.current_enemy is not None,
            "not_paused": not self.paused,
            "has_hp_attribute": hasattr(self.current_enemy, 'current_hp') if self.current_enemy else False
        }
        
        logging.debug(f"Attack validation results: {validation_results}")
        
        for key, value in validation_results.items():
            if not value:
                logging.warning(f"Attack validation failed: {key}")
                return False
                
        return True

    def _validate_battle_start(self) -> bool:
        """Validate battle start conditions."""
        if self.battle_state.is_active:
            logging.warning("Battle already in progress")
            self._update_status("Battle already in progress")
            return False
        if self.paused:
            logging.warning("Cannot start battle while paused")
            self._update_status("Game is paused")
            return False
        return True

    def _handle_victory(self) -> None:
        """Handle victory with complete update chain."""
        try:
            # Calculate and award XP
            xp_gained = max(10, self.current_enemy.max_hp * 2)
            self.player.gain_experience(xp_gained)
            
            # Update battle state
            self.battle_state.xp_gained = xp_gained
            self.battle_state.is_active = False
            self.current_enemy = None
            
            # Handle window state
            self.hide_compact_mode()
            if self.main_window:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                
                # Release any keyboard grab
                self.main_window.releaseKeyboard()
                
                # Force focus after delay
                QTimer.singleShot(100, lambda: (
                    self.main_window.raise_(),
                    self.main_window.activateWindow()
                ))
            
            # Update UI
            self._update_ui_for_victory(xp_gained)
            
            # Trigger callbacks
            if self.on_victory:
                self.on_victory()
            if self.on_battle_end:
                self.on_battle_end()
                
        except Exception as e:
            logging.error(f"Error handling victory: {e}")

    def _initialize_enemy_hp(self, task: Task) -> int:
        """Initialize enemy HP based on task."""
        hp = task.get_hp()
        logging.debug(f"Initialized enemy HP for task '{task.name}': {hp}")
        return hp

    def _update_battle_ui(self) -> None:
        """Update all UI components with current battle state."""
        try:
            if self.enemy_panel:
                self.enemy_panel.update_panel(self.current_enemy)
                
            if self.compact_window:
                self.compact_window.update_display(self.current_enemy)
                
            if hasattr(self, 'update_tasks_left'):
                self.update_tasks_left()
                
            if self.action_buttons:
                self.action_buttons.show_attack_buttons()
                
            if self.status_bar:
                self.status_bar.showMessage("Battle started!")
                
        except Exception as e:
            logging.error(f"Error updating battle UI: {e}")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI after attack."""
        if self.enemy_panel:
            self.enemy_panel.update_panel(self.current_enemy)
        if self.compact_window:
            self.compact_window.update_display(self.current_enemy)
        
        self.update_tasks_left()
        
        attack_type = "Heavy attack" if was_heavy else "Attack"
        self._update_status(f"{attack_type} landed!")

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI elements after victory."""
        try:
            victory_message = f"<p>Victory! You gained <b>{xp_gained}</b> XP!</p>"
            
            if self.story_display:
                self.story_display.append_text(victory_message)
                
            if self.status_bar:
                self.status_bar.showMessage("Victory!")
                
            # Update other UI elements
            if self.enemy_panel:
                self.enemy_panel.update_panel(None)
            if self.player_panel:
                self.player_panel.update_panel()
            if self.action_buttons:
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.show()
                
        except Exception as e:
            logging.error(f"Error updating UI for victory: {e}")

    def _update_status(self, message: str) -> None:
        """Update status bar."""
        if self.status_bar:
            self.status_bar.showMessage(message)

    def is_in_battle(self) -> bool:
        """Check if currently in battle."""
        return bool(
            self.battle_state.is_active and 
            self.current_enemy and 
            self.battle_state.enemy_hp > 0
        )

    def update_tasks_left(self) -> None:
        """Update tasks remaining display."""
        try:
            if self.current_enemy and self.tasks_left_label:
                current_hp = self.battle_state.enemy_hp
                tasks_left = max(0, current_hp)
                self.tasks_left_label.setText(str(tasks_left))

                if self.compact_window:
                    self.compact_window.update_tasks(tasks_left)
                    
        except Exception as e:
            logging.error(f"Error updating tasks left: {e}")

    def connect_signals(self, hotkey_listener) -> None:
        """Connect battle-related hotkey signals."""
        try:
            hotkey_listener.normal_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=False)
            )
            hotkey_listener.heavy_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=True)
            )
            hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
            
        except Exception as e:
            logging.error(f"Error connecting battle signals: {e}")

    def set_ui_components(self, 
                         story_display: 'StoryDisplay',
                         enemy_panel: 'EnemyPanel',
                         action_buttons: 'ActionButtons',
                         player_panel: 'PlayerPanel',
                         status_bar: 'QStatusBar',
                         tasks_left_label: 'QLabel',
                         main_window: 'TaskRPG') -> None:
        """Set UI component references."""
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
            
            logging.info("UI components set")
            
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")

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
        try:
            self.on_battle_start = on_battle_start
            self.on_battle_end = on_battle_end
            self.on_attack = on_attack
            self.on_state_change = on_state_change
            self.on_victory = on_victory
            
            logging.debug("Battle callbacks registered")
            
        except Exception as e:
            logging.error(f"Error registering battle callbacks: {e}")

    def end_battle(self) -> None:
        """End the current battle and clean up."""
        try:
            logging.debug("Ending battle")
            
            # Update battle state
            self.battle_state.is_active = False
            self.current_enemy = None
            self.battle_state.enemy_hp = 0
            
            # Hide compact window
            self.hide_compact_mode()
            
            # Ensure main window is visible and focused
            if self.main_window:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                
                # Release any keyboard grab
                self.main_window.releaseKeyboard()
                
                # Force focus to the main window
                QTimer.singleShot(100, lambda: (
                    self.main_window.raise_(),
                    self.main_window.activateWindow()
                ))
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")

    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.current_enemy

    def _handle_chapter_complete(self) -> None:
        """Display chapter completion message."""
        try:
            completion_message = (
                "<div style='text-align: center;'>"
                "<br><b>Chapter Complete!</b><br>"
                "<p style='margin: 10px 0;'>You have completed all available tasks for now.</p>"
                "<p style='margin: 10px 0;'>Feel free to start a new chapter or take a break!</p>"
                "</div>"
            )
            
            if self.story_display:
                self.story_display.append_text(completion_message)
                
            if self.status_bar:
                self.status_bar.showMessage("Chapter complete!")
                
            logging.debug("Chapter completion message displayed")
            
        except Exception as e:
            logging.error(f"Error displaying chapter completion: {e}")