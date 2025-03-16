"""
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
from modules.battle.battle_state import BattleState
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
        self.battle_state = BattleState()
        self.current_enemy: Optional[Enemy] = None
        self.paused: bool = False
        self.callbacks = BattleCallbacks()
        
        # Initialize UI Manager
        self.ui_manager = BattleUIManager()
        
        # UI Components (set later via set_ui_components)
        self.story_display: Optional['StoryDisplay'] = None
        self.enemy_panel: Optional['EnemyPanel'] = None
        self.action_buttons: Optional['ActionButtons'] = None
        self.player_panel: Optional['PlayerPanel'] = None
        self.status_bar: Optional['QStatusBar'] = None
        self.main_window: Optional['TaskRPG'] = None
        self.compact_window: Optional['CompactBattleWindow'] = None
        self.tasks_left_label: Optional['QLabel'] = None
        
        # Signal tracking
        self.signals_connected = False
        self.active_timers = []
        
        # Victory animation settings
        self.victory_animation = None
        self.victory_sound = None
        
        # Battle timing and state attributes
        self.battle_start_time = 0
        self.last_attack_time = 0
        self.paused_time: Optional[float] = None
        self.total_pause_duration: float = 0
        
        # Battle statistics
        self.attacks_performed = 0
        self.turns_taken = 0
        self.last_attack_type = ""
        self.xp_gained = 0
        
        # XP Configuration
        self.xp_base = 100  # Base XP for victories
        self.xp_multiplier = 1.0  # Multiplier for XP calculations
        self.xp_bonus_per_turn = 10  # Bonus XP per turn taken
        self.xp_time_bonus_factor = 0.5  # Factor for time-based XP bonus
        
        # Coin reward configuration
        self.coin_reward = 5  # Default coins per victory
        
        # Track completed battle nodes
        self.completed_battle_nodes = set()
        
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
                if self.status_bar:
                    self.status_bar.showMessage("No tasks available")
                return False

            # Initialize enemy
            initial_hp = task.get_hp()
            enemy_name = battle_info.get('enemy', f"Task: {task.name}")
            
            self.current_enemy = Enemy(
                name=enemy_name,
                task_name=task.name,
                max_hp=initial_hp,
                current_hp=initial_hp
            )
            
            # Update battle state
            self.battle_state.is_active = True
            self.battle_state.enemy_hp = initial_hp
            self.battle_state.enemy_max_hp = initial_hp
            self.battle_state.enemy_name = enemy_name
            self.battle_state.task_name = task.name
            self.battle_state.battle_start_time = time.time()
            
            # Update UI
            self._update_battle_ui()
            
            # Display battle start message
            message = battle_info.get('message', "A new enemy appears!")
            if self.story_display:
                self.story_display.append_text(f"<p><i>{message}</i></p>")
                
            # Execute callback
            if self.callbacks.on_battle_start:
                self.callbacks.on_battle_start()
            
            # Ensure window state is appropriate
            if self.main_window and self.main_window.isFullScreen():
                self.main_window.releaseKeyboard()
            
            logging.info(f"Battle started with {enemy_name} (Task: {task.name})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start battle: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error starting battle")
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
            attack_type = "heavy" if is_heavy else "normal"
            logging.debug(f"Processing {attack_type} attack request")
            
            # FIX: Attempt to repair battle state before validation
            self.repair_battle_state()
            
            # Validate attack conditions
            if not self._validate_attack():
                logging.warning(f"{attack_type.capitalize()} attack validation failed")
                return False

            # Track attack timing
            current_time = time.time()
            self.battle_state.last_attack_time = current_time
            self.last_attack_time = current_time
            
            # Calculate and apply damage
            damage = random.randint(2, 4) if is_heavy else 1
            
            # Log attack details before applying damage
            old_hp = self.current_enemy.current_hp
            logging.debug(f"Performing {attack_type} attack: Enemy HP before: {old_hp}, Damage: {damage}")
            
            # Apply damage
            self.current_enemy.take_damage(damage)
            new_hp = self.current_enemy.current_hp
            
            # Update battle state
            self.battle_state.enemy_hp = new_hp
            self.battle_state.attacks_performed += 1
            self.battle_state.turns_taken += 1
            self.battle_state.last_attack_type = attack_type
            
            # Update internal stats too
            self.attacks_performed += 1
            self.turns_taken += 1
            self.last_attack_type = attack_type
            
            # Log successful attack
            logging.info(f"{attack_type.capitalize()} attack successful: Enemy HP reduced from {old_hp} to {new_hp}")
            
            # Show feedback in status bar
            if self.status_bar:
                self.status_bar.showMessage(f"{attack_type.capitalize()} attack: -{damage} HP", 1500)
            
            # Update UI
            self._update_ui_after_attack(is_heavy)
            
            # Trigger shake animation if enabled
            if self.main_window and hasattr(self.main_window, 'trigger_shake_animation'):
                self.main_window.trigger_shake_animation()
            
            # Check for victory
            if self.current_enemy.is_defeated():
                self._handle_victory()
                
            # Execute callback
            if self.callbacks.on_attack:
                self.callbacks.on_attack(damage)
                
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error processing attack")
            return False

    def _handle_victory(self) -> None:
        """Handle victory with complete update chain."""
        try:
            # Calculate XP with constants
            xp = max(self.xp_base, self.current_enemy.max_hp * self.xp_multiplier)
            
            # Apply modifiers based on performance
            if self.battle_state.turns_taken < self.current_enemy.max_hp:
                xp = int(xp * 1.2)  # 20% bonus for efficiency
            
            # Award XP
            self.player.gain_experience(xp)
            
            # Award coins using the configurable coin_reward value
            self.player.earn_coins(self.coin_reward)
            
            logging.info(f"Victory! Awarded {xp} XP and {self.coin_reward} coins")
            
            # Handle task completion and count decrementing
            if self.current_enemy and self.current_enemy.task_name:
                task = self.task_manager.get_task(self.current_enemy.task_name)
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
                self.story_manager.mark_battle_complete(self.current_enemy.name)
                
            # Mark this battle as completed  
            self.mark_battle_complete(self.current_enemy.name)
            
            # Update battle state
            self.battle_state.xp_gained = xp
            self.battle_state.is_active = False
            self.xp_gained = xp
            self.current_enemy = None
            
            # Handle window state
            self.hide_compact_mode()
            if self.main_window:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                self.main_window.releaseKeyboard()
                
                # Force focus after delay for reliable window activation
                QTimer.singleShot(100, lambda: (
                    self.main_window.raise_(),
                    self.main_window.activateWindow()
                ))
            
            # Update UI with victory fanfare
            self._update_ui_for_victory(xp)
            
            # Start victory animation if available
            if self.main_window and hasattr(self.main_window, 'trigger_victory_animation'):
                QTimer.singleShot(0, self.main_window.trigger_victory_animation)
            
            # Execute callbacks
            if self.callbacks.on_victory:
                self.callbacks.on_victory()
            if self.callbacks.on_battle_end:
                self.callbacks.on_battle_end()
                
            logging.info(f"Victory handled successfully. XP gained: {xp}")
                
        except Exception as e:
            logging.error(f"Error handling victory: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error processing victory")

    def _batch_ui_update(self, updates: dict) -> None:
        """
        Perform multiple UI updates in a single batch.
        Delegates to the UI manager's batch_ui_update method.
        
        Args:
            updates: Dictionary of update functions to execute
        """
        # Delegate to UI manager
        self.ui_manager.batch_ui_update(updates)

    def _update_battle_ui(self) -> None:
        """Update all UI components with current battle state using the UI manager."""
        try:
            # Ensure compact window is initialized if needed
            if not self.compact_window and hasattr(self, 'show_compact_mode'):
                self.show_compact_mode(self.current_enemy, self.perform_attack, lambda: self.perform_attack(True))
            
            # Delegate to UI manager
            self.ui_manager.update_battle_ui(self.current_enemy)
            
            # Log successful update
            logging.debug("Battle UI updated successfully via UI manager")
            
        except Exception as e:
            logging.error(f"Error in _update_battle_ui: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating battle UI")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI components after an attack using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.update_ui_after_attack(self.current_enemy, was_heavy)

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI elements after victory with enhanced feedback using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.update_ui_for_victory(xp_gained, self.coin_reward)

    def _validate_battle_start(self) -> bool:
        """
        Validate battle start conditions.
        
        Checks:
        - No active battle in progress
        - Game not paused
        - UI components ready
        """
        if self.battle_state.is_active:
            logging.warning("Battle already in progress")
            self._update_status("Battle already in progress")
            return False
            
        if self.paused:
            logging.warning("Cannot start battle while paused")
            self._update_status("Game is paused")
            return False
            
        # Check both battle manager and UI manager components
        battle_manager_ui_ready = all([self.enemy_panel, self.action_buttons, self.status_bar])
        ui_manager_ui_ready = all([self.ui_manager.enemy_panel, self.ui_manager.action_buttons, self.ui_manager.status_bar])
        
        if not (battle_manager_ui_ready and ui_manager_ui_ready):
            logging.warning("UI components not ready")
            # Log which components are missing for debugging
            if not battle_manager_ui_ready:
                logging.debug(f"Battle manager UI components missing: enemy_panel={bool(self.enemy_panel)}, "
                             f"action_buttons={bool(self.action_buttons)}, status_bar={bool(self.status_bar)}")
            if not ui_manager_ui_ready:
                logging.debug(f"UI manager components missing: enemy_panel={bool(self.ui_manager.enemy_panel)}, "
                             f"action_buttons={bool(self.ui_manager.action_buttons)}, status_bar={bool(self.ui_manager.status_bar)}")
            return False
            
        return True

    def connect_signals(self, hotkey_listener) -> None:
        """Connect battle-related hotkey signals."""
        try:
            # Store hotkey listener reference
            self.hotkey_listener = hotkey_listener
            
            # Connect attack signals directly
            hotkey_listener.normal_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=False)
            )
            hotkey_listener.heavy_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=True)
            )
            hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
            
            # Mark signals as connected
            self.signals_connected = True
            
            # Update UI if available
            if self.status_bar:
                self.status_bar.showMessage("Battle controls ready", 2000)
            
            logging.info("Battle hotkeys connected successfully")
            
        except Exception as e:
            logging.error(f"Error connecting battle signals: {e}")

    def set_ui_components(self, 
                         story_display=None,
                         enemy_panel=None,
                         action_buttons=None,
                         player_panel=None,
                         status_bar=None,
                         tasks_left_label=None,
                         main_window=None) -> None:
        """Set UI component references."""
        try:
            # Set components in the BattleManager
            self.story_display = story_display
            self.enemy_panel = enemy_panel
            self.action_buttons = action_buttons
            self.player_panel = player_panel
            self.status_bar = status_bar
            self.tasks_left_label = tasks_left_label
            self.main_window = main_window
            
            # Also set components in the UI Manager
            self.ui_manager.set_ui_components(
                story_display=story_display,
                enemy_panel=enemy_panel,
                action_buttons=action_buttons,
                player_panel=player_panel,
                status_bar=status_bar,
                tasks_left_label=tasks_left_label,
                main_window=main_window,
                compact_window=self.compact_window
            )
            
            # Connect UI signals
            if self.action_buttons:
                try:
                    self.action_buttons.attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=False)
                    )
                    self.action_buttons.heavy_attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=True)
                    )
                    logging.debug("Action buttons signals connected")
                    
                    logging.info("UI components set and signals connected")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error connecting action button signals: {e}")
                    return False
            
            logging.info("UI components set successfully")
            return True
        
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")
            return False

    def update_tasks_left(self) -> None:
        """Update the tasks remaining display using the UI manager."""
        if self.current_enemy:
            # Delegate to UI manager
            self.ui_manager.update_tasks_left(self.current_enemy)

    def show_compact_mode(self) -> None:
        """Show compact battle window using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.show_compact_mode(
            self.current_enemy,
            lambda: self.perform_attack(is_heavy=False),
            lambda: self.perform_attack(is_heavy=True)
        )
        # Store reference to compact window for other methods
        self.compact_window = self.ui_manager.compact_window

    def hide_compact_mode(self) -> None:
        """Hide compact battle window using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.hide_compact_mode()
        # Keep reference in sync
        self.compact_window = self.ui_manager.compact_window

    def toggle_pause(self) -> None:
        """Toggle battle pause state."""
        try:
            # FIX: Attempt to repair battle state before toggling pause
            self.repair_battle_state()
            
            # FIX: Make sure battle is marked as active when unpausing
            if self.paused and self.current_enemy is not None:
                self.battle_state.is_active = True
            
            # Toggle the central pause state
            self.paused = not self.paused
            status = "paused" if self.paused else "resumed"
            logging.debug(f"Toggling pause state to: {status}")

            # Update UI components using the UI manager
            self.ui_manager.update_pause_state(self.paused)

            # Update battle state timing
            current_time = time.time()
            if self.paused:
                self.battle_state.paused_time = current_time
                self.paused_time = current_time
            elif self.battle_state.paused_time:
                pause_duration = current_time - self.battle_state.paused_time
                self.battle_state.total_pause_duration += pause_duration
                self.total_pause_duration += pause_duration
                self.battle_state.paused_time = None
                self.paused_time = None

            # Validate pause state consistency
            self._validate_pause_state()
        
            self._update_status(f"Battle {status}")
    
        except Exception as e:
            logging.error(f"Error toggling pause: {e}")
            self._show_error("Failed to toggle pause state")

    def _validate_pause_state(self) -> None:
        """Validate that pause state is consistent across all components."""
        try:
            # Check compact window state
            if self.compact_window and self.compact_window._is_paused != self.paused:
                logging.warning("Pause state mismatch detected in compact window")
                self.compact_window.update_pause_state(self.paused)
        
            # Check enemy panel state
            if self.enemy_panel and hasattr(self.enemy_panel, '_is_paused'):
                if self.enemy_panel._is_paused != self.paused:
                    logging.warning("Pause state mismatch detected in enemy panel")
                    self.enemy_panel.update_pause_state(self.paused)
        
            # Check action buttons state
            if self.action_buttons and self.action_buttons.isEnabled() == self.paused:
                logging.warning("Action buttons state inconsistent with pause state")
                self.action_buttons.setEnabled(not self.paused)
            
            logging.debug(f"Pause state validation complete. Current state: {self.paused}")
            
        except Exception as e:
            logging.error(f"Error validating pause state: {e}")

    def is_in_battle(self) -> bool:
        """Check if currently in battle."""
        return bool(
            self.battle_state.is_active and 
            self.current_enemy and 
            self.battle_state.enemy_hp > 0
        )
        
    # FIX: Add new repair_battle_state method
    def repair_battle_state(self) -> None:
        """Attempt to repair inconsistent battle state."""
        try:
            # If we have an enemy but battle isn't active, restore state
            if self.current_enemy is not None and not self.battle_state.is_active:
                logging.warning("Repairing inconsistent battle state")
                self.battle_state.is_active = True
                self.battle_state.enemy_hp = self.current_enemy.current_hp
                self.battle_state.enemy_max_hp = self.current_enemy.max_hp
                self.battle_state.enemy_name = self.current_enemy.name
                self.battle_state.task_name = self.current_enemy.task_name
                
                # Update UI to reflect repaired state
                self._update_battle_ui()
                self._update_status("Battle state repaired")
                
        except Exception as e:
            logging.error(f"Error repairing battle state: {e}")

    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.current_enemy

    def _update_status(self, message: str, timeout: int = 0) -> None:
        """Update status bar with message."""
        # Delegate to UI manager
        self.ui_manager.update_status(message, timeout)

    def _show_error(self, message: str) -> None:
        """Show error message to user using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.show_error(message)

    def end_battle(self) -> None:
        """End the current battle and clean up."""
        try:
            logging.debug("Ending battle")
            
            # Update battle state
            self.battle_state.is_active = False
            self.current_enemy = None
            self.battle_state.enemy_hp = 0
            
            # Update UI components using the UI manager
            self.ui_manager.update_ui_for_battle_end()
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")
            self._show_error("Error ending battle")
            
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
            
            # Clean up UI components using the UI manager
            self.ui_manager.cleanup_ui()
            
            # Reset state
            self.battle_state = BattleState()
            self.current_enemy = None
            self.paused = False
            
            # Disconnect signals if connected
            if self.signals_connected:
                self._disconnect_signals()
            
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
            self.battle_state = BattleState()
            self.current_enemy = None
            
            logging.warning("Emergency cleanup performed")
            
        except Exception as e:
            logging.critical(f"Emergency cleanup failed: {e}")
            
    def _disconnect_signals(self):
        """Disconnect all signal connections."""
        try:
            # Disconnect UI signals
            if self.action_buttons:
                try:
                    self.action_buttons.attack_clicked.disconnect()
                    self.action_buttons.heavy_attack_clicked.disconnect()
                except Exception:
                    pass
                    
            # Clear callbacks
            self.callbacks = BattleCallbacks()
            
            self.signals_connected = False
            logging.debug("Battle signals disconnected")
            
        except Exception as e:
            logging.error(f"Error disconnecting signals: {e}")

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
        # Check if battle is active first
        if not self.battle_state.is_active:
            logging.warning("Attack validation failed: battle is not active")
            if self.status_bar:
                self.status_bar.showMessage("No active battle", 2000)
            return False
            
        # Check if enemy exists
        if self.current_enemy is None:
            logging.warning("Attack validation failed: no current enemy")
            if self.status_bar:
                self.status_bar.showMessage("No enemy to attack", 2000)
            return False
            
        # Check if battle is paused
        if self.paused:
            logging.warning("Attack validation failed: battle is paused (press # to unpause)")
            if self.status_bar:
                self.status_bar.showMessage("Battle is paused - press # to unpause", 2000)
            return False
            
        # Check if enemy has HP attribute
        if not hasattr(self.current_enemy, 'current_hp'):
            logging.warning("Attack validation failed: enemy has no HP attribute")
            if self.status_bar:
                self.status_bar.showMessage("Enemy data error", 2000)
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
        self.completed_battle_nodes.add(node_key)
        logging.info(f"Marked battle node {node_key} as completed")
        
    def handle_chapter_complete(self) -> None:
        """Display chapter completion message using the UI manager."""
        try:
            # Delegate to UI manager
            self.ui_manager.handle_chapter_complete()
            logging.debug("Chapter completion delegated to UI manager")
            
        except Exception as e:
            logging.error(f"Error handling chapter completion: {e}")

    def _batch_ui_update(self, updates: dict) -> None:
        """
        Perform multiple UI updates in a single batch.
        Delegates to the UI manager's batch_ui_update method.
        
        Args:
            updates: Dictionary of update functions to execute
        """
        # Delegate to UI manager
        self.ui_manager.batch_ui_update(updates)

    def _update_battle_ui(self) -> None:
        """Update all UI components with current battle state using the UI manager."""
        try:
            # Ensure compact window is initialized if needed
            if not self.compact_window and hasattr(self, 'show_compact_mode'):
                self.show_compact_mode(self.current_enemy, self.perform_attack, lambda: self.perform_attack(True))
            
            # Delegate to UI manager
            self.ui_manager.update_battle_ui(self.current_enemy)
            
            # Log successful update
            logging.debug("Battle UI updated successfully via UI manager")
            
        except Exception as e:
            logging.error(f"Error in _update_battle_ui: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating battle UI")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI components after an attack using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.update_ui_after_attack(self.current_enemy, was_heavy)

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI elements after victory with enhanced feedback using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.update_ui_for_victory(xp_gained, self.coin_reward)

    def _validate_battle_start(self) -> bool:
        """
        Validate battle start conditions.
        
        Checks:
        - No active battle in progress
        - Game not paused
        - UI components ready
        """
        if self.battle_state.is_active:
            logging.warning("Battle already in progress")
            self._update_status("Battle already in progress")
            return False
            
        if self.paused:
            logging.warning("Cannot start battle while paused")
            self._update_status("Game is paused")
            return False
            
        # Check both battle manager and UI manager components
        battle_manager_ui_ready = all([self.enemy_panel, self.action_buttons, self.status_bar])
        ui_manager_ui_ready = all([self.ui_manager.enemy_panel, self.ui_manager.action_buttons, self.ui_manager.status_bar])
        
        if not (battle_manager_ui_ready and ui_manager_ui_ready):
            logging.warning("UI components not ready")
            # Log which components are missing for debugging
            if not battle_manager_ui_ready:
                logging.debug(f"Battle manager UI components missing: enemy_panel={bool(self.enemy_panel)}, "
                             f"action_buttons={bool(self.action_buttons)}, status_bar={bool(self.status_bar)}")
            if not ui_manager_ui_ready:
                logging.debug(f"UI manager components missing: enemy_panel={bool(self.ui_manager.enemy_panel)}, "
                             f"action_buttons={bool(self.ui_manager.action_buttons)}, status_bar={bool(self.ui_manager.status_bar)}")
            return False
            
        return True

    def connect_signals(self, hotkey_listener) -> None:
        """Connect battle-related hotkey signals."""
        try:
            # Store hotkey listener reference
            self.hotkey_listener = hotkey_listener
            
            # Connect attack signals directly
            hotkey_listener.normal_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=False)
            )
            hotkey_listener.heavy_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=True)
            )
            hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
            
            # Mark signals as connected
            self.signals_connected = True
            
            # Update UI if available
            if self.status_bar:
                self.status_bar.showMessage("Battle controls ready", 2000)
            
            logging.info("Battle hotkeys connected successfully")
            
        except Exception as e:
            logging.error(f"Error connecting battle signals: {e}")

    def set_ui_components(self, 
                         story_display=None,
                         enemy_panel=None,
                         action_buttons=None,
                         player_panel=None,
                         status_bar=None,
                         tasks_left_label=None,
                         main_window=None) -> None:
        """Set UI component references."""
        try:
            # Set components in the BattleManager
            self.story_display = story_display
            self.enemy_panel = enemy_panel
            self.action_buttons = action_buttons
            self.player_panel = player_panel
            self.status_bar = status_bar
            self.tasks_left_label = tasks_left_label
            self.main_window = main_window
            
            # Also set components in the UI Manager
            self.ui_manager.set_ui_components(
                story_display=story_display,
                enemy_panel=enemy_panel,
                action_buttons=action_buttons,
                player_panel=player_panel,
                status_bar=status_bar,
                tasks_left_label=tasks_left_label,
                main_window=main_window,
                compact_window=self.compact_window
            )
            
            # Connect UI signals
            if self.action_buttons:
                try:
                    self.action_buttons.attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=False)
                    )
                    self.action_buttons.heavy_attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=True)
                    )
                    logging.debug("Action buttons signals connected")
                    
                    logging.info("UI components set and signals connected")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error connecting action button signals: {e}")
                    return False
            
            logging.info("UI components set successfully")
            return True
        
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")
            return False

    def update_tasks_left(self) -> None:
        """Update the tasks remaining display using the UI manager."""
        if self.current_enemy:
            # Delegate to UI manager
            self.ui_manager.update_tasks_left(self.current_enemy)

    def show_compact_mode(self) -> None:
        """Show compact battle window using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.show_compact_mode(
            self.current_enemy,
            lambda: self.perform_attack(is_heavy=False),
            lambda: self.perform_attack(is_heavy=True)
        )
        # Store reference to compact window for other methods
        self.compact_window = self.ui_manager.compact_window

    def hide_compact_mode(self) -> None:
        """Hide compact battle window using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.hide_compact_mode()
        # Keep reference in sync
        self.compact_window = self.ui_manager.compact_window

    def toggle_pause(self) -> None:
        """Toggle battle pause state."""
        try:
            # FIX: Attempt to repair battle state before toggling pause
            self.repair_battle_state()
            
            # FIX: Make sure battle is marked as active when unpausing
            if self.paused and self.current_enemy is not None:
                self.battle_state.is_active = True
            
            # Toggle the central pause state
            self.paused = not self.paused
            status = "paused" if self.paused else "resumed"
            logging.debug(f"Toggling pause state to: {status}")

            # Update UI components using the UI manager
            self.ui_manager.update_pause_state(self.paused)

            # Update battle state timing
            current_time = time.time()
            if self.paused:
                self.battle_state.paused_time = current_time
                self.paused_time = current_time
            elif self.battle_state.paused_time:
                pause_duration = current_time - self.battle_state.paused_time
                self.battle_state.total_pause_duration += pause_duration
                self.total_pause_duration += pause_duration
                self.battle_state.paused_time = None
                self.paused_time = None

            # Validate pause state consistency
            self._validate_pause_state()
        
            self._update_status(f"Battle {status}")
    
        except Exception as e:
            logging.error(f"Error toggling pause: {e}")
            self._show_error("Failed to toggle pause state")

    def _validate_pause_state(self) -> None:
        """Validate that pause state is consistent across all components."""
        try:
            # Check compact window state
            if self.compact_window and self.compact_window._is_paused != self.paused:
                logging.warning("Pause state mismatch detected in compact window")
                self.compact_window.update_pause_state(self.paused)
        
            # Check enemy panel state
            if self.enemy_panel and hasattr(self.enemy_panel, '_is_paused'):
                if self.enemy_panel._is_paused != self.paused:
                    logging.warning("Pause state mismatch detected in enemy panel")
                    self.enemy_panel.update_pause_state(self.paused)
        
            # Check action buttons state
            if self.action_buttons and self.action_buttons.isEnabled() == self.paused:
                logging.warning("Action buttons state inconsistent with pause state")
                self.action_buttons.setEnabled(not self.paused)
            
            logging.debug(f"Pause state validation complete. Current state: {self.paused}")
            
        except Exception as e:
            logging.error(f"Error validating pause state: {e}")

    def is_in_battle(self) -> bool:
        """Check if currently in battle."""
        return bool(
            self.battle_state.is_active and 
            self.current_enemy and 
            self.battle_state.enemy_hp > 0
        )
        
    # FIX: Add new repair_battle_state method
    def repair_battle_state(self) -> None:
        """Attempt to repair inconsistent battle state."""
        try:
            # If we have an enemy but battle isn't active, restore state
            if self.current_enemy is not None and not self.battle_state.is_active:
                logging.warning("Repairing inconsistent battle state")
                self.battle_state.is_active = True
                self.battle_state.enemy_hp = self.current_enemy.current_hp
                self.battle_state.enemy_max_hp = self.current_enemy.max_hp
                self.battle_state.enemy_name = self.current_enemy.name
                self.battle_state.task_name = self.current_enemy.task_name
                
                # Update UI to reflect repaired state
                self._update_battle_ui()
                self._update_status("Battle state repaired")
                
        except Exception as e:
            logging.error(f"Error repairing battle state: {e}")

    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.current_enemy

    def _update_status(self, message: str, timeout: int = 0) -> None:
        """Update status bar with message."""
        # Delegate to UI manager
        self.ui_manager.update_status(message, timeout)

    def _show_error(self, message: str) -> None:
        """Show error message to user using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.show_error(message)

    def end_battle(self) -> None:
        """End the current battle and clean up."""
        try:
            logging.debug("Ending battle")
            
            # Update battle state
            self.battle_state.is_active = False
            self.current_enemy = None
            self.battle_state.enemy_hp = 0
            
            # Update UI components using the UI manager
            self.ui_manager.update_ui_for_battle_end()
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")
            self._show_error("Error ending battle")
            
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
            
            # Clean up UI components using the UI manager
            self.ui_manager.cleanup_ui()
            
            # Reset state
            self.battle_state = BattleState()
            self.current_enemy = None
            self.paused = False
            
            # Disconnect signals if connected
            if self.signals_connected:
                self._disconnect_signals()
            
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
            self.battle_state = BattleState()
            self.current_enemy = None
            
            logging.warning("Emergency cleanup performed")
            
        except Exception as e:
            logging.critical(f"Emergency cleanup failed: {e}")
            
    def _disconnect_signals(self):
        """Disconnect all signal connections."""
        try:
            # Disconnect UI signals
            if self.action_buttons:
                try:
                    self.action_buttons.attack_clicked.disconnect()
                    self.action_buttons.heavy_attack_clicked.disconnect()
                except Exception:
                    pass
                    
            # Clear callbacks
            self.callbacks = BattleCallbacks()
            
            self.signals_connected = False
            logging.debug("Battle signals disconnected")
            
        except Exception as e:
            logging.error(f"Error disconnecting signals: {e}")

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
        # Check if battle is active first
        if not self.battle_state.is_active:
            logging.warning("Attack validation failed: battle is not active")
            if self.status_bar:
                self.status_bar.showMessage("No active battle", 2000)
            return False
            
        # Check if enemy exists
        if self.current_enemy is None:
            logging.warning("Attack validation failed: no current enemy")
            if self.status_bar:
                self.status_bar.showMessage("No enemy to attack", 2000)
            return False
            
        # Check if battle is paused
        if self.paused:
            logging.warning("Attack validation failed: battle is paused (press # to unpause)")
            if self.status_bar:
                self.status_bar.showMessage("Battle is paused - press # to unpause", 2000)
            return False
            
        # Check if enemy has HP attribute
        if not hasattr(self.current_enemy, 'current_hp'):
            logging.warning("Attack validation failed: enemy has no HP attribute")
            if self.status_bar:
                self.status_bar.showMessage("Enemy data error", 2000)
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
        self.completed_battle_nodes.add(node_key)
        logging.info(f"Marked battle node {node_key} as completed")
        
    def handle_chapter_complete(self) -> None:
        """Display chapter completion message using the UI manager."""
        try:
            # Delegate to UI manager
            self.ui_manager.handle_chapter_complete()
            logging.debug("Chapter completion delegated to UI manager")
            
        except Exception as e:
            logging.error(f"Error handling chapter completion: {e}")

    def _batch_ui_update(self, updates: dict) -> None:
        """
        Perform multiple UI updates in a single batch.
        Delegates to the UI manager's batch_ui_update method.
        
        Args:
            updates: Dictionary of update functions to execute
        """
        # Delegate to UI manager
        self.ui_manager.batch_ui_update(updates)

    def _update_battle_ui(self) -> None:
        """Update all UI components with current battle state using the UI manager."""
        try:
            # Ensure compact window is initialized if needed
            if not self.compact_window and hasattr(self, 'show_compact_mode'):
                self.show_compact_mode(self.current_enemy, self.perform_attack, lambda: self.perform_attack(True))
            
            # Delegate to UI manager
            self.ui_manager.update_battle_ui(self.current_enemy)
            
            # Log successful update
            logging.debug("Battle UI updated successfully via UI manager")
            
        except Exception as e:
            logging.error(f"Error in _update_battle_ui: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating battle UI")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI components after an attack using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.update_ui_after_attack(self.current_enemy, was_heavy)

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI elements after victory with enhanced feedback using the UI manager."""
        # Delegate to UI manager
        self.ui_manager.update_ui_for_victory(xp_gained, self.coin_reward)

    def _validate_battle_start(self) -> bool:
        """
        Validate battle start conditions.
        
        Checks:
        - No active battle in progress
        - Game not paused
        - UI components ready
        """
        if self.battle_state.is_active:
            logging.warning("Battle already in progress")
            self._update_status("Battle already in progress")
            return False
            
        if self.paused:
            logging.warning("Cannot start battle while paused")
            self._update_status("Game is paused")
            return False
            
        # Check both battle manager and UI manager components
        battle_manager_ui_ready = all([self.enemy_panel, self.action_buttons, self.status_bar])
        ui_manager_ui_ready = all([self.ui_manager.enemy_panel, self.ui_manager.action_buttons, self.ui_manager.status_bar])
        
        if not (battle_manager_ui_ready and ui_manager_ui_ready):
            logging.warning("UI components not ready")
            # Log which components are missing for debugging
            if not battle_manager_ui_ready:
                logging.debug(f"Battle manager UI components missing: enemy_panel={bool(self.enemy_panel)}, "
                             f"action_buttons={bool(self.action_buttons)}, status_bar={bool(self.status_bar)}")
            if not ui_manager_ui_ready:
                logging.debug(f"UI manager components missing: enemy_panel={bool(self.ui_manager.enemy_panel)}, "
                             f"action_buttons={bool(self.ui_manager.action_buttons)}, status_bar={bool(self.ui_manager.status_bar)}")
            return False
            
        return True

    def connect_signals(self, hotkey_listener) -> None:
        """Connect battle-related hotkey signals."""
        try:
            # Store hotkey listener reference
            self.hotkey_listener = hotkey_listener
            
            # Connect attack signals directly
            hotkey_listener.normal_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=False)
            )
            hotkey_listener.heavy_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=True)
            )
            hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
            
            # Mark signals as connected
            self.signals_connected = True
            
            # Update UI if available
            if self.status_bar:
                self.status_bar.showMessage("Battle controls ready", 2000)
            
            logging.info("Battle hotkeys connected successfully")
            
        except Exception as e:
            logging.error(f"Error connecting battle signals: {e}")

    def set_ui_components(self, 
                         story_display=None,
                         enemy_panel=None,
                         action_buttons=None,
                         player_panel=None,
                         status_bar=None,
                         tasks_left_label=None,
                         main_window=None) -> None:
        """Set UI component references."""
        try:
            # Set components in the BattleManager
            self.story_display = story_display
            self.enemy_panel = enemy_panel
            self.action_buttons = action_buttons
            self.player_panel = player_panel
            self.status_bar = status_bar
            self.tasks_left_label = tasks_left_label
            self.main_window = main_window
            
            # Also set components in the UI Manager
            self.ui_manager.set_ui_components(
                story_display=story_display,
                enemy_panel=enemy_panel,
                action_buttons=action_buttons,
                player_panel=player_panel,
                status_bar=status_bar,
                tasks_left_label=tasks_left_label,
                main_window=main_window,
                compact_window=self.compact_window
            )
            
            # Connect UI signals
            if self.action_buttons:
                try:
                    self.action_buttons.attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=False)
                    )
                    self.action_buttons.heavy_attack_clicked.connect(
                        lambda: self.perform_attack(is_heavy=True)
                    )
                    logging.debug("Action buttons signals connected")
                    
                    logging.info("UI components set and signals connected")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error connecting action button signals: {e}")
                    return False
            
            logging.info("UI components set successfully")
            return True
        
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")
            return False

    def update_tasks_left(self) -> None:
        """Update the tasks remaining display using the UI manager."""
        if self.current_enemy:
            # Delegate to UI manager
            self.ui_manager.update_tasks_left(self.current_enemy)

    def show_compact_mode(self) -> None:
        """Show compact battle window using the UI manager."""
        try:
            if self.is_in_battle():
                # Delegate to UI manager
                self.ui_manager.show_compact_mode(
                    self.current_enemy,
                    lambda: self.perform_attack(is_heavy=False),
                    lambda: self.perform_attack(is_heavy=True)
                )
                # Store reference to compact window for other methods
                self.compact_window = self.ui_manager.compact_window
                
                # Enable attack hotkeys for compact mode
                if hasattr(self, 'hotkey_listener'):
                    self.hotkey_listener.enable()
                    logging.debug("Enabled hotkeys for compact mode")
                    
                logging.debug("Compact mode shown via UI manager")
        except Exception as e:
            logging.error(f"Error showing compact mode: {e}")