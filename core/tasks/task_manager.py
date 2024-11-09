import os
import json
import random
import logging
from typing import Dict, List, Optional, Any
from .task import Task

class TaskManager:
    """Manages task loading, saving, and selection."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()
        logging.info(f"TaskManager initialized with {len(self.tasks)} tasks")

    def load_tasks(self) -> None:
        """Load tasks from JSON file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.tasks = {
                    name: Task.from_dict(name, task_data)
                    for name, task_data in data.items()
                }
                logging.info(f"Loaded {len(self.tasks)} tasks from {self.filepath}")
            else:
                logging.warning(f"Task file not found: {self.filepath}")
                self.tasks = {}
        except Exception as e:
            logging.error(f"Error loading tasks: {e}")
            self.tasks = {}

    def save_tasks(self) -> bool:
        """Save tasks to JSON file."""
        try:
            data = {
                name: task.to_dict()
                for name, task in self.tasks.items()
            }
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logging.info(f"Saved {len(self.tasks)} tasks to {self.filepath}")
            return True
        except Exception as e:
            logging.error(f"Error saving tasks: {e}")
            return False

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

    def get_active_tasks(self) -> List[Task]:
        """Get all active tasks."""
        return [task for task in self.tasks.values() if task.active]

    def get_random_active_task(self) -> Optional[Task]:
        """Get a random active task."""
        active_tasks = self.get_active_tasks()
        return random.choice(active_tasks) if active_tasks else None

    def get_task_count(self, active_only: bool = True) -> int:
        """Get total number of tasks."""
        if active_only:
            return len([task for task in self.tasks.values() if task.active])
        return len(self.tasks)
