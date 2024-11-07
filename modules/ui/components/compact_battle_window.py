# modules/ui/components/compact_battle_window.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from modules.utils.qt_helpers import ensure_qt_application

class CompactBattleWindow(QWidget):
    """Compact window for displaying battle stats when main window loses focus."""
    def __init__(self, parent=None):
        ensure_qt_application()
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(200, 100)
        self.init_ui()
        
        # Enable mouse dragging
        self.dragging = False
        self.offset = None
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Enemy name and task
        self.enemy_label = QLabel()
        self.enemy_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.enemy_label.setStyleSheet("""
            QLabel {
                color: #2f4f4f;
            }
        """)
        layout.addWidget(self.enemy_label)
        
        # HP Bar
        self.hp_bar = QProgressBar()
        self.hp_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background-color: #76FF03;
            }
        """)
        layout.addWidget(self.hp_bar)
        
        # Tasks left
        self.tasks_label = QLabel()
        self.tasks_label.setFont(QFont("Arial", 11))
        self.tasks_label.setStyleSheet("""
            QLabel {
                color: #2f4f4f;
            }
        """)
        layout.addWidget(self.tasks_label)
        
        self.setLayout(layout)
        
        # Set window style to match main app
        self.setStyleSheet("""
            CompactBattleWindow {
                background-color: white;
                border: 1px solid #BDBDBD;
                border-radius: 5px;
            }
        """)
        
        # Add tooltip with hotkey information
        self.setToolTip("D: Normal Attack\nShift+D: Heavy Attack")
        
    def update_display(self, enemy):
        """Updates the compact display with current battle information."""
        if enemy:
            self.enemy_label.setText(f"{enemy.name} - {enemy.task_name}")
            self.hp_bar.setMaximum(enemy.max_hp)
            self.hp_bar.setValue(enemy.current_hp)
            self.tasks_label.setText(f"Tasks remaining: {enemy.current_hp}")
            
            # Update HP bar color based on remaining HP
            hp_percentage = (enemy.current_hp / enemy.max_hp) * 100
            if hp_percentage > 60:
                color = "#76FF03"  # Green
            elif hp_percentage > 30:
                color = "#FF9800"  # Orange
            else:
                color = "#F44336"  # Red
            
            self.hp_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #f5f5f5;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                }}
            """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.offset:
            new_pos = event.globalPos() - self.offset
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.offset = None
