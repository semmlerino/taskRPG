# modules/game_logic.py

import os
import json
import random
import logging
from typing import Dict, List, Optional
from .constants import TASKS_FILE, DEFAULT_TASKS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Enemy:
    def __init__(self, name: str, hp: int, image_path: str = None):
        self.name = name
        self.max_hp = hp
        self.current_hp = hp
        self.image_path = image_path
        logging.info(f"Enemy created: {self.name} with HP: {self.max_hp}")

    def take_damage(self, amount: int):
        self.current_hp = max(0, self.current_hp - amount)
        logging.debug(f"{self.name} takes {amount} damage. Current HP: {self.current_hp}")

    def is_defeated(self) -> bool:
        return self.current_hp <= 0

class Player:
    def __init__(self):
        self.level = 1
        self.experience = 0
        self.experience_to_next_level = 100
        logging.info(f"Player created: Levesl {self.level}, XP: {self.experience}")

    def gain_experience(self, amount: int):
        self.experience += amount
        logging.info(f"Player gains {amount} XP. Total XP: {self.experience}")
        while self.experience >= self.experience_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.experience -= self.experience_to_next_level
        self.experience_to_next_level = int(self.experience_to_next_level * 1.5)
        logging.info(f"Player leveled up! New level: {self.level}")

    def take_damage(self, amount: int):
        pass

    def is_defeated(self) -> bool:
        return False

class TaskManager:
    def __init__(self, filepath: str = TASKS_FILE):
        self.filepath = filepath
        self.tasks = self.load_tasks()

    def load_tasks(self) -> Dict[str, Dict]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                tasks = {
                    str(task): {
                        "min": v.get("min"),
                        "max": v.get("max"),
                        "active": v.get("active", True)
                    } for task, v in data.items()
                }
                logging.info(f"Tasks loaded from {self.filepath}.")
                return tasks
            except Exception as e:
                logging.error(f"Failed to load tasks from {self.filepath}. Using default tasks. Error: {e}")
        logging.info("Using default tasks.")
        return DEFAULT_TASKS.copy()

    def save_tasks(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.tasks, f, indent=4)
            logging.info(f"Tasks saved successfully to {self.filepath}.")
        except Exception as e:
            logging.error(f"Failed to save tasks to {self.filepath}. Error: {e}")

    def add_task(self, name: str, min_hp: Optional[int], max_hp: Optional[int], active: bool = True):
        self.tasks[name] = {"min": min_hp, "max": max_hp, "active": active}
        logging.info(f"Added new task: {name}")

    def edit_task(self, original_name: str, new_name: str, min_hp: Optional[int], max_hp: Optional[int], active: bool):
        if original_name != new_name:
            if new_name in self.tasks:
                logging.warning(f"Task name '{new_name}' already exists. Overwriting.")
            del self.tasks[original_name]
        self.tasks[new_name] = {"min": min_hp, "max": max_hp, "active": active}
        logging.info(f"Edited task: {original_name} to {new_name}")

    def delete_task(self, name: str):
        if name in self.tasks:
            del self.tasks[name]
            logging.info(f"Deleted task: {name}")
        else:
            logging.warning(f"Tried to delete non-existent task: {name}")

    def get_active_tasks(self) -> List[str]:
        return [task for task, details in self.tasks.items() if details.get("active", False)]

    def get_random_active_task(self) -> Dict[str, int]:
        active_tasks = self.get_active_tasks()
        if not active_tasks:
            logging.error("No active tasks available.")
            return {}
        task_name = random.choice(active_tasks)
        task_info = self.tasks[task_name]
        return {
            "name": task_name,
            "min": task_info['min'],
            "max": task_info['max']
        }

    def get_active_tasks_count(self) -> int:
        return len(self.get_active_tasks())

    def reset_to_default(self):
        self.tasks = DEFAULT_TASKS.copy()
        logging.info("Tasks reset to default values.")