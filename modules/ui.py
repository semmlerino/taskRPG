# modules/ui.py

import os
import random
import logging
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QProgressBar, QMessageBox, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCharFormat, QTextCursor
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
        self.setFixedSize(400, 250)  # Increased size for better visibility
        self.selected_story = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        label = QLabel("Choose a story to load:")
        label.setFont(QFont("Arial", 16))  # Increased font size
        layout.addWidget(label)

        self.list_widget = QListWidget()
        # Add available stories with titles
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
        select_button.setFont(QFont("Arial", 14))  # Increased font size
        select_button.clicked.connect(self.select_story)
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 14))  # Increased font size
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
        self.setWindowIcon(QIcon(WINDOW_ICON))  # Ensure the icon exists
        self.setFixedSize(*WINDOW_SIZE)
        
       
        # Make the window always on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Initialize Task Manager
        self.task_manager = TaskManager()

        # Initialize Player and Game State
        self.player = Player()
        self.current_enemy = None
        self.paused = False
        self.story_in_battle = False
        self.attacks_left = 0  # New attribute to track attacks left

        # Initialize Story Manager
        self.story_manager = None  # Will be initialized after story selection

        # Initialize UI Components
        self.init_ui()

        # Initialize and start global hotkeys listener
        self.init_hotkeys()

        # Removed HP Bar Animation as per user request
        # self.hp_animation = QPropertyAnimation()

        # Prompt story selection
        self.select_story()

    def init_ui(self):
        """Initializes the user interface components."""
        main_layout = QVBoxLayout()

        # Top Layout for Player and Enemy Info
        top_layout = QHBoxLayout()

        # Tasks Left Label
        self.tasks_left_label = QLabel("Tasks Left: 0")
        self.tasks_left_label.setFont(QFont("Arial", 22, QFont.Bold))  # Further increased font size
        self.tasks_left_label.setStyleSheet("color: #388E3C;")  # Dark Green
        top_layout.addWidget(self.tasks_left_label)

        # Enemy Info Layout (Label and HP Bar)
        enemy_info_layout = QVBoxLayout()

        self.enemy_label = QLabel("No Enemy")
        self.enemy_label.setFont(QFont("Arial", 28, QFont.Bold))  # Further increased font size
        self.enemy_label.setAlignment(Qt.AlignLeft)
        self.enemy_label.setStyleSheet("color: #D32F2F;")  # Dark Red
        enemy_info_layout.addWidget(self.enemy_label)

        # Enemy HP Bar Layout (HP Bar)
        hp_layout = QHBoxLayout()

        self.enemy_hp_bar = QProgressBar()
        self.enemy_hp_bar.setMaximum(100)
        self.enemy_hp_bar.setValue(0)
        # Initial color set to green
        self.enemy_hp_bar.setStyleSheet("QProgressBar::chunk { background-color: #76FF03; }")
        hp_layout.addWidget(self.enemy_hp_bar)

        # Removed "Attacks Left" Label
        # self.attacks_left_label = QLabel("Attacks Left: 0")
        # self.attacks_left_label.setFont(QFont("Arial", 18, QFont.Bold))
        # self.attacks_left_label.setStyleSheet("color: #000000;")
        # hp_layout.addWidget(self.attacks_left_label)

        enemy_info_layout.addLayout(hp_layout)
        top_layout.addLayout(enemy_info_layout)
        main_layout.addLayout(top_layout)

        # Enemy Image (Optional) - Positioned below HP Bar
        self.enemy_image_label = QLabel()
        self.enemy_image_label.setAlignment(Qt.AlignCenter)
        self.enemy_image_label.setFixedSize(400, 400)  # Further increased size
        main_layout.addWidget(self.enemy_image_label)

        # Game Display Area (Text Log)
        self.story_text = QTextEdit()
        self.story_text.setReadOnly(True)
        self.story_text.setFont(QFont("Times New Roman", 22))  # Further increased font size
        self.story_text.setStyleSheet("background-color: #FAFAFA; color: #000000;")
        main_layout.addWidget(self.story_text)

        # Choices Layout (Initially Hidden)
        self.choices_layout = QHBoxLayout()
        main_layout.addLayout(self.choices_layout)

        # Single Button for "Next" or "Attack"
        self.action_button = QPushButton("Next (G)")
        self.action_button.setFont(QFont("Arial", 22))  # Further increased font size
        self.action_button.setStyleSheet("background-color: #90CAF9; color: white;")  # Light Blue
        self.action_button.clicked.connect(self.next_story_segment)
        main_layout.addWidget(self.action_button)

        # Settings Button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setFont(QFont("Arial", 22))  # Further increased font size
        self.settings_button.setStyleSheet("background-color: #FFCC80; color: black;")  # Light Orange
        self.settings_button.clicked.connect(self.open_settings)
        main_layout.addWidget(self.settings_button)

        self.setLayout(main_layout)

    def init_hotkeys(self):
        """Initializes the global hotkeys listener."""
        self.hotkey_listener = GlobalHotkeys()
        self.hotkey_listener.normal_attack_signal.connect(self.player_attack)
        self.hotkey_listener.heavy_attack_signal.connect(self.player_heavy_attack)
        self.hotkey_listener.toggle_pause_signal.connect(self.toggle_pause)
        self.hotkey_listener.next_story_signal.connect(self.next_story_segment)
        # Removed open_settings_signal
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

        # Clear the story log and display only the latest text
        self.story_text.clear()
        self.story_text.append(f"{text}")
        self.highlight_last_text()

        if battle_info:
            # Initiate battle with a random task from tasks.json
            message = battle_info.get("message", "An enemy appears!")
            task = self.task_manager.get_random_active_task()
            if task:
                task_name = task['name']
                task_min = task['min']
                task_max = task['max']
                task_amount = random.randint(task_min, task_max)
                self.story_text.append(f"\n{message}")
                self.highlight_last_text()
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
            self.highlight_last_text()

    def highlight_last_text(self):
        """Highlights the last text added to the story log."""
        cursor = self.story_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.WordUnderCursor)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("black"))
        fmt.setFontWeight(QFont.Bold)
        cursor.mergeCharFormat(fmt)
        self.story_text.setTextCursor(cursor)

    def update_status(self):
        """Updates the status displays for the enemy and tasks left."""
        if self.current_enemy:
            # Set Tasks Left to remaining attacks
            tasks_left = self.current_enemy.current_hp
            self.tasks_left_label.setText(f"Tasks Left: {tasks_left}")
            self.enemy_label.setText(f"{self.current_enemy.name}")
            if self.current_enemy.max_hp is None:
                logging.error("Enemy's max_hp is None.")
                QMessageBox.critical(self, "Error", "Enemy's maximum attacks (max_hp) is undefined.")
                self.enemy_hp_bar.setMaximum(1)  # Set to minimum to avoid crash
                self.enemy_hp_bar.setValue(0)
            else:
                self.enemy_hp_bar.setMaximum(self.current_enemy.max_hp)
                self.enemy_hp_bar.setValue(self.current_enemy.current_hp)

                # Calculate HP percentage
                hp_percentage = (self.current_enemy.current_hp / self.current_enemy.max_hp) * 100

                # Set color based on HP percentage
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
            # When not in battle, show total active tasks
            tasks_left = self.task_manager.get_active_tasks_count()
            self.tasks_left_label.setText(f"Tasks Left: {tasks_left}")
            self.enemy_label.setText("No Enemy")
            self.enemy_hp_bar.setMaximum(100)
            self.enemy_hp_bar.setValue(0)
            self.enemy_hp_bar.setStyleSheet("QProgressBar::chunk { background-color: #76FF03; }")
            self.enemy_image_label.clear()

    def display_choices(self, choices):
        """Displays choice buttons to the player."""
        # Hide action button when choices are present
        self.action_button.hide()

        # Clear previous choices
        for i in reversed(range(self.choices_layout.count())):
            widget_to_remove = self.choices_layout.itemAt(i).widget()
            self.choices_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)

        # Create new choice buttons
        for choice in choices:
            btn = QPushButton(choice['text'])
            btn.setFont(QFont("Arial", 20))  # Further increased font size
            btn.setStyleSheet("background-color: #81A1C1; color: white;")  # Light Blue
            btn.clicked.connect(lambda checked, c=choice: self.make_choice(c))
            self.choices_layout.addWidget(btn)

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
        for i in reversed(range(self.choices_layout.count())):
            widget_to_remove = self.choices_layout.itemAt(i).widget()
            self.choices_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)

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

        # Load enemy image from fixed path
        # Fixed path: assets/images/enemy/enemy.png
        image_path = os.path.join(ASSETS_DIR, "images", "enemy", "enemy.png")
        if os.path.exists(image_path):
            self.enemy_image_label.setPixmap(QIcon(image_path).pixmap(400, 400))  # Further increased image size
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
        self.story_text.append(f"\nDo the following task to defeat it:\n{task_name}")
        self.highlight_last_text()

    def next_story_segment(self):
        """Proceeds to the next segment of the story or notifies if in battle."""
        if not self.story_in_battle and not self.current_enemy:
            self.display_story_segment()
        else:
            self.story_text.append("You must defeat the current enemy before proceeding!")
            self.highlight_last_text()

    def player_attack(self):
        """Performs a normal attack on the enemy."""
        if self.paused or not self.current_enemy:
            return

        # Player attacks enemy
        player_damage = 1  # Each attack reduces attacks left by 1
        self.current_enemy.take_damage(player_damage)
        self.story_text.append(f"You attack the {self.current_enemy.name} and deal {player_damage} damage!")
        self.highlight_last_text()
        self.update_status()  # Instant update without animation

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
                self.story_text.append("Victory! Press 'G' or click 'Next' to continue your journey.")
                self.highlight_last_text()
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
        self.story_text.append(f"You perform a heavy attack on the {self.current_enemy.name} dealing {player_damage} damage!")
        self.highlight_last_text()
        self.update_status()  # Instant update without animation

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
                self.story_text.append("Victory! Press 'G' or click 'Next' to continue your journey.")
                self.highlight_last_text()
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
            f"You have defeated the {self.current_enemy.name}!",
            f"The {self.current_enemy.name} has been vanquished!",
            f"Victory! The {self.current_enemy.name} is no more.",
            f"You emerge triumphant over the {self.current_enemy.name}!"
        ]
        self.story_text.append("\n" + random.choice(victory_messages))
        self.highlight_last_text()
        xp_gained = self.current_enemy.max_hp // 2
        self.player.gain_experience(xp_gained)
        self.story_text.append(f"You gained {xp_gained} experience points!")
        self.highlight_last_text()

    def toggle_pause(self):
        """Pauses or resumes the game."""
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        self.story_text.append(f"\nGame {status}.")
        self.highlight_last_text()

    def open_settings(self):
        """Opens the settings dialog to edit enemies (tasks)."""
        settings_dialog = SettingsDialog(self.task_manager, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            if settings_dialog.saved:
                self.task_manager = settings_dialog.task_manager
                self.task_manager.save_tasks()
                self.story_text.append("Settings updated successfully.")
                self.highlight_last_text()
                # Optionally, update tasks left count
                self.update_status()

    def closeEvent(self, event):
        """Handles the window close event. Stops hotkey listener thread."""
        self.hotkey_listener.stop()
        self.hotkey_listener.wait()
        event.accept()
