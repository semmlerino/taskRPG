from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from typing import List, Dict, Any, Callable

class ChoicesPanel(QWidget):
    """Displays choice buttons for the player."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.layout = QHBoxLayout()
        self.layout.setSpacing(20)
        self.layout.addStretch()  # Push buttons to the left
        self.setLayout(self.layout)
    
    def display_choices(self, choices: List[Dict[str, Any]], choice_callback: Callable):
        """Creates and displays choice buttons."""
        self.clear_choices()
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
            btn.setToolTip("Choose this option")
            # Connect button to callback with current choice
            btn.clicked.connect(lambda checked, c=choice: choice_callback(c))
            self.layout.addWidget(btn)
        self.layout.addStretch()  # Push buttons to the left
    
    def clear_choices(self):
        """Removes all choice buttons."""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
