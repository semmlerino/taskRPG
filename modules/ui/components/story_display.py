# modules/ui/components/story_display.py

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextBrowser, QSizePolicy, QSplitter, QScrollArea
from PyQt5.QtGui import QFont, QPixmap, QTextCursor  # Added QTextCursor import
from PyQt5.QtCore import Qt, QTimer
from os import path  # Added import for os module

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
        
        # Story Text using QTextBrowser
        self.story_text = QTextBrowser()
        self.story_text.setOpenExternalLinks(True)  # Enable hyperlink clicking
        self.story_text.setFont(QFont("Georgia", 18))  # Increased font size for better readability
        self.story_text.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                color: #333333;
                border: 2px solid #BDBDBD;
                border-radius: 5px;
                padding: 10px;  /* Added padding for better aesthetics */
            }
        """)
        self.splitter.addWidget(self.story_text)
        
        # Set initial sizes (adjust as needed)
        self.splitter.setSizes([300, 400])
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)
    
    def append_text(self, html_content: str):
        self.story_text.append(html_content)
        self.scroll_to_end()
    
    def scroll_to_end(self):
        self.story_text.moveCursor(QTextCursor.End)
    
    def display_image(self, image_path: str):
        if image_path and path.exists(image_path):  # Updated to use path.exists
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
