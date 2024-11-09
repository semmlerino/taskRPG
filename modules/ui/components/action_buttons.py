from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon

class ActionButtons(QWidget):
    attack_clicked = pyqtSignal()
    heavy_attack_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        self.next_button = QPushButton("Next (G)")
        self.next_button.setFont(QFont("Arial", 14))
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.attack_button = QPushButton("Attack (D)")
        self.attack_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.heavy_attack_button = QPushButton("Heavy Attack (Shift+D)")
        self.heavy_attack_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #F4511E;
            }
        """)
        
        self.attack_button.clicked.connect(self.attack_clicked.emit)
        self.heavy_attack_button.clicked.connect(self.heavy_attack_clicked.emit)
        
        layout.addWidget(self.next_button)
        layout.addWidget(self.attack_button)
        layout.addWidget(self.heavy_attack_button)
        
        self.setLayout(layout)
        self.hide_attack_buttons()
    
    def show_attack_buttons(self):
        """Show attack buttons during battle."""
        self.attack_button.show()
        self.heavy_attack_button.show()
    
    def hide_attack_buttons(self):
        """Hide attack buttons when not in battle."""
        self.attack_button.hide()
        self.heavy_attack_button.hide()
    
    def update_navigation_buttons(self, can_go_back: bool, can_go_forward: bool):
        """Update the enabled state of navigation buttons."""
        self.back_button.setEnabled(can_go_back)
        self.forward_button.setEnabled(can_go_forward)