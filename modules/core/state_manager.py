# modules/core/state_manager.py

import threading
import logging
from typing import Dict, Any, Optional
from enum import Enum, auto

class GameState(Enum):
    """Possible game states."""
    INITIAL = auto()
    STORY = auto()
    BATTLE = auto()
    CHOICE = auto()
    PAUSED = auto()
    END = auto()

class StateContext:
    """Context for state transition."""
    def __init__(self, old_state: GameState, new_state: GameState, state_data: Dict[str, Any]):
        self.old_state = old_state
        self.new_state = new_state
        self.state_data = state_data

class StateManager:
    """Centralized state management for the application."""
    
    def __init__(self):
        self._state_lock = threading.Lock()
        self._current_state = GameState.INITIAL
        self._state_data: Dict[str, Any] = {}
        self._state_listeners = []
        
    def get_state(self) -> GameState:
        """Get current game state thread-safely."""
        with self._state_lock:
            return self._current_state
            
    def transition_state(self, new_state: GameState, state_data: dict = None):
        """Safely transition between states with validation and cleanup."""
        try:
            # Validate transition
            if not self._validate_transition(new_state):
                raise ValueError(f"Invalid state transition: {self._current_state} -> {new_state}")

            # Create state context
            context = StateContext(
                old_state=self._current_state,
                new_state=new_state,
                state_data=state_data or {}
            )

            # Perform pre-transition cleanup
            self._cleanup_current_state(context)

            # Update state
            old_state = self._current_state
            self._current_state = new_state
            self._state_data = state_data or {}

            # Initialize new state
            self._initialize_new_state(context)

            # Notify listeners
            self._notify_listeners(old_state, new_state)

        except Exception as e:
            self._handle_transition_error(e, new_state)

    def _cleanup_current_state(self, context: StateContext):
        """Clean up resources from current state."""
        cleanup_handlers = {
            GameState.BATTLE: self._cleanup_battle_state,
            GameState.STORY: self._cleanup_story_state,
            GameState.CHOICE: self._cleanup_choice_state,
            # Add handlers for other states
        }
        
        handler = cleanup_handlers.get(self._current_state)
        if handler:
            handler(context)

    def _initialize_new_state(self, context: StateContext):
        """Initialize resources for new state."""
        init_handlers = {
            GameState.BATTLE: self._init_battle_state,
            GameState.STORY: self._init_story_state,
            GameState.CHOICE: self._init_choice_state,
            # Add handlers for other states
        }
        
        handler = init_handlers.get(context.new_state)
        if handler:
            handler(context)

    def _validate_transition(self, new_state: GameState) -> bool:
        """Validate if the state transition is allowed."""
        # Define valid transitions
        valid_transitions = {
            GameState.INITIAL: [GameState.STORY],
            GameState.STORY: [GameState.BATTLE, GameState.CHOICE, GameState.END, GameState.PAUSED],
            GameState.BATTLE: [GameState.STORY, GameState.PAUSED],
            GameState.CHOICE: [GameState.STORY, GameState.PAUSED],
            GameState.PAUSED: [GameState.STORY, GameState.BATTLE, GameState.CHOICE],
            GameState.END: [GameState.INITIAL]
        }
        
        return new_state in valid_transitions.get(self._current_state, [])
        
    def add_listener(self, listener):
        """Add a state change listener."""
        if listener not in self._state_listeners:
            self._state_listeners.append(listener)
            
    def remove_listener(self, listener):
        """Remove a state change listener."""
        if listener in self._state_listeners:
            self._state_listeners.remove(listener)
            
    def _notify_listeners(self, old_state: GameState, new_state: GameState):
        """Notify all listeners of state change."""
        for listener in self._state_listeners:
            try:
                listener(old_state, new_state, self._state_data)
            except Exception as e:
                logging.error(f"Error notifying listener: {e}")

    def cleanup(self):
        """Clean up state manager resources."""
        with self._state_lock:
            self._state_listeners.clear()
            self._state_data.clear()
            self._current_state = GameState.INITIAL
