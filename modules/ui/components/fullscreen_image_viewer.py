import sys
import os
import logging
import traceback
from functools import lru_cache

from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QTextBrowser, QApplication, QMessageBox, QWidget, QShortcut, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QKeyEvent, QPen, QPainterPath, QKeySequence, QTextOption, QFont
from PyQt5.QtCore import Qt, QSize, QRect

# Setup logging
def setup_logging():
    """
    Configures logging to output to both console and a log file with timestamps and log levels.
    """
    log_directory = os.path.join(os.path.expanduser("~"), "FullscreenImageViewerLogs")
    os.makedirs(log_directory, exist_ok=True)
    log_file = os.path.join(log_directory, "app.log")

    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for detailed logs
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

setup_logging()


class OutlinedTextBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stroke_color = QColor(0, 0, 0)  # Black outline
        self.stroke_width = 3  # Increased width of the outline
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
    def __init__(self, image_path, story_text, parent=None):
        super().__init__(parent)
        logging.info("Initializing FullscreenImageViewer")

        # Set black background
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
        QShortcut(QKeySequence('F'), self, self.close)
        QShortcut(QKeySequence('Escape'), self, self.close)
        QShortcut(QKeySequence('T'), self, self.toggle_text)

    def position_elements(self):
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
        super().resizeEvent(event)
        self.position_elements()

    def scale_image(self):
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
        self.text_browser.setVisible(not self.text_browser.isVisible())

    def close(self):
        """
        Closes the application window.
        """
        logging.info("Close shortcut activated. Closing application.")
        super().close()

    def show_error_message(self, message):
        """
        Displays a critical error message to the user and closes the application.

        :param message: The error message to display.
        """
        QMessageBox.critical(self, "Error", message)
        self.close()

    @lru_cache(maxsize=10)
    def get_scaled_pixmap(self, size_tuple):
        """
        Caches and returns a scaled version of the original pixmap that fits the screen height.

        :param size_tuple: A tuple (width, height) representing the target size.
        :return: Scaled QPixmap.
        """
        width, height = size_tuple
        target_size = QSize(width, height)
        return self.original_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,  # Changed to KeepAspectRatio
            Qt.SmoothTransformation
        )

    def on_resize(self, event):
        """
        Handles window resize events to scale the image.

        :param event: The resize event.
        """
        logging.debug(f"Window resized to: {self.size().width()}x{self.size().height()}")
        self.scale_image()
        event.accept()
        logging.debug("Window resize event handled.")

    def keyPressEvent(self, event: QKeyEvent):
        """
        Overrides the key press event to handle additional keys.

        Note: This is optional since we're using QShortcut for key handling.

        :param event: The key event.
        """
        logging.debug(f"Key pressed: {event.key()}")
        super().keyPressEvent(event)

    def __del__(self):
        """
        Cleanup resources when the object is destroyed.
        """
        logging.info("Cleaning up FullscreenImageViewer resources")
        self.get_scaled_pixmap.cache_clear()
        # Clear any other cached resources
        self.original_pixmap = None
        self.scaled_pixmap = None

    def showEvent(self, event):
        """
        Handle window show event to ensure proper focus.
        """
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()
        self.raise_()

    def format_story_text(self, text: str) -> str:
        """Format the story text into multiple lines with proper wrapping."""
        # Split into words and rebuild with line breaks
        words = text.split()
        lines = []
        current_line = []
        chars_per_line = 80  # Adjust this value based on your needs
        
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


# Example usage
if __name__ == "__main__":
    # Optionally, disable or enable High-DPI scaling
    # To disable:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

    # To enable, comment out the above two lines and uncomment the following:
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Replace "path_to_image.jpg" with the actual path to your image
    image_path = "path_to_image.jpg"
    story_text = "Your story text goes here."

    # Verify if the image exists
    if not os.path.exists(image_path):
        logging.error(f"Image file does not exist: {image_path}")
        QMessageBox.critical(None, "Error", f"Image file does not exist: {image_path}")
        sys.exit(1)

    viewer = FullscreenImageViewer(image_path, story_text)
    # Removed the redundant show() call
    # viewer.show()

    logging.info("FullscreenImageViewer launched")
    sys.exit(app.exec_())
