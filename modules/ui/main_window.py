# modules/ui/main_window.py

import os
import json
import logging
import sys
import traceback
from typing import Dict, List, Tuple, TYPE_CHECKING

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
from modules.ui.components import (
    PlayerPanel, 
    EnemyPanel, 
    StoryDisplay, 
    ActionButtons, 
    ChoicesPanel,
    CompactBattleWindow
)
from modules.ui.dialogs.settings_dialog import SettingsDialog
from modules.ui.dialogs.story_selection_dialog import StorySelectionDialog
from modules.ui.components.fullscreen_image_viewer import FullscreenImageViewer
from core.battle.battle_manager import BattleManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TaskRPG(QMainWindow):
    """
    Main game window handling UI coordination and game state management.
    """

    def __init__(self):
        super().__init__()
        logging.info("Initializing TaskRPG main window")

        # Set window properties
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))
        self.setMinimumSize(900, 700)

        # Load window settings
        self._load_window_settings()

        # Initialize core components first
        self.init_core_components()

        # Create and set central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Initialize status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Initialize UI components
        self.init_ui()

        # Initialize managers that depend on UI
        self.init_managers()

        # Start hotkey system
        self.init_hotkeys()

        # Initialize animations
        self.init_animations()

        # Setup dynamic font scaling
        self.init_font_scaling()

        # Install event filter for window state management
        self.installEventFilter(self)

        # Set focus policy
        self.setFocusPolicy(Qt.StrongFocus)

        # Prompt story selection (after UI is ready)
        QTimer.singleShot(0, self.select_story)

        # Set initial focus after a delay
        QTimer.singleShot(100, self._ensure_focus)

        logging.info("TaskRPG main window initialization complete")

    def init_core_components(self):
        """Initialize core game components."""
        try:
            # Initialize task manager
            self.task_manager = TaskManager()

            # Initialize player
            self.player = Player()

            # Initialize image generator
            self.image_generator = ImageGenerator()

            # Initialize battle manager
            self.battle_manager = BattleManager(self.task_manager, self.player)

            # Initialize story manager with default path
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

            # Top section (player, enemy, tasks)
            top_layout = self._create_top_section()
            main_layout.addLayout(top_layout)

            # Story display
            self.story_display = StoryDisplay()
            main_layout.addWidget(self.story_display)

            # Choices panel
            self.choices_panel = ChoicesPanel()
            main_layout.addWidget(self.choices_panel)

            # Action buttons
            self.action_buttons = ActionButtons()
            main_layout.addWidget(self.action_buttons)

            # Settings button
            settings_button = self._create_settings_button()
            main_layout.addWidget(settings_button, alignment=Qt.AlignRight)

            # Set layout
            self.centralWidget().setLayout(main_layout)

            # Connect signals
            self._connect_ui_signals()

            logging.info("UI components initialized")

        except Exception as e:
            logging.error(f"Error initializing UI: {e}")
            raise

    def _create_top_section(self) -> QHBoxLayout:
        """Create the top section of the UI containing player, enemy, and task info."""
        layout = QHBoxLayout()
        layout.setSpacing(30)

        # Player panel
        self.player_panel = PlayerPanel(self.player)
        layout.addWidget(self.player_panel)

        # Enemy panel
        self.enemy_panel = EnemyPanel()
        layout.addWidget(self.enemy_panel)

        # Tasks left group
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
        self.settings_button.setFixedHeight(40)
        self.settings_button.setToolTip("Open settings dialog")
        return self.settings_button

    def _connect_ui_signals(self):
        """Connect all UI signals."""
        # Story navigation
        self.story_display.navigate_back_signal.connect(self.navigate_back)
        self.story_display.navigate_forward_signal.connect(self.navigate_forward)
        self.story_display.story_advance_signal.connect(self.next_story_segment)

        # Action buttons
        self.action_buttons.next_button.clicked.connect(self.next_story_segment)

        # Settings button
        self.settings_button.clicked.connect(self.open_settings)

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

            logging.info("Managers initialized")

        except Exception as e:
            logging.error(f"Error initializing managers: {e}")
            raise

    def init_hotkeys(self):
        """Initialize the global hotkeys system."""
        try:
            self.hotkey_listener = GlobalHotkeys()

            # Connect battle hotkeys
            self.battle_manager.connect_signals(self.hotkey_listener)

            # Connect story progression
            self.hotkey_listener.next_story_signal.connect(self.next_story_segment)

            # Start hotkey listener
            self.hotkey_listener.start()

            logging.info("Hotkey system initialized")

        except Exception as e:
            logging.error(f"Error initializing hotkeys: {e}")
            raise

    def init_animations(self):
        """Initialize window animations."""
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

            # Get window dimensions
            window_width = settings.get('window', {}).get('width', 900)
            window_height = settings.get('window', {}).get('height', 736)

            # Calculate center position
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2

            # Set window geometry
            self.setGeometry(x, y, window_width, window_height)

        except Exception as e:
            logging.error(f"Error loading window settings: {e}")
            # Use default size if settings fail
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

            # Initialize story manager
            self.story_manager = StoryManager(
                filepath=story_path,
                image_generator=self.image_generator,
                image_folder=image_folder,
                ui_component=self,
                battle_manager=self.battle_manager
            )

            # Display initial segment
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

            # Handle battle nodes
            if "battle" in current_node and not current_node.get("battle_completed", False):
                battle_info = current_node["battle"]
                if self.battle_manager.start_battle(battle_info):
                    current_node["battle_completed"] = True
                    logging.info("Battle started successfully")
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
        """Handle the end of a chapter."""
        try:
            self.story_display.append_text(
                "<br><b>Chapter Complete!</b><br>"
                "<p>You have completed all available tasks for now.</p>"
                "<p>Feel free to start a new chapter or take a break!</p>"
            )

            # Update UI state
            self.action_buttons.hide_attack_buttons()
            self.action_buttons.next_button.hide()
            self.status_bar.showMessage("All tasks completed! Well done!")

            # Show completion dialog
            QMessageBox.information(
                self,
                "Tasks Complete",
                "Congratulations! You have completed all available tasks.\n\n"
                "You can start a new chapter when you're ready!"
            )

        except Exception as e:
            logging.error(f"Error handling chapter end: {e}")
            QMessageBox.critical(self, "Error", "Failed to handle chapter end properly")

    def _can_proceed(self) -> bool:
        """Check if story can proceed."""
        try:
            # Add your specific conditions here
            return True
        except Exception as e:
            logging.error(f"Error checking story progression: {e}")
            return False

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
            width = self.width()
            if width < 800:
                font_size = 12
            elif width < 1200:
                font_size = 14
            else:
                font_size = 16

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
            self.action_buttons.next_button.setFont(QFont("Arial", font_size, QFont.Bold))
            if hasattr(self.action_buttons, 'attack_button'):
                self.action_buttons.attack_button.setFont(QFont("Arial", font_size, QFont.Bold))
            if hasattr(self.action_buttons, 'heavy_attack_button'):
                self.action_buttons.heavy_attack_button.setFont(QFont("Arial", font_size, QFont.Bold))

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

    def navigate_back(self):
        """Navigate to previous story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.BACKWARD)

    def navigate_forward(self):
        """Navigate to next story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.FORWARD)

    def _ensure_focus(self):
        """Ensure proper focus is set."""
        try:
            self.activateWindow()
            self.raise_()

            if hasattr(self, 'story_display'):
                self.story_display.setFocus()
                logging.info("Focus set to story display")

        except Exception as e:
            logging.error(f"Error ensuring focus: {e}")

    def eventFilter(self, obj, event):
        """Handle window focus events."""
        if obj is self:
            if event.type() == QEvent.WindowDeactivate:
                if self.battle_manager.is_in_battle():
                    self.battle_manager.show_compact_mode()
            elif event.type() == QEvent.WindowActivate:
                self.battle_manager.hide_compact_mode()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Save window settings
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

    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        QTimer.singleShot(200, self._ensure_focus)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key events at the main window level."""
        try:
            if hasattr(self, 'story_display'):
                if event.key() == Qt.Key_F:
                    if hasattr(self.story_display, 'current_image_path') and self.story_display.current_image_path:
                        self.story_display._show_fullscreen_viewer()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = TaskRPG()
    game.show()
    sys.exit(app.exec_())
