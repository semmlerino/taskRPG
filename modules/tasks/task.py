from dataclasses import dataclass
from typing import Optional
from random import randint

@dataclass
class Task:
    name: str
    min_count: int
    max_count: int
    active: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        """Validate and fix task data after initialization"""
        self.min_count = max(1, int(self.min_count))
        self.max_count = max(self.min_count, int(self.max_count))
        self.active = bool(self.active)

    @property
    def is_active(self) -> bool:
        """Property to check if task is active"""
        return self.active

    def get_random_count(self) -> int:
        """Get a random count between min and max values"""
        return randint(self.min_count, self.max_count)

    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'Task':
        """Create a Task instance from a dictionary"""
        return cls(
            name=name,
            min_count=data.get('min', 1),
            max_count=data.get('max', 1),
            active=data.get('active', True),
            description=data.get('description')
        )

    def to_dict(self) -> dict:
        """Convert Task to dictionary format"""
        return {
            'min': self.min_count,
            'max': self.max_count,
            'active': self.active,
            'description': self.description
        }

    def get_task_count(self) -> int:
        """Get the task count that will be used as HP."""
        return self.get_random_count()

    def get_hp(self) -> int:
        """Get the HP value based on task count."""
        return max(1, self.get_task_count())
