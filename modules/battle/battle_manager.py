"""
File: modules/battle/battle_manager.py
Battle management system for TaskRPG.

This is the consolidated battle system that combines functionality from both
the core and modules implementations. This file now contains all battle-related
functionality in a single, unified implementation.

Handles the coordination between tasks, combat, and UI components
while maintaining the game's task-management metaphor.
"""

# Standard library imports
import logging
import random
import time
from typing import Optional, Callable, Dict, Any, Union, List, TYPE_CHECKING, Protocol
from enum import Enum, auto

# PyQt5 imports
from PyQt5.QtWidgets import QApplication, QMessageBox, QStatusBar, QLabel
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtSignal

# Project imports: Core functionality
from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.players.player import Player

# Project imports: Battle components
from modules.battle.enemy import Enemy
from modules.battle.battle_state import BattleState, BattleStatus
from modules.battle.battle_callbacks import BattleCallbacks
from modules.battle.ui.battle_ui_manager import BattleUIManager

# Project imports: UI components
from modules.ui.components.compact_battle_window import CompactBattleWindow

if TYPE_CHECKING:
    from modules.ui.components.story_display import StoryDisplay
    from modules.ui.components.enemy_panel import EnemyPanel
    from modules.ui.components.action_buttons import ActionButtons
    from modules.ui.components.player_panel import PlayerPanel
    from modules.ui.main_window import TaskRPG

class BattleEvent(Enum):
    """Battle system events."""
    BATTLE_START = auto()
    BATTLE_END = auto()
    ATTACK_PERFORMED = auto()
    STATE_CHANGED = auto()
    ENEMY_DEFEATED = auto()

