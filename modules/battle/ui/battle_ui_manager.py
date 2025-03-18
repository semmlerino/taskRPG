"""
File: modules/battle/ui/battle_ui_manager.py
Battle UI management for TaskRPG.

This module contains classes for managing battle UI components,
including the BattleUIManager class which handles all UI updates
related to battles.
"""

# Standard library imports
import logging
from typing import Optional, Dict, Callable, Any

# PyQt5 imports
from PyQt5.QtWidgets import QStatusBar, QLabel, QMessageBox, QApplication, QDesktopWidget
from PyQt5.QtCore import QTimer, QPoint

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
                         compact_window=None) -> bool:
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
    
    def are_components_ready(self) -> bool:
        """Check if essential UI components are ready."""
        essential_components = [
            self.enemy_panel, 
            self.action_buttons, 
            self.status_bar
        ]
        
        if not all(essential_components):
            missing_components = []
            if not self.enemy_panel:
                missing_components.append("enemy_panel")
            if not self.action_buttons:
                missing_components.append("action_buttons")
            if not self.status_bar:
                missing_components.append("status_bar")
                
            logging.warning(f"Missing essential UI components: {', '.join(missing_components)}")
            return False
            
        return True
    
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
                'tasks_left': lambda: self.update_tasks_left(current_enemy),
                'action_buttons': lambda: self.action_buttons.show_attack_buttons() if self.action_buttons else None,
                'story_display': lambda: (
                    self.story_display.append_text(
                        "<div class='battle-status' style='margin: 10px 0; padding: 10px; background-color: rgba(255, 0, 0, 0.1); border-left: 4px solid #ff0000;'>"
                        f"<p><b>{current_enemy.name}</b> - HP: {current_enemy.current_hp}/{current_enemy.max_hp}</p>"
                        "</div>"
                    ) if self.story_display else None
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
        try:
            if self.enemy_panel:
                self.enemy_panel.update_panel(current_enemy)
            if self.compact_window:
                self.compact_window.update_display(current_enemy)
            self.update_tasks_left(current_enemy)
            
            attack_type = "Heavy attack" if was_heavy else "Attack"
            if self.status_bar:
                self.status_bar.showMessage(f"{attack_type} landed!")
                
            logging.debug(f"{attack_type} UI updates completed")
            
        except Exception as e:
            logging.error(f"Error updating UI after attack: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating attack display")
    
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
            self.trigger_victory_animation()
            
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
    
    def append_story_text(self, message: str) -> None:
        """Append text to the story display."""
        if self.story_display:
            self.story_display.append_text(message)
            
    def update_status(self, message: str, timeout: int = 0) -> None:
        """Update status bar with message."""
        if self.status_bar:
            self.status_bar.showMessage(message, timeout)
            logging.debug(f"Status updated: {message}")
    
    def update_pause_state(self, paused: bool) -> None:
        """Update UI components with the current pause state."""
        try:
            # Update action buttons
            if self.action_buttons:
                self.action_buttons.setEnabled(not paused)
                logging.debug("Action buttons pause state updated")
            
            # Update enemy panel
            if self.enemy_panel and hasattr(self.enemy_panel, 'update_pause_state'):
                self.enemy_panel.update_pause_state(paused)
                logging.debug("Enemy panel pause state updated")
            
            # Update compact window
            if self.compact_window and hasattr(self.compact_window, 'update_pause_state'):
                self.compact_window.update_pause_state(paused)
                logging.debug("Compact window pause state updated")
                
            logging.debug(f"UI pause state updated to: {'paused' if paused else 'resumed'}")
            
        except Exception as e:
            logging.error(f"Error updating UI pause state: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating pause state")
                
    def validate_pause_state(self, is_paused: bool) -> None:
        """Validate that pause state is consistent across all components."""
        try:
            # Check compact window state
            if self.compact_window and hasattr(self.compact_window, '_is_paused'):
                if self.compact_window._is_paused != is_paused:
                    logging.warning("Pause state mismatch detected in compact window")
                    self.compact_window.update_pause_state(is_paused)
        
            # Check enemy panel state
            if self.enemy_panel and hasattr(self.enemy_panel, '_is_paused'):
                if self.enemy_panel._is_paused != is_paused:
                    logging.warning("Pause state mismatch detected in enemy panel")
                    self.enemy_panel.update_pause_state(is_paused)
        
            # Check action buttons state
            if self.action_buttons and self.action_buttons.isEnabled() == is_paused:
                logging.warning("Action buttons state inconsistent with pause state")
                self.action_buttons.setEnabled(not is_paused)
            
            logging.debug(f"Pause state validation complete. Current state: {is_paused}")
            
        except Exception as e:
            logging.error(f"Error validating pause state: {e}")
                
    def show_error(self, message: str) -> None:
        """Show error message to user in the UI."""
        if self.status_bar:
            self.status_bar.showMessage(message)
        logging.error(message)
        QMessageBox.critical(None, "Error", message)

    def release_keyboard_focus(self) -> None:
        """Release keyboard focus if in fullscreen mode."""
        if self.main_window and self.main_window.isFullScreen():
            self.main_window.releaseKeyboard()
            logging.debug("Keyboard focus released")
    
    def trigger_shake_animation(self) -> None:
        """Trigger shake animation on main window if available."""
        if self.main_window and hasattr(self.main_window, 'trigger_shake_animation'):
            self.main_window.trigger_shake_animation()
            logging.debug("Shake animation triggered")
        
    def trigger_victory_animation(self) -> None:
        """Trigger victory animation on main window if available."""
        if self.main_window and hasattr(self.main_window, 'trigger_victory_animation'):
            QTimer.singleShot(0, self.main_window.trigger_victory_animation)
            logging.debug("Victory animation triggered")
        
    def show_compact_mode(self, current_enemy: 'Enemy', attack_callback, heavy_attack_callback) -> None:
        """Show compact battle window positioned in the top right corner."""
        try:
            # Create compact window if it doesn't exist
            if not self.compact_window:
                from modules.ui.components.compact_battle_window import CompactBattleWindow
                self.compact_window = CompactBattleWindow()
                
                # Connect signals
                if attack_callback:
                    self.compact_window.attack_clicked.connect(attack_callback)
                if heavy_attack_callback:
                    self.compact_window.heavy_attack_clicked.connect(heavy_attack_callback)
                
                # Log creation
                logging.info("Compact battle window created and signals connected")
                
            # Update with current enemy
            if current_enemy:
                self.compact_window.update_display(current_enemy)
            
            # Position in top right corner
            screen = QDesktopWidget().availableGeometry()
            window_size = self.compact_window.sizeHint()
            position = QPoint(
                screen.right() - window_size.width() - 20,  # 20px margin from right edge
                screen.top() + 20  # 20px margin from top
            )
            self.compact_window.move(position)
                
            # Show and position window
            self.compact_window.show()
            self.compact_window.raise_()
            self.compact_window.activateWindow()
            
            logging.info("Compact battle window displayed in top right corner")
            
        except Exception as e:
            logging.error(f"Error showing compact battle window: {e}")
            self.show_error("Failed to show compact battle window")
            
    def hide_compact_mode(self) -> None:
        """Hide compact battle window."""
        if self.compact_window:
            self.compact_window.hide()
            logging.debug("Compact battle window hidden")
            
    def update_ui_for_battle_end(self) -> None:
        """Update UI components when battle ends."""
        try:
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
                
            logging.info("Battle end UI updates completed")
            
        except Exception as e:
            logging.error(f"Error updating UI for battle end: {e}")
            self.show_error("Error updating battle end display")
    
    def handle_chapter_complete(self) -> None:
        """Display chapter completion message."""
        try:
            completion_message = (
                "<div style='text-align: center;'>"
                "<br><b>Chapter Complete!</b><br>"
                "<p style='margin: 10px 0;'>You have completed all available tasks for now.</p>"
                "<p style='margin: 10px 0;'>Feel free to start a new chapter or take a break!</p>"
                "</div>"
            )
            
            # Update UI components
            updates = {
                'story_display': lambda: self.story_display.append_text(completion_message) if self.story_display else None,
                'status_bar': lambda: self.status_bar.showMessage("Chapter complete!") if self.status_bar else None
            }
            
            self.batch_ui_update(updates)
            logging.debug("Chapter completion message displayed")
            
        except Exception as e:
            logging.error(f"Error displaying chapter completion: {e}")
            self.show_error("Error displaying chapter completion")
            
    def emergency_cleanup_ui(self) -> None:
        """Emergency cleanup for UI components during critical failures.
        
        This method is called by the battle manager when a critical error occurs,
        ensuring that all UI components are properly reset even in exceptional cases.
        """
        try:
            logging.warning("Performing emergency UI cleanup due to critical failure")
            
            # Hide compact window immediately
            self.hide_compact_mode()
            
            # Release keyboard focus
            if self.main_window:
                self.main_window.releaseKeyboard()
            
            # Reset UI components with minimal operations
            # Use a more direct approach than batch_ui_update to minimize potential errors
            if self.enemy_panel:
                try:
                    self.enemy_panel.update_panel(None)
                except Exception as e:
                    logging.error(f"Failed to reset enemy panel during emergency cleanup: {e}")
                    
            if self.action_buttons:
                try:
                    self.action_buttons.hide_attack_buttons()
                except Exception as e:
                    logging.error(f"Failed to hide attack buttons during emergency cleanup: {e}")
                    
            if self.tasks_left_label:
                try:
                    self.tasks_left_label.setText("0")
                except Exception as e:
                    logging.error(f"Failed to reset tasks left label during emergency cleanup: {e}")
            
            # Update status bar with error message
            if self.status_bar:
                self.status_bar.showMessage("Battle system encountered an error and has been reset")
                
            logging.info("Emergency UI cleanup completed")
            
        except Exception as e:
            # Last resort error handling - we're already in an emergency handler
            logging.critical(f"Critical failure during emergency UI cleanup: {e}")
            # Don't raise - we're the last line of defense
            self.show_error("Error cleaning up UI components")

    def cleanup_ui(self) -> None:
        """Clean up UI components when battle manager is being cleaned up.
        
        This method handles proper cleanup of all UI components managed by the BattleUIManager,
        ensuring that all resources are released and UI state is reset.
        """
        try:
            logging.info("Cleaning up battle UI components")
            
            # Hide compact window if it exists
            self.hide_compact_mode()
            
            # Reset UI components
            updates = {
                'enemy_panel': lambda: self.enemy_panel.update_panel(None) if self.enemy_panel else None,
                'action_buttons': lambda: self.action_buttons.hide_attack_buttons() if self.action_buttons else None,
                'tasks_left': lambda: self.tasks_left_label.setText("0") if self.tasks_left_label else None,
                'status_bar': lambda: self.status_bar.showMessage("Battle ended") if self.status_bar else None
            }
            
            self.batch_ui_update(updates)
            
            # Clear references to compact window
            self.compact_window = None
            
            logging.info("Battle UI components cleaned up successfully")
            
        except Exception as e:
            logging.error(f"Error cleaning up UI components: {e}")
            # Try emergency cleanup as fallback
            try:
                self.emergency_cleanup_ui()
            except Exception as nested_e:
                logging.critical(f"Both normal and emergency cleanup failed: {nested_e}")
                self.show_error("Critical error in battle system")