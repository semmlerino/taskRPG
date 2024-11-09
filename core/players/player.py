import logging
from dataclasses import dataclass
from .inventory import Inventory

@dataclass
class PlayerStats:
    """Player statistics."""
    level: int = 1
    experience: int = 0
    experience_to_next_level: int = 100

class Player:
    """Represents the player character."""
    def __init__(self):
        self.stats = PlayerStats()
        self.inventory = Inventory()
        logging.info(f"Player created: Level {self.stats.level}, XP: {self.stats.experience}")

    def gain_experience(self, amount: int):
        """Add experience points and handle leveling."""
        self.stats.experience += amount
        logging.info(f"Player gains {amount} XP. Total XP: {self.stats.experience}")
        
        while self.stats.experience >= self.stats.experience_to_next_level:
            self.level_up()

    def level_up(self):
        """Handle player level up."""
        self.stats.level += 1
        self.stats.experience -= self.stats.experience_to_next_level
        self.stats.experience_to_next_level = int(self.stats.experience_to_next_level * 1.5)
        logging.info(f"Player leveled up! New level: {self.stats.level}")

    def get_level_progress(self) -> float:
        """Get level progress as a percentage."""
        return (self.stats.experience / self.stats.experience_to_next_level) * 100
