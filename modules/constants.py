import os
import keyboard
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
    "Example Task": {
        "min": 3,
        "max": 5,
        "active": True,
        "description": "An example task"
    }
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
    'open_settings': 's',
    'fullscreen': 'f'
}

# UI Colors
UI_COLORS = {
    'PRIMARY': '#2196F3',
    'SECONDARY': '#4CAF50',
    'ACCENT': '#FF5722',
    'BACKGROUND': '#FFFFFF',
    'TEXT': '#333333',
    'LIGHT_TEXT': '#FFFFFF',
    'DISABLED': '#CCCCCC',
    'ERROR': '#F44336',
    'WARNING': '#FFC107',
    'SUCCESS': '#4CAF50',
}

# UI Fonts
UI_FONTS = {
    'DEFAULT_FAMILY': 'Arial',
    'DEFAULT_SIZE': 10,
    'HEADER_SIZE': 14,
    'TITLE_SIZE': 16,
    'BUTTON_SIZE': 12,
}

# Create necessary directories if they don't exist
for directory in [DATA_DIR, ASSETS_DIR, STORIES_DIR, IMAGES_DIR]:
    os.makedirs(directory, exist_ok=True)
