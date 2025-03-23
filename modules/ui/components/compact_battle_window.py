# modules/ui/components/compact_battle_window.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from modules.battle.battle_manager import Enemy

class CompactBattleWindow(QWidget):
    """A compact overlay window displaying battle stats when main window loses focus."""
    
    # Add signal definitions
    attack_clicked = pyqtSignal()
    heavy_attack_clicked = pyqtSignal()
    pause_toggled = pyqtSignal()  # For pause toggle
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(250, 100)
        
        # Initialize pause state
        self._is_paused = False
        self._current_enemy = None
        
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
        
        # Tooltip with hotkeys - keep this to show available shortcuts
        self.setToolTip("D: Normal Attack\nShift+D: Heavy Attack\n#: Pause/Resume")
        
    def update_display(self, enemy: Optional['Enemy']) -> None:
        """Update the display with enemy information."""
        try:
            if enemy and hasattr(enemy, 'name') and hasattr(enemy, 'task_name'):
                self._current_enemy = enemy
                
                # Update text based on pause state
                if not self._is_paused:
                    self.enemy_label.setText(enemy.task_name)
                
                self.hp_bar.setMaximum(enemy.max_hp)
                self.hp_bar.setValue(enemy.current_hp)
                self.hp_bar.setFormat(f"{enemy.current_hp}/{enemy.max_hp}")
                self.tasks_label.setText(f"Tasks remaining: {enemy.current_hp}")
                self.show()
                logging.debug(f"Compact window display updated - Enemy: {enemy.name}, HP: {enemy.current_hp}, Paused: {self._is_paused}")
            else:
                logging.warning("Invalid enemy object provided to compact window")
                self.hide()
        except Exception as e:
            logging.error(f"Error updating compact window display: {e}")

    def update_tasks(self, tasks_left: int):
        """Update the tasks remaining display."""
        self.tasks_label.setText(f"Tasks remaining: {tasks_left}")
        self.hp_bar.setValue(tasks_left)
        
    def update_pause_state(self, is_paused: bool):
        """Update the display to show pause state."""
        try:
            # Only update if state actually changes
            if self._is_paused != is_paused:
                self._is_paused = is_paused
                
                # Update text based on pause state
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
                    # Only restore text if we have an enemy
                    if self._current_enemy:
                        self.enemy_label.setText(self._current_enemy.task_name)
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
            
                logging.debug(f"Compact window pause state updated - Paused: {is_paused}, Has Enemy: {self._current_enemy is not None}")
        
        except Exception as e:
            logging.error(f"Error updating compact window pause state: {e}")
        
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
            
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for attacks."""
        try:
            if event.key() == Qt.Key_D:
                if event.modifiers() & Qt.ShiftModifier:
                    # Shift+D for heavy attack
                    self.heavy_attack_clicked.emit()
                    logging.debug("Heavy attack shortcut triggered from compact window")
                else:
                    # D for normal attack
                    self.attack_clicked.emit()
                    logging.debug("Attack shortcut triggered from compact window")
            elif event.key() == Qt.Key_NumberSign:  # # key
                # Emit signal for pause toggle
                self.pause_toggled.emit()
                logging.debug("Pause toggle signal emitted from compact window")
        except Exception as e:
            logging.error(f"Error handling key press in compact window: {e}")