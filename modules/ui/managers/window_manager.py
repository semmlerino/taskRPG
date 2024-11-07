# modules/ui/managers/window_manager.py

import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from modules.components.compact_battle_window import CompactBattleWindow
from modules.utils.qt_helpers import ensure_qt_application

class WindowManager:
    """Manages window states, events, and the compact battle window."""
    
    def __init__(self, main_window):
        ensure_qt_application()
        self.main_window = main_window
        self.compact_window = None
        self.install_event_filter()
        logging.info("Window manager initialized")

    def install_event_filter(self):
        """Install event filter on main window."""
        self.main_window.installEventFilter(self.main_window)
        logging.debug("Event filter installed")

    def handle_window_deactivate(self):
        """Handle main window losing focus."""
        try:
            # Disable G button and its hotkey
            if hasattr(self.main_window, 'action_buttons'):
                self.main_window.action_buttons.next_button.setEnabled(False)
            
            if hasattr(self.main_window, 'hotkey_listener'):
                self.main_window.hotkey_listener.set_next_story_enabled(False)
            
            # Show compact window if in battle
            if self.main_window.battle_manager.current_enemy:
                self.show_compact_mode()
                
        except Exception as e:
            logging.error(f"Error in handle_window_deactivate: {e}")

    def handle_window_activate(self):
        """Handle main window regaining focus."""
        try:
            # Only enable G button if not in battle and in a valid story segment
            if (hasattr(self.main_window, 'battle_manager') and 
                hasattr(self.main_window, 'story_manager') and 
                not self.main_window.battle_manager.current_enemy):
                
                current_node = self.main_window.story_manager.get_current_node()
                if current_node and not current_node.get('battle'):
                    if hasattr(self.main_window, 'action_buttons'):
                        self.main_window.action_buttons.next_button.setEnabled(True)
                    if hasattr(self.main_window, 'hotkey_listener'):
                        self.main_window.hotkey_listener.set_next_story_enabled(True)
            
            # Hide compact window
            self.hide_compact_mode()
            
        except Exception as e:
            logging.error(f"Error in handle_window_activate: {e}")

    def show_compact_mode(self):
        """Shows the compact battle window when main window loses focus."""
        try:
            if not self.compact_window:
                self.compact_window = CompactBattleWindow()
            
            # Position the compact window in the top-right corner
            screen = QApplication.primaryScreen().geometry()
            self.compact_window.move(screen.width() - 220, 20)
            
            # Update and show the compact window
            self.compact_window.update_display(self.main_window.battle_manager.current_enemy)
            self.compact_window.show()
            logging.debug("Compact battle window shown")
            
        except Exception as e:
            logging.error(f"Error showing compact window: {e}")

    def hide_compact_mode(self):
        """Hides the compact battle window."""
        if self.compact_window:
            self.compact_window.hide()
            logging.debug("Compact battle window hidden")

    def handle_event(self, obj, event) -> bool:
        """Handle window events."""
        try:
            if event.type() == event.WindowDeactivate:
                self.handle_window_deactivate()
            elif event.type() == event.WindowActivate:
                self.handle_window_activate()
            return False  # Let the event propagate
        except Exception as e:
            logging.error(f"Error in handle_event: {e}")
            return False

    def cleanup(self):
        """Clean up window manager resources."""
        try:
            logging.info("Cleaning up window manager")
            if self.compact_window:
                self.compact_window.hide()
                self.compact_window.deleteLater()
                self.compact_window = None
            
            self.main_window.removeEventFilter(self.main_window)
            
        except Exception as e:
            logging.error(f"Error during window manager cleanup: {e}")

    def setup_window_signals(self):
        # Connect window state signals
        if self.compact_window:
            self.compact_window.closed.connect(self.handle_compact_window_closed)