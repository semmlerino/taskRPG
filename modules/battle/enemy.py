# modules/battle/enemy.py

import logging
from dataclasses import dataclass
from typing import Optional

@dataclass
class Enemy:
    """Represents an enemy in battle."""
    name: str
    max_hp: int
    task_name: str
    task_description: str
    current_hp: Optional[int] = None

    def __post_init__(self):
        """Initialize after creation."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        logging.debug(f"Enemy initialized - Name: {self.name}, Task: {self.task_name}, Max HP: {self.max_hp}, Current HP: {self.current_hp}")

    def take_damage(self, amount: int) -> None:
        """
        Reduce enemy HP by the given amount.
        
        Args:
            amount: Amount of damage to deal
        """
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = max(0, self.current_hp - amount)
        logging.debug(f"{self.name} takes {amount} damage. Current HP: {self.current_hp}")

    def is_defeated(self) -> bool:
        """
        Check if enemy is defeated (HP <= 0).
        
        Returns:
            bool: True if enemy is defeated
        """
        return self.current_hp <= 0

    def heal(self, amount: int) -> None:
        """
        Heal the enemy by the given amount.
        
        Args:
            amount: Amount of healing
        """
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    @property
    def hp_percentage(self) -> float:
        """
        Get current HP as a percentage.
        
        Returns:
            float: HP percentage
        """
        if self.current_hp is None:
            self.current_hp = self.max_hp
        return (self.current_hp / self.max_hp) * 100 if self.max_hp > 0 else 0

def create_enemy_from_task(task_name: str, task_data: dict) -> Enemy:
    """Create an enemy instance from task data."""
    min_hp = task_data.get('min', 1)
    max_hp = task_data.get('max', min_hp)
    
    # Use the max value as the HP to represent total subtasks
    hp = max_hp
    
    logging.debug(f"Creating enemy from task - Name: {task_name}, Min: {min_hp}, Max: {max_hp}, HP: {hp}")
    
    return Enemy(
        name=task_name,
        max_hp=hp,
        current_hp=hp,
        task_name=task_name,
        task_description=task_data.get('description', '')
    )
