# modules/ui/main_window.py

import os
import json
import logging
import sys
import traceback
from typing import Dict, List, Tuple

from PyQt5.QtWidgets import (
    QApplication, QDialog, QGroupBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QStatusBar, QVBoxLayout, QWidget, QProgressDialog
)
from PyQt5.QtCore import (
    QEasingCurve, QEvent, QPropertyAnimation, QRect, QTimer, Qt
)
from PyQt5.QtGui import QFont, QIcon, QKeyEvent

from modules.constants import (
    WINDOW_ICON, WINDOW_TITLE, ASSETS_DIR, STORIES_DIR, DATA_DIR
)
from modules.players.player import Player
from modules.tasks.task_manager import TaskManager
from modules.story import StoryManager, NavigationDirection
from modules.hotkeys import GlobalHotkeys
from modules.image_generator import ImageGenerator
from modules.ui.components.player_panel import PlayerPanel
from modules.ui.components.enemy_panel import EnemyPanel
from modules.ui.components.story_display import StoryDisplay
from modules.ui.components.action_buttons import ActionButtons
from modules.ui.components.choices_panel import ChoicesPanel
from modules.ui.dialogs.settings_dialog import SettingsDialog
from modules.ui.dialogs.story_selection_dialog import StorySelectionDialog
from modules.ui.components.fullscreen_image_viewer import FullscreenImageViewer
from core.battle.battle_manager import BattleManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TaskRPG(QMainWindow):
    """
    Main game class. Handles the UI, game logic, and interactions.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))

        # Set minimum size first
        self.setMinimumSize(900, 700)

        # Load saved window size
        settings = self.load_window_settings()
        window_width = settings.get('window', {}).get('width', 900)
        window_height = settings.get('window', {}).get('height', 736)

        # Get screen geometry
        screen = QApplication.primaryScreen().geometry()

        # Calculate center position
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2

        # Set geometry after all other window properties
        self.setGeometry(x, y, window_width, window_height)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Initialize Status Bar first (needed by UI)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Initialize core components that don't depend on UI
        self.init_core_components()

        # Initialize UI Components
        self.init_ui()

        # Initialize managers that depend on UI components
        self.init_managers()

        # Initialize and start global hotkeys listener
        self.init_hotkeys()

        # Initialize Shaking Animation
        self.init_animations()

        # Dynamic Font Scaling Timer
        self.font_scaling_timer = QTimer()
        self.font_scaling_timer.timeout.connect(self.adjust_fonts)
        self.font_scaling_timer.start(500)  # Adjust fonts every 500ms

        # Add this line after other initializations
        self.installEventFilter(self)

        # Prompt story selection
        self.select_story()

        # Add after initializing self.story_display
        self.story_display.navigate_back_signal.connect(self.navigate_back)
        self.story_display.navigate_forward_signal.connect(self.navigate_forward)

        # Connect next button click to story progression
        self.action_buttons.next_button.clicked.connect(self.next_story_segment)

        self.setFocusPolicy(Qt.StrongFocus)
        self.grabKeyboard()

    def init_core_components(self):
        """Initialize core components that don't depend on UI."""
        # Task Manager
        self.task_manager = TaskManager()

        # Player and Game State
        self.player = Player()
        self.paused = False

        # Image Generator
        self.image_generator = ImageGenerator()

        # Battle Manager - initialize before StoryManager
        self.battle_manager = BattleManager(self.task_manager, self.player)

        # Initialize with default story file path
        default_story_path = os.path.join(STORIES_DIR, "default_story.json")
        self.story_manager = StoryManager(
            filepath=default_story_path,
            image_generator=self.image_generator,
            image_folder=os.path.join(ASSETS_DIR, 'images', 'default'),
            ui_component=self,
            battle_manager=self.battle_manager  # Pass battle_manager here
        )
        self.story_image_folder = None

    def init_managers(self):
        """Initialize managers that depend on UI components."""
        # Set up battle manager UI components
        self.battle_manager.set_ui_components(
            story_display=self.story_display,
            enemy_panel=self.enemy_panel,
            action_buttons=self.action_buttons,
            player_panel=self.player_panel,
            status_bar=self.status_bar,
            tasks_left_label=self.tasks_left_label,
            main_window=self
        )

        # Connect victory callback
        self.battle_manager.register_callbacks(
            on_victory=self.player_panel.update_panel
        )

        logging.info("Managers initialized with UI components")

    def init_ui(self):
        """Initialize the user interface components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top Information Panel
        top_layout = QHBoxLayout()
        top_layout.setSpacing(30)

        # Player Panel
        self.player_panel = PlayerPanel(self.player)
        top_layout.addWidget(self.player_panel)

        # Enemy Panel
        self.enemy_panel = EnemyPanel()
        top_layout.addWidget(self.enemy_panel)

        # Tasks Left Group
        tasks_group = QGroupBox("Tasks Left")
        tasks_layout = QVBoxLayout()

        self.tasks_left_label = QLabel("0")
        self.tasks_left_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.tasks_left_label.setAlignment(Qt.AlignCenter)
        self.tasks_left_label.setStyleSheet("color: #388E3C;")  # Dark Green

        tasks_layout.addWidget(self.tasks_left_label)
        tasks_group.setLayout(tasks_layout)

        top_layout.addWidget(tasks_group)
        main_layout.addLayout(top_layout)

        # Story Display
        self.story_display = StoryDisplay()
        self.story_display.navigate_back_signal.connect(self.navigate_back)
        self.story_display.navigate_forward_signal.connect(self.navigate_forward)
        self.story_display.story_advance_signal.connect(self.next_story_segment)  # Added connection
        main_layout.addWidget(self.story_display)

        # Choices Panel
        self.choices_panel = ChoicesPanel()
        main_layout.addWidget(self.choices_panel)

        # Action Buttons
        self.action_buttons = ActionButtons()
        main_layout.addWidget(self.action_buttons)

        # Settings Button
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
        main_layout.addWidget(self.settings_button, alignment=Qt.AlignRight)

        # Set the layout on the central widget
        self.centralWidget().setLayout(main_layout)

        # Connect action buttons to battle manager
        # Note: This connection has been moved to init_managers()

    def init_status_bar(self):
        """Initialize the status bar with default messages."""
        self.status_bar.showMessage("Welcome to Task RPG! Start your adventure.")

    def init_hotkeys(self):
        """Initialize the global hotkeys listener."""
        self.hotkey_listener = GlobalHotkeys()

        # Connect battle hotkeys through battle manager
        self.battle_manager.connect_signals(self.hotkey_listener)

        # Other hotkey connections
        self.hotkey_listener.next_story_signal.connect(self.next_story_segment)

        self.hotkey_listener.start()

    def toggle_fullscreen_image(self):
        """Handle fullscreen toggle."""
        try:
            logging.info("Attempting to toggle fullscreen image")

            if not hasattr(self.story_display, 'current_image_path'):
                logging.warning("No current_image_path attribute found in story_display")
                return

            if not self.story_display.current_image_path:
                logging.warning("No current image path available")
                return

            logging.info(f"Creating fullscreen viewer for image: {self.story_display.current_image_path}")

            viewer = FullscreenImageViewer(
                self.story_display.current_image_path,
                self.story_display.story_text.toPlainText()
            )
            viewer.showFullScreen()

            # Keep a reference to prevent garbage collection
            self._current_viewer = viewer

            logging.info("Fullscreen viewer created and shown successfully")

        except Exception as e:
            logging.error(f"Error showing fullscreen image: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to show fullscreen image: {str(e)}"
            )

    def init_animations(self):
        """Initialize animation properties."""
        self.shake_animation = QPropertyAnimation(self, b"geometry")
        self.shake_animation.setDuration(100)  # Duration per shake
        self.shake_animation.setLoopCount(4)  # Number of shakes
        self.shake_animation.setEasingCurve(QEasingCurve.Linear)

    def select_story(self):
        """Prompt user to select a story to load."""
        try:
            dialog = StorySelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self._load_selected_story(dialog.selected_story)
            else:
                logging.info("User cancelled story selection")
                QMessageBox.information(self, "No Story Selected",
                                        "No story selected. Exiting the game.")
                self.close()
        except Exception as e:
            error_msg = f"Critical error in story selection: {str(e)}\n{traceback.format_exc()}"
            logging.critical(error_msg)
            QMessageBox.critical(self, "Critical Error",
                                 "A critical error occurred during story selection.")
            self.close()

    def _load_selected_story(self, selected_story: str):
        """Load the selected story file."""
        try:
            story_name = os.path.splitext(os.path.basename(selected_story))[0]
            self.story_image_folder = os.path.join(ASSETS_DIR, 'images', story_name)

            logging.info(f"Attempting to load story from: {selected_story}")
            os.makedirs(self.story_image_folder, exist_ok=True)

            # Update the story manager with the selected story file
            self.story_manager = StoryManager(
                filepath=selected_story,
                image_generator=self.image_generator,
                image_folder=self.story_image_folder,
                ui_component=self,
                battle_manager=self.battle_manager
            )
            self.story_manager.display_story_segment()
            self.update_navigation_buttons()

        except FileNotFoundError as e:
            error_msg = f"Story file not found: {selected_story}\nError: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "File Error", "The selected story file could not be found.")
            raise
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in story file: {selected_story}\nError: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Format Error", "The story file contains invalid JSON data.")
            raise
        except Exception as e:
            error_msg = f"Failed to load story: {str(e)}\nTraceback:\n{traceback.format_exc()}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Error", f"Failed to load story:\n{str(e)}")
            raise

    def generate_all_images(self):
        """Generate missing images for the story."""
        try:
            image_prompts = self.story_manager.get_all_image_prompts()
            missing_images = self._get_missing_images(image_prompts)

            if not missing_images:
                logging.info("All images already exist - skipping generation.")
                return

            self._generate_missing_images(missing_images)

        except Exception as e:
            logging.error(f"Error in generate_all_images: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate/load images: {e}")

    def _get_missing_images(self, image_prompts: Dict[str, str]) -> List[tuple]:
        """Identify which images need to be generated."""
        missing_images = []
        for node_key, prompt in image_prompts.items():
            image_filename = f"{node_key}.png"
            image_path = os.path.join(self.story_image_folder, image_filename)

            if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                missing_images.append((node_key, prompt))
        return missing_images

    def _generate_missing_images(self, missing_images: List[tuple]):
        """Generate the missing images with progress dialog."""
        progress_dialog = QProgressDialog(
            f"Generating {len(missing_images)} missing images...",
            "Cancel",
            0,
            len(missing_images),
            self
        )
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)

        for i, (node_key, prompt) in enumerate(missing_images):
            if progress_dialog.wasCanceled():
                logging.info("Image generation canceled by user.")
                break

            image_filename = f"{node_key}.png"
            image_path = os.path.join(self.story_image_folder, image_filename)

            image_path = self.image_generator.generate_image(prompt, save_path=image_path)
            if image_path:
                self.story_manager.set_generated_image(node_key, image_path)

            progress_dialog.setValue(i + 1)
            QApplication.processEvents()

        progress_dialog.close()

    def next_story_segment(self):
        """Proceed to the next segment of the story."""
        try:
            if not self._can_proceed():
                logging.debug("Cannot proceed - conditions not met")
                return

            current_node = self.story_manager.get_current_node()

            # Handle battle nodes
            if "battle" in current_node and not current_node.get("battle_completed", False):
                try:
                    battle_info = current_node["battle"]
                    if self.battle_manager.start_battle(battle_info):
                        current_node["battle_completed"] = True
                        logging.info(f"Battle started successfully: {battle_info}")
                    return
                except Exception as battle_e:
                    logging.error(f"Battle initialization failed: {str(battle_e)}\n{traceback.format_exc()}")
                    raise

            # Simple linear progression
            if next_node := current_node.get('next'):
                try:
                    self.story_manager.set_current_node(next_node)
                    self.story_manager.display_story_segment()
                    logging.debug(f"Advanced to node: {next_node}")
                except ValueError as e:
                    logging.error(f"Invalid next node '{next_node}': {str(e)}")
                    self.handle_chapter_end()
            else:
                logging.info("Reached end of story branch")
                self.handle_chapter_end()

            self.update_navigation_buttons()

        except Exception as e:
            error_msg = f"Story progression failed: {str(e)}\nTraceback:\n{traceback.format_exc()}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Error", f"Failed to advance story: {str(e)}")

    def handle_chapter_end(self):
        """Handle the end of a chapter."""
        try:
            self.story_display.append_text("<br><b>Chapter Complete!</b><br>")
            self.story_display.append_text("<p>You have completed all available tasks for now.</p>")
            self.story_display.append_text("<p>Feel free to start a new chapter or take a break!</p>")

            # Reset UI state
            self.action_buttons.hide_attack_buttons()
            self.action_buttons.next_button.hide()
            self.settings_button.setEnabled(True)  # Keep enabled to allow starting new chapter
            self.status_bar.showMessage("All tasks completed! Well done!")

            # Show completion dialog
            QMessageBox.information(self, "Tasks Complete",
                                    "Congratulations! You have completed all available tasks.\n\n"
                                    "You can start a new chapter when you're ready!")

        except Exception as e:
            logging.error(f"Error handling chapter end: {e}")
            QMessageBox.critical(self, "Error", "Failed to handle chapter end properly")

    def _can_proceed(self) -> bool:
        """Check if story can proceed to next segment."""
        if not self.isActiveWindow():
            return False

        if self.battle_manager.is_in_battle():
            QMessageBox.information(
                self,
                "Battle In Progress",
                "You must defeat the current enemy before proceeding!"
            )
            self.status_bar.showMessage("Battle in progress. Defeat the enemy to proceed.")
            return False

        if hasattr(self.action_buttons, 'next_button'):
            if not self.action_buttons.next_button.isEnabled():
                return False

        return True

    def update_tasks_left(self):
        """Update the tasks left display."""
        if self.battle_manager and self.battle_manager.current_enemy:
            current_hp = self.battle_manager.battle_state.enemy_hp
            tasks_left = max(0, current_hp)
            self.tasks_left_label.setText(str(tasks_left))

            # Update compact window if it exists
            if self.battle_manager.compact_window:
                self.battle_manager.compact_window.update_tasks(tasks_left)

    def toggle_pause(self):
        """Pause or resume the game."""
        self.battle_manager.toggle_pause()

    def open_settings(self):
        """Open the settings dialog."""
        settings_dialog = SettingsDialog(self.task_manager, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            self._apply_settings_changes(settings_dialog)

    def _apply_settings_changes(self, settings_dialog: SettingsDialog):
        """Apply changes from settings dialog."""
        if settings_dialog.saved:
            self.task_manager = settings_dialog.task_manager
            self.task_manager.save_tasks()

            settings_file = os.path.join(
                os.path.dirname(self.task_manager.filepath),
                'settings.json'
            )

            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    shake_enabled = settings.get('shake_animation', True)
                    # Notify the user about the change
                    status = "enabled" if shake_enabled else "disabled"
                    self.story_display.append_text(
                        f"<p>Shaking animation has been <b>{status}</b>.</p>"
                    )
                    self.status_bar.showMessage(f"Shaking animation {status}.")
                except Exception as e:
                    logging.error(f"Failed to load settings after saving. Error: {e}")

            self.story_display.append_text("<p>Settings updated successfully.</p>")
            self.status_bar.showMessage("Settings updated successfully.")

            # Update "Tasks Left" if not in battle
            if not self.battle_manager.is_in_battle():
                self.update_tasks_left()

    def adjust_fonts(self):
        """Adjust fonts based on window size."""
        try:
            width = self.width()
            if width < 800:
                font_size = 12
            elif width < 1200:
                font_size = 14
            else:
                font_size = 16

            # Update fonts in Player Panel
            self.player_panel.level_label.setFont(QFont("Arial", font_size, QFont.Bold))
            self.player_panel.xp_label.setFont(QFont("Arial", font_size))

            # Update fonts in Enemy Panel
            self.enemy_panel.enemy_label.setFont(QFont("Arial", font_size + 2, QFont.Bold))
            self.enemy_panel.task_label.setFont(QFont("Arial", font_size, italic=True))
            self.enemy_panel.hp_bar.setFont(QFont("Arial", font_size))

            # Update fonts in Story Display
            self.story_display.story_text.setFont(QFont("Times New Roman", font_size))
            if hasattr(self.story_display, 'image_label'):
                self.story_display.image_label.setFont(QFont("Arial", font_size))

            # Update fonts in Action Buttons - with safety checks
            if hasattr(self.action_buttons, 'next_button'):
                self.action_buttons.next_button.setFont(QFont("Arial", font_size, QFont.Bold))
            if hasattr(self.action_buttons, 'attack_button'):
                self.action_buttons.attack_button.setFont(QFont("Arial", font_size, QFont.Bold))
            if hasattr(self.action_buttons, 'heavy_attack_button'):
                self.action_buttons.heavy_attack_button.setFont(QFont("Arial", font_size, QFont.Bold))

            # Update fonts in Settings Button
            self.settings_button.setFont(QFont("Arial", font_size))

            # Update fonts in Choices Panel
            for i in range(self.choices_panel.layout.count()):
                item = self.choices_panel.layout.itemAt(i)
                if item and item.widget():
                    item.widget().setFont(QFont("Arial", font_size))

        except Exception as e:
            logging.error(f"Error during font adjustment: {e}")

    def trigger_shake_animation(self):
        """Trigger the shaking animation if enabled in settings."""
        try:
            settings_file = os.path.join(
                os.path.dirname(self.task_manager.filepath),
                'settings.json'
            )
            shake_enabled = True  # Default to True

            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)

            if shake_enabled and self.shake_animation.state() != QPropertyAnimation.Running:
                original_geometry = self.geometry()
                offset = 10  # Shake offset in pixels

                # Define keyframes for shaking
                keyframes = [
                    (0.0, QRect(original_geometry.x(), original_geometry.y(),
                                original_geometry.width(), original_geometry.height())),
                    (0.25, QRect(original_geometry.x() + offset, original_geometry.y(),
                                 original_geometry.width(), original_geometry.height())),
                    (0.5, QRect(original_geometry.x() - offset, original_geometry.y(),
                                original_geometry.width(), original_geometry.height())),
                    (0.75, QRect(original_geometry.x() + offset, original_geometry.y(),
                                 original_geometry.width(), original_geometry.height())),
                    (1.0, QRect(original_geometry.x(), original_geometry.y(),
                                original_geometry.width(), original_geometry.height()))
                ]

                self.shake_animation.stop()  # Stop any ongoing animation
                self.shake_animation.setStartValue(keyframes[0][1])
                for fraction, rect in keyframes[1:]:
                    self.shake_animation.setKeyValueAt(fraction, rect)
                self.shake_animation.start()

        except Exception as e:
            logging.error(f"Error during shaking animation: {e}")

    def eventFilter(self, obj, event):
        """Handle window focus events."""
        if obj is self:
            if event.type() == QEvent.WindowDeactivate and self.battle_manager.is_in_battle():
                self.battle_manager.show_compact_mode()
            elif event.type() == QEvent.WindowActivate:
                self.battle_manager.hide_compact_mode()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """Handle the window close event."""
        try:
            # Save window dimensions before closing
            self.save_window_settings()

            # Cleanup components
            cleanup_errors = []

            try:
                self.hotkey_listener.stop()
                self.hotkey_listener.wait()
            except Exception as e:
                cleanup_errors.append(f"Hotkey listener cleanup failed: {str(e)}")

            if self.battle_manager:
                try:
                    self.battle_manager.cleanup()
                except Exception as e:
                    cleanup_errors.append(f"Battle manager cleanup failed: {str(e)}")

            if cleanup_errors:
                error_msg = "Errors during cleanup:\n" + "\n".join(cleanup_errors)
                logging.error(error_msg)

            event.accept()

        except Exception as e:
            logging.critical(f"Critical error during window close: {str(e)}\n{traceback.format_exc()}")
            event.accept()

    def focusOutEvent(self, event):
        """Handle window losing focus - show compact battle window if in battle."""
        if self.battle_manager.is_in_battle():
            self.battle_manager.show_compact_mode()
        super().focusOutEvent(event)

    def focusInEvent(self, event):
        """Handle window regaining focus - hide compact battle window."""
        self.battle_manager.hide_compact_mode()
        super().focusInEvent(event)

    def _setup_connections(self):
        """Set up signal connections."""
        self.action_buttons.back_button.clicked.connect(self.navigate_back)
        self.action_buttons.forward_button.clicked.connect(self.navigate_forward)
        # Update button states initially
        self.update_navigation_buttons()

    def navigate_back(self):
        """Navigate to previous story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.BACKWARD)
            self.update_navigation_buttons()

    def navigate_forward(self):
        """Navigate to next story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.FORWARD)
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        """Update navigation button states."""
        can_go_back = self.story_manager._can_navigate(NavigationDirection.BACKWARD)
        can_go_forward = self.story_manager._can_navigate(NavigationDirection.FORWARD)

        # Keep the action buttons hidden
        if hasattr(self.action_buttons, 'back_button'):
            self.action_buttons.back_button.setVisible(False)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key_Left:
            self.navigate_back()
        elif event.key() == Qt.Key_Right:
            self.navigate_forward()
        elif self.story_display.hasFocus():
            self.story_display.keyPressEvent(event)
        super().keyPressEvent(event)

    def load_window_settings(self):
        """Load settings including window dimensions."""
        settings_file = os.path.join(DATA_DIR, 'settings.json')
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading window settings: {e}")
        return {'shake_animation': True, 'window': {'width': 900, 'height': 736}}

    def save_window_settings(self):
        """Save current window dimensions to settings."""
        settings_file = os.path.join(DATA_DIR, 'settings.json')
        try:
            # Load existing settings
            settings = self.load_window_settings()

            # Update window dimensions
            settings['window'] = {
                'width': self.width(),
                'height': self.height()
            }

            # Save updated settings
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)

        except Exception as e:
            logging.error(f"Error saving window settings: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = TaskRPG()
    game.show()
    sys.exit(app.exec_())
