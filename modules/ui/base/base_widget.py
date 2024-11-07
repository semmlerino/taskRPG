from PyQt6.QtWidgets import QWidget
from modules.utils.qt_helpers import ensure_qt_application

class BaseQWidget(QWidget):
    def __init__(self, parent=None):
        ensure_qt_application()
        super().__init__(parent)

# Then other widgets can inherit from this:
class SomeWidget(BaseQWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui() 