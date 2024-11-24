from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from modules.battle.battle_manager import Enemy

class CompactBattleWindow(QWidget):
    """A compact overlay window displaying battle stats when main window loses focus."""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(250, 120)
        self.init_ui()
        
        # Enable window dragging
        self.dragging = False
        self.offset = None
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        # Enemy name and task
        self.enemy_label = QLabel()
        self.enemy_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.enemy_label.setStyleSheet("""
            QLabel {
                color: #2f4f4f;
                padding: 2px;
                qproperty-alignment: AlignCenter;
            }
        """)
        layout.addWidget(self.enemy_label)
        
        # HP Bar with improved styling
        self.hp_bar = QProgressBar()
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
        layout.addWidget(self.hp_bar)
        
        # Tasks remaining
        self.tasks_label = QLabel()
        self.tasks_label.setFont(QFont("Arial", 11))
        self.tasks_label.setStyleSheet("""
            QLabel {
                color: #2f4f4f;
                padding: 2px;
            }
        """)
        layout.addWidget(self.tasks_label)
        
        self.setLayout(layout)
        
        # Window styling
        self.setStyleSheet("""
            CompactBattleWindow {
                background-color: white;
                border: 1px solid #BDBDBD;
                border-radius: 8px;
            }
        """)
        
        # Tooltip with hotkeys
        self.setToolTip("D: Normal Attack\nShift+D: Heavy Attack\n#: Pause/Resume")
        
    def update_display(self, enemy: Optional['Enemy']) -> None:
        """Update the display with enemy information."""
        try:
            if enemy and hasattr(enemy, 'name') and hasattr(enemy, 'task_name'):
                self.enemy_label.setText(enemy.task_name)
                self.hp_bar.setMaximum(enemy.max_hp)
                self.hp_bar.setValue(enemy.current_hp)
                self.hp_bar.setFormat(f"{enemy.current_hp}/{enemy.max_hp}")
                self.tasks_label.setText(f"Tasks remaining: {enemy.current_hp}")
                self.show()
                logging.debug(f"Compact window visibility - Enemy: {enemy.name if enemy else 'None'}, HP: {enemy.current_hp if enemy else 'None'}")
            else:
                logging.warning("Invalid enemy object provided to compact window")
                self.hide()
        except Exception as e:
            logging.error(f"Error updating compact window display: {e}")
            self.hide()
            
    def update_tasks(self, tasks_left: int):
        """Update the tasks remaining display."""
        self.tasks_label.setText(f"Tasks remaining: {tasks_left}")
        self.hp_bar.setValue(tasks_left)
        
    def update_pause_state(self, is_paused: bool):
        """Update the display to show pause state."""
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
            # Restore original style
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
        
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            
    def mouseMoveEvent(self, event):
        """Handle window dragging."""
        if self.dragging and self.offset:
            new_pos = event.globalPos() - self.offset
            self.move(new_pos)
            
    def mouseReleaseEvent(self, event):
        """Handle end of dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.offset = None
