# modules/hotkeys.py

import time
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import keyboard
from .constants import HOTKEYS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GlobalHotkeys(QThread):
    """
    Thread class to listen for global hotkeys.
    Handles the registration and emission of signals when hotkeys are pressed.
    """
    normal_attack_signal = pyqtSignal()
    heavy_attack_signal = pyqtSignal()
    toggle_pause_signal = pyqtSignal()
    next_story_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.next_story_enabled = True
        self.attack_hotkeys_enabled = True
        self._next_story_hotkey = None

    def run(self):
        """Registers global hotkeys and listens for them."""
        try:
            self._register_all_hotkeys()
            logging.info("Global hotkeys registered.")

            while self._running:
                time.sleep(0.1)  # Sleep briefly to allow thread to check the running flag
        except Exception as e:
            logging.error(f"Error in GlobalHotkeys thread: {e}")

    def stop(self):
        """Stops the thread and unregisters all hotkeys."""
        self._running = False
        keyboard.unhook_all()
        logging.info("Global hotkeys unregistered.")

    def set_next_story_enabled(self, enabled: bool):
        """Enable/disable the next story hotkey."""
        try:
            logging.info(f"Setting next story hotkey enabled: {enabled}")
            self.next_story_enabled = enabled
            self._register_next_story_hotkey()
        except Exception as e:
            logging.error(f"Error setting next story enabled: {e}")

    def _register_all_hotkeys(self):
        """Register all hotkeys with proper focus handling."""
        try:
            # Unregister existing hotkeys first
            keyboard.unhook_all()
            
            # Attack hotkeys - always active when in battle
            keyboard.add_hotkey(HOTKEYS['normal_attack'],
                              self._handle_normal_attack,
                              suppress=False)
            keyboard.add_hotkey(HOTKEYS['heavy_attack'],
                              self._handle_heavy_attack,
                              suppress=False)
            keyboard.add_hotkey(HOTKEYS['toggle_pause'],
                              lambda: self.toggle_pause_signal.emit(),
                              suppress=False)
            
            # Story navigation - can be disabled
            self._register_next_story_hotkey()
        except Exception as e:
            logging.error(f"Error registering hotkeys: {e}")

    def _handle_normal_attack(self):
        """Handle normal attack with focus check."""
        if self.attack_hotkeys_enabled:
            logging.debug("Normal attack hotkey ('d') pressed")
            self.normal_attack_signal.emit()
            # Don't re-register hotkeys immediately after attack as this can cause race conditions
            # Instead, use a small delay to ensure the signal is processed first
            QTimer.singleShot(50, self._register_all_hotkeys)

    def _handle_heavy_attack(self):
        """Handle heavy attack with focus check."""
        if self.attack_hotkeys_enabled:
            logging.debug("Heavy attack hotkey ('shift+d') pressed")
            self.heavy_attack_signal.emit()
            # Don't re-register hotkeys immediately after attack as this can cause race conditions
            # Instead, use a small delay to ensure the signal is processed first
            QTimer.singleShot(50, self._register_all_hotkeys)

    def set_attack_hotkeys_enabled(self, enabled: bool):
        """Enable/disable attack hotkeys."""
        self.attack_hotkeys_enabled = enabled
        self._register_all_hotkeys()  # Re-register hotkeys when enabling/disabling

    def _register_next_story_hotkey(self):
        """Registers or removes the next story hotkey based on enabled state."""
        try:
            if hasattr(self, '_next_story_hotkey') and self._next_story_hotkey:
                try:
                    keyboard.remove_hotkey(self._next_story_hotkey)
                except Exception as e:
                    logging.debug(f"Could not remove hotkey: {e}")
                self._next_story_hotkey = None
                logging.debug("Next story hotkey removed")
            
            if self.next_story_enabled and 'next_story' in HOTKEYS:
                self._next_story_hotkey = keyboard.add_hotkey(
                    HOTKEYS['next_story'],
                    lambda: self.next_story_signal.emit()
                )
                logging.debug("Next story hotkey registered")
            else:
                logging.debug("Next story hotkey disabled")
        except Exception as e:
            logging.error(f"Error in _register_next_story_hotkey: {e}")