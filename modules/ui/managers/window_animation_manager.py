from __future__ import annotations

import os
import json
import logging
from typing import Optional
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtWidgets import QMainWindow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WindowAnimationManager:
    """
    Manages window animations like shaking effects.
    
    This class encapsulates all window animation logic, providing a clean interface
    for triggering various window animations while handling settings and state management.
    """
    
    def __init__(self, window: QMainWindow, settings_file: str):
        """
        Initialize the animation manager.
        
        Args:
            window: The main window to animate
            settings_file: Path to the settings file containing animation preferences
        """
        self.window = window
        self.settings_file = settings_file
        self.shake_animation = self._init_shake_animation()
        
    def _init_shake_animation(self) -> QPropertyAnimation:
        """Initialize the shake animation properties."""
        animation = QPropertyAnimation(self.window, b"geometry")
        animation.setDuration(100)
        animation.setLoopCount(4)
        animation.setEasingCurve(QEasingCurve.Linear)
        return animation
        
    def trigger_shake(self):
        """Trigger the shaking animation if enabled in settings."""
        try:
            shake_enabled = True  # Default to True
            
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)
            
            if shake_enabled and self.shake_animation.state() != QPropertyAnimation.Running:
                original_geometry = self.window.geometry()
                offset = 10
                
                # Create keyframes for the shake animation
                keyframes = []
                for i in range(8):
                    x_offset = offset if i % 2 == 0 else -offset
                    new_geometry = QRect(
                        original_geometry.x() + x_offset,
                        original_geometry.y(),
                        original_geometry.width(),
                        original_geometry.height()
                    )
                    keyframes.append((i * 50, new_geometry))
                
                # Add the original position as the final keyframe
                keyframes.append((400, original_geometry))
                
                # Set the keyframes
                self.shake_animation.clear()
                for time, geometry in keyframes:
                    self.shake_animation.setKeyValueAt(time/400, geometry)
                
                # Start the animation
                self.shake_animation.start()
                
        except Exception as e:
            logger.error(f"Error triggering shake animation: {e}")
