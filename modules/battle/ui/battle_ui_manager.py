"""Battle UI management for TaskRPG.

This module contains classes for managing battle UI components,
including the BattleUIManager class which handles all UI updates
related to battles.
"""

# Standard library imports
import logging
from typing import Optional, Dict, Callable, Any

# PyQt5 imports
from PyQt5.QtWidgets import QStatusBar, QLabel
from PyQt5.QtCore import QTimer

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modules.ui.components.story_display import StoryDisplay
    from modules.ui.components.enemy_panel import EnemyPanel
    from modules.ui.components.action_buttons import ActionButtons
    from modules.ui.components.player_panel import PlayerPanel
    from modules.ui.main_window import TaskRPG
    from modules.ui.components.compact_battle_window import CompactBattleWindow
    from modules.battle.enemy import Enemy

class BattleUIManager:
    """
    Manages all UI updates related to battles.
    
    Responsibilities:
    - Update UI components during battle events
    - Handle victory/defeat UI updates
    - Manage battle animations and feedback
    - Coordinate between battle state and UI components
    """
    
    def __init__(self):
        """Initialize the Battle UI Manager."""
        # UI Components (set later via set_ui_components)
        self.story_display: Optional['StoryDisplay'] = None
        self.enemy_panel: Optional['EnemyPanel'] = None
        self.action_buttons: Optional['ActionButtons'] = None
        self.player_panel: Optional['PlayerPanel'] = None
        self.status_bar: Optional['QStatusBar'] = None
        self.main_window: Optional['TaskRPG'] = None
        self.compact_window: Optional['CompactBattleWindow'] = None
        self.tasks_left_label: Optional['QLabel'] = None
        
        logging.info("BattleUIManager initialized")
    
    def set_ui_components(self, 
                         story_display=None,
                         enemy_panel=None,
                         action_buttons=None,
                         player_panel=None,
                         status_bar=None,
                         tasks_left_label=None,
                         main_window=None,
                         compact_window=None) -> None:
        """Set UI component references."""
        try:
            self.story_display = story_display
            self.enemy_panel = enemy_panel
            self.action_buttons = action_buttons
            self.player_panel = player_panel
            self.status_bar = status_bar
            self.tasks_left_label = tasks_left_label
            self.main_window = main_window
            self.compact_window = compact_window
            
            logging.info("UI components set successfully in BattleUIManager")
            return True
        
        except Exception as e:
            logging.error(f"Error setting UI components in BattleUIManager: {e}")
            return False
    
    def batch_ui_update(self, updates: Dict[str, Callable]) -> None:
        """
        Perform multiple UI updates in a single batch.
        
        Args:
            updates: Dictionary of update functions to execute
        """
        try:
            # Temporarily disable window updates if possible
            if self.main_window:
                self.main_window.setUpdatesEnabled(False)
            
            # Execute all updates
            for update_name, update_func in updates.items():
                try:
                    update_func()
                except Exception as e:
                    logging.error(f"Error in UI update '{update_name}': {e}")
                    
        finally:
            # Re-enable window updates
            if self.main_window:
                self.main_window.setUpdatesEnabled(True)
                self.main_window.repaint()
    
    def update_battle_ui(self, current_enemy: 'Enemy') -> None:
        """Update all UI components with current battle state."""
        try:
            updates = {
                'enemy_panel': lambda: self.enemy_panel.update_panel(current_enemy) if self.enemy_panel else None,
                'compact_window': lambda: self.compact_window.update_display(current_enemy) if self.compact_window else None,
                'tasks_left': lambda: self.update_tasks_left(current_enemy) if hasattr(self, 'update_tasks_left') else None,
                'action_buttons': lambda: self.action_buttons.show_attack_buttons() if self.action_buttons else None,
                'story_display': lambda: (
                    self.story_display.story_text.append(
                        "<div class='battle-status' style='margin: 10px 0; padding: 10px; background-color: rgba(255, 0, 0, 0.1); border-left: 4px solid #ff0000;'>"
                        f"<p><b>{current_enemy.name}</b> - HP: {current_enemy.current_hp}/{current_enemy.max_hp}</p>"
                        "</div>"
                    ) if self.story_display and hasattr(self.story_display, 'story_text') else None
                ),
                'status_bar': lambda: self.status_bar.showMessage("Battle in progress!") if self.status_bar else None
            }
            
            self.batch_ui_update(updates)
            logging.debug("Battle UI updated successfully")
                
        except Exception as e:
            logging.error(f"Error updating battle UI: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating battle display")
    
    def update_ui_after_attack(self, current_enemy: 'Enemy', was_heavy: bool) -> None:
        """Update UI components after an attack."""
        if self.enemy_panel:
            self.enemy_panel.update_panel(current_enemy)
        if self.compact_window:
            self.compact_window.update_display(current_enemy)
        self.update_tasks_left(current_enemy)
        
        attack_type = "Heavy attack" if was_heavy else "Attack"
        if self.status_bar:
            self.status_bar.showMessage(f"{attack_type} landed!")
    
    def update_ui_for_victory(self, xp_gained: int, coin_reward: int) -> None:
        """Update UI elements after victory with enhanced feedback."""
        try:
            victory_message = (
                "<div class='victory-message' style='text-align: center;'>"
                "<h3>Victory!</h3>"
                f"<p>You gained <b>{xp_gained}</b> XP and <b>{coin_reward}</b> coins!</p>"
                "</div>"
            )
            
            # Update UI components
            updates = {
                'story_display': lambda: self.story_display.append_text(victory_message) if self.story_display else None,
                'status_bar': lambda: self.status_bar.showMessage("Victory!") if self.status_bar else None,
                'enemy_panel': lambda: self.enemy_panel.update_panel(None) if self.enemy_panel else None,
                'player_panel': lambda: self.player_panel.update_panel() if self.player_panel else None,
                'action_buttons': lambda: (
                    self.action_buttons.hide_attack_buttons(),
                    self.action_buttons.next_button.show()
                ) if self.action_buttons else None
            }
            
            self.batch_ui_update(updates)
            
            # Trigger victory animation if enabled
            if self.main_window and hasattr(self.main_window, 'trigger_victory_animation'):
                QTimer.singleShot(0, self.main_window.trigger_victory_animation)
            
            logging.info("Victory UI updates completed")
                
        except Exception as e:
            logging.error(f"Error updating UI for victory: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating victory display")
    
    def update_tasks_left(self, current_enemy: 'Enemy') -> None:
        """Update the tasks remaining display."""
        try:
            if current_enemy and self.tasks_left_label:
                current_hp = current_enemy.current_hp
                tasks_left = max(0, current_hp)
                self.tasks_left_label.setText(str(tasks_left))

                # Update compact window if it exists
                if self.compact_window:
                    self.compact_window.update_tasks(tasks_left)
                    
            logging.debug(f"Tasks left updated: {tasks_left if 'tasks_left' in locals() else 'None'}")
                    
        except Exception as e:
            logging.error(f"Error updating tasks left: {e}")
    
    def update_status(self, message: str, timeout: int = 0) -> None:
        """Update status bar with message."""
        if self.status_bar:
            self.status_bar.showMessage(message, timeout)
            logging.debug(f"Status updated: {message}")