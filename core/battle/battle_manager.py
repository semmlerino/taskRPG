# core/battle/battle_manager.py

import os
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Protocol, List, TYPE_CHECKING, Dict, Any, Union
from enum import Enum, auto
import random

# Core game system imports
from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.players.player import Player
from modules.battle.enemy import Enemy  # Changed from core.battle.enemy
from modules.battle.battle_state import BattleState  # Changed from core.battle.battle_state

# Type hints for UI components
if TYPE_CHECKING:
    from PyQt5.QtWidgets import QStatusBar
    from modules.ui.components.story_display import StoryDisplay
    from modules.ui.components.enemy_panel import EnemyPanel
    from modules.ui.components.action_buttons import ActionButtons
    from modules.ui.components.player_panel import PlayerPanel
    from modules.ui.components.compact_battle_window import CompactBattleWindow
    from modules.ui.main_window import TaskRPG


class BattleEvent(Enum):
    """Battle system events."""
    BATTLE_START = auto()
    BATTLE_END = auto()
    ATTACK_PERFORMED = auto()
    STATE_CHANGED = auto()
    ENEMY_DEFEATED = auto()


@dataclass
class BattleState:
    """Complete battle state container."""
    is_active: bool = False
    enemy_name: Optional[str] = None
    enemy_hp: Optional[int] = None
    enemy_max_hp: Optional[int] = None
    task_name: Optional[str] = None
    last_attack_type: Optional[str] = None
    xp_gained: int = 0


