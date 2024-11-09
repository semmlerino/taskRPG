# modules/tasks/task_manager.py

import os
import json
import random
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from .task import Task

DEFAULT_TASKS = {
    "Example Task": {
        "min": 3,
        "max": 5,
        "active": True,
        "description": "An example task"
    }
}

class TaskManager:
    """Manages task loading, saving, and selection."""
    
    def __init__(self, filepath: str = None):
        """
        Initialize TaskManager with optional filepath.
        
        Args:
            filepath: Optional path to tasks JSON file. If None, uses default path.
        """
        if filepath is None:
            # Get absolute path to the data directory
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'data', 
                'tasks.json'
            )
        
        self.filepath = filepath
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()
        logging.info(f"TaskManager initialized with {len(self.tasks)} tasks")
        logging.info(f"File exists check: {os.path.exists(filepath)}")

    def load_tasks(self) -> None:
        """Load tasks from JSON file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate data structure
                if not isinstance(data, dict):
                    raise ValueError("Invalid task data format - expected dictionary")
                
                self.tasks = {}
                for name, task_data in data.items():
                    try:
                        # Handle both old and new format
                        if isinstance(task_data, Task):
                            self.tasks[name] = task_data
                        elif isinstance(task_data, dict):
                            # Validate required fields
                            if 'min' not in task_data or 'max' not in task_data:
                                logging.warning(f"Task '{name}' missing required fields, skipping")
                                continue
                            
                            self.tasks[name] = Task.from_dict(name, task_data)
                        else:
                            logging.warning(f"Invalid task data for '{name}', skipping")
                            continue
                            
                    except Exception as e:
                        logging.error(f"Error loading task '{name}': {e}")
                        continue
                
                logging.info(f"Loaded {len(self.tasks)} tasks from {self.filepath}")
            else:
                logging.warning(f"Task file not found: {self.filepath}")
                self._create_default_tasks()
        except Exception as e:
            logging.error(f"Error loading tasks: {e}")
            self._create_default_tasks()

    def save_tasks(self) -> bool:
        """
        Save tasks to JSON file.
        
        Returns:
            bool: True if save successful, False otherwise.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            
            data = {
                name: task.to_dict()
                for name, task in self.tasks.items()
            }
            
            # Validate data before saving
            for name, task_dict in data.items():
                if not isinstance(task_dict, dict):
                    logging.error(f"Invalid task data for '{name}'")
                    return False
                if 'min' not in task_dict or 'max' not in task_dict:
                    logging.error(f"Missing required fields for task '{name}'")
                    return False
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            logging.info(f"Saved {len(self.tasks)} tasks to {self.filepath}")
            return True
        except Exception as e:
            logging.error(f"Error saving tasks: {e}")
            return False

    def get_task(self, name: str) -> Optional[Task]:
        """
        Get a task by name.
        
        Args:
            name: Name of the task to retrieve.
            
        Returns:
            Optional[Task]: The task if found, None otherwise.
        """
        return self.tasks.get(name)

    def get_active_tasks(self) -> Dict[str, Task]:
        """
        Get all active tasks.
        
        Returns:
            Dict[str, Task]: Dictionary of active tasks keyed by name.
        """
        active_tasks = {
            name: task for name, task in self.tasks.items() 
            if task.is_active
        }
        logging.debug(f"Retrieved {len(active_tasks)} active tasks")
        return active_tasks

    def get_random_active_task(self) -> Optional[Task]:
        """
        Get a random active task.
        
        Returns:
            Optional[Task]: Random active task or None if no active tasks.
        """
        active_tasks = self.get_active_tasks()
        if not active_tasks:
            logging.warning("No active tasks available")
            return None
        chosen_task = random.choice(list(active_tasks.values()))
        logging.debug(f"Selected random task: {chosen_task.name}")
        return chosen_task

    def get_task_count(self, active_only: bool = True) -> int:
        """
        Get total number of tasks.
        
        Args:
            active_only: If True, only count active tasks. If False, count all tasks.
            
        Returns:
            int: Number of tasks.
        """
        if active_only:
            return len(self.get_active_tasks())
        return len(self.tasks)

    def get_active_tasks_count(self) -> int:
        """
        Get count of active tasks.
        
        Returns:
            int: Number of active tasks.
        """
        return self.get_task_count(active_only=True)

    def add_task(self, name: str, min_steps: int, max_steps: int, 
                 active: bool = True, description: Optional[str] = None) -> bool:
        """
        Add a new task.
        
        Args:
            name: Task name
            min_steps: Minimum steps required
            max_steps: Maximum steps allowed
            active: Whether task is active
            description: Optional task description
            
        Returns:
            bool: True if task added successfully, False otherwise.
        """
        try:
            if name in self.tasks:
                logging.warning(f"Task '{name}' already exists")
                return False
            
            # Validate input
            min_steps = max(1, int(min_steps))
            max_steps = max(min_steps, int(max_steps))
            
            self.tasks[name] = Task(
                name=name,
                min_steps=min_steps,
                max_steps=max_steps,
                active=active,
                description=description
            )
            logging.info(f"Added new task: {name}")
            return True
        except Exception as e:
            logging.error(f"Error adding task: {e}")
            return False

    def update_task(self, name: str, **kwargs) -> bool:
        """
        Update an existing task with provided parameters.
        
        Args:
            name: Task name
            **kwargs: Fields to update (min_steps, max_steps, active, description)
            
        Returns:
            bool: True if update successful, False otherwise.
        """
        try:
            if name not in self.tasks:
                logging.warning(f"Task '{name}' not found")
                return False
            
            task = self.tasks[name]
            
            # Handle min/max steps together to maintain consistency
            if 'min_steps' in kwargs or 'max_steps' in kwargs:
                new_min = kwargs.get('min_steps', task.min_steps)
                new_max = kwargs.get('max_steps', task.max_steps)
                
                # Ensure min <= max
                new_min = max(1, int(new_min))
                new_max = max(new_min, int(new_max))
                
                task.min_steps = new_min
                task.max_steps = new_max
            
            # Update other fields
            if 'active' in kwargs:
                task.active = bool(kwargs['active'])
            if 'description' in kwargs:
                task.description = kwargs['description']
                
            logging.info(f"Updated task: {name}")
            return True
        except Exception as e:
            logging.error(f"Error updating task: {e}")
            return False

    def delete_task(self, name: str) -> bool:
        """
        Delete a task.
        
        Args:
            name: Name of task to delete
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        try:
            if name not in self.tasks:
                logging.warning(f"Task '{name}' not found")
                return False
            
            del self.tasks[name]
            logging.info(f"Deleted task: {name}")
            return True
        except Exception as e:
            logging.error(f"Error deleting task: {e}")
            return False

    def _create_default_tasks(self) -> None:
        """Create default tasks when no tasks are loaded."""
        self.tasks = {
            name: Task.from_dict(name, task_data)
            for name, task_data in DEFAULT_TASKS.items()
        }
        logging.info("Created default tasks")

    def _validate_task_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate task data structure.
        
        Args:
            data: Task data dictionary
            
        Returns:
            bool: True if data is valid, False otherwise.
        """
        required_fields = ['min', 'max']
        return all(field in data for field in required_fields)