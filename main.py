# main.py

import sys
from PyQt5.QtWidgets import QApplication
from modules.ui import TaskRPG

def main():
    app = QApplication(sys.argv)
    game = TaskRPG()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
