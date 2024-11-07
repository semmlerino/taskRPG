# modules/ui/managers/hotkey_manager.py

import logging
import keyboard
from PyQt6.QtCore import QThread, pyqtSignal
from modules.constants import HOTKEYS

class HotkeyManager(QThread):
    """Manages global hotkeys and their signals."""
    
    # Define signals
    normal_attack_signal = pyqtSignal()
    heavy_attack_signal = pyqtSignal()
    toggle_pause_signal = pyqtSignal()
    next_story_signal = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()  # Don't pass parent to QThread constructor
        self.main_window = main_window
        self._running = True
        self.next_story_enabled = True
        self.attack_hotkeys_enabled = True
        self._next_story_hotkey = None
        self.start()  # Start the thread immediately

    def run(self):
        """Register and start listening for hotkeys."""
        try:
            # Register attack hotkeys
            keyboard.add_hotkey(HOTKEYS['normal_attack'], 
                              lambda: self.normal_attack_signal.emit())
            keyboard.add_hotkey(HOTKEYS['heavy_attack'], 
                              lambda: self.heavy_attack_signal.emit())
            keyboard.add_hotkey(HOTKEYS['toggle_pause'], 
                              lambda: self.toggle_pause_signal.emit())
            
            # Register story navigation hotkey
            self._register_next_story_hotkey()
            
            logging.info("Global hotkeys registered")

            while self._running:
                self.msleep(100)  # Use QThread's msleep for better Qt integration
                
        except Exception as e:
            logging.error(f"Error in hotkey thread: {e}")

    def connect_signals(self):
        # Connect to main window or game manager methods
        self.normal_attack_signal.connect(self.main_window.handle_normal_attack)
        self.heavy_attack_signal.connect(self.main_window.handle_heavy_attack)
        self.toggle_pause_signal.connect(self.main_window.handle_pause)
        self.next_story_signal.connect(self.main_window.handle_next_story)

    def set_next_story_enabled(self, enabled: bool):
        """Enable/disable the next story hotkey."""
        try:
            self.next_story_enabled = enabled
            self._register_next_story_hotkey()
            logging.debug(f"Next story hotkey {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logging.error(f"Error setting next story enabled state: {e}")

    def set_attack_hotkeys_enabled(self, enabled: bool):
        """Enable/disable attack hotkeys."""
        try:
            self.attack_hotkeys_enabled = enabled
            logging.debug(f"Attack hotkeys {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logging.error(f"Error setting attack hotkeys state: {e}")

    def _register_next_story_hotkey(self):
        """Register or remove the next story hotkey based on enabled state."""
        try:
            if hasattr(self, '_next_story_hotkey') and self._next_story_hotkey:
                keyboard.remove_hotkey(self._next_story_hotkey)
                self._next_story_hotkey = None
            
            if self.next_story_enabled:
                self._next_story_hotkey = keyboard.add_hotkey(
                    HOTKEYS['next_story'],
                    lambda: self.next_story_signal.emit()
                )
                logging.debug("Next story hotkey registered")
            else:
                logging.debug("Next story hotkey disabled")
        except Exception as e:
            logging.error(f"Error in _register_next_story_hotkey: {e}")

    def cleanup(self):
        """Clean up hotkey manager resources."""
        try:
            logging.info("Cleaning up hotkey manager")
            self._running = False
            # Unhook all keyboard listeners first
            keyboard.unhook_all()
            # Wait for thread with timeout
            self.wait(1000)  # Wait up to 1 second
            if self.isRunning():
                self.terminate()  # Force termination if still running
            logging.info("Global hotkeys unregistered")
        except Exception as e:
            logging.error(f"Error during hotkey manager cleanup: {e}")
            
    def __del__(self):
        """Ensure cleanup on deletion."""
        self.cleanup()

    def reset_window_position(self):
        """Reset window position after shake animation."""
        if hasattr(self, 'original_geometry'):
            self.main_window.setGeometry(self.original_geometry)