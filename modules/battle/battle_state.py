"""Battle state management for TaskRPG.

This module contains classes for managing battle state, including
the BattleState class which tracks the current state of a battle.
"""

from dataclasses import dataclass
from typing import Optional
import logging
import time

@dataclass
class BattleState:
    """
    Tracks the current state of a battle.
    
    Attributes:
        is_active: Whether a battle is currently in progress
        enemy_hp: Current enemy HP
        enemy_max_hp: Maximum enemy HP
        enemy_name: Name of current enemy
        task_name: Name of associated task
        battle_start_time: Timestamp when battle started
        last_attack_time: Timestamp of last attack
        attacks_performed: Number of attacks performed
        turns_taken: Number of turns in battle
        last_attack_type: Type of last attack performed
        xp_gained: Amount of XP gained in battle
        paused_time: Timestamp when battle was paused
        total_pause_duration: Total duration of pauses in current battle
    """
    is_active: bool = False
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_name: str = ""
    task_name: str = ""
    battle_start_time: float = 0
    last_attack_time: float = 0
    attacks_performed: int = 0
    turns_taken: int = 0
    last_attack_type: str = ""
    xp_gained: int = 0
    paused_time: Optional[float] = None
    total_pause_duration: float = 0

    def __post_init__(self):
        """Validate state after initialization."""
        if self.enemy_hp is not None and self.enemy_max_hp is not None:
            self.enemy_hp = max(0, min(self.enemy_hp, self.enemy_max_hp))
    
    def reset(self) -> None:
        """Reset battle state to default values."""
        self.is_active = False
        self.enemy_hp = 0
        self.enemy_max_hp = 0
        self.enemy_name = ""
        self.task_name = ""
        self.battle_start_time = 0
        self.last_attack_time = 0
        self.attacks_performed = 0
        self.turns_taken = 0
        self.last_attack_type = ""
        self.xp_gained = 0
        self.paused_time = None
        self.total_pause_duration = 0
        logging.debug("Battle state reset to default values")
    
    def update_from_enemy(self, enemy) -> None:
        """Update state from enemy object."""
        if enemy is None:
            self.reset()
            return
            
        self.enemy_hp = enemy.current_hp
        self.enemy_max_hp = enemy.max_hp
        self.enemy_name = enemy.name
        self.task_name = enemy.task_name
        logging.debug(f"Battle state updated from enemy: {enemy.name}")
        
    def is_in_battle(self) -> bool:
        """Check if a battle is currently active."""
        return self.is_active and self.enemy_hp > 0
        
    def pause(self) -> None:
        """Pause the battle and record the pause time."""
        if not self.paused_time:
            self.paused_time = time.time()
            logging.debug(f"Battle paused at {self.paused_time}")
            
    def unpause(self) -> None:
        """Unpause the battle and update the total pause duration."""
        if self.paused_time:
            pause_duration = time.time() - self.paused_time
            self.total_pause_duration += pause_duration
            self.paused_time = None
            logging.debug(f"Battle unpaused. Pause duration: {pause_duration:.2f}s, Total: {self.total_pause_duration:.2f}s")
            
    def get_battle_duration(self) -> float:
        """Get the total duration of the battle, excluding paused time."""
        if not self.battle_start_time:
            return 0.0
            
        current_time = time.time()
        raw_duration = current_time - self.battle_start_time
        
        # Calculate pause adjustment
        pause_adjustment = self.total_pause_duration
        if self.paused_time:
            pause_adjustment += (current_time - self.paused_time)
            
        return max(0.0, raw_duration - pause_adjustment)