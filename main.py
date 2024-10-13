import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
from modules.ui import TaskRPG

def main():
    app = QApplication(sys.argv)
    
    # Set the Fusion style
    app.setStyle("Fusion")
    
    
    game = TaskRPG()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
