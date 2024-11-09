import sys
import os
import logging
import traceback
from functools import lru_cache

from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QTextBrowser, QApplication, QMessageBox, 
    QWidget, QShortcut, QSizePolicy
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QKeyEvent, QPen, QPainterPath, 
    QKeySequence, QTextOption, QFont
)
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal

class OutlinedTextBrowser(QTextBrowser):
    """Text browser with outlined text for better visibility on any background."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stroke_color = QColor(0, 0, 0)  # Black outline
        self.stroke_width = 3  # Width of the outline
        self.setViewportMargins(0, 0, 0, 0)
        self.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
                color: white;
                font-size: 18pt;
            }
        """)

    def paintEvent(self, event):
        """Custom paint event for outlined text."""
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        # Get the current text
        text = self.toPlainText()
        
        # Set up the text options
        painter.setFont(self.font())
        
        # Draw the outline (stroke) with multiple passes for better visibility
        painter.setPen(self.stroke_color)
        offsets = [
            (-3, -3), (-3, 0), (-3, 3),  # Left side
            (0, -3), (0, 3),             # Middle
            (3, -3), (3, 0), (3, 3),     # Right side
            (-2, -2), (-2, 2), (2, -2), (2, 2),  # Diagonal corners
            (-1, -1), (-1, 1), (1, -1), (1, 1)   # Inner diagonal corners
        ]
        for dx, dy in offsets:
            painter.drawText(
                self.viewport().rect().adjusted(dx, dy, dx, dy),
                Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                text
            )
        
        # Draw the main text in white
        painter.setPen(QColor(255, 255, 255))  # White text
        painter.drawText(
            self.viewport().rect(),
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            text
        )

class FullscreenImageViewer(QMainWindow):
    """Fullscreen image viewer with story progression capability."""
    
    story_advance_signal = pyqtSignal()
    
    def __init__(self, image_path, story_text, parent=None):
        super().__init__(parent)
        logging.info("Initializing FullscreenImageViewer")
        
        # Set window properties
        self.setStyleSheet("background-color: black;")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create image label
        self.image_label = QLabel(central_widget)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        
        # Create text browser
        self.text_browser = OutlinedTextBrowser(central_widget)
        self.text_browser.setText(story_text)
        self.text_browser.setReadOnly(True)
        self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Load and display image
        self.original_pixmap = QPixmap(image_path)
        self.scale_image()
        
        # Position elements
        self.position_elements()

        # Setup shortcuts
        self.setup_shortcuts()
        
        # Initialize state
        self.text_visible = True

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence('F'), self, self.close)
        QShortcut(QKeySequence('Escape'), self, self.close)
        QShortcut(QKeySequence('T'), self, self.toggle_text)
        QShortcut(QKeySequence('G'), self, self.advance_story)

    def position_elements(self):
        """Position the image and text elements."""
        screen_rect = self.geometry()
        
        # Position the image to fill the screen
        self.image_label.setGeometry(0, 0, screen_rect.width(), screen_rect.height())
        
        # Position text at the bottom with wider margins
        text_height = int(screen_rect.height() * 0.3)  # 30% of screen height
        side_margin = 120  # Wide side margins
        bottom_margin = 5  # Reduced from 10 to 5 pixels from bottom
        self.text_browser.setGeometry(
            side_margin,  # Left margin
            screen_rect.height() - text_height - bottom_margin,  # Closer to bottom
            screen_rect.width() - (side_margin * 2),  # Width (with margins on both sides)
            text_height  # Height
        )

    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        self.position_elements()
        self.scale_image()

    def scale_image(self):
        """Scale the image to fit the window while maintaining aspect ratio."""
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            screen = QApplication.primaryScreen()
            size = screen.size()
            
            # Scale to fit height
            scale_factor = size.height() / self.original_pixmap.height()
            new_width = int(self.original_pixmap.width() * scale_factor)
            scaled = self.original_pixmap.scaled(
                new_width, 
                size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

    def toggle_text(self):
        """Toggle text visibility."""
        self.text_visible = not self.text_visible
        self.text_browser.setVisible(self.text_visible)

    def advance_story(self):
        """Handle story progression request."""
        try:
            logging.debug("Story advance requested from fullscreen viewer")
            self.story_advance_signal.emit()
            self.close()
        except Exception as e:
            logging.error(f"Error advancing story from fullscreen view: {e}")

    def keyPressEvent(self, event):
        """Handle key press events."""
        try:
            if event.key() == Qt.Key_G:
                self.advance_story()
            elif event.key() == Qt.Key_T:
                self.toggle_text()
            elif event.key() in (Qt.Key_Escape, Qt.Key_F):
                self.close()
            else:
                super().keyPressEvent(event)
        except Exception as e:
            logging.error(f"Error handling key press in fullscreen viewer: {e}")

    def showEvent(self, event):
        """Handle window show event to ensure proper focus."""
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            self.cleanup_resources()
            super().closeEvent(event)
            logging.info("FullscreenImageViewer closed successfully")
        except Exception as e:
            logging.error(f"Error during FullscreenImageViewer cleanup: {e}")
            event.accept()

    def cleanup_resources(self):
        """Clean up resources before closing."""
        try:
            self.original_pixmap = None
            self.get_scaled_pixmap.cache_clear()
        except Exception as e:
            logging.error(f"Error cleaning up resources: {e}")

    @lru_cache(maxsize=10)
    def get_scaled_pixmap(self, size_tuple):
        """Cache and return scaled versions of the pixmap."""
        width, height = size_tuple
        target_size = QSize(width, height)
        return self.original_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    def update_content(self, image_path: str, story_text: str):
        """Update the viewer's content."""
        try:
            if os.path.exists(image_path):
                self.original_pixmap = QPixmap(image_path)
                self.scale_image()
            self.text_browser.setText(story_text)
            logging.debug("Fullscreen viewer content updated")
        except Exception as e:
            logging.error(f"Error updating fullscreen viewer content: {e}")

    def format_story_text(self, text: str) -> str:
        """Format the story text into multiple lines with proper wrapping."""
        words = text.split()
        lines = []
        current_line = []
        chars_per_line = 80
        
        current_length = 0
        for word in words:
            word_length = len(word)
            if current_length + word_length + 1 <= chars_per_line:
                current_line.append(word)
                current_length += word_length + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return '\n'.join(lines)