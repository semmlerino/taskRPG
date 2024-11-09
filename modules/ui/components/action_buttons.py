from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from typing import Callable

class ActionButtons(QWidget):
    """Manages action buttons like Next, Attack, and Heavy Attack."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Next Button
        self.next_button = QPushButton("Next (G)")
        self.next_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.next_button.setStyleSheet("""
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
        self.next_button.setFixedHeight(50)
        self.next_button.setToolTip("Proceed to the next story segment (Shortcut: G)")
        layout.addWidget(self.next_button)
        
        # Attack Button
        self.attack_button = QPushButton("Attack (D)")
        self.attack_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.attack_button.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
        """)
        self.attack_button.setFixedHeight(50)
        self.attack_button.setToolTip("Perform a regular attack (Shortcut: D)")
        self.attack_button.hide()  # Initially hidden
        layout.addWidget(self.attack_button)
        
        # Heavy Attack Button
        self.heavy_attack_button = QPushButton("Heavy Attack (Shift+D)")
        self.heavy_attack_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.heavy_attack_button.setStyleSheet("""
            QPushButton {
                background-color: #EF5350;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E53935;
            }
        """)
        self.heavy_attack_button.setFixedHeight(50)
        self.heavy_attack_button.setToolTip("Perform a heavy attack (Shortcut: Shift+D)")
        self.heavy_attack_button.hide()  # Initially hidden
        layout.addWidget(self.heavy_attack_button)
        
        self.setLayout(layout)
    
    def connect_buttons(self, next_func: Callable, attack_func: Callable, heavy_attack_func: Callable):
        """Connects button signals to their respective slots."""
        self.next_button.clicked.connect(next_func)
        self.attack_button.clicked.connect(attack_func)
        self.heavy_attack_button.clicked.connect(heavy_attack_func)
    
    def show_attack_buttons(self):
        """Shows Attack and Heavy Attack buttons and hides Next button."""
        self.next_button.hide()
        self.attack_button.show()
        self.heavy_attack_button.show()
    
    def hide_attack_buttons(self):
        """Hides Attack and Heavy Attack buttons and shows Next button."""
        self.attack_button.hide()
        self.heavy_attack_button.hide()
        self.next_button.show()
    
    def debug_button_state(self):
        """Print the visibility state of all buttons"""
        print(f"Next button visible: {self.next_button.isVisible()}")
        print(f"Attack button visible: {self.attack_button.isVisible()}")
        print(f"Heavy attack button visible: {self.heavy_attack_button.isVisible()}")