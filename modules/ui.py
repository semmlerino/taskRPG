# modules/ui.py

import os
import random
import logging
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QProgressBar, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QGroupBox, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCharFormat, QTextCursor, QPixmap
from .constants import (
    WINDOW_TITLE, WINDOW_ICON, WINDOW_SIZE, STORY_LINEAR_FILE,
    STORY_ADVANCED_FILE, ASSETS_DIR
)
from .game_logic import Player, Enemy, TaskManager
from .story import StoryManager
from .hotkeys import GlobalHotkeys
from .settings_dialog import SettingsDialog

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class StorySelectionDialog(QDialog):
    """
    Dialog for selecting which story to load.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Story")
        self.setFixedSize(400, 250)
        self.selected_story = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        label = QLabel("Choose a story to load:")
        label.setFont(QFont("Arial", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.list_widget = QListWidget()
        self.stories = {
            "Linear Story": STORY_LINEAR_FILE,
            "Advanced Story": STORY_ADVANCED_FILE
        }
        for title in self.stories.keys():
            item = QListWidgetItem(title)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        # Buttons
        buttons_layout = QHBoxLayout()
        select_button = QPushButton("Select")
        select_button.setFont(QFont("Arial", 12))
        select_button.clicked.connect(self.select_story)
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 12))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(select_button)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def select_story(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            selected_title = selected_items[0].text()
            self.selected_story = self.stories[selected_title]
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a story to load.")


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
        self.setMinimumSize(800, 600)

        # Initialize Task Manager
        self.task_manager = TaskManager()

        # Initialize Player and Game State
        self.player = Player()
        self.current_enemy = None
        self.paused = False
        self.story_in_battle = False

        # Initialize Story Manager
        self.story_manager = None  # Will be initialized after story selection

        # Initialize UI Components
        self.init_ui()

        # Initialize and start global hotkeys listener
        self.init_hotkeys()

        # Prompt story selection
        self.select_story()

    def init_ui(self):
        """Initializes the user interface components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top Layout for Player and Enemy Info
        top_layout = QHBoxLayout()
        top_layout.setSpacing(50)

        # Player Info Group
        player_group = QGroupBox("Player")
        player_layout = QVBoxLayout()

        self.player_level_label = QLabel(f"Level: {self.player.level}")
        self.player_level_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.player_xp_label = QLabel(f"XP: {self.player.experience}/{self.player.experience_to_next_level}")
        self.player_xp_label.setFont(QFont("Arial", 14))

        player_layout.addWidget(self.player_level_label)
        player_layout.addWidget(self.player_xp_label)
        player_group.setLayout(player_layout)

        # Enemy Info Group
        enemy_group = QGroupBox("Enemy")
        enemy_layout = QVBoxLayout()

        self.enemy_label = QLabel("No Enemy")
        self.enemy_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.enemy_label.setAlignment(Qt.AlignCenter)

        self.enemy_hp_bar = QProgressBar()
        self.enemy_hp_bar.setMaximum(100)
        self.enemy_hp_bar.setValue(0)
        self.enemy_hp_bar.setFormat("%p%")
        self.enemy_hp_bar.setAlignment(Qt.AlignCenter)
        self.enemy_hp_bar.setTextVisible(True)
        self.enemy_hp_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #76FF03;
                width: 20px;
            }
        """)

        enemy_layout.addWidget(self.enemy_label)
        enemy_layout.addWidget(self.enemy_hp_bar)
        enemy_group.setLayout(enemy_layout)

        top_layout.addWidget(player_group)
        top_layout.addWidget(enemy_group)
        main_layout.addLayout(top_layout)

        # Enemy Image
        self.enemy_image_label = QLabel()
        self.enemy_image_label.setAlignment(Qt.AlignCenter)
        self.enemy_image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.enemy_image_label.setStyleSheet("background-color: #E0E0E0; border: 1px solid #BDBDBD;")
        main_layout.addWidget(self.enemy_image_label)

        # Story Display Area (Text Log)
        self.story_text = QTextEdit()
        self.story_text.setReadOnly(True)
        self.story_text.setFont(QFont("Times New Roman", 16))
        self.story_text.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                color: #212121;
                border: 2px solid #BDBDBD;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.story_text)

        # Choices Layout
        self.choices_layout = QHBoxLayout()
        self.choices_layout.setSpacing(20)
        main_layout.addLayout(self.choices_layout)

        # Action Button (Next or Attack)
        self.action_button = QPushButton("Next (G)")
        self.action_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.action_button.setStyleSheet("""
            QPushButton {
                background-color: #42A5F5;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
        """)
        self.action_button.clicked.connect(self.next_story_segment)
        self.action_button.setFixedHeight(50)
        main_layout.addWidget(self.action_button)

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
        main_layout.addWidget(self.settings_button, alignment=Qt.AlignRight)

        self.setLayout(main_layout)

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
            selected_story = dialog.selected_story
            self.story_manager = StoryManager(selected_story)
            logging.info(f"Story loaded from {selected_story}.")
            self.display_story_segment()
        else:
            # If no story selected, exit the application
            QMessageBox.information(self, "No Story Selected", "No story selected. Exiting the game.")
            self.close()

    def display_story_segment(self):
        """Displays the current segment of the story."""
        node = self.story_manager.get_current_node()
        battle_info = self.story_manager.get_battle_info()
        choices = self.story_manager.get_choices()
        text = self.story_manager.get_text()

        # Append text to the story log
        self.story_text.append(f"{text}\n")
        self.scroll_to_end()

        if battle_info:
            # Initiate battle with a random task from tasks.json
            message = battle_info.get("message", "An enemy appears!")
            task = self.task_manager.get_random_active_task()
            if task:
                task_name = task['name']
                task_min = task['min']
                task_max = task['max']
                task_amount = random.randint(task_min, task_max)
                self.story_text.append(f"{message}\n")
                self.scroll_to_end()
                self.generate_enemy(task_name, task_amount)
            else:
                logging.error("No active tasks available.")
                QMessageBox.critical(self, "Error", "No active tasks available to assign to enemy.")
        elif choices:
            # Display choices
            self.display_choices(choices)
        else:
            # End of story
            self.story_text.append("\nThe End.")
            self.scroll_to_end()

    def scroll_to_end(self):
        """Scrolls the QTextEdit to the end."""
        cursor = self.story_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.story_text.setTextCursor(cursor)

    def update_status(self):
        """Updates the status displays for the enemy and player."""
        if self.current_enemy:
            # Update Enemy Info
            self.enemy_label.setText(f"{self.current_enemy.name}")
            if self.current_enemy.max_hp > 0:
                self.enemy_hp_bar.setMaximum(self.current_enemy.max_hp)
                self.enemy_hp_bar.setValue(self.current_enemy.current_hp)

                # Update HP Bar Color
                hp_percentage = (self.current_enemy.current_hp / self.current_enemy.max_hp) * 100
                if hp_percentage > 60:
                    color = "#76FF03"  # Green
                elif hp_percentage > 30:
                    color = "#FF9800"  # Orange
                else:
                    color = "#F44336"  # Red

                self.enemy_hp_bar.setStyleSheet(f"""
                    QProgressBar::chunk {{
                        background-color: {color};
                    }}
                """)
            else:
                self.enemy_hp_bar.setValue(0)
                self.enemy_hp_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
        else:
            # Reset Enemy Info
            self.enemy_label.setText("No Enemy")
            self.enemy_hp_bar.setValue(0)
            self.enemy_hp_bar.setStyleSheet("QProgressBar::chunk { background-color: #76FF03; }")
            self.enemy_image_label.clear()

        # Update Player Info
        self.player_level_label.setText(f"Level: {self.player.level}")
        self.player_xp_label.setText(f"XP: {self.player.experience}/{self.player.experience_to_next_level}")

    def display_choices(self, choices):
        """Displays choice buttons to the player."""
        # Hide action button when choices are present
        self.action_button.hide()

        # Clear previous choices
        self.clear_choices()

        # Create new choice buttons
        for choice in choices:
            btn = QPushButton(choice['text'])
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #81A1C1;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #5E81AC;
                }
            """)
            btn.clicked.connect(lambda checked, c=choice: self.make_choice(c))
            self.choices_layout.addWidget(btn)

        # Add stretch to push buttons to the left
        self.choices_layout.addStretch()

    def make_choice(self, choice):
        """Handles the player's choice."""
        next_node = choice.get('next')
        if next_node:
            self.story_manager.set_current_node(next_node)
            self.clear_choices()
            self.display_story_segment()

    def clear_choices(self):
        """Clears the choice buttons and shows the action button."""
        # Clear choice buttons
        while self.choices_layout.count():
            child = self.choices_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Show action button
        self.action_button.show()

    def generate_enemy(self, task_name: str, task_amount: int):
        """
        Generates an enemy based on the triggered task.
        :param task_name: The name of the task.
        :param task_amount: The number of attacks required to defeat the enemy.
        """
        # Validate task_name and task_amount
        if not task_name or not isinstance(task_amount, int):
            logging.error("Invalid task data for enemy generation.")
            QMessageBox.critical(self, "Error", "Invalid task data for enemy generation.")
            return

        # Create Enemy with attacks required
        self.current_enemy = Enemy(name=task_name, hp=task_amount)
        self.update_status()

        # Load enemy image from assets/images/enemy/enemy.png
        image_path = os.path.join(ASSETS_DIR, "images", "enemy", "enemy.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.enemy_image_label.setPixmap(pixmap)
        else:
            logging.warning(f"Enemy image not found at {image_path}.")
            self.enemy_image_label.clear()

        # Set action button to "Attack"
        self.action_button.setText("Attack (D)")
        try:
            self.action_button.clicked.disconnect()
        except Exception:
            pass  # Ignore if no connection exists
        self.action_button.clicked.connect(self.player_attack)

        # Display task information without the number
        self.story_text.append(f"\nDo the following task to defeat it:\n<b>{task_name}</b>\n")
        self.scroll_to_end()

    def next_story_segment(self):
        """Proceeds to the next segment of the story or notifies if in battle."""
        if not self.current_enemy:
            self.display_story_segment()
        else:
            QMessageBox.information(self, "Battle In Progress", "You must defeat the current enemy before proceeding!")

    def player_attack(self):
        """Performs a normal attack on the enemy."""
        if self.paused or not self.current_enemy:
            return

        # Player attacks enemy
        player_damage = 1  # Each attack reduces attacks left by 1
        self.current_enemy.take_damage(player_damage)
        self.story_text.append(f"You attack the <b>{self.current_enemy.name}</b> and deal <b>{player_damage}</b> damage!\n")
        self.scroll_to_end()
        self.update_status()

        if self.current_enemy.is_defeated():
            self.display_victory()
            defeated_node = f"{self.current_enemy.name.lower()}_defeated"
            self.current_enemy = None
            self.update_status()
            # Move to the node corresponding to victory
            if defeated_node in self.story_manager.story_data:
                self.story_manager.set_current_node(defeated_node)
                self.display_story_segment()
            else:
                self.story_text.append("Victory! Press 'G' or click 'Next' to continue your journey.\n")
                self.scroll_to_end()
            # Restore action button to "Next"
            self.action_button.setText("Next (G)")
            try:
                self.action_button.clicked.disconnect()
            except Exception:
                pass  # Ignore if no connection exists
            self.action_button.clicked.connect(self.next_story_segment)

    def player_heavy_attack(self):
        """Performs a heavy attack on the enemy."""
        if self.paused or not self.current_enemy:
            return

        # Player performs heavy attack
        player_damage = 2  # Each heavy attack reduces attacks left by 2
        self.current_enemy.take_damage(player_damage)
        self.story_text.append(f"You perform a heavy attack on the <b>{self.current_enemy.name}</b> dealing <b>{player_damage}</b> damage!\n")
        self.scroll_to_end()
        self.update_status()

        if self.current_enemy.is_defeated():
            self.display_victory()
            defeated_node = f"{self.current_enemy.name.lower()}_defeated"
            self.current_enemy = None
            self.update_status()
            # Move to the node corresponding to victory
            if defeated_node in self.story_manager.story_data:
                self.story_manager.set_current_node(defeated_node)
                self.display_story_segment()
            else:
                self.story_text.append("Victory! Press 'G' or click 'Next' to continue your journey.\n")
                self.scroll_to_end()
            # Restore action button to "Next"
            self.action_button.setText("Next (G)")
            try:
                self.action_button.clicked.disconnect()
            except Exception:
                pass  # Ignore if no connection exists
            self.action_button.clicked.connect(self.next_story_segment)

    def display_victory(self):
        """Displays victory message and awards experience points."""
        victory_messages = [
            f"You have defeated the <b>{self.current_enemy.name}</b>!",
            f"The <b>{self.current_enemy.name}</b> has been vanquished!",
            f"Victory! The <b>{self.current_enemy.name}</b> is no more.",
            f"You emerge triumphant over the <b>{self.current_enemy.name}</b>!"
        ]
        self.story_text.append(random.choice(victory_messages) + "\n")
        self.scroll_to_end()
        xp_gained = max(10, self.current_enemy.max_hp // 2)  # Ensure minimum XP
        self.player.gain_experience(xp_gained)
        self.story_text.append(f"You gained <b>{xp_gained}</b> experience points!\n")
        self.scroll_to_end()

    def toggle_pause(self):
        """Pauses or resumes the game."""
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        self.story_text.append(f"\nGame {status}.\n")
        self.scroll_to_end()

    def open_settings(self):
        """Opens the settings dialog to edit tasks."""
        settings_dialog = SettingsDialog(self.task_manager, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            if settings_dialog.saved:
                self.task_manager = settings_dialog.task_manager
                self.task_manager.save_tasks()
                self.story_text.append("Settings updated successfully.\n")
                self.scroll_to_end()
                # Optionally, update tasks left count
                self.update_status()

    def closeEvent(self, event):
        """Handles the window close event. Stops hotkey listener thread."""
        self.hotkey_listener.stop()
        self.hotkey_listener.wait()
        event.accept()
