"""Custom delegates for the settings dialog."""
from PyQt5.QtCore import Qt, QRect, QEvent
from PyQt5.QtWidgets import (
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt5.QtGui import QColor, QPainter

class CheckBoxHoverDelegate(QStyledItemDelegate):
    """Delegate for handling both hover effects and checkboxes in task table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = parent

    def paint(self, painter, option, index):
        """Paint the delegate with hover effects and checkboxes."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Draw hover effect
        if opt.state & QStyle.State_MouseOver:
            painter.save()
            painter.fillRect(opt.rect, QColor("#E3F2FD"))
            painter.restore()
        
        # Draw checkbox for checkbox columns
        if index.column() in [3, 4, 5]:  # Active, Daily, Weekly columns
            style = opt.widget.style()
            
            # Get checkbox state
            value = index.data(Qt.CheckStateRole)
            if value == Qt.Checked:
                opt.state |= QStyle.State_On
            else:
                opt.state |= QStyle.State_Off
            
            # Center the checkbox
            checkbox_rect = style.subElementRect(QStyle.SE_CheckBoxIndicator, opt, opt.widget)
            checkbox_point = QRect(
                opt.rect.center().x() - checkbox_rect.width() // 2,
                opt.rect.center().y() - checkbox_rect.height() // 2,
                checkbox_rect.width(),
                checkbox_rect.height()
            )
            opt.rect = checkbox_point
            
            # Draw the checkbox
            style.drawPrimitive(QStyle.PE_IndicatorCheckBox, opt, painter, opt.widget)
        else:
            # For other columns, use default painting
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        """Handle checkbox toggle events."""
        if not index.isValid():
            return False

        # Only handle checkbox columns
        if index.column() not in [3, 4, 5]:
            return False

        # Check if column is checkable
        flags = model.flags(index)
        if not (flags & Qt.ItemIsUserCheckable) or not (flags & Qt.ItemIsEnabled):
            return False

        # Get current checkbox state
        value = index.data(Qt.CheckStateRole)
        if value is None:
            return False

        # Handle mouse click
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            # Get checkbox rect
            checkbox_rect = self.checkboxRect(option)
            if checkbox_rect.contains(event.pos()):
                # Toggle checkbox state
                state = Qt.Unchecked if value == Qt.Checked else Qt.Checked
                return model.setData(index, state, Qt.CheckStateRole)

        return False

    def checkboxRect(self, option):
        """Get the checkbox rectangle."""
        opt = QStyleOptionViewItem(option)
        style = opt.widget.style()
        checkbox_rect = style.subElementRect(QStyle.SE_CheckBoxIndicator, opt, opt.widget)
        return QRect(
            opt.rect.center().x() - checkbox_rect.width() // 2,
            opt.rect.center().y() - checkbox_rect.height() // 2,
            checkbox_rect.width(),
            checkbox_rect.height()
        )
