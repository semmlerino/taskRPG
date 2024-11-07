from PyQt6.QtWidgets import QApplication

def ensure_qt_application():
    """Ensures a QApplication instance exists."""
    if not QApplication.instance():
        QApplication([]) 