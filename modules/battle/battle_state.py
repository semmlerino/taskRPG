# modules/battle/battle_state.py
"""
Enhanced battle state management for TaskRPG.

This module contains an improved BattleState class that serves as the single
source of truth for all battle-related information.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Set, List, Any
import logging
import time
from enum import Enum

from modules.battle.enemy import Enemy
from modules.battle.battle_event_system import BattleEventType, BattleEvent, event_dispatcher

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
    enemy_reference: Optional[Enemy] = None  # Reference to the current enemy object
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
    
    # Attack validation
    attack_cooldown: float = 0  # Cooldown in seconds
    heavy_attack_cooldown: float = 0  # Cooldown for heavy attacks
    
    # Reward settings
    coin_reward: int = 5  # Default coins per victory
    xp_base: int = 100  # Base XP for victories
    xp_multiplier: float = 1.0  # Multiplier for XP calculations
    
    def __post_init__(self):
        """Validate state after initialization."""
        if self.enemy_hp is not None and self.enemy_max_hp is not None:
            self.enemy_hp = max(0, min(self.enemy_hp, self.enemy_max_hp))
    
    def reset(self) -> None:
        """Reset battle state to default values."""
        old_status = self.status
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
        
        # Publish state change event
        if old_status != BattleStatus.INACTIVE:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.STATE_CHANGED,
                {"status": self.status.name}
            ))
        
        logging.debug("Battle state reset to default values")
    
    def update_from_enemy(self, enemy: Enemy) -> None:
        """Update state from enemy object."""
        if enemy is None:
            self.reset()
            return
        
        old_hp = self.enemy_hp
        self.enemy_reference = enemy    
        self.enemy_hp = enemy.current_hp
        self.enemy_max_hp = enemy.max_hp
        self.enemy_name = enemy.name
        self.task_name = enemy.task_name
        
        # Publish HP update event if changed
        if old_hp != self.enemy_hp:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.HP_UPDATED,
                {
                    "current_hp": self.enemy_hp,
                    "max_hp": self.enemy_max_hp
                }
            ))
        
        logging.debug(f"Battle state updated from enemy: {enemy.name}")
    
    def start_battle(self, enemy: Enemy) -> None:
        """Start a battle with the given enemy."""
        # Always force status to ACTIVE when starting a battle
        old_status = self.status
        self.status = BattleStatus.ACTIVE
        self.update_from_enemy(enemy)
        self.battle_start_time = time.time()
        self.attacks_performed = 0
        self.turns_taken = 0
        self.last_attack_type = ""
        self.xp_gained = 0
        self.paused_time = None
        self.total_pause_duration = 0
        
        # Publish battle start event
        event_dispatcher.publish(BattleEvent(
            BattleEventType.BATTLE_START,
            {
                "enemy_name": self.enemy_name,
                "enemy_hp": self.enemy_hp,
                "enemy_max_hp": self.enemy_max_hp,
                "task_name": self.task_name
            }
        ))
        
        # Publish state change event if status changed
        if old_status != self.status:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.STATE_CHANGED,
                {"status": self.status.name}
            ))
        
        logging.debug(f"Battle started with enemy: {enemy.name}")
    
    def end_battle(self) -> None:
        """End the current battle."""
        old_status = self.status
        self.status = BattleStatus.COMPLETE
        
        # Keep enemy reference for event data
        enemy_name = self.enemy_name if self.enemy_reference else "Unknown"
        enemy_hp = self.enemy_hp
        enemy_max_hp = self.enemy_max_hp
        
        # Clear enemy reference
        self.enemy_reference = None
        
        # Publish battle end event
        event_dispatcher.publish(BattleEvent(
            BattleEventType.BATTLE_END,
            {
                "enemy_name": enemy_name,
                "final_hp": enemy_hp,
                "max_hp": enemy_max_hp,
                "xp_gained": self.xp_gained
            }
        ))
        
        # Publish state change event if status changed
        if old_status != self.status:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.STATE_CHANGED,
                {"status": self.status.name}
            ))
        
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
    
    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.enemy_reference
    
    def record_attack(self, attack_type: str) -> None:
        """Record an attack in the battle stats."""
        self.last_attack_time = time.time()
        self.attacks_performed += 1
        self.turns_taken += 1
        self.last_attack_type = attack_type
        
        # Calculate damage for event
        is_heavy = attack_type == "heavy"
        damage = 0  # Will be set by the battle manager
        
        # Publish attack performed event
        event_dispatcher.publish(BattleEvent(
            BattleEventType.ATTACK_PERFORMED,
            {
                "attack_type": attack_type,
                "is_heavy": is_heavy,
                "damage": damage,
                "attacks_performed": self.attacks_performed,
                "turns_taken": self.turns_taken
            }
        ))
        
        logging.debug(f"Recorded {attack_type} attack, total attacks: {self.attacks_performed}")
    
    def update_enemy_hp(self, new_hp: int) -> None:
        """Update the enemy's HP."""
        old_hp = self.enemy_hp
        self.enemy_hp = max(0, new_hp)
        
        # Update enemy reference if it exists
        if self.enemy_reference:
            self.enemy_reference.current_hp = self.enemy_hp
        
        # Check if enemy is defeated
        is_defeated = self.enemy_hp <= 0
        
        # Publish HP update event
        event_dispatcher.publish(BattleEvent(
            BattleEventType.HP_UPDATED,
            {
                "old_hp": old_hp,
                "current_hp": self.enemy_hp,
                "max_hp": self.enemy_max_hp,
                "change": self.enemy_hp - old_hp
            }
        ))
        
        # Publish enemy defeated event if applicable
        if is_defeated and old_hp > 0:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ENEMY_DEFEATED,
                {
                    "enemy_name": self.enemy_name,
                    "task_name": self.task_name
                }
            ))
        
        logging.debug(f"Enemy HP updated from {old_hp} to {self.enemy_hp}")
    
    def pause(self) -> None:
        """Pause the battle."""
        if self.status == BattleStatus.ACTIVE:
            old_status = self.status
            self.status = BattleStatus.PAUSED
            self.paused_time = time.time()
            
            # Publish pause event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.BATTLE_PAUSED,
                {"paused_time": self.paused_time}
            ))
            
            # Publish state change event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.STATE_CHANGED,
                {"status": self.status.name}
            ))
            
            logging.debug(f"Battle paused at {self.paused_time}")
    
    def unpause(self) -> None:
        """Unpause the battle."""
        if self.status == BattleStatus.PAUSED:
            old_status = self.status
            self.status = BattleStatus.ACTIVE
            
            # Calculate pause duration
            pause_duration = 0
            if self.paused_time:
                pause_duration = time.time() - self.paused_time
                self.total_pause_duration += pause_duration
                self.paused_time = None
            
            # Publish resume event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.BATTLE_RESUMED,
                {
                    "pause_duration": pause_duration,
                    "total_pause_duration": self.total_pause_duration
                }
            ))
            
            # Publish state change event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.STATE_CHANGED,
                {"status": self.status.name}
            ))
            
            logging.debug(f"Battle unpaused. Pause duration: {pause_duration:.2f}s, Total: {self.total_pause_duration:.2f}s")
    
    def toggle_pause(self) -> None:
        """Toggle pause state."""
        if self.is_paused():
            self.unpause()
        else:
            self.pause()
        
        # Publish toggle event after state change
        event_dispatcher.publish(BattleEvent(
            BattleEventType.PAUSE_TOGGLED,
            {"is_paused": self.is_paused()}
        ))
    
    def mark_battle_complete(self, node_key: str) -> None:
        """Mark a battle node as completed."""
        self.completed_battle_nodes.add(node_key)
        logging.debug(f"Marked battle node '{node_key}' as completed")
    
    def is_battle_complete(self, node_key: str) -> bool:
        """Check if a battle node is marked as completed."""
        return node_key in self.completed_battle_nodes
    
    def record_victory(self, xp_gained: int) -> None:
        """Record a victory with XP gained."""
        old_status = self.status
        self.status = BattleStatus.COMPLETE
        self.xp_gained = xp_gained
        
        # Publish victory event
        event_dispatcher.publish(BattleEvent(
            BattleEventType.VICTORY,
            {
                "xp_gained": xp_gained,
                "coin_reward": self.coin_reward,
                "turns_taken": self.turns_taken,
                "battle_duration": self.get_battle_duration(),
                "enemy_name": self.enemy_name,
                "task_name": self.task_name
            }
        ))
        
        # Publish state change event if status changed
        if old_status != self.status:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.STATE_CHANGED,
                {"status": self.status.name}
            ))
        
        logging.debug(f"Victory recorded with {xp_gained} XP gained")
    
    def set_reward_parameters(self, coin_reward: int, xp_base: int, xp_multiplier: float) -> None:
        """Set reward parameters for battles."""
        self.coin_reward = coin_reward
        self.xp_base = xp_base
        self.xp_multiplier = xp_multiplier
        logging.debug(f"Set reward parameters: coins={coin_reward}, xp_base={xp_base}, xp_multiplier={xp_multiplier}")
    
    def validate_attack(self, is_heavy: bool = False) -> bool:
        """
        Validate if an attack can be performed.
        
        Args:
            is_heavy: Whether this is a heavy attack
            
        Returns:
            bool: True if attack is valid, False otherwise
        """
        # Check battle status
        if not self.is_active():
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ATTACK_VALIDATED,
                {
                    "is_valid": False,
                    "reason": "battle_not_active",
                    "is_heavy": is_heavy
                }
            ))
            return False
        
        # Check if enemy exists and has HP
        if not self.enemy_reference or self.enemy_hp <= 0:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ATTACK_VALIDATED,
                {
                    "is_valid": False,
                    "reason": "no_enemy",
                    "is_heavy": is_heavy
                }
            ))
            return False
        
        # Check if battle is paused
        if self.is_paused():
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ATTACK_VALIDATED,
                {
                    "is_valid": False,
                    "reason": "battle_paused",
                    "is_heavy": is_heavy
                }
            ))
            return False
        
        # Check cooldown
        current_time = time.time()
        if is_heavy and current_time - self.last_attack_time < self.heavy_attack_cooldown:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ATTACK_VALIDATED,
                {
                    "is_valid": False,
                    "reason": "heavy_cooldown",
                    "is_heavy": is_heavy,
                    "cooldown_remaining": self.heavy_attack_cooldown - (current_time - self.last_attack_time)
                }
            ))
            return False
        elif current_time - self.last_attack_time < self.attack_cooldown:
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ATTACK_VALIDATED,
                {
                    "is_valid": False,
                    "reason": "cooldown",
                    "is_heavy": is_heavy,
                    "cooldown_remaining": self.attack_cooldown - (current_time - self.last_attack_time)
                }
            ))
            return False
        
        # All checks passed
        event_dispatcher.publish(BattleEvent(
            BattleEventType.ATTACK_VALIDATED,
            {
                "is_valid": True,
                "is_heavy": is_heavy
            }
        ))
        return True
    
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