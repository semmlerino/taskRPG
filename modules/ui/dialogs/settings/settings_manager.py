"""Settings manager for handling settings persistence."""
import os
import json
import logging
from typing import Dict, Any

class SettingsManager:
    """Manages loading and saving of application settings."""

    def __init__(self, settings_file: str):
        """Initialize settings manager with settings file path."""
        self.settings_file = settings_file
        self.settings: Dict[str, Any] = {}
        
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        try:
            logging.info(f"Attempting to load settings from: {self.settings_file}")

            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                logging.info(f"Successfully loaded settings: {self.settings}")
            else:
                logging.warning(f"Settings file does not exist at: {self.settings_file}")
                self.settings = {}

        except Exception as e:
            logging.error(f"Error loading settings: {e}", exc_info=True)
            self.settings = {}
            
        return self.settings

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to file."""
        try:
            logging.info(f"Preparing to save settings: {settings}")
            logging.info(f"Saving to file: {self.settings_file}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

            # Write settings to file
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)

            self.settings = settings
            logging.info("Settings saved successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to save settings: {e}", exc_info=True)
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value by key."""
        self.settings[key] = value