class BattleManager:
    """
    Unified battle management system.
    
    Coordinates between:
    - Task system (tasks become enemies)
    - UI components (battle display)
    - Player state (XP, level progression)
    - Window management (focus, compact mode)
    """
    
    def __init__(self, task_manager: TaskManager, player: Player):
        """Initialize battle manager with core systems."""
        self.task_manager = task_manager
        self.player = player
        
        # Initialize battle state - single source of truth for battle data
        self.battle_state = BattleState()
        
        # Initialize callbacks
        self.callbacks = BattleCallbacks()
        
        # Initialize UI Manager - the only direct UI reference
        self.ui_manager = BattleUIManager()
        
        # Signal tracking
        self.signals_connected = False
        self.active_timers = []
        self.hotkey_listener = None
        
        # XP Configuration
        self.xp_base = 100  # Base XP for victories
        self.xp_multiplier = 1.0  # Multiplier for XP calculations
        self.xp_bonus_per_turn = 10  # Bonus XP per turn taken
        self.xp_time_bonus_factor = 0.5  # Factor for time-based XP bonus
        
        # Coin reward configuration
        self.coin_reward = 5  # Default coins per victory
        
        logging.info("BattleManager initialized with task manager and player")

    def start_battle(self, battle_info: dict) -> bool:
        """
        Start a new battle from story or task context.
        
        Args:
            battle_info: Dictionary containing battle configuration:
                - enemy: Name of the enemy (optional)
                - message: Battle start message (optional)
                - task_override: Specific task to use (optional)
                
        Returns:
            bool: True if battle started successfully, False otherwise
        """
        try:
            logging.debug(f"Starting battle with info: {battle_info}")
            
            if not self._validate_battle_start():
                return False

            # Get task (either specified or random)
            task = None
            
            # Task override mode
            if 'task_override' in battle_info:
                task_name = battle_info['task_override']
                task = self.task_manager.get_task(task_name)
                if not task:
                    logging.warning(f"Specified task {task_name} not found")
                    task = None
                elif not task.is_active:
                    # Force activate the task if it's specified
                    task.activate(manual=True)
                    logging.info(f"Forced activation of task {task_name} for battle")
            
            # Get random task if none specified
            if not task:
                # Check for task activations first
                self.task_manager.check_task_activations()
                task = self.task_manager.get_random_active_task()
                
                # If no active tasks, force activate a random one
                if not task:
                    all_tasks = list(self.task_manager.tasks.values())
                    if all_tasks:
                        task = random.choice(all_tasks)
                        task.activate(manual=True)
                        logging.info(f"Forced activation of random task {task.name} for battle")
                
            if not task:
                logging.warning("No tasks available for battle")
                self.ui_manager.update_status("No tasks available")
                return False

            # Initialize enemy
            initial_hp = task.get_hp()
            enemy_name = battle_info.get('enemy', f"Task: {task.name}")
            
            enemy = Enemy(
                name=enemy_name,
                task_name=task.name,
                max_hp=initial_hp,
                current_hp=initial_hp
            )
            
            # Update battle state
            self.battle_state.start_battle(enemy)
            
            # Connect battle controls if available
            if self.hotkey_listener and not self.signals_connected:
                self._connect_battle_signals()
            
            # Update UI
            self._update_battle_ui()
            
            # Display battle start message
            message = battle_info.get('message', "A new enemy appears!")
            self.ui_manager.append_story_text(f"<p><i>{message}</i></p>")
                
            # Execute callback
            if self.callbacks.on_battle_start:
                self.callbacks.on_battle_start()
            
            # Ensure window state is appropriate
            self.ui_manager.release_keyboard_focus()
            
            logging.info(f"Battle started with {enemy_name} (Task: {task.name})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start battle: {e}")
            self.ui_manager.update_status("Error starting battle")
            return False

    def perform_attack(self, is_heavy: bool = False) -> bool:
        """
        Perform an attack in battle.
        
        Args:
            is_heavy: Whether this is a heavy attack (more damage, longer cooldown)
            
        Returns:
            bool: True if attack was successful, False otherwise
        """
        try:
            # First check if a battle is actually in progress to prevent post-battle attacks
            if not self.battle_state.is_in_battle():
                logging.debug("Attack attempted but no battle is in progress")
                return False
                
            attack_type = "heavy" if is_heavy else "normal"
            logging.debug(f"Processing {attack_type} attack request")
            
            # Attempt to repair battle state before validation
            self.repair_battle_state()
            
            # Validate attack conditions
            if not self._validate_attack():
                logging.warning(f"{attack_type.capitalize()} attack validation failed")
                return False

            # Get current enemy from battle state
            enemy = self.battle_state.get_current_enemy()
            if not enemy:
                logging.warning("No current enemy found in battle state")
                return False

            # Record the attack in battle state
            self.battle_state.record_attack(attack_type)
            
            # Calculate and apply damage
            damage = random.randint(2, 4) if is_heavy else 1
            
            # Log attack details before applying damage
            old_hp = enemy.current_hp
            logging.debug(f"Performing {attack_type} attack: Enemy HP before: {old_hp}, Damage: {damage}")
            
            # Apply damage to enemy and update battle state
            enemy.take_damage(damage)
            self.battle_state.update_enemy_hp(enemy.current_hp)
            
            # Log successful attack
            logging.info(f"{attack_type.capitalize()} attack successful: Enemy HP reduced from {old_hp} to {enemy.current_hp}")
            
            # Show feedback in status bar
            self.ui_manager.update_status(f"{attack_type.capitalize()} attack: -{damage} HP", 1500)
            
            # Update UI
            self._update_ui_after_attack(is_heavy)
            
            # Trigger shake animation if enabled
            self.ui_manager.trigger_shake_animation()
            
            # Check for victory
            if enemy.is_defeated():
                self._handle_victory()
                
            # Execute callback
            if self.callbacks.on_attack:
                self.callbacks.on_attack(damage)
                
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            self.ui_manager.update_status("Error processing attack")
            return False

    def _handle_victory(self) -> None:
        """Handle victory with complete update chain."""
        try:
            # Get the enemy for reference
            enemy = self.battle_state.get_current_enemy()
            if not enemy:
                logging.warning("No enemy found for victory processing")
                return
                
            # Calculate XP with constants
            xp = max(self.xp_base, enemy.max_hp * self.xp_multiplier)
            
            # Apply modifiers based on performance
            if self.battle_state.turns_taken < enemy.max_hp:
                xp = int(xp * 1.2)  # 20% bonus for efficiency
            
            # Award XP
            self.player.gain_experience(xp)
            
            # Award coins using the configurable coin_reward value
            self.player.earn_coins(self.coin_reward)
            
            logging.info(f"Victory! Awarded {xp} XP and {self.coin_reward} coins")
            
            # Handle task completion and count decrementing
            if enemy and enemy.task_name:
                task = self.task_manager.get_task(enemy.task_name)
                if task:
                    # Handle count decrementing
                    if task.count > 0:
                        # Store previous count to check if it's being decremented to 0
                        previous_count = task.count
                        task.count -= 1
                        # For daily/weekly tasks, handle reactivation
                        if task.is_daily or task.is_weekly:
                            task.deactivate()  # This will handle daily task reactivation logic
                        # For regular tasks, only deactivate when count is decremented from 1 to 0
                        elif previous_count == 1 and task.count == 0:
                            task.active = False
                        # Otherwise, tasks with count 0 remain active
                    
                    self.task_manager.save_tasks()  # Save task state changes
            
            # Mark battle as completed in story context
            if hasattr(self, 'story_manager'):
                self.story_manager.mark_battle_complete(enemy.name)
                
            # Mark this battle as completed in battle state
            self.battle_state.mark_battle_complete(enemy.name)
            
            # Record victory in battle state
            self.battle_state.record_victory(xp)
            
            # Disconnect battle signals to prevent post-battle interactions
            self._disconnect_battle_signals()
            
            # Handle window state
            self.hide_compact_mode()
            
            # Update UI with victory fanfare
            self._update_ui_for_victory(xp)
            
            # Start victory animation if available
            self.ui_manager.trigger_victory_animation()
            
            # Execute callbacks
            if self.callbacks.on_victory:
                self.callbacks.on_victory()
            if self.callbacks.on_battle_end:
                self.callbacks.on_battle_end()
                
            logging.info(f"Victory handled successfully. XP gained: {xp}")
                
        except Exception as e:
            logging.error(f"Error handling victory: {e}")
            self.ui_manager.update_status("Error processing victory")

    def _update_battle_ui(self) -> None:
        """Update all UI components with current battle state using the UI manager."""
        try:
            # Get current enemy from battle state
            enemy = self.battle_state.get_current_enemy()
            if not enemy:
                logging.warning("No enemy found for UI update")
                return
                
            # Delegate to UI manager
            self.ui_manager.update_battle_ui(enemy)
            
            # Log successful update
            logging.debug("Battle UI updated successfully via UI manager")
            
        except Exception as e:
            logging.error(f"Error in _update_battle_ui: {e}")
            self.ui_manager.update_status("Error updating battle UI")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI components after an attack using the UI manager."""
        try:
            # Get current enemy from battle state
            enemy = self.battle_state.get_current_enemy()
            if not enemy:
                logging.warning("No enemy found for after-attack UI update")
                return
                
            # Delegate to UI manager
            self.ui_manager.update_ui_after_attack(enemy, was_heavy)
            
        except Exception as e:
            logging.error(f"Error updating UI after attack: {e}")
            self.ui_manager.update_status("Error updating attack display")

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI elements after victory with enhanced feedback using the UI manager."""
        try:
            # Delegate to UI manager
            self.ui_manager.update_ui_for_victory(xp_gained, self.coin_reward)
            
        except Exception as e:
            logging.error(f"Error updating UI for victory: {e}")
            self.ui_manager.update_status("Error updating victory display")

    def _validate_battle_start(self) -> bool:
        """
        Validate battle start conditions.
        
        Checks:
        - No active battle in progress
        - Game not paused
        - UI components ready
        """
        if self.battle_state.is_in_battle():
            logging.warning("Battle already in progress")
            self.ui_manager.update_status("Battle already in progress")
            return False
            
        if self.battle_state.is_paused():
            logging.warning("Cannot start battle while paused")
            self.ui_manager.update_status("Game is paused")
            return False
            
        # Check that UI components are ready via the UI manager
        if not self.ui_manager.are_components_ready():
            logging.warning("UI components not ready")
            return False
            
        return True

    def _connect_battle_signals(self) -> None:
        """Connect battle-related hotkey signals for combat."""
        try:
            if self.hotkey_listener:
                # Connect attack signals directly
                self.hotkey_listener.normal_attack_signal.connect(
                    lambda: self.perform_attack(is_heavy=False)
                )
                self.hotkey_listener.heavy_attack_signal.connect(
                    lambda: self.perform_attack(is_heavy=True)
                )
                self.hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
                
                # Mark signals as connected
                self.signals_connected = True
                
                logging.info("Battle hotkeys connected for combat")
                
        except Exception as e:
            logging.error(f"Error connecting battle signals: {e}")

    def _disconnect_battle_signals(self) -> None:
        """Disconnect battle-related hotkey signals after battle ends."""
        try:
            if self.hotkey_listener and self.signals_connected:
                # Disconnect all signals cleanly
                try:
                    # We can't directly disconnect lambdas, so we'll use a different approach
                    # that disconnects all connections to our methods
                    if hasattr(self.hotkey_listener.normal_attack_signal, 'disconnect'):
                        self.hotkey_listener.normal_attack_signal.disconnect()
                    if hasattr(self.hotkey_listener.heavy_attack_signal, 'disconnect'):
                        self.hotkey_listener.heavy_attack_signal.disconnect()
                    if hasattr(self.hotkey_listener.toggle_pause_signal, 'disconnect'):
                        self.hotkey_listener.toggle_pause_signal.disconnect()
                except Exception as e:
                    logging.warning(f"Error during signal disconnection: {e}")
                
                self.signals_connected = False
                logging.info("Battle hotkeys disconnected after battle end")
        except Exception as e:
            logging.error(f"Error disconnecting battle signals: {e}")

    def connect_signals(self, hotkey_listener) -> None:
        """Store hotkey listener for later use."""
        try:
            # Store hotkey listener reference only
            self.hotkey_listener = hotkey_listener
            
            # Update UI if available
            self.ui_manager.update_status("Battle controls ready", 2000)
            
            logging.info("Hotkey listener registered with battle manager")
            
        except Exception as e:
            logging.error(f"Error storing hotkey listener: {e}")

    def set_ui_components(self, 
                         story_display=None,
                         enemy_panel=None,
                         action_buttons=None,
                         player_panel=None,
                         status_bar=None,
                         tasks_left_label=None,
                         main_window=None) -> bool:
        """Set UI component references."""
        try:
            # Only set components in the UI Manager, not in the BattleManager
            result = self.ui_manager.set_ui_components(
                story_display=story_display,
                enemy_panel=enemy_panel,
                action_buttons=action_buttons,
                player_panel=player_panel,
                status_bar=status_bar,
                tasks_left_label=tasks_left_label,
                main_window=main_window,
                compact_window=None  # Initially no compact window
            )
            
            # Connect UI signals if action buttons are available
            if action_buttons:
                try:
                    action_buttons.attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=False)
                    )
                    action_buttons.heavy_attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=True)
                    )
                    logging.debug("Action buttons signals connected")
                    
                    logging.info("UI components set and signals connected")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error connecting action button signals: {e}")
                    return False
            
            logging.info("UI components set successfully")
            return result
        
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")
            return False

    def update_tasks_left(self) -> None:
        """Update the tasks remaining display using the UI manager."""
        enemy = self.battle_state.get_current_enemy()
        if enemy:
            # Delegate to UI manager
            self.ui_manager.update_tasks_left(enemy)

    def show_compact_mode(self) -> None:
        """Show compact battle window using the UI manager."""
        try:
            if self.battle_state.is_in_battle():
                # Get current enemy from battle state
                enemy = self.battle_state.get_current_enemy()
                if not enemy:
                    logging.warning("No enemy found for compact mode")
                    return
                    
                # Delegate to UI manager
                self.ui_manager.show_compact_mode(
                    enemy,
                    lambda: self.perform_attack(is_heavy=False),
                    lambda: self.perform_attack(is_heavy=True)
                )
                
                # Enable attack hotkeys for compact mode
                if self.hotkey_listener and not self.signals_connected:
                    self._connect_battle_signals()
                    
                logging.debug("Compact mode shown via UI manager")
        except Exception as e:
            logging.error(f"Error showing compact mode: {e}")

    def hide_compact_mode(self) -> None:
        """Hide compact battle window using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.hide_compact_mode()

    def toggle_pause(self) -> None:
        """Toggle battle pause state."""
        try:
            # First check if a battle is actually in progress
            if not self.battle_state.is_in_battle():
                logging.debug("Pause attempted but no battle is in progress")
                return
                
            # Attempt to repair battle state before toggling pause
            self.repair_battle_state()
            
            # Toggle the pause state in battle state
            if self.battle_state.is_paused():
                self.battle_state.unpause()
                status = "resumed"
            else:
                self.battle_state.pause()
                status = "paused"
                
            logging.debug(f"Toggling pause state to: {status}")

            # Update UI components using the UI manager
            self.ui_manager.update_pause_state(self.battle_state.is_paused())

            # Validate pause state consistency
            self._validate_pause_state()
        
            self.ui_manager.update_status(f"Battle {status}")
    
        except Exception as e:
            logging.error(f"Error toggling pause: {e}")
            self.ui_manager.show_error("Failed to toggle pause state")

    def _validate_pause_state(self) -> None:
        """Validate that pause state is consistent across all components."""
        try:
            # Get the current pause state
            is_paused = self.battle_state.is_paused()
            
            # Delegate to UI manager to validate consistency in UI components
            self.ui_manager.validate_pause_state(is_paused)
            
            logging.debug(f"Pause state validation complete. Current state: {is_paused}")
            
        except Exception as e:
            logging.error(f"Error validating pause state: {e}")

    def is_in_battle(self) -> bool:
        """Check if currently in battle."""
        return self.battle_state.is_in_battle()
        
    def repair_battle_state(self) -> None:
        """Attempt to repair inconsistent battle state."""
        try:
            # Get current enemy
            enemy = self.battle_state.get_current_enemy()
            
            # If we have an enemy but battle isn't active, restore state
            if enemy is not None and not self.battle_state.is_active():
                logging.warning("Repairing inconsistent battle state")
                
                # Force battle to active state
                self.battle_state.status = BattleStatus.ACTIVE
                
                # Update UI to reflect repaired state
                self._update_battle_ui()
                self.ui_manager.update_status("Battle state repaired")
                
        except Exception as e:
            logging.error(f"Error repairing battle state: {e}")

    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.battle_state.get_current_enemy()

    def end_battle(self) -> None:
        """End the current battle and clean up."""
        try:
            logging.debug("Ending battle")
            
            # Disconnect battle signals to prevent post-battle interactions
            self._disconnect_battle_signals()
            
            # Update battle state
            self.battle_state.end_battle()
            
            # Update UI components using the UI manager
            self.ui_manager.update_ui_for_battle_end()
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")
            self.ui_manager.show_error("Error ending battle")
            
    def cleanup(self) -> None:
        """
        Clean up battle manager resources with proper state management.
        
        Handles:
        - Window cleanup
        - State reset
        - UI updates
        - Memory cleanup
        - Signal disconnection
        """
        try:
            logging.info("Starting battle manager cleanup")
            
            # Disconnect battle signals to prevent post-cleanup interactions
            self._disconnect_battle_signals()
            
            # Clean up UI components using the UI manager
            self.ui_manager.cleanup_ui()
            
            # Reset state
            self.battle_state.reset()
            
            # Clear any remaining timers
            if hasattr(self, 'active_timers'):
                for timer in self.active_timers:
                    timer.stop()
                self.active_timers.clear()
            
            logging.info("Battle manager cleanup complete")
            
        except Exception as e:
            logging.error(f"Error during battle manager cleanup: {e}")
            # Attempt emergency cleanup
            self._emergency_cleanup()

    def _emergency_cleanup(self):
        """Emergency cleanup for critical failures."""
        try:
            # Delegate UI emergency cleanup to UI manager
            self.ui_manager.emergency_cleanup_ui()
            
            # Reset state
            self.battle_state.reset()
            
            # Ensure signals are disconnected
            self._disconnect_battle_signals()
            
            logging.warning("Emergency cleanup performed")
            
        except Exception as e:
            logging.critical(f"Emergency cleanup failed: {e}")

    def register_callbacks(self,
                          on_battle_start: Optional[Callable] = None,
                          on_battle_end: Optional[Callable] = None,
                          on_attack: Optional[Callable] = None,
                          on_state_change: Optional[Callable] = None,
                          on_victory: Optional[Callable] = None) -> None:
        """Register callback functions for battle events."""
        self.callbacks.register(
            on_battle_start=on_battle_start,
            on_battle_end=on_battle_end,
            on_attack=on_attack,
            on_state_change=on_state_change,
            on_victory=on_victory
        )

    def _validate_attack(self) -> bool:
        """Validate attack conditions."""
        # Check if battle is active
        if not self.battle_state.is_active():
            logging.warning("Attack validation failed: battle is not active")
            self.ui_manager.update_status("No active battle", 2000)
            return False
            
        # Check if enemy exists
        enemy = self.battle_state.get_current_enemy()
        if enemy is None:
            logging.warning("Attack validation failed: no current enemy")
            self.ui_manager.update_status("No enemy to attack", 2000)
            return False
            
        # Check if battle is paused
        if self.battle_state.is_paused():
            logging.warning("Attack validation failed: battle is paused (press # to unpause)")
            self.ui_manager.update_status("Battle is paused - press # to unpause", 2000)
            return False
            
        # Check if enemy has HP attribute
        if not hasattr(enemy, 'current_hp'):
            logging.warning("Attack validation failed: enemy has no HP attribute")
            self.ui_manager.update_status("Enemy data error", 2000)
            return False
        
        # All validations passed
        logging.debug("Attack validation successful")
        return True
        
    def _initialize_enemy_hp(self, task: Task) -> int:
        """Initialize enemy HP based on task."""
        hp = task.get_hp()
        logging.debug(f"Initialized enemy HP for task '{task.name}': {hp}")
        return hp
        
    def mark_battle_complete(self, node_key: str):
        """Mark a battle node as completed."""
        self.battle_state.mark_battle_complete(node_key)
        logging.info(f"Marked battle node {node_key} as completed")
        
    def handle_chapter_complete(self) -> None:
        """Display chapter completion message using the UI manager."""
        try:
            # Delegate to UI manager
            self.ui_manager.handle_chapter_complete()
            logging.debug("Chapter completion delegated to UI manager")
            
        except Exception as e:
            logging.error(f"Error handling chapter completion: {e}")