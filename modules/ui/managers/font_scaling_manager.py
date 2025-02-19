from __future__ import annotations

import logging
from typing import Dict, Any
from dataclasses import dataclass
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtGui import QFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FontConfig:
    """Configuration for a UI component's font."""
    family: str = "Arial"
    size_offset: int = 0  # Offset from base size
    weight: int = QFont.Normal
    style: int = QFont.StyleNormal

class FontScalingManager(QObject):
    """
    Manages dynamic font scaling across UI components.
    
    This class handles automatic font size adjustments based on window size,
    maintaining consistent typography across the application while ensuring
    readability at different window sizes.
    """
    
    def __init__(self, parent: QWidget):
        """
        Initialize the font scaling manager.
        
        Args:
            parent: The parent widget (usually main window) to monitor for size changes
        """
        super().__init__(parent)
        self.parent = parent
        self.components: Dict[QWidget, FontConfig] = {}
        self.base_size = 16  # Default base font size
        
        # Initialize and start the scaling timer
        self.scaling_timer = QTimer(self)
        self.scaling_timer.timeout.connect(self.update_fonts)
        self.scaling_timer.start(500)  # Check every 500ms
        
    def register_component(self, 
                         component: QWidget, 
                         family: str = "Arial",
                         size_offset: int = 0,
                         weight: int = QFont.Normal,
                         style: int = QFont.StyleNormal):
        """
        Register a UI component for font scaling.
        
        Args:
            component: The widget to manage fonts for
            family: Font family name
            size_offset: Size adjustment relative to base size
            weight: Font weight (e.g., QFont.Bold)
            style: Font style (e.g., QFont.StyleItalic)
        """
        self.components[component] = FontConfig(
            family=family,
            size_offset=size_offset,
            weight=weight,
            style=style
        )
        self._update_component_font(component)
        
    def update_fonts(self):
        """Update fonts for all registered components based on window size."""
        try:
            # Calculate base font size based on window width
            width = self.parent.width()
            if width < 800:
                self.base_size = 12
            elif width < 1200:
                self.base_size = 14
            else:
                self.base_size = 16
                
            # Update each component's font
            for component in self.components:
                self._update_component_font(component)
                
        except Exception as e:
            logger.error(f"Error updating fonts: {e}")
            
    def _update_component_font(self, component: QWidget):
        """Update font for a specific component."""
        try:
            if component in self.components:
                config = self.components[component]
                font = QFont(
                    config.family,
                    self.base_size + config.size_offset,
                    config.weight
                )
                font.setStyle(config.style)
                component.setFont(font)
        except Exception as e:
            logger.error(f"Error updating font for component: {e}")
            
    def cleanup(self):
        """Stop the scaling timer and clean up resources."""
        self.scaling_timer.stop()
        self.components.clear()
