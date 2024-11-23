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
    QListWidgetItem,
    QLineEdit,
    QTextBrowser,
    QLabel,
    QWidget
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
        self.setMinimumSize(600, 500)  # Increased size for better readability
        self.selected_story = None
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI with improved layout and styling."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title Label
        title_label = QLabel("Available Stories")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #2196F3;")
        main_layout.addWidget(title_label)

        # Story list with preview panel
        split_layout = QHBoxLayout()
        
        # Left side - Story List
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search stories...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        self.search_box.textChanged.connect(self.filter_stories)
        list_layout.addWidget(self.search_box)

        # Story list
        self.story_list = QListWidget()
        self.story_list.setFont(QFont("Arial", 11))
        self.story_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #EEEEEE;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QListWidget::item:hover:!selected {
                background-color: #F5F5F5;
            }
        """)
        list_layout.addWidget(self.story_list)
        
        # Right side - Preview Panel
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        
        preview_label = QLabel("Story Preview")
        preview_label.setFont(QFont("Arial", 12, QFont.Bold))
        preview_layout.addWidget(preview_label)
        
        self.preview_text = QTextBrowser()
        self.preview_text.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
                padding: 10px;
            }
        """)
        preview_layout.addWidget(self.preview_text)
        
        # Add both containers to split layout
        split_layout.addWidget(list_container, 1)
        split_layout.addWidget(preview_container, 1)
        main_layout.addLayout(split_layout)

        # Button container
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Select button
        select_button = QPushButton("Select Story")
        select_button.setFont(QFont("Arial", 11))
        select_button.clicked.connect(self.select_story)
        select_button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        button_layout.addWidget(select_button)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setFont(QFont("Arial", 11))
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #424242;
            }
        """)
        button_layout.addWidget(self.settings_button)

        main_layout.addLayout(button_layout)

        # Connect signals
        self.story_list.itemSelectionChanged.connect(self.update_preview)
        self.story_list.itemDoubleClicked.connect(self.select_story)
        
        # Initial population
        self.populate_story_list()

    def filter_stories(self):
        """Filter stories based on search text."""
        search_text = self.search_box.text().lower()
        for i in range(self.story_list.count()):
            item = self.story_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    def update_preview(self):
        """Update the preview panel with selected story details."""
        selected_items = self.story_list.selectedItems()
        if not selected_items:
            self.preview_text.clear()
            return

        story_path = selected_items[0].data(Qt.UserRole)
        try:
            with open(story_path, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            
            # Format preview content
            preview_html = "<h3 style='color: #1976D2;'>{}</h3>".format(
                story_data.get('title', 'Untitled Story')
            )
            
            # Add first node preview
            start_node = story_data.get('start', {})
            if isinstance(start_node, dict):
                preview_html += "<p><b>Opening:</b></p>"
                preview_html += "<p>{}</p>".format(start_node.get('text', 'No preview available'))
            
            self.preview_text.setHtml(preview_html)
            
        except Exception as e:
            self.preview_text.setPlainText("Error loading preview: {}".format(str(e)))

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
