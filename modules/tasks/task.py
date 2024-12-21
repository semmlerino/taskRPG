from dataclasses import dataclass
from typing import Optional
from random import randint
import time
from datetime import datetime, time as dt_time
import logging

@dataclass
class Task:
    """Task class representing a task with its properties."""
    name: str
    min_count: int
    max_count: int
    active: bool = True
    is_daily: bool = False
    is_weekly: bool = False
    next_activation_time: Optional[float] = None
    manually_deactivated: bool = False
    count: int = 0  # New field for usage count
    activation_time: Optional[dt_time] = None  # New field for daily activation time
    muted_until: Optional[float] = None  # Timestamp when task should be unmuted

    def __post_init__(self):
        """Validate and fix task data after initialization"""
        self.min_count = max(1, int(self.min_count))
        self.max_count = max(self.min_count, int(self.max_count))
        self.active = bool(self.active)
        self.is_daily = bool(self.is_daily)
        self.is_weekly = bool(self.is_weekly)
        self.manually_deactivated = bool(self.manually_deactivated)
        self.count = max(0, int(self.count))  # Ensure count is non-negative integer
        
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
            
        # Check activation time if set
        if self.activation_time and not self.active:
            current_time = datetime.now().time()
            if (current_time.hour == self.activation_time.hour and 
                current_time.minute == self.activation_time.minute):
                self.active = True
                self.activation_time = None  # Clear activation time after activating
                logging.info(f"Task '{self.name}' activated at scheduled time. Activation time cleared.")
                return True
            return False
            
        # Check if task is muted
        if self.muted_until is not None:
            current_time = time.time()
            if current_time >= self.muted_until:
                self.muted_until = None  # Clear mute if time has passed
            else:
                return False  # Still muted
            
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

    def set_activation_time(self, time_str: Optional[str] = None):
        """Set the activation time for this task
        
        Args:
            time_str: Time string in HH:MM format, or None to clear
        """
        if time_str is None:
            self.activation_time = None
            logging.info(f"Activation time cleared for task '{self.name}'")
            return
            
        try:
            hour, minute = map(int, time_str.split(':'))
            self.activation_time = dt_time(hour=hour, minute=minute)
            self.active = False  # Deactivate until activation time
            self.manually_deactivated = False  # Clear manual deactivation
            logging.info(f"Activation time set to {time_str} for task '{self.name}'")
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid time format for task '{self.name}': {e}")

    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'Task':
        """Create a Task instance from a dictionary"""
        activation_time = None
        if 'activation_time' in data:
            try:
                hour, minute = map(int, data['activation_time'].split(':'))
                activation_time = dt_time(hour=hour, minute=minute)
            except (ValueError, TypeError, AttributeError):
                activation_time = None
                
        return cls(
            name=name,
            min_count=data.get('min', 1),
            max_count=data.get('max', 1),
            active=data.get('active', True),
            is_daily=data.get('is_daily', False),
            is_weekly=data.get('is_weekly', False),
            next_activation_time=data.get('next_activation_time'),
            manually_deactivated=data.get('manually_deactivated', False),
            count=data.get('count', 0),
            activation_time=activation_time,
            muted_until=data.get('muted_until')
        )

    def to_dict(self) -> dict:
        """Convert task to dictionary for serialization"""
        data = {
            'min': self.min_count,
            'max': self.max_count,
            'active': self.active,
            'is_daily': self.is_daily,
            'is_weekly': self.is_weekly,
            'next_activation_time': self.next_activation_time,
            'manually_deactivated': self.manually_deactivated,
            'count': self.count,
            'muted_until': self.muted_until
        }
        if self.activation_time:
            data['activation_time'] = f"{self.activation_time.hour:02d}:{self.activation_time.minute:02d}"
        return data

    def get_task_count(self) -> int:
        """Get the task count that will be used as HP."""
        return self.get_random_count()

    def get_hp(self) -> int:
        """Get the HP value based on task count."""
        return max(1, self.get_task_count())

    def mute_until(self, mute_datetime: datetime):
        """Mute the task until the specified datetime
        
        Args:
            mute_datetime: Datetime when the task should be unmuted
        """
        self.muted_until = mute_datetime.timestamp()
        logging.info(f"Task '{self.name}' muted until {mute_datetime}")

    def unmute(self):
        """Unmute the task immediately"""
        self.muted_until = None
        logging.info(f"Task '{self.name}' unmuted")
