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
    """Widget for displaying story content with text and images.
    
    This widget provides a split view with an image display area on top
    and a text display area below. It supports fullscreen image viewing,
    keyboard navigation, and dynamic resizing.
    """
    
    # Signals for story navigation
    story_advance_signal = pyqtSignal()
    navigate_back_signal = pyqtSignal()
    navigate_forward_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the story display widget."""
        super().__init__(parent)
        self.current_node_key = None
        self.current_image_path = None
        self._fullscreen_viewer = None
        
        # Enable keyboard focus for hotkey support
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Setup fullscreen shortcut (F key)
        self.fullscreen_shortcut = QShortcut(QKeySequence('F'), self)
        self.fullscreen_shortcut.activated.connect(self._show_fullscreen_viewer)
        
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create vertical splitter for image/text areas
        self.splitter = QSplitter(Qt.Vertical)
        
        # Setup image display area
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.image_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        
        # Setup text display area
        self.story_text = StoryTextBrowser()
        
        # Add both components to splitter
        self.splitter.addWidget(self.image_scroll)
        self.splitter.addWidget(self.story_text)
        
        # Set default split positions
        self.splitter.setSizes([300, 400])
        
        # Connect splitter movement to image resize
        self.splitter.splitterMoved.connect(self.load_image)
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)

    def set_page(self, node_key: str, html_content: str, image_path: str = None):
        """Set the content for the current story page.
        
        Args:
            node_key: Identifier for the current story node
            html_content: HTML formatted text content
            image_path: Path to the image file (optional)
        """
        try:
            self.current_node_key = node_key
            self.clear()
            
            if image_path and os.path.exists(image_path):
                self.current_image_path = image_path
                self.load_image()
            else:
                self.current_image_path = None
                
            self.story_text.append(html_content)
            
            # Update fullscreen viewer if active
            if self._fullscreen_viewer:
                self._fullscreen_viewer.update_content(
                    self.current_image_path,
                    self.story_text.toPlainText()
                )
                
        except Exception as e:
            logging.error(f"Error setting page: {e}")
            self.show_error("Failed to set page content")

    def clear(self):
        """Clear all content from the display."""
        self.story_text.clear()
        self.image_label.clear()
        self.current_image_path = None

    def load_image(self):
        """Load and scale the current image to fit the display area."""
        try:
            if not self.current_image_path:
                return
                
            pixmap = QPixmap(self.current_image_path)
            if pixmap.isNull():
                logging.error(f"Failed to load image: {self.current_image_path}")
                return
            
            # Get current scroll area size
            scroll_size = self.image_scroll.size()
            
            # Scale image to fit while maintaining aspect ratio
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
        """Handle keyboard navigation and shortcuts.
        
        Supported keys:
            F: Toggle fullscreen image view
            Left: Navigate back
            Right: Navigate forward
            G: Advance story
        """
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
            self.show_error("Failed to handle key press")

    def _show_fullscreen_viewer(self):
        """Create and display the fullscreen image viewer."""
        try:
            if not os.path.exists(self.current_image_path):
                logging.error(f"Image file not found: {self.current_image_path}")
                self.show_error("Image file not found")
                return

            self.cleanup_viewer()
            
            # Create new fullscreen viewer
            self._fullscreen_viewer = FullscreenImageViewer(
                self.current_image_path,
                self.story_text.toPlainText()
            )
            
            # Connect story advance signal
            self._fullscreen_viewer.story_advance_signal.connect(
                self.story_advance_signal.emit
            )
            
            self._fullscreen_viewer.showFullScreen()
            logging.info("Fullscreen viewer displayed")
            
        except Exception as e:
            logging.error(f"Error showing fullscreen viewer: {e}")
            self.show_error("Failed to show fullscreen view")

    def cleanup_viewer(self):
        """Clean up any existing fullscreen viewer instance."""
        if self._fullscreen_viewer:
            try:
                self._fullscreen_viewer.close()
                self._fullscreen_viewer.deleteLater()
            except Exception as e:
                logging.error(f"Error cleaning up viewer: {e}")
            finally:
                self._fullscreen_viewer = None

    def show_error(self, message: str):
        """Display an error message dialog.
        
        Args:
            message: The error message to display
        """
        logging.error(message)
        QMessageBox.critical(self, "Error", message)

    def append_text(self, text: str) -> None:
        """Append text to the story display."""
        current_text = self.story_text.toPlainText()
        if current_text:
            # Add a newline if there's existing text
            self.story_text.setPlainText(f"{current_text}\n{text}")
        else:
            # Just set the text if the display is empty
            self.story_text.setPlainText(text)
        
        # Scroll to the bottom to show new text
        scrollbar = self.story_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())