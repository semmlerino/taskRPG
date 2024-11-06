# modules/constants.py

import os

# Base directory (one level above 'modules')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directory
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Assets directory
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# Stories directory
STORIES_DIR = os.path.join(BASE_DIR, 'stories')

# Image directory
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')

# Paths to JSON files
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
STORY_DEFAULT_FILE = os.path.join(DATA_DIR, 'story_linear.json')

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
    # ... rest of default tasks ...
}

# Window configurations
WINDOW_TITLE = "Task RPG"
WINDOW_ICON = os.path.join(ASSETS_DIR, "icon.png")
WINDOW_SIZE = (800, 600)  # Width x Height

# Hotkeys Definitions
HOTKEYS = {
    'normal_attack': 'd',
    'heavy_attack': 'shift+d',
    'toggle_pause': '#',
    'next_story': 'g',
    'open_settings': 's'
}

# Create necessary directories if they don't exist
for directory in [DATA_DIR, ASSETS_DIR, STORIES_DIR, IMAGES_DIR]:
    os.makedirs(directory, exist_ok=True)