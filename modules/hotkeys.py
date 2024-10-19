# modules/hotkeys.py

import time
import logging
from PyQt5.QtCore import QThread, pyqtSignal
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
    # Removed open_settings_signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        """Registers global hotkeys and listens for them."""
        try:
            keyboard.add_hotkey(HOTKEYS['normal_attack'], lambda: self.normal_attack_signal.emit())
            keyboard.add_hotkey(HOTKEYS['heavy_attack'], lambda: self.heavy_attack_signal.emit())
            keyboard.add_hotkey(HOTKEYS['toggle_pause'], lambda: self.toggle_pause_signal.emit())
            keyboard.add_hotkey(HOTKEYS['next_story'], lambda: self.next_story_signal.emit())
            # Removed open_settings hotkey
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

