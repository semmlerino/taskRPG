from PyQt6.QtWidgets import QApplication
import sys
import logging

def ensure_qt_application():
    """
    Ensures a QApplication instance exists before creating widgets.
    Returns the QApplication instance.
    """
    app = QApplication.instance()
    if app is None:
        logging.debug("Creating new QApplication instance")
        app = QApplication(sys.argv)
    else:
        logging.debug("Using existing QApplication instance")
    return app 