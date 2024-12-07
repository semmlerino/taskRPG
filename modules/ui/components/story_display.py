# Standard library imports
import logging
import os

# PyQt5 imports
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QKeySequence, QKeyEvent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextBrowser,
    QScrollArea,
    QShortcut,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QPushButton
)

# Local imports
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
        self.current_image_prompt = None
        self._fullscreen_viewer = None
        
        # Enable keyboard focus for hotkey support
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Setup fullscreen shortcut (F key)
        self.fullscreen_shortcut = QShortcut(QKeySequence('F'), self)
        self.fullscreen_shortcut.activated.connect(self._show_fullscreen_viewer)
        
        self.init_ui()
        
        # Schedule focus check after initialization
        QTimer.singleShot(100, self._ensure_focus)

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

    def set_page(self, content: 'StoryContent'):
        """Set the page content."""
        try:
            self.current_node_key = content.node_key
            self.story_text.clear()
            
            # Store image prompt
            logging.info(f"Setting image prompt: {content.image_prompt}")
            self.current_image_prompt = content.image_prompt
            
            # Only update image if we have a new one
            if content.image_path:
                self.current_image_path = content.image_path
                self.load_image()
            # Don't clear the image if no new image is provided
            
            self.story_text.append(content.to_html())
            
            # Update fullscreen viewer if active
            if self._fullscreen_viewer:
                logging.info(f"Updating fullscreen viewer with prompt: {self.current_image_prompt}")
                self._fullscreen_viewer.update_content(
                    self.current_image_path,
                    self.story_text.toPlainText(),
                    self.current_image_prompt
                )
                
            self.setFocus()
            
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
        """Handle keyboard navigation and shortcuts."""
        logging.info(f"StoryDisplay received key press: {event.key()}")
        try:
            if event.key() == Qt.Key_F:
                if hasattr(self, 'current_image_path') and self.current_image_path:
                    self._show_fullscreen_viewer()
            elif event.key() == Qt.Key_Left:
                logging.info("Left key pressed in StoryDisplay")
                self.navigate_back_signal.emit()
            elif event.key() in (Qt.Key_Right, Qt.Key_G):
                logging.info("Advance key pressed in StoryDisplay")
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
            
            logging.info(f"Current image prompt before creating viewer: {self.current_image_prompt}")
            
            # Create new fullscreen viewer with image prompt
            self._fullscreen_viewer = FullscreenImageViewer(
                self.current_image_path,
                self.story_text.toPlainText(),
                self.current_image_prompt
            )
            
            # Verify prompt was set
            if hasattr(self._fullscreen_viewer, 'prompt_label'):
                logging.info(f"Fullscreen viewer prompt text: {self._fullscreen_viewer.prompt_label.toPlainText()}")
                logging.info(f"Prompt visible: {self._fullscreen_viewer.prompt_label.isVisible()}")
            
            # Connect signals
            main_window = self.window()
            if main_window:
                # Connect story advance signal
                if hasattr(main_window, 'next_story_segment'):
                    self._fullscreen_viewer.story_advance_signal.connect(
                        main_window.next_story_segment
                    )
                    logging.info("Story advance signal connected")
                
                # Connect back navigation signal
                self._fullscreen_viewer.navigate_back_signal.connect(
                    self.navigate_back_signal.emit
                )
                logging.info("Back navigation signal connected")
            
            # Handle global hotkeys
            if hasattr(main_window, 'hotkey_listener'):
                main_window.hotkey_listener.set_next_story_enabled(False)
                logging.info("Disabled global G hotkey for fullscreen mode")
            
            # Connect close event
            self._fullscreen_viewer.closeEvent = lambda event: self._handle_fullscreen_close(event)
            
            self._fullscreen_viewer.showFullScreen()
            logging.info("Fullscreen viewer displayed")
            
        except Exception as e:
            logging.error(f"Error showing fullscreen viewer: {e}")
            self.show_error("Failed to show fullscreen view")

    def _handle_fullscreen_close(self, event):
        """Handle fullscreen viewer close event."""
        try:
            # Release keyboard grab
            if self._fullscreen_viewer:
                self._fullscreen_viewer.releaseKeyboard()
                
            # Re-enable global G hotkey
            main_window = self.window()
            if hasattr(main_window, 'hotkey_listener'):
                main_window.hotkey_listener.set_next_story_enabled(True)
                logging.info("Re-enabled global G hotkey")
            
            # Force cleanup of viewer
            self.cleanup_viewer()
            
            # Call original close event
            event.accept()
        except Exception as e:
            logging.error(f"Error handling fullscreen close: {e}")
            # Emergency cleanup
            if self._fullscreen_viewer:
                self._fullscreen_viewer.releaseKeyboard()
                self._fullscreen_viewer.close()
                self._fullscreen_viewer = None

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
        """Append text to the story display with HTML support."""
        try:
            if self.story_text.toHtml():
                # Add new HTML content while preserving existing content
                current_html = self.story_text.toHtml()
                # Insert new content before the closing body tag
                new_html = current_html.replace('</body>', f'{text}</body>')
                self.story_text.setHtml(new_html)
            else:
                # Just set the HTML if the display is empty
                self.story_text.setHtml(text)
            
            # Scroll to the bottom to show new text
            scrollbar = self.story_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            logging.error(f"Error appending HTML text: {e}")

    def showEvent(self, event):
        """Handle widget show event."""
        super().showEvent(event)
        # Schedule focus set after show
        QTimer.singleShot(100, self._ensure_focus)
        logging.info("StoryDisplay shown")

    def _ensure_focus(self):
        """Ensure widget has focus."""
        self.setFocus()
        self.activateWindow()
        logging.info("StoryDisplay focus ensured")

    def clear_content(self):
        """Clear all content from the display."""
        self.story_text.clear()
        self.image_label.clear()
        # Remove any existing chapter selection button
        for child in self.findChildren(QPushButton):
            if child.text() == "Select New Chapter":
                child.deleteLater()