from __future__ import annotations

import os
import json
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Character:
    """Represents a story character with their visual identity."""
    name: str
    description: str
    reference_image_path: str
    traits: Dict[str, str]  # Additional character traits like age, gender, etc.
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "reference_image_path": self.reference_image_path,
            "traits": self.traits
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Character':
        return cls(
            name=data["name"],
            description=data["description"],
            reference_image_path=data["reference_image_path"],
            traits=data["traits"]
        )

class CharacterManager:
    """Manages character generation and consistency using IP-Adapters."""
    
    def __init__(self, story_path: str, image_generator: 'ImageGenerator'):
        self.story_path = story_path
        self.image_generator = image_generator
        self.characters: Dict[str, Character] = {}
        self.characters_dir = os.path.join(os.path.dirname(story_path), "characters")
        os.makedirs(self.characters_dir, exist_ok=True)
        
        # Load existing characters if any
        self._load_characters()
    
    def _load_characters(self):
        """Load existing character data from the characters directory."""
        char_file = os.path.join(self.characters_dir, "characters.json")
        if os.path.exists(char_file):
            with open(char_file, 'r') as f:
                data = json.load(f)
                self.characters = {
                    name: Character.from_dict(char_data)
                    for name, char_data in data.items()
                }
    
    def _save_characters(self):
        """Save character data to disk."""
        char_file = os.path.join(self.characters_dir, "characters.json")
        with open(char_file, 'w') as f:
            json.dump(
                {name: char.to_dict() for name, char in self.characters.items()},
                f, indent=2
            )
    
    def generate_character_image(self, character: Character) -> str:
        """Generate a reference image for a character using the image generator."""
        # Construct a detailed prompt based on character traits
        prompt = f"portrait of {character.description}"
        if "age" in character.traits:
            prompt += f", {character.traits['age']} years old"
        if "gender" in character.traits:
            prompt += f", {character.traits['gender']}"
            
        # Add additional traits to the prompt
        for trait, value in character.traits.items():
            if trait not in ["age", "gender"]:
                prompt += f", {value}"
        
        # Generate the image
        image_path = os.path.join(self.characters_dir, f"{character.name.lower()}_reference.png")
        self.image_generator.generate_image(prompt, save_path=image_path)
        return image_path
    
    def add_character(self, name: str, description: str, traits: Dict[str, str]) -> Character:
        """Add a new character and generate their reference image."""
        if name in self.characters:
            raise ValueError(f"Character {name} already exists")
        
        character = Character(
            name=name,
            description=description,
            reference_image_path="",  # Will be set after generation
            traits=traits
        )
        
        # Generate reference image
        image_path = self.generate_character_image(character)
        character.reference_image_path = image_path
        
        # Save character
        self.characters[name] = character
        self._save_characters()
        return character
    
    def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name."""
        return self.characters.get(name)
    
    def generate_character_scene(self, character_name: str, scene_description: str) -> str:
        """Generate a scene featuring a character while maintaining visual consistency."""
        character = self.get_character(character_name)
        if not character:
            raise ValueError(f"Character {character_name} not found")
        
        # Modify the image generator workflow to use IP-Adapter
        workflow = self.image_generator.default_workflow_json()
        
        # Add IP-Adapter nodes to the workflow
        workflow["nodes"].extend([
            {
                "id": "ip_adapter_loader",
                "type": "IPAdapterLoader",
                "inputs": {
                    "image": character.reference_image_path,
                    "model": "ip-adapter_sd15.safetensors"  # Use appropriate model
                }
            },
            {
                "id": "ip_adapter_apply",
                "type": "IPAdapterApply",
                "inputs": {
                    "model": workflow["nodes"][0]["outputs"]["model"],
                    "ip_adapter": "ip_adapter_loader.ip_adapter",
                    "weight": 0.8  # Adjust weight as needed
                }
            }
        ])
        
        # Update the main model node to use the IP-Adapter output
        for node in workflow["nodes"]:
            if node["type"] == "KSampler":
                node["inputs"]["model"] = "ip_adapter_apply.output"
        
        # Generate the image with the modified workflow
        image_path = os.path.join(
            self.characters_dir,
            f"{character_name.lower()}_{hash(scene_description)[:8]}.png"
        )
        self.image_generator.queue_and_generate(workflow, save_path=image_path)
        return image_path
