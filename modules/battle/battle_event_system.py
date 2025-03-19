# modules/battle/battle_event_system.py
"""
Battle event system for TaskRPG.

This module introduces a proper event system for battle-related events,
enabling better decoupling between battle logic and UI components.
"""

import logging
from enum import Enum, auto
from typing import Dict, List, Callable, Any, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BattleEventType(Enum):
    """Types of battle events."""
    BATTLE_START = auto()
    BATTLE_END = auto()
    ATTACK_PERFORMED = auto()
    ATTACK_VALIDATED = auto()
    STATE_CHANGED = auto()
    ENEMY_DEFEATED = auto()
    PAUSE_TOGGLED = auto()
    BATTLE_PAUSED = auto()
    BATTLE_RESUMED = auto()
    VICTORY = auto()
    HP_UPDATED = auto()
    UI_UPDATE_REQUESTED = auto()
    ERROR_OCCURRED = auto()

class BattleEvent:
    """Class representing a battle event with data."""
    
    def __init__(self, event_type: BattleEventType, data: Optional[Dict[str, Any]] = None):
        """
        Initialize a battle event.
        
        Args:
            event_type: Type of the event
            data: Optional dictionary with event data
        """
        self.event_type = event_type
        self.data = data or {}
        
    def __str__(self) -> str:
        """String representation of the event."""
        return f"BattleEvent({self.event_type.name}, data={self.data})"

class BattleEventDispatcher:
    """
    Event dispatcher for battle events.
    
    Handles event subscription and publishing, allowing components
    to communicate without direct dependencies.
    """
    
    def __init__(self):
        """Initialize the event dispatcher."""
        self._subscribers: Dict[BattleEventType, List[Callable[[BattleEvent], None]]] = {}
        self._logging_enabled = True
        
    def subscribe(self, event_type: BattleEventType, callback: Callable[[BattleEvent], None]) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        if self._logging_enabled:
            logger.debug(f"Subscribed to {event_type.name} events")
    
    def unsubscribe(self, event_type: BattleEventType, callback: Callable[[BattleEvent], None]) -> None:
        """
        Unsubscribe from a specific event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            if self._logging_enabled:
                logger.debug(f"Unsubscribed from {event_type.name} events")
    
    def publish(self, event: BattleEvent) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: The event to publish
        """
        if event.event_type in self._subscribers:
            if self._logging_enabled:
                logger.debug(f"Publishing event: {event}")
            
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.event_type.name}: {e}")
    
    def clear_subscribers(self) -> None:
        """Clear all event subscribers."""
        self._subscribers.clear()
        logger.info("All event subscribers cleared")
    
    def set_logging(self, enabled: bool) -> None:
        """Enable or disable event logging."""
        self._logging_enabled = enabled

# Create a global event dispatcher instance
event_dispatcher = BattleEventDispatcher()