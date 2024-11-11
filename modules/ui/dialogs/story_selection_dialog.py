import os
import json
import logging
import traceback
from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QMessageBox, QProgressDialog, QListWidgetItem
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from modules.constants import STORIES_DIR, ASSETS_DIR
from modules.ui.dialogs.settings_dialog import SettingsDialog
from modules.story import StoryManager

class StorySelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Story")
        self.setFixedSize(500, 400)
        self.selected_story = None
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
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
        """Loads available stories from the stories directory."""
        try:
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
                self.story_list.addItem(item)

        except Exception as e:
            logging.error(f"Error populating story list: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to load story files: {str(e)}")

    def select_story(self):
        """Handles the selection of a story."""
        selected_items = self.story_list.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            story_path = selected_item.data(Qt.UserRole)
            self.selected_story = story_path
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", 
                              "Please select a story to load.")

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

            # Progress dialog for image generation
            progress = QProgressDialog(
                "Checking and generating story images...",
                "Cancel",
                0,
                100,
                self
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            try:
                # Generate any missing images
                main_window = self.parent()
                generated_images = main_window.image_generator.generate_missing_story_images(
                    progress_dialog=progress
                )
                
                if generated_images:
                    logging.info(f"Generated {len(generated_images)} new images for {story_name}")
                    
            except Exception as e:
                logging.error(f"Error during image generation: {e}")
                QMessageBox.warning(
                    self,
                    "Image Generation Warning",
                    "Some images could not be generated. The story will continue with available images."
                )
            finally:
                progress.close()

            # Initialize the StoryManager with the selected story
            self.parent().story_manager = StoryManager(
                filepath=self.selected_story,
                image_generator=self.parent().image_generator,
                image_folder=image_folder,
                ui_component=self.parent(),
                battle_manager=self.parent().battle_manager
            )

            # Display the initial story segment
            self.parent().story_manager.display_story_segment()

            logging.info(f"Story '{story_name}' loaded successfully")

            super().accept()

        except Exception as e:
            logging.error(f"Failed to load story: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load the selected story:\n{str(e)}"
            )

    def open_settings(self):
        """Opens the settings dialog."""
        settings_dialog = SettingsDialog(self.parent().task_manager, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            self._apply_settings_changes(settings_dialog)

    def _apply_settings_changes(self, settings_dialog: SettingsDialog):
        """Apply changes from settings dialog."""
        if settings_dialog.saved:
            self.parent().task_manager = settings_dialog.task_manager
            self.parent().task_manager.save_tasks()
            self.parent().story_display.append_text("<p>Settings updated successfully.</p>")
            self.parent().status_bar.showMessage("Settings updated successfully.")

    def create_default_story(self):
        """Creates a default story file."""
        default_story = {
            "title": "Default Story",
            "start": {
                "text": "Welcome to TaskRPG. Your journey begins here.",
                "image_prompt": "A mystical forest path at dawn, rays of sunlight filtering through ancient trees",
                "next": "first_task"
            },
            "first_task": {
                "text": "Your first challenge awaits!",
                "battle": {
                    "enemy": "Task Guardian",
                    "message": "A Task Guardian appears, ready to test your resolve!"
                },
                "next": "victory"
            },
            "victory": {
                "text": "Congratulations on completing your first task!",
                "image_prompt": "A victorious hero standing in a clearing, rays of golden light surrounding them",
                "next": "end"
            },
            "end": {
                "text": "This concludes the introduction. Your real journey awaits!",
                "end": True
            }
        }

        try:
            default_story_path = os.path.join(STORIES_DIR, "default_story.json")
            with open(default_story_path, 'w', encoding='utf-8') as f:
                json.dump(default_story, f, indent=4)
            logging.info(f"Default story created at {default_story_path}")
            QMessageBox.information(
                self, 
                "Default Story Created",
                f"A default story has been created at {default_story_path}"
            )
        except Exception as e:
            logging.error(f"Failed to create default story: {e}")
            QMessageBox.critical(self, "Error", "Failed to create default story")

    def extract_story_title(self, story_path: str) -> Optional[str]:
        """Extracts the title from a story file."""
        try:
            with open(story_path, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            return story_data.get('title') or os.path.splitext(os.path.basename(story_path))[0]
        except Exception as e:
            logging.error(f"Failed to extract title from {story_path}: {e}")
            return None