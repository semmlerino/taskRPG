# modules/ui/main_window.py

import os
import json
import logging
import random
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QProgressBar, QMessageBox, QDialog, QGroupBox, QSizePolicy,
    QStatusBar, QProgressDialog, QApplication
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from modules.constants import WINDOW_TITLE, WINDOW_ICON, WINDOW_SIZE, ASSETS_DIR
from modules.game_logic import Player, Enemy, TaskManager
from modules.story import StoryManager
from modules.hotkeys import GlobalHotkeys
from modules.image_generator import ImageGenerator
from modules.ui.components.player_panel import PlayerPanel
from modules.ui.components.enemy_panel import EnemyPanel
from modules.ui.components.story_display import StoryDisplay
from modules.ui.components.action_buttons import ActionButtons
from modules.ui.dialogs.settings_dialog import SettingsDialog
from modules.ui.components.choices_panel import ChoicesPanel
from modules.ui.dialogs.story_selection_dialog import StorySelectionDialog
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TaskRPG(QWidget):
    """
    Main game class. Handles the UI, game logic, and interactions.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))
        self.resize(*WINDOW_SIZE)

        # Make the window resizable with minimum size constraints
        self.setMinimumSize(900, 700)

        # Initialize Task Manager
        self.task_manager = TaskManager()

        # Initialize Player and Game State
        self.player = Player()
        self.current_enemy = None
        self.paused = False

        # Initialize ImageGenerator and StoryManager
        self.image_generator = ImageGenerator()
        self.story_manager = None  # Will be initialized after story selection
        self.story_image_folder = None

        # Initialize Status Bar before init_ui to prevent AttributeError
        self.status_bar = QStatusBar()

        # Initialize UI Components
        self.init_ui()

        # Initialize and start global hotkeys listener
        self.init_hotkeys()

        # Initialize Shaking Animation
        self.shake_animation = QPropertyAnimation(self, b"geometry")
        self.shake_animation.setDuration(100)  # Duration per shake
        self.shake_animation.setLoopCount(4)  # Number of shakes
        self.shake_animation.setEasingCurve(QEasingCurve.Linear)

        # Dynamic Font Scaling Timer
        self.font_scaling_timer = QTimer()
        self.font_scaling_timer.timeout.connect(self.adjust_fonts)
        self.font_scaling_timer.start(500)  # Adjust fonts every 500ms

        # Initialize Status Bar
        self.init_status_bar()

        # Prompt story selection
        self.select_story()

    def init_ui(self):
        """Initializes the user interface components."""
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
        self.action_buttons.connect_buttons(
            next_func=self.next_story_segment,
            attack_func=self.player_attack,
            heavy_attack_func=self.player_heavy_attack
        )
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

        # Add Status Bar
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    def init_status_bar(self):
        """Initializes the status bar with default messages."""
        self.status_bar.showMessage("Welcome to Task RPG! Start your adventure.")

    def init_hotkeys(self):
        """Initializes the global hotkeys listener."""
        self.hotkey_listener = GlobalHotkeys()
        self.hotkey_listener.normal_attack_signal.connect(self.player_attack)
        self.hotkey_listener.heavy_attack_signal.connect(self.player_heavy_attack)
        self.hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
        self.hotkey_listener.next_story_signal.connect(self.next_story_segment)
        self.hotkey_listener.start()

    def select_story(self):
        """Prompts the user to select a story to load."""
        dialog = StorySelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                selected_story = dialog.selected_story
                story_name = os.path.splitext(os.path.basename(selected_story))[0]
                self.story_image_folder = os.path.join(ASSETS_DIR, 'images', story_name)
                
                # Create story image folder if it doesn't exist
                os.makedirs(self.story_image_folder, exist_ok=True)

                self.story_manager = StoryManager(selected_story, image_generator=self.image_generator, image_folder=self.story_image_folder)
                logging.info(f"Story loaded from {selected_story}.")
                self.generate_all_images()
                self.display_story_segment()
            except Exception as e:
                logging.error(f"Error loading story: {e}")
                QMessageBox.critical(self, "Error", f"Failed to load story: {e}")
        else:
            # If no story selected, exit the application
            QMessageBox.information(self, "No Story Selected", "No story selected. Exiting the game.")
            self.close()

    def generate_all_images(self):
        """Generates all images for the story at the beginning."""
        try:
            image_prompts = self.story_manager.get_all_image_prompts()
            total_images = len(image_prompts)
            
            if total_images == 0:
                logging.info("No images to generate for the selected story.")
                return

            progress_dialog = QProgressDialog("Generating/Loading images...", "Cancel", 0, total_images, self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            
            for i, (node_key, prompt) in enumerate(image_prompts.items()):
                if progress_dialog.wasCanceled():
                    logging.info("Image generation canceled by user.")
                    break
                
                image_filename = f"{node_key}.png"
                image_path = os.path.join(self.story_image_folder, image_filename)
                
                try:
                    if os.path.exists(image_path):
                        logging.info(f"Image for {node_key} already exists. Skipping generation.")
                    else:
                        image_path = self.image_generator.generate_image(prompt, save_path=image_path)
                    
                    if image_path:
                        self.story_manager.set_generated_image(node_key, image_path)
                except Exception as e:
                    logging.error(f"Error generating/loading image for {node_key}: {e}")
                
                progress_dialog.setValue(i + 1)
                QApplication.processEvents()
            
            progress_dialog.close()
        except Exception as e:
            logging.error(f"Error in generate_all_images: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate/load images: {e}")

    def display_story_segment(self):
        """Displays the current segment of the story."""
        node = self.story_manager.get_current_node()
        text = self.story_manager.get_text()
        environment = self.story_manager.get_environment()
        npc_info = self.story_manager.get_npc()
        event = self.story_manager.get_event()
        battle_info = self.story_manager.get_battle_info()
        choices = self.story_manager.get_choices()
        
        # Display main narrative text
        self.story_display.append_text(f"<p>{text}</p>")

        # Display pre-generated image if available
        image_path = self.story_manager.get_generated_image(self.story_manager.current_node_key)
        if image_path and os.path.exists(image_path):
            self.story_display.display_image(image_path)
        else:
            self.story_display.display_image("")  # Clear image

        # Display environment description if available
        if environment:
            self.story_display.append_text(f"<p><i>Environment:</i> {environment}</p>")

        # Display event description if available
        if event:
            self.story_display.append_text(f"<p><i>Event:</i> {event}</p>")

        # Display NPC dialogue if available
        if npc_info:
            npc_name = npc_info.get("name", "Unknown NPC")
            dialogue = npc_info.get("dialogue", "")
            self.story_display.append_text(f"<p><b>{npc_name} says:</b> \"{dialogue}\"</p>")

        if battle_info:
            # Initiate battle with a random task from tasks.json
            message = battle_info.get("message", "An enemy appears!")
            enemy_name = battle_info.get("enemy", "Unknown Enemy")
            task = self.task_manager.get_random_active_task()
            if task:
                task_name = task['name']
                task_min = task['min']
                task_max = task['max']
                task_amount = random.randint(task_min, task_max)
                # Insert both messages together within paragraphs
                self.story_display.append_text(
                    f"<p><i>{message}</i></p>"
                    f"<p>To defeat the <b>{enemy_name}</b>, you need to complete the task: <b>{task_name}</b></p>"
                )
                # Generate the enemy
                self.generate_enemy(enemy_name, task_name, task_amount)
            else:
                logging.error("No active tasks available.")
                QMessageBox.critical(self, "Error", "No active tasks available to assign to enemy.")
        elif choices:
            # Display choices
            self.choices_panel.display_choices(choices, self.make_choice)
        else:
            # End of story or continue to next node
            if self.story_manager.is_end():
                self.story_display.append_text("<br><b>The End.</b><br>")
                self.action_buttons.hide_attack_buttons()
                self.settings_button.setEnabled(False)
                self.status_bar.showMessage("Story concluded.")
            else:
                self.story_display.append_text("<br>Press 'G' or click 'Next' to continue.<br>")
                self.action_buttons.show_attack_buttons()  # Ensure correct button visibility
                self.action_buttons.next_button.show()
                self.status_bar.showMessage("Awaiting your next move.")

    def make_choice(self, choice: Dict[str, Any]):
        """Handles the player's choice."""
        next_node = choice.get('next')
        if next_node:
            self.story_manager.set_current_node(next_node)
            self.choices_panel.clear_choices()
            self.display_story_segment()

    def generate_enemy(self, enemy_name: str, task_name: str, task_amount: int):
        """
        Generates an enemy based on the triggered task.
        """
        try:
            # Validate enemy_name, task_name, and task_amount
            if not enemy_name or not task_name or not isinstance(task_amount, int):
                logging.error("Invalid enemy data for enemy generation.")
                QMessageBox.critical(self, "Error", "Invalid enemy data for enemy generation.")
                return

            # Create Enemy with attacks required
            self.current_enemy = Enemy(name=enemy_name, hp=task_amount, task_name=task_name)
            self.enemy_panel.update_panel(self.current_enemy)
            self.update_tasks_left()

            # Show Attack and Heavy Attack buttons, hide Next button
            self.action_buttons.show_attack_buttons()

            # Update status bar
            self.status_bar.showMessage(f"A {self.current_enemy.name} appears! Complete the task '{self.current_enemy.task_name}' to defeat it.")

            # Trigger shaking animation if enabled
            self.trigger_shake_animation()
        except Exception as e:
            logging.error(f"Failed to generate enemy. Error: {e}")
            QMessageBox.critical(self, "Error", "An unexpected error occurred while generating the enemy.")

    def update_tasks_left(self):
        """Updates the 'Tasks Left' display."""
        if self.current_enemy:
            self.tasks_left_label.setText(str(self.current_enemy.current_hp))
        else:
            tasks_left = self.task_manager.get_active_tasks_count()
            self.tasks_left_label.setText(str(tasks_left))

    def next_story_segment(self):
        """Proceeds to the next segment of the story or notifies if in battle."""
        if not self.current_enemy:
            next_node = self.story_manager.get_current_node().get('next')
            if next_node:
                self.story_manager.set_current_node(next_node)
                self.display_story_segment()
            else:
                QMessageBox.information(self, "End of Story", "You have reached the end of the story.")
                self.status_bar.showMessage("Story concluded.")
        else:
            QMessageBox.information(self, "Battle In Progress", "You must defeat the current enemy before proceeding!")
            self.status_bar.showMessage("Battle in progress. Defeat the enemy to proceed.")

    def player_attack(self):
        """Performs a regular attack on the enemy."""
        try:
            if self.paused or not self.current_enemy:
                return

            # Player attacks enemy
            player_damage = 1  # Each attack reduces attacks left by 1
            self.current_enemy.take_damage(player_damage)
            self.story_display.append_text(f"<p>You attack the <b>{self.current_enemy.name}</b> and deal <b>{player_damage}</b> damage!</p>")
            self.enemy_panel.update_panel(self.current_enemy)
            self.update_tasks_left()

            # Trigger shaking animation if enabled
            self.trigger_shake_animation()

            if self.current_enemy.is_defeated():
                self.display_victory()
                defeated_node = f"{self.current_enemy.name.lower()}_defeated"
                self.current_enemy = None
                self.enemy_panel.update_panel(None)
                self.update_tasks_left()
                # Move to the node corresponding to victory
                if defeated_node in self.story_manager.story_data:
                    self.story_manager.set_current_node(defeated_node)
                    self.display_story_segment()
                else:
                    self.story_display.append_text("<p>Victory! Press 'G' or click 'Next' to continue your journey.</p>")
                # Hide Attack and Heavy Attack buttons, show Next button
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.show()
                self.status_bar.showMessage("Enemy defeated! Proceeding to next segment.")
        except Exception as e:
            logging.error(f"Error during attack: {e}")
            QMessageBox.critical(self, "Error", "An unexpected error occurred during your attack.")

    def player_heavy_attack(self):
        """Performs a heavy attack on the enemy."""
        try:
            if self.paused or not self.current_enemy:
                return

            # Player performs heavy attack
            player_damage = 2  # Each heavy attack reduces attacks left by 2
            self.current_enemy.take_damage(player_damage)
            self.story_display.append_text(f"<p>You perform a heavy attack on the <b>{self.current_enemy.name}</b> dealing <b>{player_damage}</b> damage!</p>")
            self.enemy_panel.update_panel(self.current_enemy)
            self.update_tasks_left()

            # Trigger shaking animation if enabled
            self.trigger_shake_animation()

            if self.current_enemy.is_defeated():
                self.display_victory()
                defeated_node = f"{self.current_enemy.name.lower()}_defeated"
                self.current_enemy = None
                self.enemy_panel.update_panel(None)
                self.update_tasks_left()
                # Move to the node corresponding to victory
                if defeated_node in self.story_manager.story_data:
                    self.story_manager.set_current_node(defeated_node)
                    self.display_story_segment()
                else:
                    self.story_display.append_text("<p>Victory! Press 'G' or click 'Next' to continue your journey.</p>")
                # Hide Attack and Heavy Attack buttons, show Next button
                self.action_buttons.hide_attack_buttons()
                self.action_buttons.next_button.show()
                self.status_bar.showMessage("Enemy defeated! Proceeding to next segment.")
        except Exception as e:
            logging.error(f"Error during heavy attack: {e}")
            QMessageBox.critical(self, "Error", "An unexpected error occurred during your heavy attack.")

    def display_victory(self):
        """Displays victory message and awards experience points."""
        try:
            victory_messages = [
                f"You have defeated the <b>{self.current_enemy.name}</b>!",
                f"The <b>{self.current_enemy.name}</b> has been vanquished!",
                f"Victory! The <b>{self.current_enemy.name}</b> is no more.",
                f"You emerge triumphant over the <b>{self.current_enemy.name}</b>!"
            ]
            self.story_display.append_text(f"<p>{random.choice(victory_messages)}</p>")
            xp_gained = max(10, self.current_enemy.max_hp // 2)  # Ensure minimum XP
            self.player.gain_experience(xp_gained)
            self.story_display.append_text(f"<p>You gained <b>{xp_gained}</b> experience points!</p>")

            # Update status bar
            self.status_bar.showMessage(f"You gained {xp_gained} XP!")

        except Exception as e:
            logging.error(f"Error during victory display: {e}")
            QMessageBox.critical(self, "Error", "An unexpected error occurred during victory display.")

    def trigger_shake_animation(self):
        """Triggers the shaking animation if enabled in settings."""
        try:
            settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
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
                    (0.0, QRect(original_geometry.x(), original_geometry.y(), original_geometry.width(), original_geometry.height())),
                    (0.25, QRect(original_geometry.x() + offset, original_geometry.y(), original_geometry.width(), original_geometry.height())),
                    (0.5, QRect(original_geometry.x() - offset, original_geometry.y(), original_geometry.width(), original_geometry.height())),
                    (0.75, QRect(original_geometry.x() + offset, original_geometry.y(), original_geometry.width(), original_geometry.height())),
                    (1.0, QRect(original_geometry.x(), original_geometry.y(), original_geometry.width(), original_geometry.height()))
                ]

                self.shake_animation.stop()  # Stop any ongoing animation
                self.shake_animation.setStartValue(keyframes[0][1])
                for fraction, rect in keyframes[1:]:
                    self.shake_animation.setKeyValueAt(fraction, rect)
                self.shake_animation.start()
        except Exception as e:
            logging.error(f"Error during shaking animation: {e}")

    def toggle_pause(self):
        """Pauses or resumes the game."""
        self.paused = not self.paused
        if self.paused:
            self.story_display.append_text("<p><i>Game paused.</i></p>")
            self.status_bar.showMessage("Game paused.")
        else:
            self.story_display.append_text("<p><i>Game resumed.</i></p>")
            self.status_bar.showMessage("Game resumed.")

    def open_settings(self):
        """Opens the settings dialog to edit tasks and settings."""
        settings_dialog = SettingsDialog(self.task_manager, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            if settings_dialog.saved:
                self.task_manager = settings_dialog.task_manager
                self.task_manager.save_tasks()
                # Reload settings
                settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
                if os.path.exists(settings_file):
                    try:
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                        shake_enabled = settings.get('shake_animation', True)
                        # Notify the user about the change
                        status = "enabled" if shake_enabled else "disabled"
                        self.story_display.append_text(f"<p>Shaking animation has been <b>{status}</b>.</p>")
                        self.status_bar.showMessage(f"Shaking animation {status}.")
                    except Exception as e:
                        logging.error(f"Failed to load settings after saving. Error: {e}")
                self.story_display.append_text("<p>Settings updated successfully.</p>")
                self.status_bar.showMessage("Settings updated successfully.")
                # Update "Tasks Left" if not in battle
                if not self.current_enemy:
                    self.update_tasks_left()

    def closeEvent(self, event):
        """Handles the window close event. Stops hotkey listener thread."""
        self.hotkey_listener.stop()
        self.hotkey_listener.wait()
        event.accept()

    def adjust_fonts(self):
        """Adjusts font sizes based on window size for better readability."""
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
            self.story_display.image_label.setFont(QFont("Arial", font_size))

            # Update fonts in Action Buttons
            self.action_buttons.next_button.setFont(QFont("Arial", font_size, QFont.Bold))
            self.action_buttons.attack_button.setFont(QFont("Arial", font_size, QFont.Bold))
            self.action_buttons.heavy_attack_button.setFont(QFont("Arial", font_size, QFont.Bold))

            # Update fonts in Settings Button
            self.settings_button.setFont(QFont("Arial", font_size))

            # Update fonts in Choices Panel
            for i in range(self.choices_panel.layout.count()):
                item = self.choices_panel.layout.itemAt(i)
                if item.widget():
                    item.widget().setFont(QFont("Arial", font_size))
        except Exception as e:
            logging.error(f"Error during font adjustment: {e}")
