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

        # After initializing story_display
        self.story_display.setFocusPolicy(Qt.StrongFocus)
        
        # Create a timer to set focus after window is shown
        QTimer.singleShot(100, self._ensure_focus)

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

    def init_hotkeys(self):
        """Initialize the global hotkeys listener."""
        self.hotkey_listener = GlobalHotkeys()

        # Connect battle hotkeys through battle manager
        self.battle_manager.connect_signals(self.hotkey_listener)

        # Other hotkey connections
        self.hotkey_listener.next_story_signal.connect(self.next_story_segment)

        self.hotkey_listener.start()

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

        # After loading the story, set focus to story display
        self.story_display.setFocus()

    def _load_selected_story(self, selected_story: str):
        """Load the selected story file."""
        try:
            story_name = os.path.splitext(os.path.basename(selected_story))[0]
            self.story_image_folder = os.path.join(ASSETS_DIR, 'images', story_name)

            # Ensure the image folder exists
            os.makedirs(self.story_image_folder, exist_ok=True)

            # Initialize the StoryManager with the selected story and existing BattleManager
            self.story_manager = StoryManager(
                filepath=selected_story,
                image_generator=self.image_generator,
                image_folder=self.story_image_folder,
                ui_component=self,
                battle_manager=self.battle_manager  # Pass existing BattleManager
            )

            # Display the initial story segment
            self.story_manager.display_story_segment()

            logging.info(f"Story '{story_name}' loaded successfully.")

        except Exception as e:
            logging.error(f"Failed to load selected story: {e}")
            QMessageBox.critical(self, "Error",
                                 f"Failed to load the selected story:\n{str(e)}")

    def next_story_segment(self):
        """Progress to next story segment."""
        try:
            logging.info("next_story_segment called in TaskRPG")
            
            if not hasattr(self, 'story_manager'):
                logging.error("No story manager found")
                return
            
            if not self._can_proceed():
                logging.debug("Cannot proceed - conditions not met")
                return

            logging.info("Proceeding with story advancement")
            current_node = self.story_manager.get_current_node()
            logging.info(f"Current node: {current_node.get('next', 'No next node')}")

            # Handle battle nodes
            if "battle" in current_node and not current_node.get("battle_completed", False):
                try:
                    battle_info = current_node["battle"]
                    if self.battle_manager.start_battle(battle_info):
                        current_node["battle_completed"] = True
                        logging.info(f"Battle started successfully: {battle_info}")
                    return
                except Exception as battle_e:
                    logging.error(f"Battle initialization failed: {str(battle_e)}")
                    raise

            # Simple linear progression
            if next_node := current_node.get('next'):
                try:
                    logging.info(f"Attempting to advance to node: {next_node}")
                    self.story_manager.set_current_node(next_node)
                    result = self.story_manager.display_story_segment()
                    logging.info(f"Story segment display result: {result}")
                    logging.info(f"Advanced to node: {next_node}")
                except ValueError as e:
                    logging.error(f"Invalid next node '{next_node}': {str(e)}")
                    self.handle_chapter_end()
            else:
                logging.info("Reached end of story branch")
                self.handle_chapter_end()
        except Exception as e:
            logging.error(f"Error in next_story_segment: {e}", exc_info=True)

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

    def _can_proceed(self):
        """Check if story can proceed."""
        try:
            logging.info("Checking if story can proceed")
            # Add your conditions here
            can_proceed = True  # Or your actual conditions
            logging.info(f"Can proceed: {can_proceed}")
            return can_proceed
        except Exception as e:
            logging.error(f"Error in _can_proceed: {e}")
            return False

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

            settings_file = os.path.join(DATA_DIR, 'settings.json')
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

            # Update fonts in Action Buttons
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
            settings_file = os.path.join(DATA_DIR, 'settings.json')
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
            if event.type() == QEvent.WindowDeactivate:
                logging.debug("Window deactivated")
                if self.battle_manager.is_in_battle():
                    logging.debug("Battle is active, showing compact window")
                    self.battle_manager.show_compact_mode()
                else:
                    logging.debug("Battle not active, skipping compact window")
            elif event.type() == QEvent.WindowActivate:
                logging.debug("Window activated")
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
        """Handle window losing focus - show compact battle window."""
        logging.debug("Focus lost - Checking battle state")
        if self.battle_manager.is_in_battle():
            logging.debug("Battle active, showing compact window")
            self.battle_manager.show_compact_mode()
        else:
            logging.debug("No active battle during focus loss")
        super().focusOutEvent(event)

    def focusInEvent(self, event):
        """Handle window regaining focus - hide compact battle window."""
        logging.debug("Focus gained - Hiding compact window")
        self.battle_manager.hide_compact_mode()
        super().focusInEvent(event)

    def navigate_back(self):
        """Navigate to previous story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.BACKWARD)

    def navigate_forward(self):
        """Navigate to next story segment."""
        if self._can_proceed():
            self.story_manager.navigate(NavigationDirection.FORWARD)

    def load_window_settings(self) -> dict:
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

    def show_compact_mode(self):
        """Show compact battle window when main window loses focus."""
        try:
            logging.debug("Focus lost - Checking battle state")
            if self.battle_manager.is_in_battle():
                logging.debug("Battle active, showing compact window")
                self.battle_manager.show_compact_mode()
            else:
                logging.debug("No active battle during focus loss")
        except Exception as e:
            logging.error(f"Error showing compact window: {e}")

    def _ensure_focus(self):
        """Ensure proper focus is set after window is shown."""
        try:
            if hasattr(self, 'story_display'):
                logging.info("Setting initial focus to StoryDisplay")
                self.story_display.setFocus()
                self.story_display.activateWindow()
        except Exception as e:
            logging.error(f"Error setting initial focus: {e}")

    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        # Schedule another focus check
        QTimer.singleShot(200, self._ensure_focus)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key events at the main window level."""
        try:
            # If we have a story display, delegate key events to it
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