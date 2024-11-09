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
