"""Custom delegates for the settings dialog."""
from PyQt5.QtCore import Qt, QRect, QEvent as QMouseEvent
from PyQt5.QtWidgets import (
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt5.QtGui import QColor, QPainter

class RowHoverDelegate(QStyledItemDelegate):
    """Delegate for handling row hover effects in task table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = parent

    def paint(self, painter, option, index):
        """Paint the delegate with proper hover effects."""
        # Get the original option
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Draw the background
        if opt.state & QStyle.State_MouseOver:
            painter.save()
            painter.fillRect(opt.rect, QColor("#E3F2FD"))
            painter.restore()
        
        # Draw the rest of the item
        super().paint(painter, option, index)

class CheckBoxCenterDelegate(QStyledItemDelegate):
    """Delegate for centering checkboxes in the task table."""

    def createEditor(self, parent, option, index):
        """Disable editing for checkbox columns."""
        return None

    def paint(self, painter, option, index):
        """Paint centered checkbox."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Center the checkbox
        style = opt.widget.style()
        checkbox_rect = style.subElementRect(QStyle.SE_ViewItemCheckIndicator, opt, opt.widget)
        checkbox_point = QRect(
            opt.rect.center().x() - checkbox_rect.width() // 2,
            opt.rect.center().y() - checkbox_rect.height() // 2,
            checkbox_rect.width(),
            checkbox_rect.height()
        )
        opt.rect = checkbox_point
        
        style.drawPrimitive(QStyle.PE_IndicatorViewItemCheck, opt, painter, opt.widget)

    def editorEvent(self, event, model, option, index):
        """Handle checkbox toggle events."""
        flags = model.flags(index)
        if not (flags & Qt.ItemIsUserCheckable) or not (flags & Qt.ItemIsEnabled):
            return False

        value = index.data(Qt.CheckStateRole)
        if value is None:
            return False

        if event.type() in {QMouseEvent.MouseButtonRelease, QMouseEvent.MouseButtonDblClick}:
            if event.button() != Qt.LeftButton or \
                not self.checkboxRect(option).contains(event.pos()):
                return False
            if event.type() == QMouseEvent.MouseButtonDblClick:
                return True

            state = Qt.Unchecked if value == Qt.Checked else Qt.Checked
            return model.setData(index, state, Qt.CheckStateRole)

        return False

    def checkboxRect(self, option):
        """Get the checkbox rectangle."""
        opt = QStyleOptionViewItem(option)
        style = opt.widget.style()
        checkbox_rect = style.subElementRect(QStyle.SE_ViewItemCheckIndicator, opt, opt.widget)
        return QRect(
            opt.rect.center().x() - checkbox_rect.width() // 2,
            opt.rect.center().y() - checkbox_rect.height() // 2,
            checkbox_rect.width(),
            checkbox_rect.height()
        )
