from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTextBrowser, 
    QSizePolicy, QSplitter, QScrollArea
)
from PyQt5.QtGui import QFont, QPixmap, QTextCursor
from PyQt5.QtCore import Qt, QTimer
from os import path
from typing import Optional

class StoryDisplay(QWidget):
    """Displays story text and images."""
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
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #E0E0E0;
                border: 1px solid #BDBDBD;
                border-radius: 10px;
            }
        """)
        self.splitter.addWidget(self.image_label)
        
        # Story Text using QTextBrowser
        self.story_text = QTextBrowser()
        self.story_text.setOpenExternalLinks(True)
        self.story_text.setFont(QFont("Times New Roman", 18))
        self.story_text.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                color: #333333;
                border: 2px solid #BDBDBD;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.splitter.addWidget(self.story_text)
        
        # Set initial sizes
        self.splitter.setSizes([300, 400])
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)
    
    def append_text(self, html_content: str):
        """Appends text to the story display."""
        self.story_text.append(html_content)
        self.scroll_to_end()
    
    def scroll_to_end(self):
        """Scrolls to the end of the text display."""
        self.story_text.moveCursor(QTextCursor.End)
    
    def display_image(self, image_path: str):
        """Displays an image in the image label."""
        if image_path and path.exists(image_path):
            self.current_image_path = image_path
            self.resize_timer.start(100)
        else:
            self.image_label.clear()
            self.current_image_path = None

    def delayed_resize(self):
        """Handles delayed image resize."""
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
        """Handles resize events."""
        super().resizeEvent(event)
        self.resize_timer.start(100)

    def set_page(self, node_key: str, html_content: str, image_path: Optional[str]):
        """Updates display content."""
        self.clear()
        if image_path:
            self.display_image(image_path)
        self.append_text(html_content)
        
    def clear(self):
        """Clears all content."""
        self.story_text.clear()
        self.image_label.clear()
        
    def clear_history(self):
        """Clears display history."""
        self.clear()
