from dataclasses import dataclass
from typing import Optional
import random

@dataclass
class Task:
    """Represents a task that can be assigned to enemies."""
    name: str
    min_steps: int
    max_steps: int
    active: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        """Validate task data after initialization."""
        self.min_steps = max(1, int(self.min_steps))
        self.max_steps = max(self.min_steps, int(self.max_steps))
        self.active = bool(self.active)

    @property
    def is_active(self) -> bool:
        return self.active

    def get_random_steps(self) -> int:
        """Get random number of steps between min and max."""
        return random.randint(self.min_steps, self.max_steps)

    def to_dict(self) -> dict:
        """Convert task to dictionary format."""
        return {
            "min": self.min_steps,
            "max": self.max_steps,
            "active": self.active,
            "description": self.description
        }

    @staticmethod
    def from_dict(name: str, data: dict) -> 'Task':
        """Create a Task from dictionary data."""
        return Task(
            name=name,
            min_steps=data.get("min", 1),
            max_steps=data.get("max", 1),
            active=data.get("active", True),
            description=data.get("description")
        )
