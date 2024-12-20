import json
import os
import re
from typing import Dict

class CharacterDescriptionManager:
    def __init__(self):
        self.descriptions: Dict[str, str] = {}

    def load_descriptions_from_story(self, story_data: Dict):
        """Load character descriptions from story data"""
        # Reset descriptions for this story
        self.descriptions = {}
        
        # Check for top-level character_descriptions dictionary
        if "character_descriptions" in story_data and isinstance(story_data["character_descriptions"], dict):
            # Convert all keys to lowercase for case-insensitive matching
            self.descriptions = {
                name.lower(): desc 
                for name, desc in story_data["character_descriptions"].items()
            }
            return

        # Fallback: look for character descriptions in individual nodes
        for node_key, node_data in story_data.items():
            if isinstance(node_data, dict):
                if "character_description" in node_data:
                    char_name = node_data.get("name", "").lower()
                    if char_name:
                        self.descriptions[char_name] = node_data["character_description"]

    def expand_character_descriptions(self, prompt: str) -> str:
        """
        Replace character names in the prompt with their full descriptions.
        If a character name is found but has no description, it is left unchanged.
        """
        if not prompt or not self.descriptions:
            return prompt

        # Create a pattern that matches any of the character names
        # Use word boundaries to ensure we match whole words only
        pattern = r'\b(' + '|'.join(re.escape(name) for name in self.descriptions.keys()) + r')\b'
        
        def replace_match(match):
            character_name = match.group(0).lower()  # Convert to lowercase for matching
            return self.descriptions.get(character_name, match.group(0))

        # Make the replacement case-insensitive by converting prompt names to lowercase
        result = prompt
        for name, desc in self.descriptions.items():
            # Use word boundaries and case-insensitive matching
            pattern = fr'\b{re.escape(name)}\b'
            result = re.sub(pattern, desc, result, flags=re.IGNORECASE)
        
        return result

# Create a singleton instance
description_manager = CharacterDescriptionManager()
