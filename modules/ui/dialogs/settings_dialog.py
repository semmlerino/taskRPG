import os
import json
import logging
import base64
from typing import Dict, Optional, Tuple, List

from PyQt5.QtCore import Qt, QModelIndex, QAbstractTableModel, pyqtSignal, QByteArray, QMimeData, QRect
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QTableView, QHeaderView, QWidget, QCheckBox, QMessageBox,
    QSizePolicy, QItemDelegate, QStyledItemDelegate, QStyle,
    QStyleOptionViewItem
)
from PyQt5.QtGui import QFont, QColor, QCursor, QPalette

from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task
from modules.constants import DATA_DIR

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')


class TaskTableModel(QAbstractTableModel):
    """Custom table model for managing tasks with drag and drop support."""

    def __init__(self, tasks: Dict[str, Task], parent=None):
        """Initialize the model with tasks dictionary."""
        super().__init__(parent)
        self._tasks: List[Tuple[str, int, int, bool, bool, bool, Optional[str], int]] = []
        self._headers = ['Name', 'Min', 'Max', 'Active', 'Daily', 'Weekly', 'Description', 'Count']
        self._original_tasks = tasks
        self._drag_source_row = -1
        
        # Convert tasks dictionary to list while preserving all attributes
        for name, task in tasks.items():
            self._tasks.append((
                name,
                task.min_count,
                task.max_count,
                task.active,
                task.is_daily,
                task.is_weekly,
                task.description,
                task.count
            ))
        logging.debug(f"TaskTableModel initialized with {len(self._tasks)} tasks")

    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows in the model."""
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns in the model."""
        return len(self._headers)

    def flags(self, index):
        """Return item flags."""
        if not index.isValid():
            return Qt.ItemIsEnabled
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        
        # Make Name column editable
        if index.column() == 0:
            flags |= Qt.ItemIsEditable
            
        # Make Min/Max columns editable
        elif index.column() in [1, 2]:
            flags |= Qt.ItemIsEditable
            
        # Make Active, Daily, and Weekly columns checkable
        elif index.column() in [3, 4, 5]:
            flags |= Qt.ItemIsUserCheckable
            
        # Make Description and Count columns editable
        elif index.column() in [6, 7]:
            flags |= Qt.ItemIsEditable
            
        return flags

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Return data for the given role and section."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0:  # Name
                return self._tasks[row][0]
            elif col == 1:  # Min
                return self._tasks[row][1]
            elif col == 2:  # Max
                return self._tasks[row][2]
            elif col == 6:  # Description
                return self._tasks[row][6] or ""
            elif col == 7:  # Count
                return self._tasks[row][7]
            
        elif role == Qt.CheckStateRole:
            if col in [3, 4, 5]:  # Active, Daily, Weekly
                return Qt.Checked if self._tasks[row][col] else Qt.Unchecked

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
        """Set data for the given role and section."""
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()

        if role == Qt.EditRole:
            if col == 0:  # Name
                self._tasks[row] = (value, *self._tasks[row][1:])
            elif col in [1, 2]:  # Min, Max
                try:
                    value = int(value)
                    if value < 0:
                        return False
                    task_list = list(self._tasks[row])
                    task_list[col] = value
                    self._tasks[row] = tuple(task_list)
                except ValueError:
                    return False
            elif col == 6:  # Description
                task_list = list(self._tasks[row])
                task_list[6] = value
                self._tasks[row] = tuple(task_list)
            elif col == 7:  # Count
                try:
                    value = int(value)
                    if value < 0:
                        return False
                    task_list = list(self._tasks[row])
                    task_list[7] = value
                    self._tasks[row] = tuple(task_list)
                except ValueError:
                    return False
        elif role == Qt.CheckStateRole:
            if col in [3, 4, 5]:  # Active, Daily, Weekly
                task_list = list(self._tasks[row])
                task_list[col] = value == Qt.Checked
                self._tasks[row] = tuple(task_list)

        self.dataChanged.emit(index, index, [role])
        return True

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole) -> Optional[str]:
        """Return the header data for the given role and section."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-qabstractitemmodeldatalist']

    def mimeData(self, indexes):
        self._drag_source_row = indexes[0].row()
        return super().mimeData(indexes)

    def canDropMimeData(self, data, action, row, column, parent):
        """Check if drop is allowed."""
        try:
            if not data.hasFormat('application/x-qabstractitemmodeldatalist'):
                return False

            if action == Qt.IgnoreAction:
                return True

            # Get target row
            target_row = row if row != -1 else self.rowCount()
            if parent.isValid():
                target_row = parent.row()
                
            # Get source row
            try:
                source_row = self._drag_source_row
            except ValueError:
                return False
                
            # Validate rows
            if not (0 <= source_row < len(self._tasks)):
                return False
                
            if not (0 <= target_row <= len(self._tasks)):
                return False
                
            # Don't allow dropping onto itself
            if target_row == source_row or target_row == source_row + 1:
                return False
                
            logging.debug(f"Drop allowed from {source_row} to {target_row}")
            return True
            
        except Exception as e:
            logging.error(f"Error in canDropMimeData: {e}")
            return False

    def dropMimeData(self, data, action, row, column, parent):
        """Handle dropping of rows."""
        if not data.hasFormat('application/x-qabstractitemmodeldatalist'):
            return False

        if action == Qt.IgnoreAction:
            return True

        # Get the source row
        source_row = self._drag_source_row
        if source_row < 0:
            return False

        # Calculate target row
        target_row = parent.row() if parent.isValid() else row
        if target_row < 0:
            target_row = self.rowCount()

        # Adjust target row if moving down
        if target_row > source_row:
            target_row -= 1

        if source_row == target_row:
            return False

        # Move the task in the list
        self.beginMoveRows(QModelIndex(), source_row, source_row, QModelIndex(), target_row + (1 if target_row < source_row else 0))
        task = self._tasks.pop(source_row)
        self._tasks.insert(target_row, task)
        self.endMoveRows()

        return True

    def get_tasks_dict(self) -> Dict[str, Task]:
        """Convert internal list representation back to task dictionary."""
        return {
            task[0]: Task(
                name=task[0],
                min_count=task[1],
                max_count=task[2],
                active=task[3],
                is_daily=task[4],
                is_weekly=task[5],
                description=task[6],
                count=task[7]
            )
            for task in self._tasks
        }


class RowHoverDelegate(QStyledItemDelegate):
    """Delegate for handling row hover effects in task table."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = parent

    def paint(self, painter, option, index):
        """Paint the delegate with proper hover effects."""
        opt = QStyleOptionViewItem(option)
        view = self._view
        
        # Get base background color based on alternate rows
        if index.row() % 2:
            base_color = QColor("#EDF5FF")  # Alternate row color
        else:
            base_color = QColor("#FFFFFF")  # Regular row color
            
        # Fill with base color first
        painter.fillRect(option.rect, base_color)
        
        # Check if row is being hovered using mouse position
        mouse_pos = view.viewport().mapFromGlobal(QCursor.pos())
        row_being_hovered = view.rowAt(mouse_pos.y()) == index.row()
        
        # Apply hover effect if row is hovered and not selected
        if row_being_hovered and not (opt.state & QStyle.State_Selected):
            hover_color = QColor("#C2E0FF")  # Darker blue for better visibility
            painter.fillRect(option.rect, hover_color)
            
        # Handle selection state
        if opt.state & QStyle.State_Selected:
            select_color = QColor("#A7C7E7")
            painter.fillRect(option.rect, select_color)
            
        # Ensure consistent text coloring
        opt.palette.setColor(QPalette.Text, QColor("#2c456b"))
        opt.palette.setColor(QPalette.HighlightedText, QColor("#2c456b"))
        
        # Draw the actual item content
        QStyledItemDelegate.paint(self, painter, opt, index)


class CheckBoxCenterDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        return None  # Use default editor
        
    def paint(self, painter, option, index):
        if not index.isValid():
            return

        # Get the view and check for hover
        view = self.parent()
        mouse_pos = view.viewport().mapFromGlobal(QCursor.pos())
        row_being_hovered = view.rowAt(mouse_pos.y()) == index.row()
        
        # Paint background based on state
        opt = QStyleOptionViewItem(option)
        
        # Get base background color based on alternate rows
        if index.row() % 2:
            base_color = QColor("#EDF5FF")  # Alternate row color
        else:
            base_color = QColor("#FFFFFF")  # Regular row color
            
        # Fill with base color first
        painter.fillRect(opt.rect, base_color)
        
        # Apply hover effect if row is hovered and not selected
        if row_being_hovered and not (opt.state & QStyle.State_Selected):
            hover_color = QColor("#C2E0FF")  # Darker blue for better visibility
            painter.fillRect(opt.rect, hover_color)
            
        # Handle selection state
        if opt.state & QStyle.State_Selected:
            select_color = QColor("#A7C7E7")
            painter.fillRect(opt.rect, select_color)

        # Center the checkbox
        style = view.style()
        checkbox_rect = style.subElementRect(
            style.SE_CheckBoxIndicator, opt, view
        )
        
        # Calculate center position
        checkbox_rect.moveCenter(opt.rect.center())
        
        # Update the option rect to the centered position
        opt.rect = checkbox_rect
        
        # Set the state based on the checkbox value
        checked = index.data(Qt.CheckStateRole) == Qt.Checked
        opt.state |= style.State_On if checked else style.State_Off
            
        # Add hover and focus states
        if row_being_hovered:
            opt.state |= style.State_MouseOver
        if opt.state & style.State_HasFocus:
            opt.state |= style.State_HasFocus
        
        # Draw the checkbox
        style.drawPrimitive(
            style.PE_IndicatorCheckBox,
            opt,
            painter,
            view
        )

    def editorEvent(self, event, model, option, index):
        if not index.isValid():
            return False
            
        # Get checkbox rect
        style = self.parent().style()
        opt = QStyleOptionViewItem(option)
        checkbox_rect = style.subElementRect(
            style.SE_CheckBoxIndicator, opt, self.parent()
        )
        checkbox_rect.moveCenter(option.rect.center())
        
        # Handle mouse events
        if event.type() == event.MouseButtonRelease:
            if checkbox_rect.contains(event.pos()):
                current = index.data(Qt.CheckStateRole)
                newValue = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                return model.setData(index, newValue, Qt.CheckStateRole)
                
        return False


