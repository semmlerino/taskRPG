from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, 
    QProgressBar, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import Optional
import logging

from modules.battle.enemy import Enemy

class EnemyPanel(QWidget):
    """Displays enemy statistics and task information."""
    def __init__(self, parent=None):
        super().__init__(parent)
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
            self.enemy_label.setText(enemy.name)
            self.task_label.setText(enemy.task_name)
            self.hp_bar.setMaximum(enemy.max_hp)
            self.hp_bar.setValue(enemy.current_hp)
            self.hp_bar.setFormat(f"{enemy.current_hp}/{enemy.max_hp}")
        else:
            logging.debug("No enemy provided to update_panel")
            self.enemy_label.setText("No Enemy")
            self.task_label.setText("")
            self.hp_bar.setMaximum(100)
            self.hp_bar.setValue(0)
            self.hp_bar.setFormat("%p%")
