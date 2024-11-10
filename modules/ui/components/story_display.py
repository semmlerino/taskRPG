# modules/ui/components/story_display.py

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTextBrowser, 
    QSizePolicy, QSplitter, QScrollArea, QPushButton, 
    QHBoxLayout, QMessageBox, QShortcut
)
from PyQt5.QtGui import QFont, QPixmap, QTextCursor, QKeyEvent, QKeySequence
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from typing import Optional
from .fullscreen_image_viewer import FullscreenImageViewer
import logging
import traceback
import os

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
        self.setFontPointSize(12)
        
        # Enable external links but handle them internally
        self.setOpenExternalLinks(False)
        
        # Apply stylesheet
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

class StoryDisplay(QWidget):
    """Displays story text and images with fullscreen capability."""
    navigate_back_signal = pyqtSignal()
    navigate_forward_signal = pyqtSignal()
    story_advance_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Define class attributes
        self.image_min_height = 200
        self.text_min_height = 100
        self.current_image_path = None
        self.current_node_key = None
        self._fullscreen_viewer = None
        
        # Create widgets first
        self.create_widgets()
        # Then set up the layout
        self.init_ui()
        
        # Connect internal signals
        self._setup_connections()
        
        # Add shortcut for fullscreen
        self.fullscreen_shortcut = QShortcut(QKeySequence('F'), self)
        self.fullscreen_shortcut.activated.connect(self._handle_fullscreen_shortcut)
        
        logging.info("StoryDisplay initialized")

    def create_widgets(self):
        """Create all widget instances."""
        # Story text browser
        self.story_text = StoryTextBrowser(self)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(100, 100)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
            }
        """)
        
        # Navigation buttons
        self.left_button = QPushButton("◀")
        self.right_button = QPushButton("▶")
        
        # Style navigation buttons
        nav_button_style = """
            QPushButton {
                background: rgba(255, 255, 255, 180);
                color: #333333;
                border: 2px solid #2196F3;
                border-radius: 4px;
                font-size: 28px;
                padding: 0px;
                min-width: 36px;
                min-height: 36px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 220);
                color: #000000;
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 120);
                color: rgba(51, 51, 51, 60);
                border: 1px solid rgba(33, 150, 243, 0.3);
            }
        """
        self.left_button.setStyleSheet(nav_button_style)
        self.right_button.setStyleSheet(nav_button_style)

    def init_ui(self):
        """Initialize the UI layout."""
        main_layout = QVBoxLayout(self)
        
        # Create splitter
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        
        # Image section with navigation
        image_container = QWidget()
        image_container.setMinimumHeight(self.image_min_height)
        image_layout = QHBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add navigation buttons and image
        image_layout.addWidget(self.left_button)
        image_layout.addWidget(self.image_label, 1)  # 1 for stretch factor
        image_layout.addWidget(self.right_button)
        
        # Story text section
        self.story_text.setMinimumHeight(self.text_min_height)
        
        # Add components to splitter
        self.splitter.addWidget(image_container)
        self.splitter.addWidget(self.story_text)
        
        # Set initial size ratio (40% image, 60% text)
        self.splitter.setSizes([400, 600])
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        # Connect signals
        self.splitter.splitterMoved.connect(self.handle_splitter_moved)
        self.left_button.clicked.connect(self.navigate_back_signal.emit)
        self.right_button.clicked.connect(self.navigate_forward_signal.emit)

    def _setup_connections(self):
        """Set up internal signal connections."""
        self.left_button.clicked.connect(self.navigate_back_signal.emit)
        self.right_button.clicked.connect(self.navigate_forward_signal.emit)

    def set_page(self, node_key: str, html_content: str, image_path: Optional[str]):
        """Set the content for the current story page."""
        try:
            self.current_node_key = node_key
            self.clear()
            
            if image_path and os.path.exists(image_path):
                self.current_image_path = image_path
                self.load_image()
                logging.debug(f"Image loaded: {image_path}")
            else:
                self.current_image_path = None
                logging.debug("No valid image path provided")
                
            self.append_text(html_content)
            
            # Update fullscreen viewer if it exists
            if self._fullscreen_viewer:
                self._fullscreen_viewer.update_content(
                    self.current_image_path,
                    self.story_text.toPlainText()
                )
                
            logging.debug(f"Page set for node: {node_key}")
            
        except Exception as e:
            logging.error(f"Error setting page: {e}")
            self.show_error("Failed to set page content")

    def append_text(self, html_content: str):
        """Append text to the story display."""
        self.story_text.append(html_content)
        self.scroll_to_end()

    def scroll_to_end(self):
        """Scroll to the end of the text display."""
        self.story_text.moveCursor(QTextCursor.End)

    def load_image(self):
        """Load and display the image, maintaining aspect ratio."""
        if not self.current_image_path:
            return

        try:
            pixmap = QPixmap(self.current_image_path)
            if pixmap.isNull():
                logging.error("Failed to load image")
                return

            # Get the available size
            available_width = self.image_label.width()
            available_height = self.splitter.sizes()[0]

            # Scale the image
            scaled_pixmap = pixmap.scaled(
                available_width,
                available_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)
            
        except Exception as e:
            logging.error(f"Error loading image: {e}")
            self.show_error("Failed to load image")

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.load_image()

    def handle_splitter_moved(self, pos, index):
        """Handle splitter movement."""
        sizes = self.splitter.sizes()
        total_height = sum(sizes)
        
        # Calculate minimum heights as percentages
        min_image_percent = max(0.2, self.image_min_height / total_height)
        min_text_percent = max(0.2, self.text_min_height / total_height)
        
        # Get current percentages
        image_percent = sizes[0] / total_height
        text_percent = sizes[1] / total_height
        
        # Adjust if below minimums
        if image_percent < min_image_percent:
            sizes[0] = int(total_height * min_image_percent)
            sizes[1] = total_height - sizes[0]
        elif text_percent < min_text_percent:
            sizes[1] = int(total_height * min_text_percent)
            sizes[0] = total_height - sizes[1]
            
        # Apply new sizes
        self.splitter.setSizes(sizes)
        
        # Ensure image is resized properly
        QTimer.singleShot(50, self.load_image)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        logging.debug(f"Key pressed in StoryDisplay: {event.key()}")
        try:
            if event.key() == Qt.Key_F:
                logging.debug("F key detected - attempting to show fullscreen")
                if hasattr(self, 'current_image_path') and self.current_image_path:
                    logging.debug(f"Current image path: {self.current_image_path}")
                    self._show_fullscreen_viewer()
                else:
                    logging.debug("No image available for fullscreen view")
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
        """Show the fullscreen image viewer."""
        try:
            if not os.path.exists(self.current_image_path):
                logging.error(f"Image file not found: {self.current_image_path}")
                self.show_error("Image file not found")
                return

            self.cleanup_viewer()
            
            self._fullscreen_viewer = FullscreenImageViewer(
                self.current_image_path,
                self.story_text.toPlainText()
            )
            
            # Connect story progression signal
            self._fullscreen_viewer.story_advance_signal.connect(
                self.story_advance_signal.emit
            )
            
            self._fullscreen_viewer.showFullScreen()
            logging.info("Fullscreen viewer displayed")
            
        except Exception as e:
            logging.error(f"Error showing fullscreen viewer: {e}")
            self.show_error("Failed to show fullscreen view")

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
    def clear(self):
        """Clear all content."""
        self.story_text.clear()
        self.image_label.clear()
        self.current_image_path = None
        self.current_node_key = None

    def show_error(self, message: str):
        """Show error message to user."""
        QMessageBox.critical(self, "Error", message)

    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup_viewer()

    def _handle_fullscreen_shortcut(self):
        """Handle fullscreen shortcut activation."""
        logging.debug("Fullscreen shortcut activated")
        if hasattr(self, 'current_image_path') and self.current_image_path:
            self._show_fullscreen_viewer()
        else:
            logging.debug("No image available for fullscreen view")
