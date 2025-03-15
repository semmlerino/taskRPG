"""Battle callbacks management for TaskRPG.

This module contains the BattleCallbacks class which manages
callback functions for battle events.
"""

from dataclasses import dataclass
from typing import Optional, Callable
import logging

@dataclass
class BattleCallbacks:
    """Container for battle event callbacks.
    
    Attributes:
        on_battle_start: Called when battle starts
        on_battle_end: Called when battle ends
        on_attack: Called when attack performed
        on_state_change: Called when battle state changes
        on_victory: Called on victory
    """
    on_battle_start: Optional[Callable] = None
    on_battle_end: Optional[Callable] = None
    on_attack: Optional[Callable] = None
    on_state_change: Optional[Callable] = None
    on_victory: Optional[Callable] = None
    
    def register(self,
                on_battle_start: Optional[Callable] = None,
                on_battle_end: Optional[Callable] = None,
                on_attack: Optional[Callable] = None,
                on_state_change: Optional[Callable] = None,
                on_victory: Optional[Callable] = None) -> None:
        """Register callback functions for battle events.
        
        Args:
            on_battle_start: Called when battle starts
            on_battle_end: Called when battle ends
            on_attack: Called when attack performed
            on_state_change: Called when battle state changes
            on_victory: Called on victory
        """
        try:
            if on_battle_start is not None:
                self.on_battle_start = on_battle_start
            if on_battle_end is not None:
                self.on_battle_end = on_battle_end
            if on_attack is not None:
                self.on_attack = on_attack
            if on_state_change is not None:
                self.on_state_change = on_state_change
            if on_victory is not None:
                self.on_victory = on_victory
                
            logging.debug("Battle callbacks registered")
            
        except Exception as e:
            logging.error(f"Error registering battle callbacks: {e}")
    
    def reset(self) -> None:
        """Reset all callbacks to None."""
        self.on_battle_start = None
        self.on_battle_end = None
        self.on_attack = None
        self.on_state_change = None
        self.on_victory = None
        logging.debug("Battle callbacks reset")