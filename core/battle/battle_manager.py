import logging
import random
from typing import Optional, Callable
from .battle_state import BattleState
from modules.battle.enemy import Enemy
from ..tasks.task_manager import TaskManager
from ..players.player import Player

class BattleManager:
    """Manages battle logic and state."""

    def __init__(self, task_manager: TaskManager, player: Player):
        self.task_manager = task_manager
        self.player = player
        self.battle_state = BattleState()
        self.current_enemy: Optional[Enemy] = None
        self.on_battle_end: Optional[Callable] = None
        logging.info("BattleManager initialized")

    def start_battle(self, enemy_name: str) -> bool:
        """Start a new battle."""
        try:
            if self.battle_state.is_active:
                logging.warning("Cannot start new battle while battle is active")
                return False

            task = self.task_manager.get_random_active_task()
            if not task:
                logging.error("No active tasks available for battle")
                return False

            self.current_enemy = Enemy.from_task(task, enemy_name)
            
            self.battle_state.is_active = True
            self.battle_state.enemy_name = enemy_name
            self.battle_state.enemy_hp = self.current_enemy.current_hp
            self.battle_state.enemy_max_hp = self.current_enemy.max_hp
            self.battle_state.task_name = task.name

            logging.info(f"Battle started with {enemy_name}, HP: {self.current_enemy.current_hp}, Task: {task.name}")
            return True

        except Exception as e:
            logging.error(f"Error starting battle: {e}")
            return False

    def perform_attack(self, damage: int = 1) -> bool:
        """Perform an attack on the current enemy."""
        try:
            if not self.battle_state.is_active or not self.current_enemy:
                logging.warning("No active battle for attack")
                return False

            self.current_enemy.take_damage(damage)
            self.battle_state.enemy_hp = self.current_enemy.current_hp

            if self.current_enemy.is_defeated():
                self._handle_victory()
                return True

            logging.debug(f"Attack performed, damage: {damage}, remaining HP: {self.current_enemy.current_hp}")
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            return False

    def _handle_victory(self):
        """Handle enemy defeat and victory rewards."""
        try:
            xp_gained = max(10, self.current_enemy.max_hp * 2)
            self.player.gain_experience(xp_gained)
            
            self.battle_state.is_active = False
            self.current_enemy = None

            logging.info(f"Battle won! XP gained: {xp_gained}")
            
            if self.on_battle_end:
                self.on_battle_end()

        except Exception as e:
            logging.error(f"Error handling victory: {e}")

    def end_battle(self):
        """Force end the current battle."""
        self.battle_state.is_active = False
        self.current_enemy = None
        logging.info("Battle ended")

    def is_in_battle(self) -> bool:
        """Check if a battle is active."""
        return self.battle_state.is_active
