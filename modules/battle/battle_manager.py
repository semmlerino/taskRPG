# modules/battle/battle_manager.py
"""
Refactored battle management system for TaskRPG.

This module contains the improved battle system that separates battle logic
from UI management, using the event system to communicate between components.
"""

# Standard library imports
import logging
import random
import time
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum, auto

# Project imports: Core functionality
from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.players.player import Player

# Project imports: Battle components
from modules.battle.enemy import Enemy
from modules.battle.battle_state import BattleState, BattleStatus
from modules.battle.battle_event_system import BattleEventType, BattleEvent, event_dispatcher

# Type checking imports
if TYPE_CHECKING:
    from modules.ui.components.story_display import StoryDisplay
    from modules.ui.components.enemy_panel import EnemyPanel
    from modules.ui.components.action_buttons import ActionButtons
    from modules.ui.components.player_panel import PlayerPanel
    from modules.ui.main_window import TaskRPG
    from modules.battle.ui.battle_ui_manager import BattleUIManager

class BattleManager:
    """
    Refactored battle management system.
    
    This class focuses exclusively on battle logic, delegating UI updates
    to the BattleUIManager through the event system.
    """
    
    def __init__(self, task_manager: TaskManager, player: Player):
        """Initialize battle manager with core systems."""
        self.task_manager = task_manager
        self.player = player
        
        # Initialize battle state - single source of truth for battle data
        self.battle_state = BattleState()
        
        # Set default reward parameters
        self.battle_state.set_reward_parameters(
            coin_reward=5,  # Default coins per victory
            xp_base=100,    # Base XP for victories
            xp_multiplier=1.0  # Multiplier for XP calculations
        )
        
        # UI Manager - will be set after initialization
        self.ui_manager = None
        
        # Register event handlers
        self._register_event_handlers()
        
        logging.info("BattleManager initialized with task manager and player")

    def _register_event_handlers(self):
        """Register handlers for battle events."""
        # Listen for pause toggle events
        event_dispatcher.subscribe(
            BattleEventType.PAUSE_TOGGLED,
            self._handle_pause_toggle_event
        )
        
        # Listen for enemy defeated events
        event_dispatcher.subscribe(
            BattleEventType.ENEMY_DEFEATED,
            self._handle_enemy_defeated_event
        )

    def _handle_pause_toggle_event(self, event: BattleEvent):
        """Handle pause toggle events."""
        # Only handle if we're in a battle
        if self.battle_state.is_in_battle():
            # Extract the source of the event to prevent recursive handling
            source = event.data.get('source', None)
            
            # Only process events that didn't come from this instance
            if source != 'battle_manager':
                logging.debug(f"Processing pause toggle from external source: {source}")
                # Set the _toggling_pause flag to prevent recursive event processing
                self.battle_state._toggling_pause = True
                self.battle_state.toggle_pause()
                # Reset the flag after toggling
                self.battle_state._toggling_pause = False

    def _handle_enemy_defeated_event(self, event: BattleEvent):
        """Handle enemy defeated events."""
        self._handle_victory()

    def set_ui_manager(self, ui_manager: 'BattleUIManager'):
        """Set the UI manager reference."""
        self.ui_manager = ui_manager
        logging.info("UI manager set for Battle Manager")

    def start_battle(self, battle_info: Dict[str, Any]) -> bool:
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
            
            # Validate battle start conditions
            if self.battle_state.is_in_battle():
                logging.warning("Battle already in progress")
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
            
            # Update battle state to start the battle
            self.battle_state.start_battle(enemy)
            
            # Publish battle info for display
            event_dispatcher.publish(BattleEvent(
                BattleEventType.UI_UPDATE_REQUESTED,
                {
                    "action": "display_battle_message",
                    "message": battle_info.get('message', "A new enemy appears!")
                }
            ))
            
            logging.info(f"Battle started with {enemy_name} (Task: {task.name})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start battle: {e}")
            # Publish error event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ERROR_OCCURRED,
                {
                    "message": "Error starting battle",
                    "details": str(e)
                }
            ))
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
            
            # First check if a battle is actually in progress
            if not self.battle_state.is_in_battle():
                logging.debug("Attack attempted but no battle is in progress")
                return False
            
            # Validate attack conditions
            if not self.battle_state.validate_attack(is_heavy):
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
            
            # Apply damage to enemy
            enemy.take_damage(damage)
            
            # Update battle state with new HP
            self.battle_state.update_enemy_hp(enemy.current_hp)
            
            # Publish UI update event for damage feedback
            event_dispatcher.publish(BattleEvent(
                BattleEventType.UI_UPDATE_REQUESTED,
                {
                    "action": "show_attack_feedback",
                    "attack_type": attack_type,
                    "damage": damage,
                    "old_hp": old_hp,
                    "new_hp": enemy.current_hp
                }
            ))
            
            # Log successful attack
            logging.info(f"{attack_type.capitalize()} attack successful: Enemy HP reduced from {old_hp} to {enemy.current_hp}")
            
            return True

        except Exception as e:
            logging.error(f"Error performing attack: {e}")
            # Publish error event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ERROR_OCCURRED,
                {
                    "message": "Error processing attack",
                    "details": str(e)
                }
            ))
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
            xp = max(self.battle_state.xp_base, enemy.max_hp * self.battle_state.xp_multiplier)
            
            # Apply modifiers based on performance
            if self.battle_state.turns_taken < enemy.max_hp:
                xp = int(xp * 1.2)  # 20% bonus for efficiency
            
            # Award XP
            self.player.gain_experience(xp)
            
            # Award coins using the configurable coin_reward value
            self.player.earn_coins(self.battle_state.coin_reward)
            
            logging.info(f"Victory! Awarded {xp} XP and {self.battle_state.coin_reward} coins")
            
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
            
            # Mark battle as completed in battle state
            self.battle_state.record_victory(xp)
            
            logging.info(f"Victory handled successfully. XP gained: {xp}")
                
        except Exception as e:
            logging.error(f"Error handling victory: {e}")
            # Publish error event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ERROR_OCCURRED,
                {
                    "message": "Error processing victory",
                    "details": str(e)
                }
            ))

    def connect_signals(self, hotkey_listener) -> None:
        """Store hotkey listener for later use."""
        try:
            # Connect hotkey signals
            hotkey_listener.normal_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=False)
            )
            hotkey_listener.heavy_attack_signal.connect(
                lambda: self.perform_attack(is_heavy=True)
            )
            hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
            
            logging.info("Hotkey listener connected with battle manager")
            
        except Exception as e:
            logging.error(f"Error connecting hotkey listener: {e}")

    def is_in_battle(self) -> bool:
        """Check if currently in battle."""
        return self.battle_state.is_in_battle()
        
    def get_current_enemy(self) -> Optional[Enemy]:
        """Get the current enemy if any."""
        return self.battle_state.get_current_enemy()

    def end_battle(self) -> None:
        """End the current battle and clean up."""
        try:
            logging.debug("Ending battle")
            
            # Update battle state
            self.battle_state.end_battle()
            
            logging.info("Battle ended successfully")
            
        except Exception as e:
            logging.error(f"Error ending battle: {e}")
            # Publish error event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ERROR_OCCURRED,
                {
                    "message": "Error ending battle",
                    "details": str(e)
                }
            ))
            
    def cleanup(self) -> None:
        """
        Clean up battle manager resources with proper state management.
        
        Handles:
        - State reset
        - Event handlers unsubscription
        - Memory cleanup
        """
        try:
            logging.info("Starting battle manager cleanup")
            
            # Reset state
            self.battle_state.reset()
            
            # Unsubscribe from events
            event_dispatcher.unsubscribe(
                BattleEventType.PAUSE_TOGGLED,
                self._handle_pause_toggle_event
            )
            event_dispatcher.unsubscribe(
                BattleEventType.ENEMY_DEFEATED,
                self._handle_enemy_defeated_event
            )
            
            logging.info("Battle manager cleanup complete")
            
        except Exception as e:
            logging.error(f"Error during battle manager cleanup: {e}")
            # Emergency cleanup
            self._emergency_cleanup()

    def _emergency_cleanup(self):
        """Emergency cleanup for critical failures."""
        try:
            # Reset state
            self.battle_state.reset()
            
            # Clear all event subscribers
            event_dispatcher.clear_subscribers()
            
            logging.warning("Emergency cleanup performed")
            
        except Exception as e:
            logging.critical(f"Emergency cleanup failed: {e}")

    def mark_battle_complete(self, node_key: str):
        """Mark a battle node as completed."""
        self.battle_state.mark_battle_complete(node_key)
        logging.info(f"Marked battle node {node_key} as completed")
        
    def handle_chapter_complete(self) -> None:
        """Handle chapter completion event."""
        # Publish UI update event for chapter completion
        event_dispatcher.publish(BattleEvent(
            BattleEventType.UI_UPDATE_REQUESTED,
            {
                "action": "show_chapter_complete"
            }
        ))
        logging.debug("Chapter completion event published")

    def toggle_pause(self) -> None:
        """Toggle battle pause state."""
        try:
            # Only toggle if in battle
            if self.battle_state.is_in_battle():
                self.battle_state.toggle_pause()
                logging.debug(f"Battle pause toggled: {self.battle_state.is_paused()}")
            else:
                logging.debug("Toggle pause attempted but no battle is in progress")
        
        except Exception as e:
            logging.error(f"Error toggling pause: {e}")
            # Publish error event
            event_dispatcher.publish(BattleEvent(
                BattleEventType.ERROR_OCCURRED,
                {
                    "message": "Failed to toggle pause state",
                    "details": str(e)
                }
            ))

    def set_coin_reward(self, value: int) -> None:
        """Set the coin reward value for victories."""
        old_value = self.battle_state.coin_reward
        self.battle_state.coin_reward = value
        logging.info(f"Coin reward updated from {old_value} to {value}")
