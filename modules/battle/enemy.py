import logging
from dataclasses import dataclass

@dataclass
class Enemy:
    """Represents an enemy in battle."""
    name: str
    max_hp: int
    task_name: str
    task_description: str

    def __post_init__(self):
        self.current_hp = self.max_hp
        logging.info(f"Enemy created: {self.name} with HP: {self.max_hp}")

    def take_damage(self, amount: int):
        """Reduce enemy HP by the given amount."""
        self.current_hp = max(0, self.current_hp - amount)
        logging.debug(f"{self.name} takes {amount} damage. Current HP: {self.current_hp}")

    def is_defeated(self) -> bool:
        """Check if enemy is defeated (HP <= 0)."""
        return self.current_hp <= 0

    def heal(self, amount: int):
        """Heal the enemy by the given amount."""
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    @property
    def hp_percentage(self) -> float:
        """Get current HP as a percentage."""
        return (self.current_hp / self.max_hp) * 100 if self.max_hp > 0 else 0

    def get_health_percentage(self) -> float:
        """Legacy method for getting HP percentage."""
        return self.hp_percentage

    @classmethod
    def from_task(cls, task: 'Task') -> 'Enemy':
        """Create an enemy instance from a task"""
        task_count = task.get_random_count()
        return cls(
            name=task.name,
            max_hp=task_count,
            task_name=task.name,
            task_description=task.description
        )
