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
from dataclasses import dataclass
from enum import Enum, auto

# PyQt5 imports
from PyQt5.QtWidgets import QApplication, QMessageBox, QStatusBar, QLabel
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtSignal

# Project imports: Core functionality
from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.players.player import Player

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

@dataclass
class Enemy:
    """Represents an enemy in battle."""
    name: str
    max_hp: int
    task_name: str
    current_hp: Optional[int] = None

    def __post_init__(self):
        """Initialize derived values after creation."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        logging.debug(f"Enemy initialized - Name: {self.name}, Task: {self.task_name}, Max HP: {self.max_hp}, Current HP: {self.current_hp}")

    def take_damage(self, amount: int) -> None:
        """Reduce enemy HP by damage amount."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = max(0, self.current_hp - amount)
        logging.debug(f"{self.name} takes {amount} damage. Current HP: {self.current_hp}")

    def is_defeated(self) -> bool:
        """Check if enemy is defeated (HP <= 0)."""
        return self.current_hp <= 0

    def heal(self, amount: int) -> None:
        """Heal enemy by specified amount, up to max HP."""
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        logging.debug(f"{self.name} healed for {amount}. Current HP: {self.current_hp}")

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

@dataclass
class BattleCallbacks:
    """Container for battle event callbacks."""
    on_battle_start: Optional[Callable] = None
    on_battle_end: Optional[Callable] = None
    on_attack: Optional[Callable] = None
    on_state_change: Optional[Callable] = None
    on_victory: Optional[Callable] = None

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
            if not self._validate_attack():
                return False

            # Track attack timing
            current_time = time.time()
            self.battle_state.last_attack_time = current_time
            self.last_attack_time = current_time
            
            # Calculate and apply damage
            damage = random.randint(2, 4) if is_heavy else 1
            
            old_hp = self.current_enemy.current_hp
            self.current_enemy.take_damage(damage)
            new_hp = self.current_enemy.current_hp
            
            # Update battle state
            self.battle_state.enemy_hp = new_hp
            self.battle_state.attacks_performed += 1
            self.battle_state.turns_taken += 1
            self.battle_state.last_attack_type = "heavy" if is_heavy else "normal"
            
            # Update internal stats too
            self.attacks_performed += 1
            self.turns_taken += 1
            self.last_attack_type = "heavy" if is_heavy else "normal"
            
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
            
            # New coin reward (6 per battle)
            self.player.earn_coins(6)
            
            logging.info(f"Victory! Awarded {xp} XP and 7 coins")
            
            # Handle task completion and count decrementing
            if self.current_enemy and self.current_enemy.task_name:
                task = self.task_manager.get_task(self.current_enemy.task_name)
                if task:
                    was_decremented = False
                    # Handle count decrementing
                    if task.count > 0:
                        task.count -= 1
                        was_decremented = True
                        if task.count == 0 and was_decremented:
                            task.active = False
                    
                    # For daily/weekly tasks, only deactivate if count was decremented
                    if was_decremented and (task.is_daily or task.is_weekly):
                        task.deactivate()  # This will handle daily task reactivation logic
                    elif task.count == 0 and was_decremented:
                        task.active = False
                    
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
        
        Args:
            updates: Dictionary of update functions to execute
        """
        try:
            # Temporarily disable window updates if possible
            if self.main_window:
                self.main_window.setUpdatesEnabled(False)
            
            # Execute all updates
            for update_name, update_func in updates.items():
                try:
                    update_func()
                except Exception as e:
                    logging.error(f"Error in UI update '{update_name}': {e}")
                    
        finally:
            # Re-enable window updates
            if self.main_window:
                self.main_window.setUpdatesEnabled(True)
                self.main_window.repaint()

    def _update_battle_ui(self) -> None:
        """Update all UI components with current battle state."""
        try:
            updates = {
                'enemy_panel': lambda: self.enemy_panel.update_panel(self.current_enemy) if self.enemy_panel else None,
                'compact_window': lambda: self.compact_window.update_display(self.current_enemy) if self.compact_window else None,
                'tasks_left': lambda: self.update_tasks_left() if hasattr(self, 'update_tasks_left') else None,
                'action_buttons': lambda: self.action_buttons.show_attack_buttons() if self.action_buttons else None,
                'story_display': lambda: (
                    self.story_display.story_text.append(
                        "<div class='battle-status' style='margin: 10px 0; padding: 10px; background-color: rgba(255, 0, 0, 0.1); border-left: 4px solid #ff0000;'>"
                        f"<p><b>{self.current_enemy.name}</b> - HP: {self.current_enemy.current_hp}/{self.current_enemy.max_hp}</p>"
                        "</div>"
                    ) if self.story_display and hasattr(self.story_display, 'story_text') else None
                ),
                'status_bar': lambda: self.status_bar.showMessage("Battle in progress!") if self.status_bar else None
            }
            
            self._batch_ui_update(updates)
            logging.debug("Battle UI updated successfully")
                
        except Exception as e:
            logging.error(f"Error updating battle UI: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating battle display")

    def _update_ui_after_attack(self, was_heavy: bool) -> None:
        """Update UI components after an attack."""
        if self.enemy_panel:
            self.enemy_panel.update_panel(self.current_enemy)
        if self.compact_window:
            self.compact_window.update_display(self.current_enemy)
        self.update_tasks_left()
        
        attack_type = "Heavy attack" if was_heavy else "Attack"
        if self.status_bar:
            self.status_bar.showMessage(f"{attack_type} landed!")

    def _update_ui_for_victory(self, xp_gained: int) -> None:
        """Update UI elements after victory with enhanced feedback."""
        try:
            victory_message = (
                "<div class='victory-message' style='text-align: center;'>"
                "<h3>Victory!</h3>"
                f"<p>You gained <b>{xp_gained}</b> XP and <b>7</b> coins!</p>"
                "</div>"
            )
            
            # Update UI components
            updates = {
                'story_display': lambda: self.story_display.append_text(victory_message) if self.story_display else None,
                'status_bar': lambda: self.status_bar.showMessage("Victory!") if self.status_bar else None,
                'enemy_panel': lambda: self.enemy_panel.update_panel(None) if self.enemy_panel else None,
                'player_panel': lambda: self.player_panel.update_panel() if self.player_panel else None,
                'action_buttons': lambda: (
                    self.action_buttons.hide_attack_buttons(),
                    self.action_buttons.next_button.show()
                ) if self.action_buttons else None
            }
            
            self._batch_ui_update(updates)
            
            # Trigger victory animation if enabled
            if self.main_window and hasattr(self.main_window, 'trigger_victory_animation'):
                QTimer.singleShot(0, self.main_window.trigger_victory_animation)
            
            logging.info("Victory UI updates completed")
                
        except Exception as e:
            logging.error(f"Error updating UI for victory: {e}")
            if self.status_bar:
                self.status_bar.showMessage("Error updating victory display")

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
            
        if not all([self.enemy_panel, self.action_buttons, self.status_bar]):
            logging.warning("UI components not ready")
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
            self.story_display = story_display
            self.enemy_panel = enemy_panel
            self.action_buttons = action_buttons
            self.player_panel = player_panel
            self.status_bar = status_bar
            self.tasks_left_label = tasks_left_label
            self.main_window = main_window
            
            # Connect UI signals
            if self.action_buttons:
                self.action_buttons.attack_clicked.connect(
                    lambda: self.perform_attack(is_heavy=False)
                )
                self.action_buttons.heavy_attack_clicked.connect(
                    lambda: self.perform_attack(is_heavy=True)
                )
                
            logging.info("UI components set and signals connected")
            
        except Exception as e:
            logging.error(f"Error setting UI components: {e}")

    def update_tasks_left(self) -> None:
        """Update the tasks remaining display."""
        try:
            if self.current_enemy and self.tasks_left_label:
                current_hp = self.battle_state.enemy_hp
                tasks_left = max(0, current_hp)
                self.tasks_left_label.setText(str(tasks_left))

                # Update compact window if it exists
                if self.compact_window:
                    self.compact_window.update_tasks(tasks_left)
                    
            logging.debug(f"Tasks left updated: {tasks_left if 'tasks_left' in locals() else 'None'}")
                    
        except Exception as e:
            logging.error(f"Error updating tasks left: {e}")

    def show_compact_mode(self) -> None:
        """Show compact battle window."""
        try:
            if not self.compact_window and self.is_in_battle():
                logging.debug("Creating new compact battle window")
                self.compact_window = CompactBattleWindow()
                
                # Position the window
                screen = QApplication.primaryScreen()
                screen_geo = screen.availableGeometry()
                margin = 10
                x = screen_geo.width() - self.compact_window.width() - margin
                y = margin
                self.compact_window.move(x, y)
                
                # Initialize pause state before showing window
                self.compact_window.update_pause_state(self.paused)
                logging.debug(f"Initialized compact window pause state: {self.paused}")
                
                # Update display if we have an enemy
                if self.current_enemy:
                    self.compact_window.update_display(self.current_enemy)
                    logging.debug("Updated compact window with enemy display")
                
                # Show and raise window
                self.compact_window.show()
                self.compact_window.raise_()
                
                # Enable attack hotkeys for compact mode
                if hasattr(self, 'hotkey_listener'):
                    self.hotkey_listener.set_attack_hotkeys_enabled(True)
                    logging.debug("Attack hotkeys enabled for compact mode")
                
                # Validate state consistency after showing
                self._validate_pause_state()
                
                logging.info(f"Compact battle window shown and initialized with pause state: {self.paused}")
                
        except Exception as e:
            logging.error(f"Error showing compact window: {e}")

    def hide_compact_mode(self) -> None:
        """Hide and cleanup compact battle window."""
        try:
            if self.compact_window:
                # Store the current pause state before cleanup
                was_paused = self.compact_window._is_paused
                
                # Cleanup the window
                self.compact_window.close()
                self.compact_window.deleteLater()
                self.compact_window = None
                
                # Disable attack hotkeys when compact mode is hidden
                if hasattr(self, 'hotkey_listener'):
                    self.hotkey_listener.set_attack_hotkeys_enabled(False)
                    logging.debug("Attack hotkeys disabled after compact mode")
                
                # Ensure main window components reflect the correct pause state
                self.paused = was_paused
                if self.enemy_panel:
                    self.enemy_panel.update_pause_state(was_paused)
                if self.action_buttons:
                    self.action_buttons.setEnabled(not was_paused)
                
                # Validate state consistency
                self._validate_pause_state()
                
                logging.info(f"Compact battle window hidden and cleaned up. Pause state synchronized: {was_paused}")
                
        except Exception as e:
            logging.error(f"Error hiding compact window: {e}")
            # Attempt force cleanup
            self.compact_window = None

    def toggle_pause(self) -> None:
        """Toggle battle pause state."""
        try:
            # Toggle the central pause state
            self.paused = not self.paused
            status = "paused" if self.paused else "resumed"
            logging.debug(f"Toggling pause state to: {status}")

            # Synchronize UI components in a specific order to maintain consistency
            # 1. First update main window components
            if self.action_buttons:
                self.action_buttons.setEnabled(not self.paused)
                logging.debug("Action buttons pause state updated")
    
            if self.enemy_panel:
                self.enemy_panel.update_pause_state(self.paused)
                logging.debug("Enemy panel pause state updated")

            # 2. Then update compact window if it exists
            if self.compact_window:
                self.compact_window.update_pause_state(self.paused)
                logging.debug("Compact window pause state updated")

            # 3. Update battle state timing
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

            # 4. Validate pause state consistency
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

    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.current_enemy

    def _update_status(self, message: str) -> None:
        """Update status bar with message."""
        if self.status_bar:
            self.status_bar.showMessage(message)

    def _show_error(self, message: str) -> None:
        """Show error message to user."""
        if self.status_bar:
            self.status_bar.showMessage(message)
        logging.error(message)

    def end_battle(self) -> None:
        """End the current battle and clean up."""
        try:
            logging.debug("Ending battle")
            
            # Update battle state
            self.battle_state.is_active = False
            self.current_enemy = None
            self.battle_state.enemy_hp = 0
            
            # Hide compact window
            self.hide_compact_mode()
            
            # Ensure main window is visible and focused
            if self.main_window:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                
                # Release any keyboard grab
                self.main_window.releaseKeyboard()
                
                # Force focus to the main window
                QTimer.singleShot(100, lambda: (
                    self.main_window.raise_(),
                    self.main_window.activateWindow()
                ))
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")
            
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
            
            # Clean up windows
            self.hide_compact_mode()
            
            # Reset state
            self.battle_state = BattleState()
            self.current_enemy = None
            self.paused = False
            
            # Release window focus
            if self.main_window:
                self.main_window.releaseKeyboard()
            
            # Update UI components
            cleanup_updates = {
                'enemy_panel': lambda: self.enemy_panel.update_panel(None) if self.enemy_panel else None,
                'action_buttons': lambda: self.action_buttons.hide_attack_buttons() if self.action_buttons else None,
                'tasks_left': lambda: self.tasks_left_label.setText("0") if self.tasks_left_label else None
            }
            
            self._batch_ui_update(cleanup_updates)
            
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
            if self.compact_window:
                self.compact_window.close()
                self.compact_window = None
            
            if self.main_window:
                self.main_window.releaseKeyboard()
                
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
        """
        Register callback functions for battle events.
        
        Args:
            on_battle_start: Called when battle starts
            on_battle_end: Called when battle ends
            on_attack: Called when attack performed
            on_state_change: Called when battle state changes
            on_victory: Called on victory
        """
        try:
            self.callbacks = BattleCallbacks(
                on_battle_start=on_battle_start,
                on_battle_end=on_battle_end,
                on_attack=on_attack,
                on_state_change=on_state_change,
                on_victory=on_victory
            )
            
            logging.debug("Battle callbacks registered")
            
        except Exception as e:
            logging.error(f"Error registering battle callbacks: {e}")

    def _validate_attack(self) -> bool:
        """Validate attack conditions."""
        validation_results = {
            "battle_active": self.battle_state.is_active,
            "enemy_exists": self.current_enemy is not None,
            "not_paused": not self.paused,
            "has_hp_attribute": hasattr(self.current_enemy, 'current_hp') if self.current_enemy else False
        }
        
        logging.debug(f"Attack validation results: {validation_results}")
        
        for key, value in validation_results.items():
            if not value:
                logging.warning(f"Attack validation failed: {key}")
                return False
                
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
        """Display chapter completion message."""
        try:
            completion_message = (
                "<div style='text-align: center;'>"
                "<br><b>Chapter Complete!</b><br>"
                "<p style='margin: 10px 0;'>You have completed all available tasks for now.</p>"
                "<p style='margin: 10px 0;'>Feel free to start a new chapter or take a break!</p>"
                "</div>"
            )
            
            if self.story_display:
                self.story_display.append_text(completion_message)
                
            if self.status_bar:
                self.status_bar.showMessage("Chapter complete!")
                
            logging.debug("Chapter completion message displayed")
            
        except Exception as e:
            logging.error(f"Error displaying chapter completion: {e}")