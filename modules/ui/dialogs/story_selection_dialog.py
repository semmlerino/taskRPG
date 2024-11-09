import os
import json
import logging
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from modules.constants import STORIES_DIR
from modules.tasks.task_manager import TaskManager

class StorySelectionDialog(QDialog):
    """Dialog for selecting which story to load."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Story")
        self.setFixedSize(500, 400)
        self.selected_story = None
        self.task_manager = TaskManager()
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()

        label = QLabel("Choose a story to load:")
        label.setFont(QFont("Arial", 16))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.load_stories()
        layout.addWidget(self.list_widget)

        # Buttons
        buttons_layout = QHBoxLayout()
        select_button = QPushButton("Select")
        select_button.setFont(QFont("Arial", 14))
        select_button.clicked.connect(self.select_story)
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 14))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(select_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        # Settings Button
        settings_button = QPushButton("Settings")
        settings_button.setFont(QFont("Arial", 14))
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: #FFB74D;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FFA726;
            }
        """)
        settings_button.clicked.connect(self.open_settings)
        settings_button.setFixedHeight(40)
        settings_button.setToolTip("Open settings dialog")
        layout.addWidget(settings_button, alignment=Qt.AlignRight)

        self.setLayout(layout)

    def open_settings(self):
        """Opens the settings dialog."""
        from modules.ui.dialogs.settings_dialog import SettingsDialog
        settings_dialog = SettingsDialog(self.task_manager, self)
        settings_dialog.exec_()

    def load_stories(self):
        """Loads available stories from the stories directory."""
        if not os.path.exists(STORIES_DIR):
            os.makedirs(STORIES_DIR)
            logging.info(f"Created stories directory at {STORIES_DIR}")

        story_files = [f for f in os.listdir(STORIES_DIR) if f.endswith('.json')]
        
        if not story_files:
            reply = QMessageBox.question(
                self, "No Stories Found",
                f"No story files found in {STORIES_DIR}. Would you like to create a default story?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.create_default_story()
                story_files = [f for f in os.listdir(STORIES_DIR) if f.endswith('.json')]
            else:
                QMessageBox.warning(self, "No Stories Available", 
                                  "Please add JSON story files to the /stories folder "
                                  "and restart the application.")
                self.close()
                return

        for story_file in story_files:
            story_path = os.path.join(STORIES_DIR, story_file)
            story_title = self.extract_story_title(story_path) or story_file
            item = QListWidgetItem(story_title)
            item.setData(Qt.UserRole, story_path)
            self.list_widget.addItem(item)

    def extract_story_title(self, story_path: str) -> str:
        """Extracts the title from a story file."""
        try:
            with open(story_path, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            title = story_data.get('title')
            if title:
                return title
            return os.path.splitext(os.path.basename(story_path))[0]
        except Exception as e:
            logging.error(f"Failed to extract title from {story_path}. Error: {e}")
            return None

    def create_default_story(self):
        """Creates a default story file."""
        default_story = {
            "title": "Default Story",
            "start": {
                "text": "Welcome to the Default Story. This is where your adventure begins.",
                "choices": [
                    {
                        "text": "Proceed to the Forest",
                        "next": "forest"
                    }
                ]
            },
            "forest": {
                "text": "You venture into the forest and encounter a mystical stag.",
                "battle": {
                    "enemy": "Forest Troll",
"message": "A Forest Troll blocks your path with a menacing glare!"
                },
                "choices": [
                    {
                        "text": "Attack the Troll",
                        "next": "victory"
                    },
                    {
                        "text": "Run away",
                        "next": "retreat"
                    }
                ]
            },
            "victory": {
                "text": "You have defeated the Forest Troll and continue your journey.",
                "choices": [
                    {
                        "text": "Press 'G' or click 'Next' to continue your journey.",
                        "next": "end"
                    }
                ]
            },
            "retreat": {
                "text": "You decide it's best not to meddle with mystical forces and head back home.",
                "choices": [
                    {
                        "text": "Press 'G' or click 'Next' to conclude your adventure.",
                        "next": "end"
                    }
                ]
            },
            "end": {
                "text": "Thank you for playing the Default Story!",
                "choices": []
            }
        }
        default_story_path = os.path.join(STORIES_DIR, "default_story.json")
        try:
            with open(default_story_path, 'w', encoding='utf-8') as f:
                json.dump(default_story, f, indent=4)
            logging.info(f"Default story created at {default_story_path}")
            QMessageBox.information(
                self, 
                "Default Story Created",
                f"A default story has been created at {default_story_path}. "
                "Please restart the application to load it."
            )
            self.close()
        except Exception as e:
            logging.error(f"Failed to create default story. Error: {e}")
            QMessageBox.critical(self, "Error", "Failed to create a default story.")

    def select_story(self):
        """Handles the selection of a story."""
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            story_path = selected_item.data(Qt.UserRole)
            self.selected_story = story_path
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a story to load.")