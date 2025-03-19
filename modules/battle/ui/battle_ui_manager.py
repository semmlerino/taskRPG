# modules/battle/ui/battle_ui_manager.py
"""
Refactored battle UI management for TaskRPG.

This module contains the improved BattleUIManager class that handles all UI updates
related to battles, subscribing to events from the battle system.
"""

# Standard library imports
import logging
from typing import Optional, Dict, Callable, Any

# PyQt5 imports
from PyQt5.QtWidgets import QStatusBar, QLabel, QMessageBox, QApplication, QDesktopWidget
from PyQt5.QtCore import QTimer, QPoint

# Project imports
from modules.battle.battle_event_system import BattleEventType, BattleEvent, event_dispatcher

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
    from modules.battle.battle_manager import BattleManager

class BattleUIManager:
    """
    Manages all UI updates related to battles.
    
    This class subscribes to battle events and updates UI components accordingly,
    keeping UI concerns separate from battle logic.
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
        
        # Battle manager reference
        self.battle_manager: Optional['BattleManager'] = None
        
        # Active timers
        self.active_timers = []
        
        logging.info("BattleUIManager initialized")
    
    def set_battle_manager(self, battle_manager: 'BattleManager') -> None:
        """Set the battle manager reference."""
        self.battle_manager = battle_manager
        battle_manager.set_ui_manager(self)
        self._register_event_handlers()
        logging.info("Battle manager set for UI Manager")
    
    def _register_event_handlers(self) -> None:
        """Register handlers for battle events."""
        # Subscribe to battle events
        event_dispatcher.subscribe(
            BattleEventType.BATTLE_START,
            self._handle_battle_start
        )
        event_dispatcher.subscribe(
            BattleEventType.BATTLE_END,
            self._handle_battle_end
        )
        event_dispatcher.subscribe(
            BattleEventType.ATTACK_PERFORMED,
            self._handle_attack_performed
        )
        event_dispatcher.subscribe(
            BattleEventType.HP_UPDATED,
            self._handle_hp_updated
        )
        event_dispatcher.subscribe(
            BattleEventType.BATTLE_PAUSED,
            self._handle_battle_paused
        )
        event_dispatcher.subscribe(
            BattleEventType.BATTLE_RESUMED,
            self._handle_battle_resumed
        )
        event_dispatcher.subscribe(
            BattleEventType.VICTORY,
            self._handle_victory
        )
        event_dispatcher.subscribe(
            BattleEventType.ENEMY_DEFEATED,
            self._handle_enemy_defeated
        )
        event_dispatcher.subscribe(
            BattleEventType.UI_UPDATE_REQUESTED,
            self._handle_ui_update_request
        )
        event_dispatcher.subscribe(
            BattleEventType.ERROR_OCCURRED,
            self._handle_error
        )
        
        logging.info("Event handlers registered for BattleUIManager")
    
    def _handle_battle_start(self, event: BattleEvent) -> None:
        """Handle battle start event."""
        try:
            # Update UI with enemy information
            if self.enemy_panel and self.battle_manager:
                enemy = self.battle_manager.get_current_enemy()
                if enemy:
                    self.enemy_panel.update_panel(enemy)
            
            # Show attack buttons
            if self.action_buttons:
                self.action_buttons.show_attack_buttons()
            
            # Update status bar
            if self.status_bar:
                self.status_bar.showMessage("Battle in progress!")
            
            logging.debug("UI updated for battle start")
        except Exception as e:
            logging.error(f"Error handling battle start event: {e}")
    
    def _handle_battle_end(self, event: BattleEvent) -> None:
        """Handle battle end event."""
        try:
            # Hide compact window
            self.hide_compact_mode()
            
            # Update UI components
            if self.enemy_panel:
                self.enemy_panel.update_panel(None)
            
            if self.action_buttons:
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.show()
            
            # Update status bar
            if self.status_bar:
                self.status_bar.showMessage("Battle ended")
            
            logging.debug("UI updated for battle end")
        except Exception as e:
            logging.error(f"Error handling battle end event: {e}")
    
    def _handle_attack_performed(self, event: BattleEvent) -> None:
        """Handle attack performed event."""
        try:
            attack_type = event.data.get("attack_type", "normal")
            is_heavy = event.data.get("is_heavy", False)
            damage = event.data.get("damage", 0)
            
            # Show feedback in status bar
            if self.status_bar:
                self.status_bar.showMessage(f"{attack_type.capitalize()} attack: -{damage} HP", 1500)
            
            # Trigger shake animation if available
            if self.main_window and hasattr(self.main_window, 'trigger_shake_animation'):
                self.main_window.trigger_shake_animation()
            
            logging.debug(f"UI updated for {attack_type} attack")
        except Exception as e:
            logging.error(f"Error handling attack performed event: {e}")
    
    def _handle_hp_updated(self, event: BattleEvent) -> None:
        """Handle HP updated event."""
        try:
            # Update enemy panel
            if self.enemy_panel and self.battle_manager:
                enemy = self.battle_manager.get_current_enemy()
                if enemy:
                    self.enemy_panel.update_panel(enemy)
            
            # Update compact window
            if self.compact_window and self.battle_manager:
                enemy = self.battle_manager.get_current_enemy()
                if enemy:
                    self.compact_window.update_display(enemy)
            
            # Update tasks left
            if self.tasks_left_label and self.battle_manager:
                enemy = self.battle_manager.get_current_enemy()
                if enemy:
                    tasks_left = max(0, enemy.current_hp)
                    self.tasks_left_label.setText(str(tasks_left))
                    
                    # Update compact window tasks
                    if self.compact_window:
                        self.compact_window.update_tasks(tasks_left)
            
            logging.debug("UI updated for HP change")
        except Exception as e:
            logging.error(f"Error handling HP updated event: {e}")
    
    def _handle_battle_paused(self, event: BattleEvent) -> None:
        """Handle battle paused event."""
        try:
            # Update UI to show paused state
            self.update_pause_state(True)
            
            logging.debug("UI updated for battle pause")
        except Exception as e:
            logging.error(f"Error handling battle paused event: {e}")
    
    def _handle_battle_resumed(self, event: BattleEvent) -> None:
        """Handle battle resumed event."""
        try:
            # Update UI to show active state
            self.update_pause_state(False)
            
            logging.debug("UI updated for battle resume")
        except Exception as e:
            logging.error(f"Error handling battle resumed event: {e}")
    
    def _handle_victory(self, event: BattleEvent) -> None:
        """Handle victory event."""
        try:
            xp_gained = event.data.get("xp_gained", 0)
            coin_reward = event.data.get("coin_reward", 0)
            
            # Update UI with victory message
            victory_message = (
                "<div class='victory-message' style='text-align: center;'>"
                "<h3>Victory!</h3>"
                f"<p>You gained <b>{xp_gained}</b> XP and <b>{coin_reward}</b> coins!</p>"
                "</div>"
            )
            
            if self.story_display:
                self.story_display.append_text(victory_message)
            
            if self.status_bar:
                self.status_bar.showMessage("Victory!")
            
            if self.enemy_panel:
                self.enemy_panel.update_panel(None)
            
            if self.player_panel:
                self.player_panel.update_panel()
            
            if self.action_buttons:
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.show()
            
            # Trigger victory animation if available
            if self.main_window and hasattr(self.main_window, 'trigger_victory_animation'):
                QTimer.singleShot(0, self.main_window.trigger_victory_animation)
            
            logging.info("Victory UI updates completed")
        except Exception as e:
            logging.error(f"Error handling victory event: {e}")
    
    def _handle_enemy_defeated(self, event: BattleEvent) -> None:
        """Handle enemy defeated event."""
        # No action needed here as victory handling will take care of UI updates
        pass
    
    def _handle_ui_update_request(self, event: BattleEvent) -> None:
        """Handle UI update request event."""
        try:
            action = event.data.get("action", "")
            
            if action == "display_battle_message":
                message = event.data.get("message", "A new enemy appears!")
                if self.story_display:
                    self.story_display.append_text(f"<p><i>{message}</i></p>")
            
            elif action == "show_attack_feedback":
                attack_type = event.data.get("attack_type", "normal")
                damage = event.data.get("damage", 0)
                
                if self.status_bar:
                    self.status_bar.showMessage(f"{attack_type.capitalize()} attack: -{damage} HP", 1500)
            
            elif action == "show_chapter_complete":
                self.handle_chapter_complete()
            
            logging.debug(f"UI update request handled: {action}")
        except Exception as e:
            logging.error(f"Error handling UI update request: {e}")
    
    def _handle_error(self, event: BattleEvent) -> None:
        """Handle error event."""
        try:
            message = event.data.get("message", "An error occurred")
            details = event.data.get("details", "")
            
            if self.status_bar:
                self.status_bar.showMessage(message)
            
            logging.error(f"Error event handled: {message} - {details}")
        except Exception as e:
            logging.error(f"Error handling error event: {e}")
    
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
            
            # Connect action button signals if provided
            if action_buttons and self.battle_manager:
                action_buttons.attack_clicked.connect(
                    lambda: self.battle_manager.perform_attack(is_heavy=False)
                )
                action_buttons.heavy_attack_clicked.connect(
                    lambda: self.battle_manager.perform_attack(is_heavy=True)
                )
                logging.debug("Action buttons signals connected")
            
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
                
                # Connect pause toggle signal to battle manager
                if self.battle_manager:
                    self.compact_window.pause_toggled.connect(self.battle_manager.toggle_pause)
                
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
    
    def update_pause_state(self, is_paused: bool) -> None:
        """Update UI components with the current pause state."""
        try:
            # Update action buttons
            if self.action_buttons:
                self.action_buttons.setEnabled(not is_paused)  # FIXED: Changed from paused to is_paused
                logging.debug("Action buttons pause state updated")
            
            # Update enemy panel
            if self.enemy_panel and hasattr(self.enemy_panel, 'update_pause_state'):
                self.enemy_panel.update_pause_state(is_paused)
                logging.debug("Enemy panel pause state updated")
            
            # Update compact window
            if self.compact_window and hasattr(self.compact_window, 'update_pause_state'):
                self.compact_window.update_pause_state(is_paused)
                logging.debug("Compact window pause state updated")
                
            logging.debug(f"UI pause state updated to: {'paused' if is_paused else 'resumed'}")
            
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
    
    def append_story_text(self, message: str) -> None:
        """Append text to the story display."""
        if self.story_display:
            self.story_display.append_text(message)

    def update_status(self, message: str, timeout: int = 0) -> None:
        """Update status bar with message."""
        if self.status_bar:
            self.status_bar.showMessage(message, timeout)
            logging.debug(f"Status updated: {message}")
    
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
            
            if self.story_display:
                self.story_display.append_text(completion_message)
            
            if self.status_bar:
                self.status_bar.showMessage("Chapter complete!")
                
            logging.debug("Chapter completion message displayed")
            
        except Exception as e:
            logging.error(f"Error displaying chapter completion: {e}")
            self.show_error("Error displaying chapter completion")
    
    def cleanup(self) -> None:
        """Clean up UI Manager resources."""
        try:
            logging.info("Cleaning up BattleUIManager")
            
            # Hide compact window
            self.hide_compact_mode()
            
            # Clear any remaining timers
            for timer in self.active_timers:
                timer.stop()
            self.active_timers.clear()
            
            # Unsubscribe from events
            event_dispatcher.unsubscribe(BattleEventType.BATTLE_START, self._handle_battle_start)
            event_dispatcher.unsubscribe(BattleEventType.BATTLE_END, self._handle_battle_end)
            event_dispatcher.unsubscribe(BattleEventType.ATTACK_PERFORMED, self._handle_attack_performed)
            event_dispatcher.unsubscribe(BattleEventType.HP_UPDATED, self._handle_hp_updated)
            event_dispatcher.unsubscribe(BattleEventType.BATTLE_PAUSED, self._handle_battle_paused)
            event_dispatcher.unsubscribe(BattleEventType.BATTLE_RESUMED, self._handle_battle_resumed)
            event_dispatcher.unsubscribe(BattleEventType.VICTORY, self._handle_victory)
            event_dispatcher.unsubscribe(BattleEventType.ENEMY_DEFEATED, self._handle_enemy_defeated)
            event_dispatcher.unsubscribe(BattleEventType.UI_UPDATE_REQUESTED, self._handle_ui_update_request)
            event_dispatcher.unsubscribe(BattleEventType.ERROR_OCCURRED, self._handle_error)
            
            logging.info("BattleUIManager cleanup complete")
            
        except Exception as e:
            logging.error(f"Error during BattleUIManager cleanup: {e}")