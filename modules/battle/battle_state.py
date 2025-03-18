"""
File: modules/battle/battle_state.py
Battle state management for TaskRPG.

This module contains classes for managing battle state, including
the BattleState class which tracks the current state of a battle.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Set
import logging
import time
from enum import Enum

class BattleStatus(Enum):
    """Status of a battle."""
    INACTIVE = 0
    ACTIVE = 1
    PAUSED = 2
    COMPLETE = 3

@dataclass
class BattleState:
    """
    Tracks the current state of a battle.
    
    This class is the single source of truth for all battle state data,
    ensuring consistency throughout the battle system.
    """
    # Battle status
    status: BattleStatus = BattleStatus.INACTIVE
    
    # Enemy state
    enemy_reference: Optional['Enemy'] = None  # Reference to the current enemy object
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_name: str = ""
    task_name: str = ""
    
    # Battle timing
    battle_start_time: float = 0
    last_attack_time: float = 0
    paused_time: Optional[float] = None
    total_pause_duration: float = 0
    
    # Battle statistics
    attacks_performed: int = 0
    turns_taken: int = 0
    last_attack_type: str = ""
    xp_gained: int = 0
    
    # Tracking
    completed_battle_nodes: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Validate state after initialization."""
        if self.enemy_hp is not None and self.enemy_max_hp is not None:
            self.enemy_hp = max(0, min(self.enemy_hp, self.enemy_max_hp))
    
    def reset(self) -> None:
        """Reset battle state to default values."""
        self.status = BattleStatus.INACTIVE
        self.enemy_reference = None
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
        
        self.enemy_reference = enemy    
        self.enemy_hp = enemy.current_hp
        self.enemy_max_hp = enemy.max_hp
        self.enemy_name = enemy.name
        self.task_name = enemy.task_name
        logging.debug(f"Battle state updated from enemy: {enemy.name}")
    
    def start_battle(self, enemy) -> None:
        """Start a battle with the given enemy."""
        # Always force status to ACTIVE when starting a battle
        self.status = BattleStatus.ACTIVE
        self.update_from_enemy(enemy)
        self.battle_start_time = time.time()
        self.attacks_performed = 0
        self.turns_taken = 0
        self.last_attack_type = ""
        self.xp_gained = 0
        self.paused_time = None
        self.total_pause_duration = 0
        logging.debug(f"Battle started with enemy: {enemy.name}")
    
    def end_battle(self) -> None:
        """End the current battle."""
        self.status = BattleStatus.COMPLETE
        self.enemy_reference = None
        logging.debug("Battle marked as complete")
    
    def is_active(self) -> bool:
        """Check if a battle is active (not paused or completed)."""
        return self.status == BattleStatus.ACTIVE
    
    def is_paused(self) -> bool:
        """Check if a battle is currently paused."""
        return self.status == BattleStatus.PAUSED
    
    def is_in_battle(self) -> bool:
        """Check if currently in an active battle with an enemy."""
        return (self.status in (BattleStatus.ACTIVE, BattleStatus.PAUSED) and 
                self.enemy_reference is not None and 
                self.enemy_hp > 0)
    
    def get_current_enemy(self) -> Optional['Enemy']:
        """Get the current enemy if any."""
        return self.enemy_reference
    
    def record_attack(self, attack_type: str) -> None:
        """Record an attack in the battle stats."""
        self.last_attack_time = time.time()
        self.attacks_performed += 1
        self.turns_taken += 1
        self.last_attack_type = attack_type
        logging.debug(f"Recorded {attack_type} attack, total attacks: {self.attacks_performed}")
    
    def update_enemy_hp(self, new_hp: int) -> None:
        """Update the enemy's HP."""
        old_hp = self.enemy_hp
        self.enemy_hp = max(0, new_hp)
        if self.enemy_reference:
            self.enemy_reference.current_hp = self.enemy_hp
        logging.debug(f"Enemy HP updated from {old_hp} to {self.enemy_hp}")
    
    def pause(self) -> None:
        """Pause the battle."""
        if self.status == BattleStatus.ACTIVE:
            self.status = BattleStatus.PAUSED
            self.paused_time = time.time()
            logging.debug(f"Battle paused at {self.paused_time}")
    
    def unpause(self) -> None:
        """Unpause the battle."""
        if self.status == BattleStatus.PAUSED:
            self.status = BattleStatus.ACTIVE
            if self.paused_time:
                pause_duration = time.time() - self.paused_time
                self.total_pause_duration += pause_duration
                self.paused_time = None
                logging.debug(f"Battle unpaused. Pause duration: {pause_duration:.2f}s, Total: {self.total_pause_duration:.2f}s")
    
    def mark_battle_complete(self, node_key: str) -> None:
        """Mark a battle node as completed."""
        self.completed_battle_nodes.add(node_key)
        logging.debug(f"Marked battle node '{node_key}' as completed")
    
    def is_battle_complete(self, node_key: str) -> bool:
        """Check if a battle node is marked as completed."""
        return node_key in self.completed_battle_nodes
    
    def record_victory(self, xp_gained: int) -> None:
        """Record a victory with XP gained."""
        self.status = BattleStatus.COMPLETE
        self.xp_gained = xp_gained
        logging.debug(f"Victory recorded with {xp_gained} XP gained")
    
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