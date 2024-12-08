from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, 
    QProgressBar, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import Optional
import logging

from modules.battle.battle_manager import Enemy

class EnemyPanel(QWidget):
    """Displays enemy statistics and task information."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_paused = False
        self._current_enemy = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        enemy_group = QGroupBox("Enemy Stats")
        enemy_layout = QVBoxLayout()
        
        self.enemy_label = QLabel("No Enemy")
        self.enemy_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.enemy_label.setAlignment(Qt.AlignCenter)
        
        self.task_label = QLabel("")  # Task Name
        self.task_label.setFont(QFont("Arial", 12, italic=True))
        self.task_label.setAlignment(Qt.AlignCenter)
        self.task_label.setStyleSheet("color: #616161;")  # Dark Grey
        
        self.hp_bar = QProgressBar()
        self.hp_bar.setMaximum(100)
        self.hp_bar.setValue(0)
        self.hp_bar.setFormat("%p%")
        self.hp_bar.setAlignment(Qt.AlignCenter)
        self.hp_bar.setTextVisible(True)
        self.hp_bar.setStyleSheet("""
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
        enemy_layout.addWidget(self.task_label)
        enemy_layout.addWidget(self.hp_bar)
        enemy_group.setLayout(enemy_layout)
        layout.addWidget(enemy_group)
        
        self.setLayout(layout)
    
    def update_panel(self, enemy: Optional[Enemy]):
        """Update panel with enemy information."""
        if enemy:
            logging.debug(f"Updating enemy panel - Name: {enemy.name}, HP: {enemy.current_hp}/{enemy.max_hp}")
            self.update_enemy(enemy)
            self.task_label.setText(enemy.task_name)
        else:
            logging.debug("No enemy provided to update_panel")
            self.enemy_label.setText("No Enemy")
            self.task_label.setText("")
            self.hp_bar.setMaximum(100)
            self.hp_bar.setValue(0)
            self.hp_bar.setFormat("%p%")

    def update_pause_state(self, is_paused: bool):
        """Update the display to show pause state."""
        try:
            self._is_paused = is_paused
            if is_paused:
                self.enemy_label.setText("PAUSED")
                self.hp_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #BDBDBD;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #f5f5f5;
                        height: 20px;
                        font-weight: bold;
                    }
                    QProgressBar::chunk {
                        background-color: #FF9800;
                        border-radius: 3px;
                    }
                """)
            else:
                # Restore original style and text
                if self._current_enemy:
                    self.enemy_label.setText(self._current_enemy.name)
                    self.hp_bar.setStyleSheet("""
                        QProgressBar {
                            border: 2px solid #BDBDBD;
                            border-radius: 5px;
                            text-align: center;
                            background-color: #f5f5f5;
                            height: 20px;
                            font-weight: bold;
                        }
                        QProgressBar::chunk {
                            background-color: #76FF03;
                            border-radius: 3px;
                        }
                    """)
            logging.debug(f"Enemy panel pause state updated: {is_paused}")
        except Exception as e:
            logging.error(f"Error updating enemy panel pause state: {e}")

    def update_enemy(self, enemy):
        """Update the enemy display."""
        try:
            self._current_enemy = enemy
            if not self._is_paused:
                self.enemy_label.setText(enemy.name)
            self.hp_bar.setMaximum(enemy.max_hp)
            self.hp_bar.setValue(enemy.current_hp)
            self.hp_bar.setFormat(f"{enemy.current_hp}/{enemy.max_hp}")
        except Exception as e:
            logging.error(f"Error updating enemy display: {e}")
