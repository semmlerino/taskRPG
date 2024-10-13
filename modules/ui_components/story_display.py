from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit, QSizePolicy, QSplitter
from PyQt5.QtGui import QFont, QPixmap, QTextCursor
from PyQt5.QtCore import Qt, QTimer
import os

class StoryDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.delayed_resize)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create a splitter
        self.splitter = QSplitter(Qt.Vertical)
        
        # Image Display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("background-color: #E0E0E0; border: 1px solid #BDBDBD; border-radius: 10px;")
        self.splitter.addWidget(self.image_label)
        
        # Story Text
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
        self.splitter.addWidget(self.story_text)
        
        # Set initial sizes (adjust as needed)
        self.splitter.setSizes([300, 300])
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)
    
    def append_text(self, html_content: str):
        self.story_text.moveCursor(QTextCursor.End)
        self.story_text.insertHtml(html_content)
        self.story_text.insertHtml("<br>")
        self.scroll_to_end()
    
    def scroll_to_end(self):
        cursor = self.story_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.story_text.setTextCursor(cursor)
    
    def display_image(self, image_path: str):
        if image_path and os.path.exists(image_path):
            self.current_image_path = image_path
            self.resize_timer.start(100)  # Delay resize by 100ms
        else:
            self.image_label.clear()
            self.current_image_path = None

    def delayed_resize(self):
        if hasattr(self, 'current_image_path') and self.current_image_path:
            pixmap = QPixmap(self.current_image_path)
            scaled_pixmap = pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(100)  # Delay resize by 100ms