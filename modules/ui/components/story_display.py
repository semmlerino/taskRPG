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
        self._last_fullscreen_state = False
        self._last_window_geometry = None
        
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
        
        # Add change story button
        self.change_story_button = QPushButton("Change Story")
        self.change_story_button.clicked.connect(self._change_story)
        
        # Add both components to splitter
        self.splitter.addWidget(self.image_scroll)
        self.splitter.addWidget(self.story_text)
        self.splitter.addWidget(self.change_story_button)
        
        # Set default split positions
        self.splitter.setSizes([300, 400, 50])
        
        # Connect splitter movement to image resize
        self.splitter.splitterMoved.connect(self.load_image)
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)

    def set_page(self, content: 'StoryContent'):
        """Set the page content."""
        try:
            logging.info(f"[FULLSCREEN] Setting page for node: {content.node_key}")
            
            # Store current content
            self.current_node_key = content.node_key
            self.current_image_path = content.image_path
            self.current_image_prompt = content.image_prompt
            
            # Clear existing content
            self.story_text.clear()
            
            # Update image if provided
            if content.image_path:
                self.load_image()
            
            # Update story text
            html_content = content.to_html()
            logging.info(f"Generated HTML content length: {len(html_content)}")
            
            if not html_content.strip():
                logging.warning("HTML content is empty, using fallback")
                # Fallback content if HTML is empty
                html_content = f"""
                <div style='font-family: Arial, sans-serif; line-height: 1.6; color: #333333;'>
                    <p>{content.text}</p>
                    {f"<p><i>Environment:</i> {content.environment}</p>" if content.environment else ""}
                    {f"<div style='margin: 10px 0; padding: 10px; background-color: rgba(255, 0, 0, 0.1); border-left: 4px solid #ff0000;'>"
                     f"<p><b>Battle:</b> {content.battle_info.get('message', '')}</p>"
                     f"<p><b>Enemy:</b> {content.battle_info.get('enemy', '')}</p></div>"
                     if content.battle_info else ""}
                </div>
                """
            
            # Append to story text
            self.story_text.append_text(html_content)
            logging.info("Content appended to story text")
            
            # Update fullscreen viewer if it exists and is visible
            if self._fullscreen_viewer and self._fullscreen_viewer.isVisible():
                logging.info("[FULLSCREEN] Updating existing fullscreen viewer in set_page")
                # Store current fullscreen state
                was_fullscreen = self._fullscreen_viewer.isFullScreen()
                logging.info(f"[FULLSCREEN] Current viewer state - Fullscreen: {was_fullscreen}")
                
                # Update content
                self._fullscreen_viewer.update_content(
                    content.image_path,
                    self.story_text.toPlainText(),
                    content.image_prompt
                )
                
            elif hasattr(self, '_last_fullscreen_state') and self._last_fullscreen_state:
                logging.info("[FULLSCREEN] Recreating fullscreen viewer with previous state")
                self._show_fullscreen_viewer()
            
            # Set focus back to story display
            self.setFocus()
            logging.info("Page set successfully")
            
        except Exception as e:
            logging.error(f"[FULLSCREEN] Error setting page: {e}")
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
                logging.error(f"[FULLSCREEN] Image file not found: {self.current_image_path}")
                self.show_error("Image file not found")
                return

            # If we already have a viewer, just update its content
            if self._fullscreen_viewer and self._fullscreen_viewer.isVisible():
                logging.info("[FULLSCREEN] Updating existing fullscreen viewer in _show_fullscreen_viewer")
                # Store current fullscreen state
                was_fullscreen = self._fullscreen_viewer.isFullScreen()
                logging.info(f"[FULLSCREEN] Current viewer state - Fullscreen: {was_fullscreen}")
                
                # Update content
                self._fullscreen_viewer.update_content(
                    self.current_image_path,
                    self.story_text.toPlainText(),
                    self.current_image_prompt
                )
                
            # Otherwise, create a new viewer
            logging.info("[FULLSCREEN] Creating new fullscreen viewer")
            self.cleanup_viewer()
            
            logging.info(f"Current image prompt before creating viewer: {self.current_image_prompt}")
            
            # Create new fullscreen viewer with image prompt
            self._fullscreen_viewer = FullscreenImageViewer(
                self.current_image_path,
                self.story_text.toPlainText(),
                self.current_image_prompt
            )
            
            # Connect signals
            main_window = self.window()
            if main_window:
                # Connect story advance signal
                if hasattr(main_window, 'next_story_segment'):
                    self._fullscreen_viewer.story_advance_signal.connect(
                        main_window.next_story_segment
                    )
                    logging.info("[FULLSCREEN] Story advance signal connected")
                
                # Connect back navigation signal
                if hasattr(main_window, 'navigate_back'):
                    self._fullscreen_viewer.navigate_back_signal.connect(
                        main_window.navigate_back
                    )
                    logging.info("[FULLSCREEN] Back navigation signal connected")
                else:
                    logging.warning("Main window does not have navigate_back method")
            
            # Handle global hotkeys
            if hasattr(main_window, 'hotkey_listener'):
                main_window.hotkey_listener.set_next_story_enabled(False)
                logging.info("Disabled global G hotkey for fullscreen mode")
            
            # Connect close event
            self._fullscreen_viewer.closeEvent = lambda event: self._handle_fullscreen_close(event)
            
            self._fullscreen_viewer.showFullScreen()
            logging.info("[FULLSCREEN] New viewer displayed in fullscreen mode")
            
        except Exception as e:
            logging.error(f"[FULLSCREEN] Error showing fullscreen viewer: {e}")
            self.show_error("Failed to show fullscreen view")

    def _handle_fullscreen_close(self, event):
        """Handle fullscreen viewer close event."""
        try:
            logging.info("[FULLSCREEN] Handling fullscreen viewer close event")
            if self._fullscreen_viewer:
                # Store state before cleanup
                was_fullscreen = self._fullscreen_viewer.isFullScreen()
                logging.info(f"[FULLSCREEN] State before close - Fullscreen: {was_fullscreen}")
                
                # Release keyboard grab
                self._fullscreen_viewer.releaseKeyboard()
                
                # Re-enable global G hotkey
                main_window = self.window()
                if hasattr(main_window, 'hotkey_listener'):
                    main_window.hotkey_listener.set_next_story_enabled(True)
                    logging.info("[FULLSCREEN] Re-enabled global G hotkey")
                
                # Store state for potential restoration
                if was_fullscreen:
                    self._last_fullscreen_state = True
                    logging.info("[FULLSCREEN] Stored state for potential restoration")
                
                # Force cleanup of viewer
                self.cleanup_viewer()
                
            # Call original close event
            event.accept()
            logging.info("[FULLSCREEN] Close event handled successfully")
            
        except Exception as e:
            logging.error(f"[FULLSCREEN] Error handling fullscreen close: {e}")
            # Emergency cleanup
            if self._fullscreen_viewer:
                try:
                    self._fullscreen_viewer.releaseKeyboard()
                    self._fullscreen_viewer.close()
                    self._fullscreen_viewer = None
                    logging.info("[FULLSCREEN] Emergency cleanup completed")
                except Exception as cleanup_error:
                    logging.error(f"[FULLSCREEN] Error during emergency cleanup: {cleanup_error}")

    def cleanup_viewer(self):
        """Clean up any existing fullscreen viewer instance."""
        if self._fullscreen_viewer:
            try:
                logging.info("[FULLSCREEN] Starting viewer cleanup")
                was_fullscreen = self._fullscreen_viewer.isFullScreen()
                logging.info(f"[FULLSCREEN] Viewer state before cleanup - Fullscreen: {was_fullscreen}")
                
                # Store state for potential restoration
                if was_fullscreen:
                    self._last_fullscreen_state = True
                    logging.info("[FULLSCREEN] Stored state for potential restoration")
                
                # First release keyboard and disable window flags
                self._fullscreen_viewer.releaseKeyboard()
                self._fullscreen_viewer.setWindowFlags(Qt.Widget)
                self._fullscreen_viewer.close()
                
                # Re-enable global hotkey
                main_window = self.window()
                if hasattr(main_window, 'hotkey_listener'):
                    main_window.hotkey_listener.set_next_story_enabled(True)
                    logging.info("[FULLSCREEN] Re-enabled global G hotkey during cleanup")
                
                # Schedule deletion for next event loop
                self._fullscreen_viewer.deleteLater()
                logging.info("[FULLSCREEN] Viewer scheduled for deletion")
                
            except Exception as e:
                logging.error(f"[FULLSCREEN] Error cleaning up viewer: {e}")
            finally:
                self._fullscreen_viewer = None
                logging.info("[FULLSCREEN] Viewer cleanup complete")

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

    def _change_story(self):
        """Open story selection dialog to switch stories."""
        from modules.ui.dialogs.story_selection_dialog import StorySelectionDialog
        
        # Find the main window by traversing up the widget hierarchy
        main_window = self
        while main_window and not hasattr(main_window, 'story_manager'):
            main_window = main_window.parent()
            
        if not main_window:
            logging.error("Could not find main window")
            return
            
        # Clear any existing choices or state
        self.clear_choices()
        self.story_text.clear()
            
        dialog = StorySelectionDialog(main_window)
        if dialog.exec_():
            # The dialog will handle story initialization if accepted
            pass

    def clear_choices(self):
        """Clear any existing choice buttons."""
        # Find and remove all choice buttons
        for child in self.findChildren(QPushButton):
            if hasattr(child, 'choice_data'):  # Identify choice buttons by their choice_data attribute
                child.deleteLater()