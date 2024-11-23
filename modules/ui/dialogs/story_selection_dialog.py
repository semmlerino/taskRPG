"""
Story selection dialog for TaskRPG.

Handles story file selection and image generation for story nodes.

"""

import os
import json
import logging
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QMessageBox,
    QProgressDialog,
    QListWidgetItem
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QSize

# Project imports
from modules.constants import STORIES_DIR, ASSETS_DIR
from modules.ui.dialogs.settings_dialog import SettingsDialog
from modules.story import StoryManager
from modules.image_generator import ImageGenerator


class StorySelectionDialog(QDialog):
    """Dialog for selecting and initializing stories."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Story")
        self.setFixedSize(500, 400)
        self.selected_story = None
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI with updated styles and functionalities."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Story list
        self.story_list = QListWidget()
        self.story_list.setFont(QFont("Arial", 12))
        self.story_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #E3F2FD;
            }
        """)
        self.populate_story_list()
        layout.addWidget(self.story_list)

        # Button container
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Select button
        select_button = QPushButton("Select Story")
        select_button.setFont(QFont("Arial", 12))
        select_button.clicked.connect(self.select_story)
        select_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(select_button)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setFont(QFont("Arial", 12))
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        button_layout.addWidget(self.settings_button)

        # Add button layout with alignment
        layout.addLayout(button_layout)

        # Connect double-click signal to select_story
        self.story_list.itemDoubleClicked.connect(self.select_story)

    def populate_story_list(self):
        """Loads available stories from the stories directory."""
        try:
            if not os.path.exists(STORIES_DIR):
                os.makedirs(STORIES_DIR)
                logging.info(f"Created stories directory at {STORIES_DIR}")

            story_files = [f for f in os.listdir(STORIES_DIR) if f.endswith('.json')]

            if not story_files:
                reply = QMessageBox.question(
                    self, 
                    "No Stories Found",
                    f"No story files found in {STORIES_DIR}. Would you like to create a default story?",
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.create_default_story()
                    story_files = [f for f in os.listdir(STORIES_DIR) if f.endswith('.json')]
                else:
                    QMessageBox.warning(
                        self, 
                        "No Stories Available", 
                        "Please add JSON story files to the /stories folder and restart the application."
                    )
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
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to load story files: {str(e)}"
            )

    def accept(self):
        """Handle dialog acceptance and story initialization."""
        if not self.selected_story:
            return

        try:
            # Load story data
            with open(self.selected_story, 'r', encoding='utf-8') as f:
                story_data = json.load(f)

            # Get story name (used for image folder path)
            story_name = os.path.splitext(os.path.basename(self.selected_story))[0]

            # Create story-specific image directory using project structure
            image_folder = os.path.join(ASSETS_DIR, 'images', story_name)
            os.makedirs(image_folder, exist_ok=True)

            # Get main window reference
            main_window = self.parent()
            if not main_window or not hasattr(main_window, 'image_generator'):
                raise RuntimeError("Image generator not available")

            # First check if ComfyUI is available
            if not main_window.image_generator.validate_server_connection():
                result = QMessageBox.warning(
                    self,
                    "ComfyUI Not Available",
                    "ComfyUI server is not available. Story will load without generating missing images.\n"
                    "Would you like to continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if result == QMessageBox.No:
                    return
                # If user continues, we'll load without image generation
                super().accept()
                return

            # Scan for missing images
            missing_images = main_window.image_generator.scan_story_for_missing_images(
                story_data,
                story_name
            )

            if missing_images:
                # Create progress dialog
                progress = QProgressDialog(
                    "Generating story images...",
                    "Cancel",
                    0,
                    len(missing_images),
                    self
                )
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setAutoClose(False)
                progress.setStyleSheet("""
                    QProgressDialog {
                        background-color: white;
                        border: 1px solid #BDBDBD;
                        border-radius: 5px;
                    }
                    QProgressBar {
                        border: 1px solid #BDBDBD;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #F5F5F5;
                    }
                    QProgressBar::chunk {
                        background-color: #2196F3;
                        border-radius: 3px;
                    }
                """)

                try:
                    # Set image folder in image generator
                    main_window.image_generator.image_folder = image_folder

                    # Generate missing images
                    generated_images = main_window.image_generator.generate_missing_story_images(
                        story_data,
                        story_name,
                        progress_dialog=progress
                    )

                    if progress.wasCanceled():
                        result = QMessageBox.question(
                            self,
                            "Generation Cancelled",
                            "Image generation was cancelled. Story can be loaded with existing images.\n"
                            "Would you like to continue?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        if result == QMessageBox.No:
                            progress.close()
                            return
                    elif generated_images:
                        QMessageBox.information(
                            self,
                            "Image Generation Complete",
                            f"Successfully generated {len(generated_images)} new images for the story."
                        )

                except Exception as e:
                    logging.error(f"Error during image generation: {e}")
                    result = QMessageBox.warning(
                        self,
                        "Image Generation Warning",
                        "Some images could not be generated. Story can be loaded with existing images.\n"
                        "Would you like to continue?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if result == QMessageBox.No:
                        progress.close()
                        return
                finally:
                    progress.close()

            # Initialize story manager using project structure
            main_window.story_manager = StoryManager(
                filepath=self.selected_story,
                image_generator=main_window.image_generator,
                image_folder=image_folder,
                ui_component=main_window,
                battle_manager=main_window.battle_manager
            )

            # Display first story segment
            main_window.story_manager.display_story_segment()

            super().accept()

        except Exception as e:
            logging.error(f"Error in story initialization: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to initialize story: {str(e)}"
            )

    def select_story(self):
        """Handle story selection."""
        selected_items = self.story_list.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            story_path = selected_item.data(Qt.UserRole)
            self.selected_story = story_path
            self.accept()
        else:
            QMessageBox.warning(
                self, 
                "No Selection", 
                "Please select a story to load."
            )

    def extract_story_title(self, story_path: str) -> Optional[str]:
        """Extracts the title from a story file."""
        try:
            with open(story_path, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            return story_data.get('title') or os.path.splitext(os.path.basename(story_path))[0]
        except Exception as e:
            logging.error(f"Failed to extract title from {story_path}: {e}")
            return None

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
            self.parent().status_bar.showMessage("Settings updated successfully")
