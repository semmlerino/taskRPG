import os
import json
import random
import logging
from typing import Dict, List, Optional, Union
from .task import Task
import traceback

DEFAULT_TASKS = {
    "default": {
        "min": 1,
        "max": 1,
        "active": True,
        "description": "Default task"
    }
}

class TaskManager:
    """Manages task loading, saving, and selection."""
    
    def __init__(self, filepath: str = None):
        if filepath is None:
            # Get absolute path to the data directory
            filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'tasks.json')
        
        logging.info(f"Initializing TaskManager with filepath: {filepath}")
        logging.info(f"File exists check: {os.path.exists(filepath)}")
        
        self.filepath = filepath
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()

    def load_tasks(self) -> None:
        """Load tasks from JSON file."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
                self.tasks = {}
                for name, data in task_data.items():
                    # Ensure we're creating Task objects
                    self.tasks[name] = self._convert_to_task(name, data)
        except Exception as e:
            logging.error(f"Error loading tasks: {str(e)}")
            self.tasks = {
                name: self._convert_to_task(name, data)
                for name, data in DEFAULT_TASKS.items()
            }

    def _convert_to_task(self, name: str, data: Union[dict, Task]) -> Task:
        """Convert dictionary to Task object if needed"""
        if isinstance(data, Task):
            return data
        return Task(
            name=name,
            min_count=data.get('min', 1),
            max_count=data.get('max', 1),
            active=data.get('active', True),
            description=data.get('description')
        )

    def get_task(self, name: str) -> Optional[Task]:
        """Get a task by name"""
        if name in self.tasks:
            return self.tasks[name]
        return None

    def get_random_active_task(self) -> Optional[Task]:
        """Get a random active task"""
        active_tasks = [
            task for task in self.tasks.values()
            if task.active  # Using the property directly
        ]
        return random.choice(active_tasks) if active_tasks else None

    def update_task(self, name: str, data: dict) -> None:
        """Update a task with new data"""
        self.tasks[name] = self._convert_to_task(name, data)

    def save_tasks(self) -> None:
        """Save tasks to JSON file"""
        try:
            task_data = {
                name: {
                    'min': task.min_count,
                    'max': task.max_count,
                    'active': task.active,
                    'description': task.description
                }
                for name, task in self.tasks.items()
            }
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving tasks: {str(e)}")

    def add_task(self, name: str, min_steps: int, max_steps: int, 
                 active: bool = True, description: Optional[str] = None) -> bool:
        """Add a new task."""
        try:
            if name in self.tasks:
                logging.warning(f"Task '{name}' already exists")
                return False
            self.tasks[name] = Task(name, min_steps, max_steps, active, description)
            logging.info(f"Added new task: {name}")
            return True
        except Exception as e:
            logging.error(f"Error adding task: {e}")
            return False

    def update_task(self, name: str, min_steps: Optional[int] = None,
                    max_steps: Optional[int] = None, active: Optional[bool] = None,
                    description: Optional[str] = None) -> bool:
        """Update an existing task."""
        try:
            if name not in self.tasks:
                logging.warning(f"Task '{name}' not found")
                return False
            
            task = self.tasks[name]
            if min_steps is not None:
                task.min_steps = min_steps
            if max_steps is not None:
                task.max_steps = max_steps
            if active is not None:
                task.active = active
            if description is not None:
                task.description = description
                
            logging.info(f"Updated task: {name}")
            return True
        except Exception as e:
            logging.error(f"Error updating task: {e}")
            return False

    def delete_task(self, name: str) -> bool:
        """Delete a task."""
        try:
            if name in self.tasks:
                del self.tasks[name]
                logging.info(f"Deleted task: {name}")
                return True
            logging.warning(f"Task '{name}' not found")
            return False
        except Exception as e:
            logging.error(f"Error deleting task: {e}")
            return False

    def get_active_tasks(self) -> Dict[str, Task]:
        """Returns only the active tasks."""
        active_tasks = {
            name: task for name, task in self.tasks.items() 
            if task.active
        }
        logging.info(f"Total tasks: {len(self.tasks)}")
        logging.info(f"Active tasks: {len(active_tasks)}")
        logging.info(f"Active task names: {list(active_tasks.keys())}")
        return active_tasks

    def get_random_active_task(self) -> Optional[Task]:
        """Get a random active task."""
        active_tasks = self.get_active_tasks()
        return random.choice(list(active_tasks.values())) if active_tasks else None

    def get_task_count(self, active_only: bool = True) -> int:
        """Get total number of tasks."""
        if active_only:
            return len([task for task in self.tasks.values() if task.active])
        return len(self.tasks)

    def get_active_tasks_count(self) -> int:
        """Returns the count of active tasks."""
        return len(self.get_active_tasks())
