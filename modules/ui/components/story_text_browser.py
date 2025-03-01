from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QPalette, QColor

class StoryTextBrowser(QTextBrowser):
    """Custom text browser with enhanced features for story display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        # Enable rich text
        self.setAcceptRichText(True)
        
        # Font size will be managed by FontScalingManager
        
        # Enable external links but handle them internally
        self.setOpenExternalLinks(False)
        
        # Custom palette for better readability
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.Text, QColor("#333333"))
        self.setPalette(palette)
        
        # Apply stylesheet directly
        self.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 8px;
                selection-background-color: #2196F3;
                selection-color: #FFFFFF;
            }
            QTextBrowser:focus {
                border: 1px solid #2196F3;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #BBBBBB;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def append_text(self, text: str):
        """Append text and scroll to the end."""
        self.append(text)
        self.moveCursor(QTextCursor.End)
        self.ensureCursorVisible()

    def clear_content(self):
        """Clear all content."""
        self.clear()
        self.clearHistory()

    def wheelEvent(self, event):
        """Handle mouse wheel scrolling with modifier keys."""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn(1)
            else:
                self.zoomOut(1)
        else:
            super().wheelEvent(event)
