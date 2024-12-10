"""Custom delegates for the settings dialog."""
from PyQt5.QtCore import Qt, QRect, QEvent, QPoint
from PyQt5.QtWidgets import (
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt5.QtGui import QColor, QPainter, QPen, QPolygon

class CheckBoxHoverDelegate(QStyledItemDelegate):
    """Delegate for handling both hover effects and checkboxes in task table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = parent

    def paint(self, painter, option, index):
        """Paint the delegate with hover effects and checkboxes."""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Draw hover effect for the entire row
        is_hovering = opt.state & QStyle.State_MouseOver
        if is_hovering:
            # Get the view and the row rect
            view = self._view
            row_rect = QRect(0, opt.rect.y(), view.viewport().width(), opt.rect.height())
            painter.save()
            
            # Create gradient effect for hover
            if index.row() % 2 == 0:
                # Normal row
                hover_color = QColor("#2196F3")  # Material Blue
            else:
                # Alternate row
                hover_color = QColor("#1E88E5")  # Slightly darker blue
                
            hover_color.setAlpha(40)  # Very transparent base layer
            painter.fillRect(row_rect, hover_color)
            
            # Add a second layer for more intensity
            hover_color.setAlpha(20)
            painter.fillRect(row_rect, hover_color)
            
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
            
            # Draw custom checkbox
            painter.save()
            if value == Qt.Checked:
                # Checked state
                if is_hovering:
                    bg_color = QColor("#1976D2")  # Darker blue on hover
                    border_color = QColor("#1565C0")  # Even darker blue for border
                else:
                    bg_color = QColor("#2196F3")  # Normal blue
                    border_color = QColor("#1E88E5")  # Slightly darker blue for border
            else:
                # Unchecked state
                if is_hovering:
                    bg_color = QColor("#90CAF9")  # Light blue on hover
                    border_color = QColor("#2196F3")  # Blue border
                else:
                    bg_color = QColor("white")
                    border_color = QColor("#BDBDBD")  # Gray border
            
            # Draw checkbox with rounded corners
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(border_color)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(checkbox_point, 4, 4)
            
            # Draw checkmark if checked
            if value == Qt.Checked:
                painter.setPen(QPen(QColor("white"), 2))
                # Calculate checkmark points
                x1 = checkbox_point.left() + 4
                y1 = checkbox_point.center().y()
                x2 = checkbox_point.center().x() - 2
                y2 = checkbox_point.bottom() - 4
                x3 = checkbox_point.right() - 4
                y3 = checkbox_point.top() + 4
                
                # Draw checkmark
                painter.drawLine(x1, y1, x2, y2)
                painter.drawLine(x2, y2, x3, y3)
            
            painter.restore()
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
