from dataclasses import dataclass
from typing import Optional
from random import randint
import time

@dataclass
class Task:
    name: str
    min_count: int
    max_count: int
    active: bool = True
    description: Optional[str] = None
    is_daily: bool = False
    is_weekly: bool = False
    next_activation_time: Optional[float] = None
    manually_deactivated: bool = False

    def __post_init__(self):
        """Validate and fix task data after initialization"""
        self.min_count = max(1, int(self.min_count))
        self.max_count = max(self.min_count, int(self.max_count))
        self.active = bool(self.active)
        self.is_daily = bool(self.is_daily)
        self.is_weekly = bool(self.is_weekly)
        self.manually_deactivated = bool(self.manually_deactivated)
        
        # Ensure task can't be both daily and weekly
        if self.is_daily and self.is_weekly:
            self.is_weekly = False
            
        # Clear next_activation_time if task is manually deactivated
        if self.manually_deactivated:
            self.next_activation_time = None

    @property
    def is_active(self) -> bool:
        """Property to check if task is active"""
        # If manually deactivated, always return False
        if self.manually_deactivated:
            return False
            
        # For daily/weekly tasks, check for reactivation
        if (self.is_daily or self.is_weekly) and not self.active and self.next_activation_time:
            if time.time() >= self.next_activation_time:
                self.active = True
                self.next_activation_time = None
                
        return self.active

    def deactivate(self, manual: bool = False):
        """Deactivate the task and set next activation time if it's daily/weekly"""
        self.active = False
        
        if manual:
            # Manual deactivation overrides everything
            self.manually_deactivated = True
            self.next_activation_time = None
            return
            
        # Only set next_activation_time if not manually deactivated
        if not self.manually_deactivated:
            current_time = time.time()
            if self.is_daily:
                self.next_activation_time = current_time + (12 * 3600)  # 12 hours
            elif self.is_weekly:
                self.next_activation_time = current_time + (7 * 24 * 3600)  # 7 days
        else:
            self.next_activation_time = None

    def activate(self, manual: bool = False):
        """Activate the task"""
        if manual:
            # Manual activation clears manual deactivation flag
            self.manually_deactivated = False
            
        self.active = True
        self.next_activation_time = None

    def check_reactivation(self) -> bool:
        """Check and handle task reactivation if needed. Returns True if reactivated."""
        # Don't reactivate if manually deactivated
        if self.manually_deactivated:
            return False
            
        if (self.is_daily or self.is_weekly) and not self.active and self.next_activation_time:
            if time.time() >= self.next_activation_time:
                self.active = True
                self.next_activation_time = None
                return True
        return False

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
            description=data.get('description'),
            is_daily=data.get('is_daily', False),
            is_weekly=data.get('is_weekly', False),
            next_activation_time=data.get('next_activation_time'),
            manually_deactivated=data.get('manually_deactivated', False)
        )

    def to_dict(self) -> dict:
        """Convert Task to dictionary format"""
        return {
            'min': self.min_count,
            'max': self.max_count,
            'active': self.active,
            'description': self.description,
            'is_daily': self.is_daily,
            'is_weekly': self.is_weekly,
            'next_activation_time': self.next_activation_time,
            'manually_deactivated': self.manually_deactivated
        }

    def get_task_count(self) -> int:
        """Get the task count that will be used as HP."""
        return self.get_random_count()

    def get_hp(self) -> int:
        """Get the HP value based on task count."""
        return max(1, self.get_task_count())
