# main.py

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from modules.ui import TaskRPG

def main():
    app = QApplication(sys.argv)
    
    # Set the Fusion style
    app.setStyle("Fusion")
    
    # Create Classic Blue and Gray palette
    palette = QPalette()
    
    # Window background
    palette.setColor(QPalette.Window, QColor(255, 255, 255))  # White
    
    # Window text
    palette.setColor(QPalette.WindowText, QColor(47, 79, 79))  # Dark Slate Gray
    
    # Base (e.g., text input backgrounds)
    palette.setColor(QPalette.Base, QColor(245, 245, 245))  # White Smoke
    
    # Alternate base (e.g., alternate rows in tables)
    palette.setColor(QPalette.AlternateBase, QColor(220, 220, 220))  # Gainsboro
    
    # Text
    palette.setColor(QPalette.Text, QColor(47, 79, 79))  # Dark Slate Gray
    
    # Button background
    palette.setColor(QPalette.Button, QColor(30, 144, 255))  # Dodger Blue
    
    # Button text
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))  # White
    
    # Highlight (e.g., selected items)
    palette.setColor(QPalette.Highlight, QColor(135, 206, 250))  # Light Sky Blue
    
    # Highlighted text
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # White
    
    # Apply the Classic Blue and Gray palette
    app.setPalette(palette)
    
    game = TaskRPG()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
