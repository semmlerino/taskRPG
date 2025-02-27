import sys
import os
import logging
import traceback
from functools import lru_cache
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal, QTimer

from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QTextBrowser, QApplication, QMessageBox, 
    QWidget, QShortcut, QSizePolicy
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QKeyEvent, QPen, QPainterPath, 
    QKeySequence, QTextOption, QFont, QTextCursor
)

from modules.constants import HOTKEYS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class OutlinedTextBrowser(QTextBrowser):
    """Text browser with outlined text for better visibility on any background."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Configure text browser for better visibility
        self.setViewportMargins(0, 0, 0, 0)
        self.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(0, 0, 0, 0.7);
                border: 2px solid white;
                border-radius: 5px;
                color: white;
                font-size: 28pt;
                padding: 10px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.2);
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.8);
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: white;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        # Enable rich text and proper text wrapping
        self.setAcceptRichText(True)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set text color and format
        self.document().setDefaultStyleSheet("body { color: white; }")
    
    def wheelEvent(self, event):
        """Handle mouse wheel events for better scrolling."""
        try:
            # Handle zoom with Ctrl+wheel
            if event.modifiers() & Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    # Zoom in
                    self.zoomIn(1)
                else:
                    # Zoom out
                    self.zoomOut(1)
                event.accept()
            else:
                # Enhanced scrolling speed for better experience
                delta = event.angleDelta().y()
                scrollbar = self.verticalScrollBar()
                
                # Calculate scroll amount based on content size
                scroll_amount = max(50, int(abs(delta) * 1.5))
                if delta < 0:
                    # Scroll down
                    new_value = min(scrollbar.value() + scroll_amount, scrollbar.maximum())
                else:
                    # Scroll up
                    new_value = max(scrollbar.value() - scroll_amount, scrollbar.minimum())
                
                # Apply the scroll
                scrollbar.setValue(new_value)
                event.accept()
                
                # Process events to ensure immediate visual feedback
                QApplication.processEvents()
        except Exception as e:
            logging.error(f"Error in wheelEvent: {e}")
            # Fall back to default behavior
            super().wheelEvent(event)


class FullscreenImageViewer(QMainWindow):
    """Fullscreen image viewer with story progression capability."""
    
    # Define all signals at class level
    story_advance_signal = pyqtSignal()
    navigate_back_signal = pyqtSignal()
    
    def __init__(self, image_path, story_text, image_prompt=None, parent=None):
        super().__init__(parent)
        logging.info("Initializing FullscreenImageViewer")
        logging.info(f"Image prompt received: {image_prompt}")
        
        # Initialize state variables first
        self.text_visible = True
        self.prompt_visible = False
        self._fullscreen = False  # Track fullscreen state
        
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
        self.text_browser.setHtml(story_text)
        self.text_browser.setReadOnly(True)
        self.text_browser.moveCursor(QTextCursor.Start)
        self.text_browser.ensureCursorVisible()
        # Set size policy to allow vertical expansion
        self.text_browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        # Set minimum height to ensure text has room to display
        self.text_browser.setMinimumHeight(200)
        
        # Create prompt label
        self.prompt_label = OutlinedTextBrowser(central_widget)
        self.prompt_label.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(0, 0, 0, 0.7);
                border: 2px solid white;
                border-radius: 5px;
                color: white;
                font-size: 28pt;
                padding: 10px;
                margin: 10px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.1);
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: white;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        self.prompt_label.setReadOnly(True)
        self.prompt_label.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.prompt_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.prompt_label.setVisible(False)  # Set prompt to invisible by default
        self.prompt_label.setMinimumHeight(100)  # Ensure minimum height
        if image_prompt:
            logging.info("Setting initial prompt text")
            # Convert image_prompt to string if it's a dictionary
            if isinstance(image_prompt, dict):
                prompt_str = str(image_prompt)
            else:
                prompt_str = str(image_prompt)
            self.prompt_label.setHtml(f"""
                <div style='line-height: 1.4;'>
                    <p style='font-weight: bold; font-size: 28pt; margin-bottom: 10px;'>Image Prompt:</p>
                    <p style='font-size: 28pt; margin: 0;'>{prompt_str}</p>
                </div>
            """)
            logging.info(f"Prompt text set to: {self.prompt_label.toPlainText()}")
            logging.info(f"Prompt visible: {self.prompt_label.isVisible()}")
        
        # Create layout for central widget
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.image_label)
        
        # Add prompt and text browser to central widget
        self.prompt_label.setParent(central_widget)
        self.text_browser.setParent(central_widget)
        
        # Ensure prompt and text are on top of the image
        self.prompt_label.raise_()
        self.text_browser.raise_()
        
        # Load and display image
        self.original_pixmap = QPixmap(image_path)
        self.scale_image()
        
        # Position elements
        self.position_elements()

        # Setup shortcuts
        self.setup_shortcuts()
        
        # Set focus policy to accept keyboard input
        self.setFocusPolicy(Qt.StrongFocus)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Use the HOTKEYS from constants for fullscreen
        QShortcut(QKeySequence(HOTKEYS['fullscreen'].upper()), self, self.close)
        QShortcut(QKeySequence('Escape'), self, self.close)
        QShortcut(QKeySequence('T'), self, self.toggle_text)
        QShortcut(QKeySequence('G'), self, self.advance_story)
        QShortcut(QKeySequence('I'), self, self.toggle_prompt)

    def position_elements(self):
        """Position the image and text elements."""
        screen_rect = self.geometry()
        
        # Position the image to fill the screen
        self.image_label.setGeometry(0, 0, screen_rect.width(), screen_rect.height())
        
        # Calculate text dimensions
        text_height = min(int(screen_rect.height() * 0.5), 600)  # Increased to 50% of screen or 600px
        side_margin = int(screen_rect.width() * 0.1)  # Reduced to 10% margin on each side
        bottom_margin = 20  # Bottom margin
        
        # Position text with better spacing
        text_y = screen_rect.height() - text_height - bottom_margin
        text_width = screen_rect.width() - (side_margin * 2)
        
        # Set text browser geometry
        self.text_browser.setGeometry(
            side_margin,
            text_y,
            text_width,
            text_height
        )

        # Position prompt at the top
        prompt_height = min(int(screen_rect.height() * 0.35), 300)  # Max 35% of screen or 300px
        prompt_top_margin = 30
        prompt_width = text_width
        
        self.prompt_label.setGeometry(
            side_margin,
            prompt_top_margin,
            prompt_width,
            prompt_height
        )
        
        # Ensure prompt and text stay on top and are visible
        self.prompt_label.raise_()
        self.text_browser.raise_()
        self.prompt_label.setVisible(self.prompt_visible)  # Use the instance variable
        self.text_browser.setVisible(self.text_visible)    # Also handle text visibility
        
        # Ensure scrollbar is visible and working
        self.text_browser.verticalScrollBar().setVisible(True)
        self.prompt_label.verticalScrollBar().setVisible(True)
        
        logging.info(f"Position updated - Prompt visible: {self.prompt_label.isVisible()}, Text visible: {self.text_browser.isVisible()}")

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
        logging.info(f"Text visibility toggled to: {self.text_visible}")

    def toggle_prompt(self):
        """Toggle prompt visibility."""
        self.prompt_visible = not self.prompt_visible
        self.prompt_label.setVisible(self.prompt_visible)
        logging.info(f"Prompt visibility toggled to: {self.prompt_visible}")

    def advance_story(self):
        """Handle story progression request."""
        try:
            logging.info("[FULLSCREEN] Advance story method called in FullscreenImageViewer")
            self.story_advance_signal.emit()
        except Exception as e:
            logging.error(f"Error advancing story: {e}", exc_info=True)

    def keyPressEvent(self, event):
        """Handle key press events."""
        try:
            if event.key() == Qt.Key_Escape:
                logging.info("[FULLSCREEN] Escape key pressed, closing viewer")
                self.close()
            elif event.key() in (Qt.Key_G, Qt.Key_Space, Qt.Key_Right):  # Support G, Space, and Right Arrow
                logging.info(f"[FULLSCREEN] Advance key pressed: {event.key()}")
                self.story_advance_signal.emit()
            elif event.key() == Qt.Key_P:
                logging.info("[FULLSCREEN] Toggle prompt visibility")
                self.toggle_prompt()
            elif event.key() in (Qt.Key_Left, Qt.Key_Backspace):
                logging.info("[FULLSCREEN] Back navigation key pressed")
                self.navigate_back_signal.emit()
            event.accept()
        except Exception as e:
            logging.error(f"Error handling key press: {e}")
            event.ignore()

    def update_content(self, image_path: str, text: str, prompt: str = None):
        """Update the viewer content."""
        try:
            logging.info(f"[FULLSCREEN] Updating content with prompt: {prompt}")
            if not self.isVisible():
                logging.warning("[FULLSCREEN] Attempted to update content of hidden viewer")
                return

            # Removed fullscreen state restoration to prevent flickering
            # was_fullscreen = self.isFullScreen()
            # logging.info(f"[FULLSCREEN] Current state - Fullscreen: {was_fullscreen}")
            
            if image_path and os.path.exists(image_path):
                self.original_pixmap = QPixmap(image_path)
                self.scale_image()
            
            # Format the text with appropriate styling for better readability
            formatted_text = f"""
            <div style='font-family: Arial, sans-serif; line-height: 1.6;'>
                {text}
            </div>
            """
            
            # Update text content
            self.text_browser.setHtml(formatted_text)
            
            # Ensure text is visible and scrolled to top
            self.text_browser.moveCursor(QTextCursor.Start)
            self.text_browser.ensureCursorVisible()
            
            # Process events to ensure UI updates immediately
            QApplication.processEvents()
            
            if prompt:
                logging.info("[FULLSCREEN] Setting prompt text")
                # Convert prompt to string if it's a dictionary
                prompt_str = str(prompt) if not isinstance(prompt, dict) else str(prompt)
                self.prompt_label.setHtml(f"""
                    <div style='line-height: 1.4;'>
                        <p style='font-weight: bold; font-size: 28pt; margin-bottom: 10px;'>Image Prompt:</p>
                        <p style='font-size: 28pt; margin: 0;'>{prompt_str}</p>
                    </div>
                """)
                self.prompt_label.setVisible(False)  # Keep prompt invisible by default
                self.prompt_visible = False  # Update state
                self.prompt_label.raise_()
            else:
                self.prompt_label.setVisible(False)
                self.prompt_visible = False
                
            # Removed window state restoration to prevent flickering
            # if was_fullscreen:
            #     logging.info("[FULLSCREEN] Restoring fullscreen state")
            #     self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            #     self.showFullScreen()
            #     self.activateWindow()
            #     self.raise_()
            #     logging.info("[FULLSCREEN] Restored fullscreen state")
                
        except Exception as e:
            logging.error(f"[FULLSCREEN] Error updating fullscreen content: {e}")

    def showFullScreen(self):
        """Override showFullScreen to track state."""
        logging.info("[FULLSCREEN] Entering fullscreen mode")
        super().showFullScreen()
        self._fullscreen = True
        self.activateWindow()
        self.raise_()
        logging.info("[FULLSCREEN] Fullscreen mode entered, state set to True")

    def showNormal(self):
        """Override showNormal to track state."""
        logging.info("[FULLSCREEN] Exiting fullscreen mode")
        super().showNormal()
        self._fullscreen = False
        self.activateWindow()
        self.raise_()
        logging.info("[FULLSCREEN] Normal mode entered, state set to False")

    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()
        self.grabKeyboard()  # Force keyboard focus
        logging.info("Fullscreen viewer activated and focused")

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Always release keyboard first
            self.releaseKeyboard()
            
            # Then attempt cleanup
            try:
                self.cleanup_resources()
            except Exception as e:
                logging.error(f"Error during FullscreenImageViewer cleanup: {e}")
                # Continue with close even if cleanup fails
            
            super().closeEvent(event)
            logging.info("FullscreenImageViewer closed successfully")
        except Exception as e:
            logging.error(f"Error during FullscreenImageViewer close: {e}")
        finally:
            # Ensure keyboard is released even if there's an error
            try:
                self.releaseKeyboard()
            except:
                pass
            event.accept()

    def cleanup_resources(self):
        """Clean up resources before closing."""
        try:
            # Only cleanup if we're actually closing
            if not self.isVisible():
                logging.info("[FULLSCREEN] Starting cleanup of hidden viewer")
                # Clear keyboard focus and window flags
                self.releaseKeyboard()
                self.setWindowFlags(Qt.Widget)
                
                # Clear image resources
                self.original_pixmap = None
                # self.get_scaled_pixmap.cache_clear()
                
                # Clear text resources
                if hasattr(self, 'text_browser'):
                    self.text_browser.clear()
                if hasattr(self, 'prompt_label'):
                    self.prompt_label.clear()
                    
                # Force process events to ensure cleanup
                QApplication.processEvents()
                logging.info("[FULLSCREEN] Cleanup completed")
                
        except Exception as e:
            logging.error(f"[FULLSCREEN] Error cleaning up resources: {e}")

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


# Example usage (for testing purposes)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Replace these with actual paths and content
    sample_image_path = "path/to/your/image.jpg"
    sample_story_text = "<p>Your story text goes here.</p>"
    sample_image_prompt = {"prompt": "Describe the image."}
    
    viewer = FullscreenImageViewer(sample_image_path, sample_story_text, sample_image_prompt)
    viewer.showFullScreen()
    
    # Example signal connections (to be implemented as needed)
    # viewer.story_advance_signal.connect(your_advance_method)
    # viewer.navigate_back_signal.connect(your_back_method)
    
    sys.exit(app.exec_())
