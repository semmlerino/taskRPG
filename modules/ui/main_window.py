from __future__ import annotations

# Standard library imports
import os
import json
import logging
import sys
import traceback
from typing import Dict, List, Tuple, Optional

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QShortcut,
    QStatusBar,
    QVBoxLayout,
    QWidget
)
from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRect,
    QTimer,
    Qt,
    pyqtSlot
)
from PyQt5.QtGui import (
    QFont,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QPalette,
    QColor
)

# Local application imports
from modules.constants import (
    WINDOW_ICON,
    WINDOW_TITLE,
    ASSETS_DIR,
    STORIES_DIR,
    DATA_DIR
)
from modules.players.player import Player
from modules.tasks.task_manager import TaskManager
from modules.story import StoryManager, NavigationDirection
from modules.hotkeys import GlobalHotkeys
from modules.image_generator import ImageGenerator, ImageQuality  # Updated import
from modules.ui.components import (
    PlayerPanel,
    EnemyPanel,
    StoryDisplay,
    ActionButtons,
    ChoicesPanel,
    CompactBattleWindow
)
from modules.ui.dialogs.settings import SettingsDialog  # Import from new settings package
from modules.ui.dialogs.story_selection_dialog import StorySelectionDialog
from modules.ui.components.fullscreen_image_viewer import FullscreenImageViewer
from modules.battle.battle_manager import BattleManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TaskRPG(QMainWindow):
    """
    Main game window handling UI coordination and game state management.

    Manages the overall game state, window behavior, and component interactions.
    Handles fullscreen transitions, battle states, and focus management.
    """

    def __init__(self):
        """Initialize the main game window."""
        super().__init__()
        logging.info("Initializing TaskRPG main window")

        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))
        self.setMinimumSize(900, 700)

        # Load window settings first
        self._load_window_settings()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Initialize Status Bar (needed by UI)
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
        self.init_font_scaling()

        # Install event filter for window state management
        self.installEventFilter(self)

        # Add focus and keyboard handling
        self.setFocusPolicy(Qt.StrongFocus)

        # Startup Image Generation
        self._startup_image_generation()

        logging.info("TaskRPG main window initialization complete")

    def _startup_image_generation(self):
        """Handle startup image generation before story selection."""
        try:
            def generate_all_story_images():
                """Generate missing images for all stories at startup."""
                try:
                    if not os.path.exists(STORIES_DIR):
                        return

                    story_files = [f for f in os.listdir(STORIES_DIR) if f.endswith('.json')]
                    if not story_files:
                        return

                    # Create progress dialog
                    progress = QProgressDialog(
                        "Checking stories for missing images...",
                        "Cancel",
                        0,
                        len(story_files),
                        self
                    )
                    progress.setWindowModality(Qt.WindowModal)
                    progress.setMinimumDuration(0)
                    progress.setAutoClose(False)

                    total_generated = 0
                    for idx, story_file in enumerate(story_files):
                        if progress.wasCanceled():
                            break

                        story_path = os.path.join(STORIES_DIR, story_file)
                        story_name = os.path.splitext(story_file)[0]

                        try:
                            # Load story data
                            with open(story_path, 'r', encoding='utf-8') as f:
                                story_data = json.load(f)

                            # Update progress dialog
                            progress.setLabelText(f"Checking story: {story_name}")
                            progress.setValue(idx)

                            # Scan for missing images
                            missing_images = self.image_generator.scan_story_for_missing_images(
                                story_data,
                                story_name
                            )

                            if missing_images:
                                # Update dialog for generation
                                progress.setLabelText(f"Generating images for: {story_name}")

                                # Generate missing images
                                generated = self.image_generator.generate_missing_story_images(
                                    story_data,
                                    story_name,
                                    progress_dialog=progress
                                )

                                if generated:
                                    total_generated += len(generated)

                        except Exception as e:
                            logging.error(f"Error processing story {story_name}: {e}")
                            continue

                    progress.close()

                    if total_generated > 0:
                        QMessageBox.information(
                            self,
                            "Image Generation Complete",
                            f"Successfully generated {total_generated} images across all stories."
                        )

                except Exception as e:
                    logging.error(f"Error during startup image generation: {e}")

            # Check ComfyUI availability first
            if self.image_generator.validate_server_connection():
                generate_all_story_images()
            else:
                QMessageBox.warning(
                    self,
                    "ComfyUI Not Available",
                    "ComfyUI server is not available. Stories will load without generating missing images."
                )

        except Exception as e:
            logging.error(f"Error initializing startup image generation: {e}")

        # Schedule story selection and focus setup
        QTimer.singleShot(0, self.select_story)
        QTimer.singleShot(100, self._ensure_focus)

    def init_core_components(self):
        """Initialize core game components."""
        try:
            # Task Manager
            self.task_manager = TaskManager()

            # Player and Game State
            self.player = Player()

            # Load image quality from settings
            settings_file = os.path.join(DATA_DIR, 'settings.json')
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                quality_name = settings.get('image_quality', 'HIGH')
                image_quality = ImageQuality[quality_name]
            except Exception as e:
                logging.error(f"Error loading image quality setting: {e}")
                image_quality = ImageQuality.HIGH  # Default quality

            # Image Generator with proper path handling and ULTRA quality
            comfyui_path = os.getenv('COMFYUI_PATH', 
                r"C:\StableDiffusion\ComfyUI_windows_portable_nvidia_cu121_or_cpu\ComfyUI_windows_portable\ComfyUI")
            
            self.image_generator = ImageGenerator(
                checkpoints_dir=os.path.join(comfyui_path, 'models', 'checkpoints'),
                quality=ImageQuality.ULTRA  # Set to ULTRA quality
            )

            # Battle Manager - initialize before StoryManager
            self.battle_manager = BattleManager(self.task_manager, self.player)

            # Initialize with default story file path
            default_story_path = os.path.join(STORIES_DIR, "default_story.json")
            self.story_manager = StoryManager(
                filepath=default_story_path,
                image_generator=self.image_generator,
                image_folder=os.path.join(ASSETS_DIR, 'images', 'default'),
                ui_component=self,
                battle_manager=self.battle_manager
            )

            logging.info("Core components initialized")

        except Exception as e:
            logging.error(f"Error initializing core components: {e}")
            raise

    def init_ui(self):
        """Initialize the user interface components."""
        try:
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(20, 20, 20, 20)
            main_layout.setSpacing(15)

            # Top Information Panel
            top_layout = self._create_top_section()
            main_layout.addLayout(top_layout)

            # Story Display
            self.story_display = StoryDisplay()
            main_layout.addWidget(self.story_display)

            # Choices Panel
            self.choices_panel = ChoicesPanel()
            main_layout.addWidget(self.choices_panel)

            # Action Buttons
            self.action_buttons = ActionButtons()
            main_layout.addWidget(self.action_buttons)

            # Settings Button
            self.settings_button = self._create_settings_button()
            main_layout.addWidget(self.settings_button, alignment=Qt.AlignRight)

            # Set layout
            self.centralWidget().setLayout(main_layout)

            # Connect UI signals
            self._connect_ui_signals()

            logging.info("UI components initialized")

        except Exception as e:
            logging.error(f"Error initializing UI: {e}")
            raise

    def _create_top_section(self) -> QHBoxLayout:
        """Create the top section containing player, enemy, and task info."""
        layout = QHBoxLayout()
        layout.setSpacing(30)

        # Player Panel
        self.player_panel = PlayerPanel(self.player)
        layout.addWidget(self.player_panel)

        # Enemy Panel
        self.enemy_panel = EnemyPanel()
        layout.addWidget(self.enemy_panel)

        # Tasks Left Group
        tasks_group = QGroupBox("Tasks Left")
        tasks_layout = QVBoxLayout()

        self.tasks_left_label = QLabel("0")
        self.tasks_left_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.tasks_left_label.setAlignment(Qt.AlignCenter)
        self.tasks_left_label.setStyleSheet("color: #388E3C;")

        tasks_layout.addWidget(self.tasks_left_label)
        tasks_group.setLayout(tasks_layout)
        layout.addWidget(tasks_group)

        return layout

    def _create_settings_button(self) -> QPushButton:
        """Create and configure the settings button."""
        button = QPushButton("Settings")
        button.setFont(QFont("Arial", 14))
        button.setStyleSheet("""
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
        button.setFixedHeight(40)
        button.setToolTip("Open settings dialog")
        return button

    def _connect_ui_signals(self):
        """Connect all UI signals."""
        try:
            # Story navigation
            self.story_display.navigate_back_signal.connect(self.navigate_back)
            self.story_display.navigate_forward_signal.connect(self.navigate_forward)
            self.story_display.story_advance_signal.connect(self.next_story_segment)

            # Action buttons
            self.action_buttons.next_button.clicked.connect(self.next_story_segment)

            # Settings button
            self.settings_button.clicked.connect(self.open_settings)

            logging.debug("UI signals connected")

        except Exception as e:
            logging.error(f"Error connecting UI signals: {e}")

    def init_managers(self):
        """Initialize managers that depend on UI components."""
        try:
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

        except Exception as e:
            logging.error(f"Error initializing managers: {e}")
            raise

    def init_hotkeys(self):
        """Initialize the global hotkeys system."""
        try:
            self.hotkey_listener = GlobalHotkeys()

            # Connect battle hotkeys through battle manager
            self.battle_manager.connect_signals(self.hotkey_listener)

            # Connect story progression
            self.hotkey_listener.next_story_signal.connect(self.next_story_segment)

            self.hotkey_listener.start()
            logging.info("Hotkey system initialized")

        except Exception as e:
            logging.error(f"Error initializing hotkeys: {e}")
            raise

    def init_animations(self):
        """Initialize animation properties."""
        self.shake_animation = QPropertyAnimation(self, b"geometry")
        self.shake_animation.setDuration(100)
        self.shake_animation.setLoopCount(4)
        self.shake_animation.setEasingCurve(QEasingCurve.Linear)

    def init_font_scaling(self):
        """Initialize dynamic font scaling."""
        self.font_scaling_timer = QTimer()
        self.font_scaling_timer.timeout.connect(self.adjust_fonts)
        self.font_scaling_timer.start(500)

    def _load_window_settings(self):
        """Load and apply window settings."""
        try:
            settings = self._load_settings_file()

            window_width = settings.get('window', {}).get('width', 900)
            window_height = settings.get('window', {}).get('height', 736)

            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2

            self.setGeometry(x, y, window_width, window_height)

        except Exception as e:
            logging.error(f"Error loading window settings: {e}")
            self.resize(900, 736)

    def _load_settings_file(self) -> dict:
        """Load settings from file."""
        settings_file = os.path.join(DATA_DIR, 'settings.json')
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error reading settings file: {e}")
        return {'window': {'width': 900, 'height': 736}}

    def select_story(self):
        """Show story selection dialog."""
        try:
            dialog = StorySelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self._load_selected_story(dialog.selected_story)
                QTimer.singleShot(100, self._ensure_focus)
            else:
                logging.info("User cancelled story selection")
                QMessageBox.information(
                    self,
                    "No Story Selected",
                    "No story selected. Exiting the game."
                )
                self.close()
        except Exception as e:
            logging.error(f"Error in story selection: {e}")
            QMessageBox.critical(
                self,
                "Critical Error",
                "Failed to load story selection."
            )
            self.close()

    def _load_selected_story(self, story_path: str):
        """Load the selected story file."""
        try:
            story_name = os.path.splitext(os.path.basename(story_path))[0]
            image_folder = os.path.join(ASSETS_DIR, 'images', story_name)
            os.makedirs(image_folder, exist_ok=True)

            self.story_manager = StoryManager(
                filepath=story_path,
                image_generator=self.image_generator,
                image_folder=image_folder,
                ui_component=self,
                battle_manager=self.battle_manager
            )

            self.story_manager.display_story_segment()
            logging.info(f"Story '{story_name}' loaded successfully")

        except Exception as e:
            logging.error(f"Error loading story: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load story: {str(e)}"
            )

    def next_story_segment(self):
        """Progress to next story segment."""
        try:
            if not hasattr(self, 'story_manager'):
                logging.error("No story manager found")
                return

            if not self._can_proceed():
                logging.debug("Cannot proceed - conditions not met")
                return

            current_node = self.story_manager.get_current_node()

            # First check if this is an end node
            if current_node.get('end', False):
                logging.info("Reached story end node")
                self.handle_chapter_end()
                return

            # Handle battle nodes
            if "battle" in current_node and not current_node.get("battle_completed", False):
                battle_info = current_node["battle"]
                if self.battle_manager.start_battle(battle_info):
                    current_node["battle_completed"] = True
                    logging.info("Battle started successfully")
                    # Check if this is the last node
                    if not current_node.get('next'):
                        self.handle_chapter_end()
                return

            # Handle story progression
            if next_node := current_node.get('next'):
                try:
                    self.story_manager.set_current_node(next_node)
                    self.story_manager.display_story_segment()
                    logging.info(f"Advanced to node: {next_node}")
                except ValueError as e:
                    logging.error(f"Invalid next node: {e}")
                    self.handle_chapter_end()
            else:
                logging.info("Reached end of story branch")
                self.handle_chapter_end()

        except Exception as e:
            logging.error(f"Error in story progression: {e}")
            self.status_bar.showMessage("Error progressing story")

    def handle_chapter_end(self):
        """Handle the end of a chapter with improved logging and error handling."""
        try:
            logging.info("Handling chapter end")
            
            # First ensure any fullscreen viewer is closed
            if hasattr(self, 'story_display') and hasattr(self.story_display, '_fullscreen_viewer'):
                logging.info("Cleaning up fullscreen viewer")
                self.story_display.cleanup_viewer()

            # Move story to completed folder
            if hasattr(self, 'story_manager'):
                logging.info(f"Story filepath: {self.story_manager.filepath}")
                if self.story_manager.move_to_completed():
                    status_msg = "Chapter complete! Story moved to completed folder."
                    logging.info("Successfully moved story to completed folder")
                else:
                    status_msg = "Chapter complete! Failed to move story file."
                    logging.error("Failed to move story to completed folder")
            else:
                status_msg = "Chapter complete!"
                logging.warning("No story manager available for completion handling")

            # Clean up existing UI elements
            if hasattr(self, 'story_display'):
                # Remove any existing chapter selection buttons
                for child in self.story_display.findChildren(QPushButton):
                    if child.text() == "Select New Chapter":
                        child.setParent(None)
                        child.deleteLater()

                # Update UI with completion message
                self.story_display.clear()  # Clear existing content
                self.story_display.append_text(
                    "<br><div style='text-align: center;'>"
                    "<h2>Chapter Complete!</h2>"
                    "<p>You have completed all available tasks for now.</p>"
                    "<p>Press G or click 'Select New Chapter' to continue your adventure!</p>"
                    "</div>"
                )

                # Add new chapter selection button
                try:
                    layout = self.story_display.layout()
                    if layout is not None:
                        new_chapter_button = QPushButton("Select New Chapter")
                        new_chapter_button.clicked.connect(self._show_story_selection)
                        layout.addWidget(new_chapter_button)
                    else:
                        logging.error("Story display has no layout")
                except Exception as e:
                    logging.error(f"Error adding chapter selection button: {e}")

            # Update UI state
            if hasattr(self, 'action_buttons'):
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.hide()
            
            if hasattr(self, 'settings_button'):
                self.settings_button.setEnabled(True)
                
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(status_msg)
            
            # Clear story manager and reset state
            self.story_manager = None
            
            logging.info("Chapter end handling complete")

        except Exception as e:
            logging.error(f"Error handling chapter end: {e}", exc_info=True)
            self.status_bar.showMessage("Error completing chapter")

    def _show_story_selection(self):
        """Show the story selection dialog."""
        try:
            # Clean up existing UI state
            if hasattr(self, 'story_display'):
                self.story_display.clear()
                
            if hasattr(self, 'action_buttons'):
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.hide()

            # Show story selection dialog
            dialog = StorySelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted and dialog.selected_story:
                self._load_selected_story(dialog.selected_story)
            else:
                logging.info("Story selection cancelled or no story selected")
                # Restore chapter end state
                self.handle_chapter_end()

        except Exception as e:
            logging.error(f"Error showing story selection: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", "Failed to show story selection")

    def _can_proceed(self) -> bool:
        """Check if story can proceed."""
        try:
            if self.battle_manager.is_in_battle():
                logging.debug("Cannot proceed during battle")
                return False

            if not hasattr(self, 'story_manager'):
                logging.debug("No story manager available")
                return False

            return True

        except Exception as e:
            logging.error(f"Error checking story progression: {e}")
            return False

    def toggle_fullscreen(self):
        """Toggle fullscreen state with proper battle handling."""
        try:
            if self.isFullScreen():
                self.showNormal()
                if self.battle_manager.is_in_battle():
                    self.battle_manager.hide_compact_mode()
            else:
                self.showFullScreen()

            self._ensure_focus()
            logging.debug(f"Fullscreen toggled: {self.isFullScreen()}")

        except Exception as e:
            logging.error(f"Error toggling fullscreen: {e}")
            # Emergency exit from fullscreen if needed
            self.showNormal()

    def _ensure_focus(self):
        """Ensure proper focus is set."""
        try:
            # First check if we're in fullscreen
            if self.isFullScreen():
                # If in battle, ensure we can exit
                if self.battle_manager.is_in_battle():
                    # Only show compact mode if not already paused
                    if not self.battle_manager.paused:
                        self.battle_manager.toggle_pause()
                    self.battle_manager.show_compact_mode()
            # Set window focus
            self.activateWindow()
            self.raise_()

            # Set focus to story display
            if hasattr(self, 'story_display'):
                self.story_display.setFocus()
                logging.info("Focus set to story display")

        except Exception as e:
            logging.error(f"Error ensuring focus: {e}")

    def update_tasks_left(self):
        """Update the tasks left display."""
        try:
            if self.battle_manager and self.battle_manager.current_enemy:
                current_hp = self.battle_manager.battle_state.enemy_hp
                tasks_left = max(0, current_hp)
                self.tasks_left_label.setText(str(tasks_left))

                # Update compact window if it exists
                if self.battle_manager.compact_window:
                    self.battle_manager.compact_window.update_tasks(tasks_left)

        except Exception as e:
            logging.error(f"Error updating tasks left: {e}")

    def toggle_pause(self):
        """Pause or resume the game."""
        try:
            self.battle_manager.toggle_pause()
        except Exception as e:
            logging.error(f"Error toggling pause: {e}")

    def open_settings(self):
        """Open the settings dialog."""
        try:
            settings_dialog = SettingsDialog(self.task_manager, self)
            if settings_dialog.exec_() == QDialog.Accepted:
                self._apply_settings_changes(settings_dialog)
        except Exception as e:
            logging.error(f"Error opening settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open settings: {str(e)}")

    def _apply_settings_changes(self, settings_dialog: SettingsDialog):
        """Apply changes from settings dialog."""
        try:
            if settings_dialog.saved:
                # Update task manager
                self.task_manager = settings_dialog.task_manager
                self.task_manager.save_tasks()

                # Load and apply shake animation setting
                settings_file = os.path.join(DATA_DIR, 'settings.json')
                if os.path.exists(settings_file):
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    shake_enabled = settings.get('shake_animation', True)
                    status = "enabled" if shake_enabled else "disabled"
                    self.story_display.append_text(
                        f"<p>Shaking animation has been <b>{status}</b>.</p>"
                    )
                    self.status_bar.showMessage(f"Shaking animation {status}")

                # Update UI
                self.story_display.append_text("<p>Settings updated successfully.</p>")
                self.status_bar.showMessage("Settings updated successfully")

                # Update tasks display if not in battle
                if not self.battle_manager.is_in_battle():
                    self.update_tasks_left()

        except Exception as e:
            logging.error(f"Error applying settings changes: {e}")
            QMessageBox.critical(self, "Error", "Failed to apply settings changes")

    def adjust_fonts(self):
        """Adjust fonts based on window size."""
        try:
            # Calculate font size based on window width
            width = self.width()
            font_size = 16  # Default
            if width < 800:
                font_size = 12
            elif width < 1200:
                font_size = 14

            # Update Player Panel fonts
            self.player_panel.level_label.setFont(QFont("Arial", font_size, QFont.Bold))
            self.player_panel.xp_label.setFont(QFont("Arial", font_size))

            # Update Enemy Panel fonts
            self.enemy_panel.enemy_label.setFont(QFont("Arial", font_size + 2, QFont.Bold))
            self.enemy_panel.task_label.setFont(QFont("Arial", font_size, QFont.StyleItalic))
            self.enemy_panel.hp_bar.setFont(QFont("Arial", font_size))

            # Update Story Display fonts
            self.story_display.story_text.setFont(QFont("Times New Roman", font_size))

            # Update Action Button fonts
            if hasattr(self.action_buttons, 'next_button'):
                self.action_buttons.next_button.setFont(QFont("Arial", font_size, QFont.Bold))
            if hasattr(self.action_buttons, 'attack_button'):
                self.action_buttons.attack_button.setFont(QFont("Arial", font_size))
            if hasattr(self.action_buttons, 'heavy_attack_button'):
                self.action_buttons.heavy_attack_button.setFont(QFont("Arial", font_size))

            # Update Settings Button font
            self.settings_button.setFont(QFont("Arial", font_size))

            # Update Choices Panel fonts
            for i in range(self.choices_panel.layout.count()):
                item = self.choices_panel.layout.itemAt(i)
                if item and item.widget():
                    item.widget().setFont(QFont("Arial", font_size))

        except Exception as e:
            logging.error(f"Error adjusting fonts: {e}")

    def trigger_shake_animation(self):
        """Trigger the shaking animation if enabled."""
        try:
            settings_file = os.path.join(DATA_DIR, 'settings.json')
            shake_enabled = True  # Default to True

            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)

            if shake_enabled and self.shake_animation.state() != QPropertyAnimation.Running:
                original_geometry = self.geometry()
                offset = 10

                # Define shake keyframes
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

                self.shake_animation.stop()
                self.shake_animation.setStartValue(keyframes[0][1])
                for fraction, rect in keyframes[1:]:
                    self.shake_animation.setKeyValueAt(fraction, rect)
                self.shake_animation.start()

        except Exception as e:
            logging.error(f"Error during shake animation: {e}")

    def eventFilter(self, obj, event):
        """Handle window focus events."""
        if obj is self:
            if event.type() == QEvent.WindowDeactivate:
                if self.battle_manager.is_in_battle():
                    self.battle_manager.show_compact_mode()
            elif event.type() == QEvent.WindowActivate:
                self.battle_manager.hide_compact_mode()
                if self.isFullScreen():
                    self.releaseKeyboard()
        return super().eventFilter(obj, event)

    def navigate_back(self):
        """Navigate to previous story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.BACKWARD)

    def navigate_forward(self):
        """Navigate to next story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.FORWARD)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key events at the main window level."""
        try:
            # Handle escape from fullscreen
            if event.key() == Qt.Key_Escape:
                if self.isFullScreen():
                    self.showNormal()
                    if self.battle_manager.is_in_battle():
                        self.battle_manager.hide_compact_mode()
                    self._ensure_focus()
                    return

            if hasattr(self, 'story_display'):
                if event.key() == Qt.Key_F:
                    if hasattr(self.story_display, 'current_image_path') and self.story_display.current_image_path:
                        self.story_display._show_fullscreen_viewer()
                elif event.key() == Qt.Key_F11:
                    self.toggle_fullscreen()
                elif event.key() == Qt.Key_Left:
                    logging.info("Left key pressed in main window")
                    self.story_display.navigate_back_signal.emit()
                elif event.key() in (Qt.Key_Right, Qt.Key_G):
                    logging.info("Advance key pressed in main window")
                    self.story_display.story_advance_signal.emit()
                else:
                    super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)

        except Exception as e:
            logging.error(f"Error handling key press in main window: {e}")

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Save window settings
            self.save_window_settings()

            # Cleanup components
            cleanup_errors = []

            # Stop hotkey listener
            try:
                self.hotkey_listener.stop()
                self.hotkey_listener.wait()
            except Exception as e:
                cleanup_errors.append(f"Hotkey listener cleanup failed: {str(e)}")

            # Cleanup battle manager
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
            logging.critical(f"Critical error during window close: {str(e)}")
            event.accept()

    def save_window_settings(self):
        """Save current window settings."""
        try:
            settings_file = os.path.join(DATA_DIR, 'settings.json')
            settings = self._load_settings_file()

            # Update window dimensions
            settings['window'] = {
                'width': self.width(),
                'height': self.height()
            }

            # Save settings
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)

        except Exception as e:
            logging.error(f"Error saving window settings: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = TaskRPG()
    game.show()
    sys.exit(app.exec_())
