from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTextBrowser, 
    QSizePolicy, QSplitter, QScrollArea, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt5.QtGui import QFont, QPixmap, QTextCursor, QKeyEvent
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from os import path
from typing import Optional
from .fullscreen_image_viewer import FullscreenImageViewer
from modules.ui.components.story_text_browser import StoryTextBrowser
import logging
import traceback
import os

class StoryDisplay(QWidget):
    """Displays story text and images."""
    navigate_back_signal = pyqtSignal()
    navigate_forward_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Define class attributes first
        self.image_min_height = 200
        self.text_min_height = 100
        self.current_image_path = None
        
        # Create widgets first
        self.create_widgets()
        # Then set up the layout
        self.init_ui()
        
        self._fullscreen_viewer = None  # Single reference for the viewer
    
    def create_widgets(self):
        """Create all widget instances."""
        # Create existing widgets
        self.story_text = StoryTextBrowser(self)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.splitter = QSplitter(Qt.Vertical)
        
        # Create navigation buttons
        self.left_button = QPushButton("◀")
        self.left_button.setStyleSheet("""
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
        """)
        
        self.right_button = QPushButton("▶")
        self.right_button.setStyleSheet(self.left_button.styleSheet())

    def init_ui(self):
        """Initialize the UI layout."""
        main_layout = QVBoxLayout(self)
        
        # Set minimum sizes for splitter sections
        self.image_min_height = 200
        self.text_min_height = 150
        
        # Create splitter with proper size policies
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        
        # Image section with navigation
        image_container = QWidget()
        image_container.setMinimumHeight(self.image_min_height)
        image_layout = QHBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create and configure image label
        self.image_label = QLabel()
        self.image_label.setMinimumSize(100, 100)  # Set minimum size
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
            }
        """)
        
        # Add image label to image container
        image_layout.addWidget(self.image_label)
        
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
            self.load_image()
        else:
            self.image_label.clear()
            self.current_image_path = None

    def load_image(self):
        """Load and display the image, maintaining aspect ratio."""
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            return

        try:
            # Load the image
            pixmap = QPixmap(self.current_image_path)
            if pixmap.isNull():
                return

            # Get the available size for the image
            available_width = self.image_label.width()
            available_height = self.splitter.sizes()[0]  # Height of top splitter section

            # Scale the image maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                available_width,
                available_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Set the scaled image
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)

        except Exception as e:
            print(f"Error loading image: {e}")

    def resizeEvent(self, event):
        """Handles resize events."""
        super().resizeEvent(event)
        self.load_image()

    def set_page(self, node_key: str, html_content: str, image_path: Optional[str]):
        """Updates display content."""
        self.clear()
        if image_path:
            self.display_image(image_path)
        self.append_text(html_content)
        
        # Update fullscreen viewer if it exists
        if self._fullscreen_viewer:
            self._fullscreen_viewer.update_content(image_path, self.story_text.toPlainText())
    
    def clear(self):
        """Clears all content."""
        self.story_text.clear()
        self.image_label.clear()
        
    def clear_history(self):
        """Clears display history."""
        self.clear()

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

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        try:
            if event.key() == Qt.Key_F and self.current_image_path:
                logging.info(f"F key pressed, attempting to show fullscreen image: {self.current_image_path}")
                
                # Verify image exists
                if not os.path.exists(self.current_image_path):
                    logging.error(f"Image file does not exist: {self.current_image_path}")
                    QMessageBox.warning(self, "Error", "Image file not found!")
                    return

                # Clean up any existing viewer
                self.cleanup_viewer()
                
                # Create new viewer
                try:
                    self._fullscreen_viewer = FullscreenImageViewer(
                        self.current_image_path,
                        self.story_text.toPlainText()
                    )
                    self._fullscreen_viewer.showFullScreen()
                    event.accept()
                    logging.info("Fullscreen viewer created and displayed")
                    
                except Exception as e:
                    logging.error(f"Failed to create viewer: {str(e)}\n{traceback.format_exc()}")
                    QMessageBox.critical(self, "Error", f"Failed to show fullscreen image: {str(e)}")
                    self.cleanup_viewer()
                    
            else:
                super().keyPressEvent(event)
                
        except Exception as e:
            logging.error(f"Error in keyPressEvent handling: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to handle key press: {str(e)}")

    def handle_splitter_moved(self, pos, index):
        """Handle splitter movement to prevent sections from disappearing and resize image"""
        # Get current sizes
        sizes = self.splitter.sizes()
        total_height = sum(sizes)
        
        # Calculate minimum heights as percentages of total height
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

    def set_content(self, text, image_path=None):
        """Set the content of the display."""
        self.story_text.setText(text)
        
        # Update image
        self.current_image_path = image_path
        if image_path:
            self.load_image()
        else:
            self.image_label.clear()
