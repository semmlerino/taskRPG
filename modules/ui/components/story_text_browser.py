from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QPalette, QColor
from modules.ui.styles.style_manager import StyleManager

class StoryTextBrowser(QTextBrowser):
    """Custom text browser with enhanced features for story display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        # Enable rich text
        self.setAcceptRichText(True)
        
        # Set default font size
        self.setFontPointSize(UI_FONTS['DEFAULT_SIZE'])
        
        # Enable external links but handle them internally
        self.setOpenExternalLinks(False)
        
        # Custom palette for better readability
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.Text, QColor("#333333"))
        self.setPalette(palette)
        
        # Custom stylesheet
        self.setStyleSheet(StyleManager.get_text_browser_style())

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
