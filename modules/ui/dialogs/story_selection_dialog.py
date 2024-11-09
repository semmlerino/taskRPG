# modules/ui/dialogs/story_selection_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QMessageBox
)
from PyQt5.QtGui import QFont
from modules.ui.dialogs.settings_dialog import SettingsDialog
import logging

import os

from modules.constants import STORIES_DIR, ASSETS_DIR
from modules.story import StoryManager


class StorySelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Story")
        self.setFixedSize(500, 400)
        self.selected_story = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Story list
        self.story_list = QListWidget()
        self.populate_story_list()
        layout.addWidget(self.story_list)

        # Button layout
        button_layout = QHBoxLayout()

        # Select button
        select_button = QPushButton("Select Story")
        select_button.clicked.connect(self.select_story)
        button_layout.addWidget(select_button)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setFont(QFont("Arial", 14))
        self.settings_button.setStyleSheet("""
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
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setFixedHeight(40)
        self.settings_button.setToolTip("Open settings dialog")
        button_layout.addWidget(self.settings_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def populate_story_list(self):
        try:
            story_files = [f for f in os.listdir(STORIES_DIR)
                          if f.endswith('.json')]

            if not story_files:
                QMessageBox.warning(self, "No Stories Found",
                                    "No story files found in the stories directory.")
                return

            self.story_list.addItems(story_files)
            self.story_list.setCurrentRow(0)

        except Exception as e:
            logging.error(f"Error populating story list: {e}")
            QMessageBox.critical(self, "Error",
                                 f"Failed to load story files: {str(e)}")

    def select_story(self):
        if self.story_list.currentItem():
            self.selected_story = os.path.join(
                STORIES_DIR,
                self.story_list.currentItem().text()
            )
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection",
                                "Please select a story to continue.")

    def accept(self):
        """Handle dialog acceptance and story initialization."""
        if not self.selected_story:
            return

        try:
            # Extract story name without extension
            story_name = os.path.splitext(os.path.basename(self.selected_story))[0]
            image_folder = os.path.join(ASSETS_DIR, 'images', story_name)

            # Ensure the image folder exists
            os.makedirs(image_folder, exist_ok=True)

            # Initialize the StoryManager with the selected story and existing BattleManager
            self.parent().story_manager = StoryManager(
                filepath=self.selected_story,
                image_generator=self.parent().image_generator,
                image_folder=image_folder,
                ui_component=self.parent(),
                battle_manager=self.parent().battle_manager  # Pass existing BattleManager
            )

            # Display the initial story segment
            self.parent().story_manager.display_story_segment()

            logging.info(f"Story '{story_name}' loaded successfully.")

            super().accept()

        except Exception as e:
            logging.error(f"Failed to load selected story: {e}")
            QMessageBox.critical(self, "Error",
                                 f"Failed to load the selected story:\n{str(e)}")

    def open_settings(self):
        """Open the settings dialog."""
        try:
            if hasattr(self.parent(), 'task_manager'):
                settings_dialog = SettingsDialog(self.parent().task_manager, self)
                settings_dialog.exec_()
                if settings_dialog.saved:
                    self.parent().task_manager = settings_dialog.task_manager
                    self.parent().task_manager.save_tasks()
        except Exception as e:
            logging.error(f"Error opening settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open settings: {str(e)}")