class BattleManager:
    """
    Unified battle management system handling both core logic and UI coordination.
    """

    def __init__(self, task_manager: TaskManager, player: Player):
        """
        Initialize the battle manager.

        Args:
            task_manager: Task management system
            player: Player instance
        """
        self.task_manager = task_manager
        self.player = player
        self.battle_state = BattleState()
        self.current_enemy: Optional[Enemy] = None
        self.paused: bool = False

        # UI update callbacks
        self.on_battle_start: Optional[Callable] = None
        self.on_battle_end: Optional[Callable] = None
        self.on_attack: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_victory: Optional[Callable] = None

        # UI Components (set by UI layer)
        self.story_display: Optional['StoryDisplay'] = None
        self.enemy_panel: Optional['EnemyPanel'] = None
        self.action_buttons: Optional['ActionButtons'] = None
        self.player_panel: Optional['PlayerPanel'] = None
        self.status_bar: Optional['QStatusBar'] = None
        self.main_window: Optional['TaskRPG'] = None
        self.compact_window: Optional['CompactBattleWindow'] = None

        logging.info("BattleManager initialized")

    def start_battle(self, battle_info: Dict[str, Any]) -> bool:
        """
        Start a new battle with task integration.

        Args:
            battle_info: Dictionary containing battle configuration

        Returns:
            bool: True if battle started successfully
        """
        try:
            if not self._validate_battle_start():
                return False

            # Get random task
            task = self.task_manager.get_random_active_task()
            if not task:
                logging.error("No active tasks available")
                self._update_status("No tasks available for battle")
                return False

            # Create enemy from task
            enemy_name = battle_info.get("enemy", "Unknown Enemy")
            max_hp = task.get_random_count()

            self.current_enemy = Enemy(
                name=enemy_name,
                max_hp=max_hp,
                task_name=task.name,
                task_description=task.description or "Complete the task!"
            )

            # Verify enemy creation
            if not self.current_enemy or not hasattr(self.current_enemy, 'current_hp'):
                logging.error("Enemy creation failed or invalid enemy state")
                return False

            # Update battle state
            self.battle_state = BattleState(
                is_active=True,
                enemy_name=enemy_name,
                enemy_hp=self.current_enemy.current_hp,
                enemy_max_hp=max_hp,
                task_name=task.name
            )

            # Debug logging
            logging.debug(f"Enemy created with HP: {self.current_enemy.current_hp}")
            logging.debug(f"Battle state HP: {self.battle_state.enemy_hp}")

            # Update UI
            self._update_ui_for_battle_start(battle_info)
            logging.info(f"Battle started with {enemy_name}, Task: {task.name}")
            return True

        except Exception as e:
            logging.error(f"Error starting battle: {e}")
            self._update_status("Error starting battle")
            return False

    def perform_attack(self, is_heavy: bool = False) -> bool:
        """
        Perform an attack with complete update chain.

        Args:
            is_heavy: Whether to perform a heavy attack

        Returns:
            bool: True if attack was successful
        """
        try:
            if not self._validate_attack():
                logging.warning("Attack validation failed")
                return False

            if not self.current_enemy:
                logging.error("No current enemy for attack")
                return False

            # Calculate and apply damage
            if is_heavy:
                damage = random.randint(2, 4)  # Random damage between 2-4 for heavy attacks
            else:
                damage = 1  # Normal attack damage remains 1

            # Update both enemy object and battle state
            self.current_enemy.take_damage(damage)
            self.battle_state.enemy_hp = self.current_enemy.current_hp
            self.battle_state.last_attack_type = "heavy" if is_heavy else "normal"

            # Debug logging
            logging.debug(f"Current enemy HP after attack: {self.current_enemy.current_hp}")
            logging.debug(f"Battle state HP after attack: {self.battle_state.enemy_hp}")

            # Update UI after attack
            self._update_ui_after_attack(is_heavy)

            # Check for victory
            if self.current_enemy.is_defeated():
                self._handle_victory()
                return True

            logging.debug(f"Attack performed: {'heavy' if is_heavy else 'normal'}, "
                          f"remaining HP: {self.current_enemy.current_hp}")
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            self._update_status("Attack failed")
            return False

    def _validate_attack(self) -> bool:
        """
        Validate attack conditions.

        Returns:
            bool: True if attack can be performed
        """
        if not self.battle_state.is_active:
            logging.warning("No active battle")
            return False
        if not self.current_enemy:
            logging.warning("No current enemy")
            return False
        if self.paused:
            logging.warning("Battle is paused")
            return False
        if not hasattr(self.current_enemy, 'current_hp'):
            logging.error("Enemy missing current_hp attribute")
            return False
        return True

    def _handle_victory(self) -> None:
        """Handle victory with complete update chain."""
        try:
            # Calculate and award XP
            xp_gained = max(10, self.current_enemy.max_hp * 2)
            self.player.gain_experience(xp_gained)
            self.battle_state.xp_gained = xp_gained

            # Update battle state
            self.battle_state.is_active = False
            self.current_enemy = None

            # Update UI for victory
            self._update_ui_for_victory(xp_gained)

            # Notify victory
            if self.on_victory:
                self.on_victory()
            if self.on_battle_end:
                self.on_battle_end()

            logging.info(f"Battle won! XP gained: {xp_gained}")

        except Exception as e:
            logging.error(f"Error handling victory: {e}")
            self._update_status("Error processing victory")

    def toggle_pause(self) -> None:
        """Toggle the pause state of the battle."""
        try:
            self.paused = not self.paused
            status = "paused" if self.paused else "resumed"

            # Update UI pause state
            if self.action_buttons:
                self.action_buttons.setEnabled(not self.paused)
            if self.compact_window:
                self.compact_window.setEnabled(not self.paused)

            self._update_status(f"Battle {status}")
            logging.info(f"Battle {status}")

        except Exception as e:
            logging.error(f"Error toggling pause: {e}")

    def show_compact_mode(self) -> None:
        """Show compact battle window when main window loses focus."""
        try:
            if self.is_in_battle() and not self.compact_window:
                from modules.ui.components.compact_battle_window import CompactBattleWindow
                self.compact_window = CompactBattleWindow()

                # Position window relative to main window
                if self.main_window:
                    main_geo = self.main_window.geometry()
                    self.compact_window.move(
                        main_geo.x() + main_geo.width() + 10,
                        main_geo.y()
                    )

                if self.current_enemy:
                    self.compact_window.update_display(self.current_enemy)
                self.compact_window.show()
                logging.info("Compact battle window shown")

        except Exception as e:
            logging.error(f"Error showing compact window: {e}")

    def hide_compact_mode(self) -> None:
        """Hide compact battle window."""
        try:
            if self.compact_window:
                self.compact_window.close()
                self.compact_window.deleteLater()
                self.compact_window = None
                logging.info("Compact battle window hidden")

        except Exception as e:
            logging.error(f"Error hiding compact window: {e}")

    def _validate_battle_start(self) -> bool:
        """
        Validate battle start conditions.

        Returns:
            bool: True if battle can start
        """
        if self.battle_state.is_active:
            logging.warning("Battle already in progress")
            self._update_status("Battle already in progress")
            return False
        if self.paused:
            logging.warning("Cannot start battle while paused")
            self._update_status("Game is paused")
            return False
        return True

    def _update_ui_for_battle_start(self, battle_info: Dict[str, Any]) -> None:
        """
        Update UI for battle start.

        Args:
            battle_info: Dictionary containing battle information
        """
        if self.enemy_panel:
            self.enemy_panel.update_panel(self.current_enemy)
        if self.action_buttons:
            self.action_buttons.show_attack_buttons()
        if self.story_display:
            message = battle_info.get("message", "A new enemy appears!")
            self.story_display.append_text(f"<p><i>{message}</i></p>")
        if self.compact_window:
            self.compact_window.update_display(self.current_enemy)
        self._update_status("Battle started!")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """
        Update UI after attack.

        Args:
            was_heavy: Whether the attack was a heavy attack
        """
        if self.enemy_panel:
            self.enemy_panel.update_panel(self.current_enemy)
        if self.compact_window:
            self.compact_window.update_display(self.current_enemy)

        attack_type = "Heavy attack" if was_heavy else "Attack"
        self._update_status(f"{attack_type} landed!")

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """
        Update UI for victory.

        Args:
            xp_gained: Amount of XP gained from victory
        """
        if self.story_display:
            self.story_display.append_text(
                f"<p>Victory! You gained <b>{xp_gained}</b> XP!</p>"
            )
        if self.enemy_panel:
            self.enemy_panel.update_panel(None)
        if self.action_buttons:
            self.action_buttons.hide_attack_buttons()
            self.action_buttons.next_button.show()
        if self.player_panel:
            self.player_panel.update_panel()
        self._update_status("Victory! Story continues...")

    def _update_status(self, message: str) -> None:
        """
        Update status bar if available.

        Args:
            message: Status message to display
        """
        if self.status_bar:
            self.status_bar.showMessage(message)

    def is_in_battle(self) -> bool:
        """
        Check if battle is active.

        Returns:
            bool: True if in battle
        """
        return self.battle_state.is_active

    def get_current_enemy(self) -> Optional[Enemy]:
        """
        Get current enemy.

        Returns:
            Optional[Enemy]: Current enemy or None
        """
        return self.current_enemy

    def cleanup(self) -> None:
        """Clean up battle resources."""
        try:
            self.hide_compact_mode()
            self.battle_state = BattleState()
            self.current_enemy = None
            self.paused = False
            logging.info("Battle manager cleanup complete")
        except Exception as e:
            logging.error(f"Error during battle manager cleanup: {e}")
