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
        "active": True
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
                            task = task_data
                            task.check_reactivation()  # Check reactivation for existing Task objects
                            self.tasks[name] = task
                        elif isinstance(task_data, dict):
                            # Validate required fields
                            if 'min' not in task_data or 'max' not in task_data:
                                logging.warning(f"Task '{name}' missing required fields, skipping")
                                continue
                            
                            # Task.from_dict now handles reactivation
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
            
            # Write to temp file first
            temp_file = self.filepath + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            # Backup existing file if it exists
            if os.path.exists(self.filepath):
                backup_file = self.filepath + '.bak'
                os.replace(self.filepath, backup_file)
            
            # Rename temp file to actual file
            os.rename(temp_file, self.filepath)
            
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
        # Check and reactivate any daily tasks that are ready
        for task in self.tasks.values():
            if task.is_daily and not task.is_active:
                if task.check_reactivation():  # This will reactivate if enough time has passed
                    self.save_tasks()  # Save state if any tasks were reactivated
        
        active_tasks = self.get_active_tasks()
        if not active_tasks:
            logging.warning("No active tasks available")
            return None
        
        try:
            chosen_task = random.choice(list(active_tasks.values()))
            logging.debug(f"Selected random task: {chosen_task.name}")
            return chosen_task
            
        except Exception as e:
            logging.error(f"Error selecting random task: {e}")
            return None

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

    def check_task_activations(self) -> bool:
        """Check all tasks for activation conditions.
        
        Returns:
            bool: True if any tasks were activated
        """
        any_activated = False
        try:
            # First check daily/weekly reactivations
            for task in self.tasks.values():
                logging.debug(f"Checking task '{task.name}' - Active: {task.is_active}, Activation time: {task.activation_time}")
                
                if task.check_reactivation():
                    any_activated = True
                    logging.info(f"Task '{task.name}' reactivated by schedule")
                    
                # Check activation time
                if not task.is_active and task.activation_time:
                    was_active = task.is_active  # Get current state
                    is_active = task.is_active   # This will trigger the check in the property
                    if not was_active and is_active:
                        any_activated = True
                        logging.info(f"Task '{task.name}' activated by time trigger")
            
            if any_activated:
                self.save_tasks()  # Save state if any tasks were activated
                logging.info("Tasks saved after activation changes")
                
            return any_activated
                
        except Exception as e:
            logging.error(f"Error checking task activations: {e}")
            return False

    def add_task(self, name: str, min_steps: int, max_steps: int, 
             active: bool = True) -> bool:
        """
        Add a new task.
        
        Args:
            name: Task name
            min_steps: Minimum steps required
            max_steps: Maximum steps allowed
            active: Whether task is active
            
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
                min_count=min_steps,
                max_count=max_steps,
                active=active
            )
            
            logging.info(f"Added new task: {name}")
            return True
        except Exception as e:
            logging.error(f"Error adding task: {e}")
            return False

    def update_task(self, name: str, min_steps: Optional[int] = None, 
               max_steps: Optional[int] = None, active: Optional[bool] = None) -> bool:
        """
        Update an existing task.
        
        Args:
            name: Task name
            min_steps: New minimum steps (optional)
            max_steps: New maximum steps (optional)
            active: New active state (optional)
            
        Returns:
            bool: True if update successful, False otherwise.
        """
        try:
            task = self.tasks.get(name)
            if not task:
                logging.warning(f"Task '{name}' not found")
                return False
            
            if min_steps is not None:
                task.min_count = max(1, int(min_steps))
            
            if max_steps is not None:
                task.max_count = max(task.min_count, int(max_steps))
            
            if active is not None:
                task.active = bool(active)
            
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
        self.save_tasks()

    def _validate_task_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate task data structure.
        
        Args:
            data: Task data dictionary
            
        Returns:
            bool: True if data is valid, False otherwise.
        """
        try:
            # Check required fields exist
            required_fields = ['min', 'max', 'active']
            if not all(field in data for field in required_fields):
                return False
                
            # Validate types
            if not isinstance(data['min'], int) or not isinstance(data['max'], int):
                return False
            if not isinstance(data['active'], bool):
                return False
                
            # Validate values
            if data['min'] < 1 or data['max'] < data['min']:
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error validating task data: {e}")
            return False

    def import_tasks(self, import_file: str) -> bool:
        """
        Import tasks from another JSON file.
        
        Args:
            import_file: Path to JSON file to import
            
        Returns:
            bool: True if import successful, False otherwise.
        """
        try:
            if not os.path.exists(import_file):
                logging.error(f"Import file not found: {import_file}")
                return False
                
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
                
            if not isinstance(import_data, dict):
                logging.error("Invalid import data format")
                return False
                
            # Import tasks
            for name, task_data in import_data.items():
                if self._validate_task_data(task_data):
                    self.tasks[name] = Task.from_dict(name, task_data)
                else:
                    logging.warning(f"Skipping invalid task during import: {name}")
                    
            logging.info(f"Imported tasks from {import_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error importing tasks: {e}")
            return False

    def export_tasks(self, export_file: str) -> bool:
        """
        Export tasks to JSON file.
        
        Args:
            export_file: Path to export tasks to
            
        Returns:
            bool: True if export successful, False otherwise.
        """
        try:
            export_data = {
                name: task.to_dict()
                for name, task in self.tasks.items()
            }
            
            # Create directory if needed
            os.makedirs(os.path.dirname(export_file), exist_ok=True)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4)
                
            logging.info(f"Exported tasks to {export_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error exporting tasks: {e}")
            return False