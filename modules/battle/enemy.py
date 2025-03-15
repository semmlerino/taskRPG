"""Enemy management for TaskRPG.

This module contains the Enemy class which represents enemies in battle.
"""

import logging
from dataclasses import dataclass
from typing import Optional

@dataclass
class Enemy:
    """Represents an enemy in battle.
    
    Attributes:
        name: Name of the enemy
        max_hp: Maximum hit points
        task_name: Name of the associated task
        current_hp: Current hit points (defaults to max_hp if None)
        difficulty: Difficulty level of the enemy (affects rewards)
        type: Type of enemy (affects behavior and rewards)
    """
    name: str
    max_hp: int
    task_name: str
    current_hp: Optional[int] = None
    difficulty: str = "normal"
    type: str = "task"

    def __post_init__(self):
        """Initialize derived values after creation."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        logging.debug(f"Enemy initialized - Name: {self.name}, Task: {self.task_name}, Max HP: {self.max_hp}, Current HP: {self.current_hp}")

    def take_damage(self, amount: int) -> None:
        """Reduce enemy HP by damage amount."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = max(0, self.current_hp - amount)
        logging.debug(f"{self.name} takes {amount} damage. Current HP: {self.current_hp}")

    def is_defeated(self) -> bool:
        """Check if enemy is defeated (HP <= 0)."""
        return self.current_hp <= 0

    def heal(self, amount: int) -> None:
        """Heal enemy by specified amount, up to max HP."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        logging.debug(f"{self.name} healed for {amount}. Current HP: {self.current_hp}")