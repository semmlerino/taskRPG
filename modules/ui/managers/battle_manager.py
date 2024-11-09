# Update the imports at the top of battle_manager.py
import logging
import random
from typing import Optional, Union, List
from PyQt5.QtWidgets import QMessageBox, QApplication

from modules.battle.enemy import Enemy  # Updated path
from modules.battle.battle_state import BattleState
from modules.tasks.task_manager import TaskManager
from modules.players.player import Player
from modules.ui.components.compact_battle_window import CompactBattleWindow
from modules.tasks.task import Task

class UIBattleManager:
    """Manages battle UI state and interactions."""
    
    def __init__(self, main_window, task_manager: TaskManager, player: Player):
        self.main_window = main_window
        self.task_manager = task_manager
        self.player = player
        self.battle_state = BattleState()
        self.current_enemy: Optional[Enemy] = None
        self.compact_window = None
        self.paused = False
        
        # Connect UI elements
        self.story_display = main_window.story_display
        self.enemy_panel = main_window.enemy_panel
        self.action_buttons = main_window.action_buttons
        self.status_bar = main_window.status_bar
        
        logging.info("UIBattleManager initialized")

    def start_battle(self, battle_info: dict) -> None:
        """Start a battle with enemy data from story."""
        try:
            logging.info(f"Received battle_info: {battle_info}")
            
            # Extract enemy data, handling both direct and nested structures
            if isinstance(battle_info, dict) and "battle" in battle_info:
                enemy_data = battle_info["battle"]
            else:
                enemy_data = battle_info
                
            # If enemy_data contains an "enemy" key with just the name
            if isinstance(enemy_data, dict) and "enemy" in enemy_data and isinstance(enemy_data["enemy"], str):
                enemy_name = enemy_data["enemy"]
                enemy = Enemy(
                    name=enemy_name,
                    max_hp=random.randint(3, 7),  # Default range if not specified
                    task_name=self.task_manager.get_random_active_task().name,
                    task_description="Defeat the enemy!"
                )
            else:
                # Create enemy with provided data
                enemy = Enemy(
                    name=enemy_data.get('name', 'Unknown Enemy'),
                    max_hp=enemy_data.get('hp', 10),
                    task_name=enemy_data.get('task_name'),
                    task_description=enemy_data.get('description', '')
                )
            
            # Update battle state
            self.current_enemy = enemy
            self.battle_state.is_active = True
            self.battle_state.enemy_name = enemy.name
            self.battle_state.enemy_hp = enemy.current_hp
            self.battle_state.enemy_max_hp = enemy.max_hp
            self.battle_state.task_name = enemy.task_name
            
            # Explicitly show attack buttons
            if hasattr(self, 'action_buttons'):
                self.action_buttons.show_attack_buttons()
                self.action_buttons.debug_button_state()  # Add this for debugging
            
            # Update UI
            if hasattr(self, 'enemy_panel'):
                self.enemy_panel.update_panel(enemy)
            if hasattr(self, 'main_window'):
                self.main_window.update_tasks_left()
                
        except Exception as e:
            logging.error(f"Error starting battle: {e}", exc_info=True)
            raise

    def perform_attack(self, is_heavy: bool = False) -> bool:
        """Perform an attack on the current enemy."""
        try:
            if not self.battle_state.is_active or not self.current_enemy:
                logging.warning("Cannot perform attack - no active battle or enemy")
                return False

            # Calculate damage based on attack type
            damage = 2 if is_heavy else 1
            
            self.current_enemy.take_damage(damage)
            self.battle_state.enemy_hp = self.current_enemy.current_hp

            # Display attack message
            self._display_attack_message(is_heavy, damage)

            if self.current_enemy.is_defeated():
                self.handle_victory()
                return True

            # Update UI elements
            if hasattr(self, 'enemy_panel'):
                self.enemy_panel.update_panel(self.current_enemy)
            
            logging.debug(f"Attack performed, damage: {damage}, remaining HP: {self.current_enemy.current_hp}")
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            return False

    def handle_victory(self):
        """Handles enemy defeat and victory conditions."""
        try:
            # Hide compact window if visible
            if self.compact_window:
                self.compact_window.hide()

            # Bring main window to front
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.main_window.setFocus()

            # Award XP and display victory
            xp_gained = max(10, self.current_enemy.max_hp * 2)
            self.player.gain_experience(xp_gained)
            self._display_victory(xp_gained)
            
            # Update game state
            self.current_enemy = None
            self.battle_state.is_active = False
            self.enemy_panel.update_panel(None)
            self.main_window.update_tasks_left()

            # Get current node and move to next
            current_node = self.main_window.story_manager.get_current_node()
            if next_node := current_node.get('next'):
                self.main_window.story_manager.set_current_node(next_node)
                self.main_window.story_manager.display_story_segment()
            
            # Update UI elements
            self.action_buttons.hide_attack_buttons()
            self.action_buttons.next_button.show()
            self.status_bar.showMessage("Enemy defeated! Story continues...")

        except Exception as e:
            logging.error(f"Error handling victory: {e}")
            QMessageBox.critical(self.main_window, "Error", 
                               "An error occurred while processing victory")

    def _can_attack(self) -> bool:
        """Checks if an attack can be performed."""
        return (not self.paused and 
                self.current_enemy is not None and 
                self.battle_state.is_active)

    def _display_attack_message(self, is_heavy: bool, damage: int):
        """Displays the attack message in the story display."""
        if is_heavy:
            message = (f"<p>You perform a heavy attack on the <b>{self.current_enemy.name}</b> "
                      f"dealing <b>{damage}</b> damage!</p>")
        else:
            message = (f"<p>You attack the <b>{self.current_enemy.name}</b> "
                      f"and deal <b>{damage}</b> damage!</p>")
        self.story_display.append_text(message)

    def _display_victory(self, xp_gained: int):
        """Displays victory message and experience gained."""
        victory_messages = [
            f"You have defeated the <b>{self.current_enemy.name}</b>!",
            f"The <b>{self.current_enemy.name}</b> has been vanquished!",
            f"Victory! The <b>{self.current_enemy.name}</b> is no more.",
            f"You emerge triumphant over the <b>{self.current_enemy.name}</b>!"
        ]
        self.story_display.append_text(f"<p>{random.choice(victory_messages)}</p>")
        self.story_display.append_text(f"<p>You gained <b>{xp_gained}</b> experience points!</p>")
        self.main_window.player_panel.update_panel()
        self.status_bar.showMessage(f"You gained {xp_gained} XP!")

    def show_compact_mode(self):
        """Show the compact battle window."""
        if not self.compact_window:
            self.compact_window = CompactBattleWindow()
        
        if self.current_enemy:
            self.compact_window.update_display(self.current_enemy)
        
        self.compact_window.show()

    def hide_compact_mode(self):
        """Hides the compact battle window."""
        if self.compact_window:
            self.compact_window.hide()
            logging.debug("Hiding compact battle window")

    def is_in_battle(self) -> bool:
        """Checks if currently in battle."""
        return self.battle_state.is_active

    def toggle_pause(self):
        """Toggles the pause state."""
        self.paused = not self.paused
        message = "Game paused." if self.paused else "Game resumed."
        self.story_display.append_text(f"<p><i>{message}</i></p>")
        self.status_bar.showMessage(message)

    def cleanup(self):
        """Cleanup battle manager resources."""
        if self.compact_window:
            self.compact_window.hide()
            self.compact_window.deleteLater()
            self.compact_window = None

    def _generate_battle_html(self) -> List[str]:
        """Generate HTML for battle information."""
        html_parts = []
        battle_data = self.battle_info.get("battle", self.battle_info)
        message = battle_data.get("message", "An enemy appears!")
        enemy_name = battle_data.get("enemy", "Unknown Enemy")
        html_parts.append(f"<p><i>{message}</i></p>")
        html_parts.append(f"<p>A wild <b>{enemy_name}</b> appears!</p>")
        return html_parts