class SettingsDialog(QDialog):
    """Dialog for managing game settings and tasks."""

    def __init__(self, task_manager: TaskManager, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 400)
        self.task_manager = task_manager
        self.saved = False
        self.task_model = TaskTableModel(task_manager.tasks, self)

        # Ensure DATA_DIR exists
        os.makedirs(DATA_DIR, exist_ok=True)
        self.settings_file = os.path.join(DATA_DIR, 'settings.json')
        logging.info(f"Settings file path: {self.settings_file}")

        if parent:
            self.setWindowModality(Qt.WindowModal)

        # Load settings before initializing UI
        self.settings = self.load_saved_settings()
        self.init_ui()
        self.apply_window_settings()

    def load_saved_settings(self) -> dict:
        """Load settings from file."""
        try:
            logging.info(f"Attempting to load settings from: {self.settings_file}")

            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                logging.info(f"Successfully loaded settings: {settings}")
                return settings
            else:
                logging.warning(f"Settings file does not exist at: {self.settings_file}")
                return {}

        except Exception as e:
            logging.error(f"Error loading settings: {e}", exc_info=True)
            return {}

    def save_settings(self):
        """Save settings including window size and column widths."""
        try:
            if not self.validate_tasks():
                return

            # Save tasks first
            new_tasks = self.task_model.get_tasks_dict()
            self.task_manager.tasks = new_tasks
            if not self.task_manager.save_tasks():
                raise Exception("Failed to save tasks")

            # Get window geometry using base64 encoding
            window_geometry = self.saveGeometry().toBase64().data().decode('utf-8')
            logging.debug(f"Window geometry (base64): {window_geometry}")

            # Prepare settings dictionary
            settings = {
                'shake_animation': bool(self.shake_checkbox.isChecked()),
                'window_geometry': window_geometry,  # Encoded geometry
                'column_widths': [
                    int(self.task_view.columnWidth(i))
                    for i in range(self.task_view.model().columnCount())
                ]
            }

            logging.info(f"Preparing to save settings: {settings}")
            logging.info(f"Saving to file: {self.settings_file}")

            # Write settings to file
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)

            self.saved = True
            QMessageBox.information(self, "Settings Saved",
                "Settings have been saved successfully.")
            logging.info("Settings saved successfully")
            self.accept()

        except Exception as e:
            logging.error(f"Failed to save settings: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def apply_window_settings(self):
        """Apply window size and column settings."""
        try:
            # Apply window geometry
            if 'window_geometry' in self.settings:
                try:
                    window_geometry = self.settings['window_geometry']
                    geometry_bytes = QByteArray.fromBase64(window_geometry.encode('utf-8'))
                    if geometry_bytes:
                        self.restoreGeometry(geometry_bytes)
                        logging.info("Window geometry restored successfully")
                    else:
                        logging.warning("Failed to decode window geometry from settings")
                except Exception as e:
                    logging.error(f"Error restoring window geometry: {e}")
                    # Fall back to default size
                    self.resize(800, 600)

            # Apply column widths with validation
            if 'column_widths' in self.settings:
                try:
                    col_widths = self.settings['column_widths']
                    total_width = self.width() - 50  # Account for margins and scrollbar
                    
                    # Validate total width
                    current_total = sum(col_widths)
                    if current_total > total_width:
                        # Scale down proportionally
                        scale_factor = total_width / current_total
                        col_widths = [int(w * scale_factor) for w in col_widths]
                    
                    # Ensure minimum widths
                    min_widths = [100, 60, 60, 50, 50, 50, 150, 50]  # Minimum widths for each column
                    for i, (width, min_width) in enumerate(zip(col_widths, min_widths)):
                        if i < self.task_view.model().columnCount():
                            final_width = max(width, min_width)
                            self.task_view.setColumnWidth(i, final_width)
                            
                    logging.info(f"Applied adjusted column widths: {[self.task_view.columnWidth(i) for i in range(self.task_view.model().columnCount())]}")
                except Exception as e:
                    logging.error(f"Error applying column widths: {e}")
                    # Set default column widths
                    default_widths = [200, 80, 80, 80, 80, 80, 200, 80]
                    for i, width in enumerate(default_widths):
                        if i < self.task_view.model().columnCount():
                            self.task_view.setColumnWidth(i, width)

        except Exception as e:
            logging.error(f"Error applying window settings: {e}", exc_info=True)
            # Ensure window has a reasonable size
            self.resize(800, 600)

    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        try:
            # Adjust column widths on resize
            if hasattr(self, 'task_view'):
                total_width = self.task_view.width() - 50  # Account for margins and scrollbar
                if total_width > 0:
                    # Get current widths
                    col_widths = [self.task_view.columnWidth(i) 
                                for i in range(self.task_view.model().columnCount())]
                    current_total = sum(col_widths)
                    
                    if current_total > total_width:
                        # Scale down proportionally
                        scale_factor = total_width / current_total
                        for i, width in enumerate(col_widths):
                            new_width = max(int(width * scale_factor), 
                                         [100, 60, 60, 50, 50, 50, 150, 50][i])  # Minimum widths
                            self.task_view.setColumnWidth(i, new_width)
        except Exception as e:
            logging.error(f"Error in resizeEvent: {e}")

    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Task RPG Settings")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.task_view = QTableView()
        self.task_view.setSelectionMode(QTableView.SingleSelection)
        self.task_view.setSelectionBehavior(QTableView.SelectRows)
        self.task_view.setAlternatingRowColors(True)
        self.task_view.setDragEnabled(True)
        self.task_view.setAcceptDrops(True)
        self.task_view.setDragDropMode(QTableView.InternalMove)
        self.task_view.setDropIndicatorShown(True)
        self.task_view.setShowGrid(True)
        self.task_view.horizontalHeader().setHighlightSections(False)
        
        # Set the drag drop overlay mode to always show between items
        self.task_view.setDragDropOverwriteMode(False)
        
        # Updated stylesheet without competing hover effects
        self.task_view.setStyleSheet("""
            QTableView {
                selection-background-color: #A7C7E7;
                selection-color: #2c456b;
                alternate-background-color: #EDF5FF;
                background-color: white;
                font-size: 13pt;
                gridline-color: #D0D0D0;
            }
            QTableView::item {
                border: none;
                padding: 5px;
                color: #2c456b;
            }
            QTableView::item:selected {
                background-color: #A7C7E7;
                color: #2c456b;
            }
            QTableView::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #BDBDBD;
                border-radius: 4px;
                background-color: white;
            }
            QTableView::indicator:hover {
                border-color: #2196F3;
                background-color: #E3F2FD;
            }
            QTableView::indicator:checked {
                background-color: #2196F3;
                border: 2px solid #2196F3;
                border-radius: 4px;
            }
            QTableView::indicator:checked:hover {
                background-color: #1976D2;
                border-color: #1976D2;
            }
            QTableView::indicator:unchecked:hover {
                border-color: #2196F3;
                background-color: #E3F2FD;
            }
        """)
        
        # Set up the model and delegate
        self.task_model = TaskTableModel(self.task_manager.tasks, self)
        self.task_view.setModel(self.task_model)
        
        # Set custom delegate for row hover effect
        hover_delegate = RowHoverDelegate(self.task_view)
        self.task_view.setItemDelegate(hover_delegate)
        
        # Enable mouse tracking for hover effects
        self.task_view.setMouseTracking(True)
        
        # Set up the header
        header = self.task_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)  # Changed to False to show all columns
        
        # Set column widths and alignment
        self.task_view.setColumnWidth(0, 200)  # Name
        self.task_view.setColumnWidth(1, 60)   # Min
        self.task_view.setColumnWidth(2, 60)   # Max
        self.task_view.setColumnWidth(3, 100)  # Active
        self.task_view.setColumnWidth(4, 100)  # Daily
        self.task_view.setColumnWidth(5, 100)  # Weekly
        self.task_view.setColumnWidth(6, 200)  # Description
        self.task_view.setColumnWidth(7, 80)   # Count

        # Center align checkboxes and numeric columns
        for col in [1, 2, 3, 4, 5, 7]:  # Min, Max, Active, Daily, Weekly, Count
            self.task_model.setHeaderData(col, Qt.Horizontal, Qt.AlignCenter, Qt.TextAlignmentRole)
            if col in [3, 4, 5]:  # Only checkboxes
                self.task_view.setItemDelegateForColumn(col, CheckBoxCenterDelegate(self.task_view))
        
        header.setStyleSheet("""
            QHeaderView::section {
                padding: 6px;
                background-color: #A7C7E7;
                color: #2c456b;
                border: 1px solid #2c456b;
                font-weight: bold;
            }
        """)
            
        # Set vertical header (row numbers)
        vertical_header = self.task_view.verticalHeader()
        vertical_header.setDefaultSectionSize(40)  # Increase row height
        vertical_header.setStyleSheet("""
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 4px;
                border: 1px solid #E0E0E0;
            }
        """)
            
        layout.addWidget(self.task_view)

        # Task Management Buttons
        button_layout = QHBoxLayout()

        # Add Task Button
        add_button = QPushButton("Add Task")
        add_button.setFont(QFont("Arial", 13))
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #BDECC4;
                color: #2E7D32;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #A5D6A7; }
            QPushButton:pressed { background-color: #C8E6C9; }
        """)
        add_button.clicked.connect(self.add_task)
        button_layout.addWidget(add_button)

        # Remove Task Button
        remove_button = QPushButton("Remove Selected")
        remove_button.setFont(QFont("Arial", 13))
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #FFD7D9;
                color: #C62828;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #FFCDD2; }
            QPushButton:pressed { background-color: #FFEBEE; }
        """)
        remove_button.clicked.connect(self.remove_task)
        button_layout.addWidget(remove_button)

        layout.addLayout(button_layout)

        # Game Settings Section
        settings_label = QLabel("Game Settings:")
        settings_label.setFont(QFont("Arial", 16))
        layout.addWidget(settings_label)

        # Shake Animation Toggle
        self.shake_checkbox = QCheckBox("Enable Shaking Animation")
        self.shake_checkbox.setFont(QFont("Arial", 13))
        self.shake_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 10px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #BDBDBD;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #2196F3;
                background-color: #E3F2FD;
            }
            QCheckBox::indicator:checked {
                background-color: #90CAF9;
                border: 2px solid #90CAF9;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #64B5F6;
                border-color: #64B5F6;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #2196F3;
                background-color: #E3F2FD;
            }
        """)
        self.load_shaking_setting()
        layout.addWidget(self.shake_checkbox)

        # Bottom buttons
        dialog_buttons = QHBoxLayout()

        # Save Button
        save_button = QPushButton("Save Changes")
        save_button.setFont(QFont("Arial", 13))
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #D6EAFF;
                color: #1565C0;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #BBDEFB; }
            QPushButton:pressed { background-color: #E3F2FD; }
        """)
        save_button.clicked.connect(self.save_settings)
        dialog_buttons.addWidget(save_button)

        # Cancel Button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 13))
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #EDF2F7;
                color: #4A5568;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
            QPushButton:pressed { background-color: #F7FAFC; }
        """)
        cancel_button.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_button)

        layout.addLayout(dialog_buttons)
        
        self.setLayout(layout)

    def add_task(self):
        """Add a new task."""
        try:
            row_count = self.task_model.rowCount()
            new_task_name = f"Task_{row_count + 1}"

            # Ensure unique name
            counter = 1
            base_name = new_task_name
            while any(task[0] == new_task_name for task in self.task_model._tasks):
                new_task_name = f"{base_name}_{counter}"
                counter += 1

            # Add new task
            self.task_model.beginInsertRows(QModelIndex(), row_count, row_count)
            self.task_model._tasks.append((
                new_task_name,   # name
                1,              # min_count
                3,              # max_count
                True,           # active
                False,          # is_daily
                False,          # is_weekly
                "",             # description
                0               # count
            ))
            self.task_model.endInsertRows()

            # Select the new task
            index = self.task_model.index(row_count, 0)
            self.task_view.setCurrentIndex(index)
            self.task_view.edit(index)  # Start editing the name

            logging.info(f"Added new task: {new_task_name}")

        except Exception as e:
            logging.error(f"Error adding task: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add task: {str(e)}")

    def remove_task(self):
        """Remove selected task."""
        try:
            indexes = self.task_view.selectedIndexes()
            if not indexes:
                QMessageBox.warning(self, "No Selection", "Please select a task to remove.")
                return

            row = indexes[0].row()
            task_name = self.task_model._tasks[row][0]

            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Are you sure you want to remove task '{task_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.task_model.beginRemoveRows(QModelIndex(), row, row)
                del self.task_model._tasks[row]
                self.task_model.endRemoveRows()
                logging.info(f"Removed task: {task_name}")

        except Exception as e:
            logging.error(f"Error removing task: {e}")
            QMessageBox.critical(self, "Error", f"Failed to remove task: {str(e)}")

    def load_shaking_setting(self):
        """Load shake animation setting from settings file."""
        try:
            settings_file = os.path.join(DATA_DIR, 'settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)
                self.shake_checkbox.setChecked(shake_enabled)
                logging.debug(f"Loaded shake animation setting: {shake_enabled}")
            else:
                self.shake_checkbox.setChecked(True)  # Default to enabled
                logging.debug("No settings file found, defaulting shake animation to enabled")

        except Exception as e:
            logging.error(f"Error loading shake setting: {e}")
            self.shake_checkbox.setChecked(True)  # Default to enabled on error

    def validate_tasks(self) -> bool:
        """Validate all tasks before saving."""
        tasks = self.task_model._tasks
        seen_names = set()

        for i, (name, min_count, max_count, active, is_daily, is_weekly, _, _) in enumerate(tasks):
            # Check for empty names
            if not name.strip():
                QMessageBox.warning(self, "Invalid Task",
                    f"Task name in row {i + 1} cannot be empty.")
                return False

            # Check for duplicate names
            if name in seen_names:
                QMessageBox.warning(self, "Invalid Task",
                    f"Task name '{name}' is duplicated.")
                return False
            seen_names.add(name)

            # Validate min/max values
            if min_count < 1:
                QMessageBox.warning(self, "Invalid Task",
                    f"Minimum value for task '{name}' must be at least 1.")
                return False

            if max_count < min_count:
                QMessageBox.warning(self, "Invalid Task",
                    f"Maximum value for task '{name}' must be greater than or equal to minimum.")
                return False

        return True

    def closeEvent(self, event):
        """Handle dialog close event."""
        try:
            if not self.saved:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "You have unsaved changes. Do you want to save them?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )

                if reply == QMessageBox.Save:
                    self.save_settings()
                    if self.saved:  # Only accept if save was successful
                        event.accept()
                    else:
                        event.ignore()
                elif reply == QMessageBox.Cancel:
                    event.ignore()
                else:  # Discard
                    event.accept()
            else:
                event.accept()
        except Exception as e:
            logging.error(f"Error in closeEvent: {e}")
            event.accept()  # Accept the close event even if there's an error
