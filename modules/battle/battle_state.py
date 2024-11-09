# modules/battle/battle_state.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class BattleState:
    """Represents the current state of a battle."""
    is_active: bool = False
    enemy_name: Optional[str] = None
    enemy_hp: Optional[int] = None
    enemy_max_hp: Optional[int] = None
    task_name: Optional[str] = None
    last_attack_type: Optional[str] = None
    xp_gained: int = 0

    def __post_init__(self):
        """Validate state after initialization."""
        if self.enemy_hp is not None and self.enemy_max_hp is not None:
            self.enemy_hp = max(0, min(self.enemy_hp, self.enemy_max_hp))
