# modules/constants.py

import os

# Base directory (one level above 'modules')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directory
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Assets directory
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# Stories directory
STORIES_DIR = os.path.join(BASE_DIR, 'stories')  # New line added

# Paths to JSON files
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
# Removed static story file paths for dynamic detection
# STORY_LINEAR_FILE = os.path.join(DATA_DIR, 'story_linear.json')
# STORY_ADVANCED_FILE = os.path.join(DATA_DIR, 'story_advanced.json')
STORY_DEFAULT_FILE = os.path.join(DATA_DIR, 'story_linear.json')  # Optional: default story

# Default tasks in case tasks.json fails to load
DEFAULT_TASKS = {
    "Mails": {
        "min": 8,
        "max": 15,
        "active": True
    },
    "Clean Room": {
        "min": 1,
        "max": 1,
        "active": False
    },
    "ToDo": {
        "min": 1,
        "max": 3,
        "active": False
    },
    "Gym": {
        "min": 1,
        "max": 1,
        "active": False
    },
    "Tabs": {
        "min": 4,
        "max": 10,
        "active": True
    },
    "GPTs": {
        "min": 5,
        "max": 25,
        "active": True
    },
    "Perplexities": {
        "min": 2,
        "max": 4,
        "active": True
    },
    "Claudes": {
        "min": 3,
        "max": 7,
        "active": True
    },
    "Gemini": {
        "min": 2,
        "max": 5,
        "active": True
    },
    "FitRPG": {
        "min": 1,
        "max": 1,
        "active": False
    },
    "KanaRPG": {
        "min": 1,
        "max": 1,
        "active": False
    },
    "3DE scripting": {
        "min": 1,
        "max": 1,
        "active": False
    },
    "SG scripting": {
        "min": 1,
        "max": 1,
        "active": True
    }
}

# Window configurations
WINDOW_TITLE = "Task RPG"
WINDOW_ICON = os.path.join(ASSETS_DIR, "icon.png")  # Ensure this icon exists
WINDOW_SIZE = (800, 600)  # Width x Height

# Hotkeys Definitions
HOTKEYS = {
    'normal_attack': 'd',
    'heavy_attack': 'shift+d',
    'toggle_pause': '#',
    'next_story': 'g',
    'open_settings': 's'
}
