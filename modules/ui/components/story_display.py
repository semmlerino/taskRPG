from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextBrowser, 
                            QScrollArea, QShortcut, QMessageBox, QSizePolicy,
                            QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QKeySequence, QKeyEvent
import logging
import os

from modules.ui.components.fullscreen_image_viewer import FullscreenImageViewer
from modules.ui.components.story_text_browser import StoryTextBrowser

class StoryDisplay(QWidget):
    """Widget for displaying story content with text and images."""
    
    story_advance_signal = pyqtSignal()
    navigate_back_signal = pyqtSignal()
    navigate_forward_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_node_key = None
        self.current_image_path = None
        self._fullscreen_viewer = None
        
        # Enable keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Create fullscreen shortcut
        self.fullscreen_shortcut = QShortcut(QKeySequence('F'), self)
        self.fullscreen_shortcut.activated.connect(self._show_fullscreen_viewer)
        
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter
        self.splitter = QSplitter(Qt.Vertical)
        
        # Image display
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.image_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        
        # Story text display
        self.story_text = StoryTextBrowser()
        
        # Add widgets to splitter
        self.splitter.addWidget(self.image_scroll)
        self.splitter.addWidget(self.story_text)
        
        # Set initial sizes
        self.splitter.setSizes([300, 400])
        
        # Connect splitter's splitterMoved signal
        self.splitter.splitterMoved.connect(self.load_image)
        
        # Add splitter to layout
        layout.addWidget(self.splitter)
        
        self.setLayout(layout)

    def set_page(self, node_key: str, html_content: str, image_path: str = None):
        """Set the content for the current story page."""
        try:
            self.current_node_key = node_key
            self.clear()
            
            if image_path and os.path.exists(image_path):
                self.current_image_path = image_path
                self.load_image()
            else:
                self.current_image_path = None
                
            self.story_text.append(html_content)
            
            if self._fullscreen_viewer:
                self._fullscreen_viewer.update_content(
                    self.current_image_path,
                    self.story_text.toPlainText()
                )
                
        except Exception as e:
            logging.error(f"Error setting page: {e}")
            QMessageBox.critical(self, "Error", "Failed to set page content")

    def clear(self):
        """Clear all content from the display."""
        self.story_text.clear()
        self.image_label.clear()
        self.current_image_path = None

    def load_image(self):
        """Load and display the current image."""
        try:
            if not self.current_image_path:
                return
                
            pixmap = QPixmap(self.current_image_path)
            if pixmap.isNull():
                logging.error(f"Failed to load image: {self.current_image_path}")
                return
            
            # Get the current size of the image scroll area
            scroll_size = self.image_scroll.size()
            
            # Scale image to fit the scroll area while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                scroll_size.width(),
                scroll_size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logging.error(f"Error loading image: {e}")
            self.show_error("Failed to load image")

    def resizeEvent(self, event):
        """Handle widget resize events."""
        super().resizeEvent(event)
        if hasattr(self, 'current_image_path') and self.current_image_path:
            self.load_image()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation and fullscreen toggle."""
        try:
            if event.key() == Qt.Key_F:
                if hasattr(self, 'current_image_path') and self.current_image_path:
                    self._show_fullscreen_viewer()
            elif event.key() == Qt.Key_Left:
                self.navigate_back_signal.emit()
            elif event.key() == Qt.Key_Right:
                self.navigate_forward_signal.emit()
            elif event.key() == Qt.Key_G:
                self.story_advance_signal.emit()
            else:
                super().keyPressEvent(event)
        except Exception as e:
            logging.error(f"Error handling key press: {e}")
            QMessageBox.critical(self, "Error", "Failed to handle key press")

    def _show_fullscreen_viewer(self):
        """Show the fullscreen image viewer."""
        try:
            if not os.path.exists(self.current_image_path):
                logging.error(f"Image file not found: {self.current_image_path}")
                return

            self.cleanup_viewer()
            
            self._fullscreen_viewer = FullscreenImageViewer(
                self.current_image_path,
                self.story_text.toPlainText()
            )
            
            self._fullscreen_viewer.story_advance_signal.connect(
                self.story_advance_signal.emit
            )
            
            self._fullscreen_viewer.showFullScreen()
            logging.info("Fullscreen viewer displayed")
            
        except Exception as e:
            logging.error(f"Error showing fullscreen viewer: {e}")
            QMessageBox.critical(self, "Error", "Failed to show fullscreen view")

    def cleanup_viewer(self):
        """Clean up any existing fullscreen viewer."""
        if self._fullscreen_viewer:
            try:
                self._fullscreen_viewer.close()
                self._fullscreen_viewer.deleteLater()
            except Exception as e:
                logging.error(f"Error cleaning up viewer: {e}")
            finally:
                self._fullscreen_viewer = None

    def show_error(self, message: str):
        """Display an error message."""
        logging.error(message)
        QMessageBox.critical(self, "Error", message)