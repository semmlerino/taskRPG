"""Task table model for the settings dialog."""
import logging
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import (
    Qt, QModelIndex, QAbstractTableModel, QByteArray, QMimeData
)
import time
from modules.tasks.task import Task

class TaskTableModel(QAbstractTableModel):
    """Custom table model for managing tasks with drag and drop support."""

    def __init__(self, tasks: Dict[str, Task], parent=None):
        """Initialize the model with tasks dictionary."""
        super().__init__(parent)
        self._tasks: List[Tuple[str, int, int, bool, bool, bool, int]] = []
        self._headers = ['Name', 'Min', 'Max', 'Active', 'Daily', 'Weekly', 'Count']
        self._original_tasks = tasks
        self._drag_source_row = -1
        
        # Convert tasks dictionary to list while preserving all attributes
        for name, task in tasks.items():
            # Skip muted tasks
            if task.muted_until and time.time() < task.muted_until:
                continue
                
            self._tasks.append((
                name,
                task.min_count,
                task.max_count,
                task.active,
                task.is_daily,
                task.is_weekly,
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
            
        # Make Count column editable
        elif index.column() == 6:
            flags |= Qt.ItemIsEditable
            
        return flags

    def data(self, index, role=Qt.DisplayRole):
        """Return data for the specified role."""
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            row = index.row()
            col = index.column()
            if row < 0 or row >= len(self._tasks):
                return None
            
            value = self._tasks[row][col]
            if col in (3, 4, 5):  # Active, Daily, Weekly columns
                return "Yes" if value else "No"
            return str(value)

        elif role == Qt.CheckStateRole:
            if index.column() in (3, 4, 5):  # Active, Daily, Weekly columns
                return Qt.Checked if self._tasks[index.row()][index.column()] else Qt.Unchecked

        return None

    def setData(self, index, value, role=Qt.EditRole):
        """Set data for the given role and section."""
        if not index.isValid():
            return False
            
        row = index.row()
        col = index.column()
        
        try:
            # Get the current task name before any changes
            current_task_name = self._tasks[row][0]
            current_task = self._original_tasks.get(current_task_name)
            
            if role == Qt.EditRole:
                if col == 0:  # Name
                    # Ensure value is a string and not empty
                    if not isinstance(value, str) or not value.strip():
                        return False
                    
                    # If renaming, update the original tasks reference
                    if current_task and value != current_task_name:
                        # Check if new name already exists
                        if value in self._original_tasks:
                            return False
                            
                        # Create a copy of the original task with the new name
                        self._original_tasks[value] = Task(
                            name=value,
                            min_count=current_task.min_count,
                            max_count=current_task.max_count,
                            active=current_task.active,
                            is_daily=current_task.is_daily,
                            is_weekly=current_task.is_weekly,
                            count=current_task.count
                        )
                        # Remove the old task reference
                        del self._original_tasks[current_task_name]
                    
                    # Update the task name in the list
                    self._tasks[row] = (value, *self._tasks[row][1:])
                elif col == 1:  # Min
                    value = max(1, int(value))
                    self._tasks[row] = (*self._tasks[row][:1], value, *self._tasks[row][2:])
                    if current_task:
                        current_task.min_count = value
                elif col == 2:  # Max
                    value = max(self._tasks[row][1], int(value))
                    self._tasks[row] = (*self._tasks[row][:2], value, *self._tasks[row][3:])
                    if current_task:
                        current_task.max_count = value
                elif col == 6:  # Count
                    value = max(0, int(value))
                    self._tasks[row] = (*self._tasks[row][:6], value)
                    if current_task:
                        current_task.count = value
                    
            elif role == Qt.CheckStateRole:
                value = bool(value == Qt.Checked)
                if col == 3:  # Active
                    self._tasks[row] = (*self._tasks[row][:3], value, *self._tasks[row][4:])
                    if current_task:
                        current_task.active = value
                elif col == 4:  # Daily
                    if value and self._tasks[row][5]:  # If setting daily and weekly is true
                        self._tasks[row] = (*self._tasks[row][:4], value, False, *self._tasks[row][6:])
                        if current_task:
                            current_task.is_daily = value
                            current_task.is_weekly = False
                    else:
                        self._tasks[row] = (*self._tasks[row][:4], value, *self._tasks[row][5:])
                        if current_task:
                            current_task.is_daily = value
                elif col == 5:  # Weekly
                    if value and self._tasks[row][4]:  # If setting weekly and daily is true
                        self._tasks[row] = (*self._tasks[row][:4], False, value, *self._tasks[row][6:])
                        if current_task:
                            current_task.is_daily = False
                            current_task.is_weekly = value
                    else:
                        self._tasks[row] = (*self._tasks[row][:5], value, *self._tasks[row][6:])
                        if current_task:
                            current_task.is_weekly = value
                        
            self.dataChanged.emit(index, index)
            return True
            
        except (ValueError, IndexError) as e:
            logging.error(f"Error setting data: {e}")
            return False

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        """Return the header data for the given role and section."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def supportedDropActions(self):
        """Return supported drop actions."""
        return Qt.MoveAction

    def mimeTypes(self):
        """Return supported mime types."""
        return ['application/x-taskrow']

    def mimeData(self, indexes):
        """Create mime data for drag operation."""
        if not indexes:
            return None
            
        mime_data = QMimeData()
        encoded_data = QByteArray()
        
        # Store the source row
        self._drag_source_row = indexes[0].row()
        encoded_data.setNum(self._drag_source_row)
        
        mime_data.setData('application/x-taskrow', encoded_data)
        return mime_data

    def canDropMimeData(self, data, action, row, column, parent):
        """Check if drop is allowed."""
        if not data or not data.hasFormat('application/x-taskrow'):
            return False
            
        if action != Qt.MoveAction:
            return False
            
        return True

    def dropMimeData(self, data, action, row, column, parent):
        """Handle dropping of rows."""
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
            
        if action == Qt.IgnoreAction:
            return True
            
        source_row = int(data.data('application/x-taskrow').toInt()[0])
        
        if row == -1:
            row = parent.row()
        
        # Adjust target row if moving down
        if row > source_row:
            row -= 1
            
        if row == source_row:
            return False
            
        # Move the task in view model
        self.beginMoveRows(QModelIndex(), source_row, source_row,
                          QModelIndex(), row + (1 if row > source_row else 0))
        task = self._tasks.pop(source_row)
        self._tasks.insert(row, task)
        self.endMoveRows()
        
        # Update task order in original tasks
        # We'll create a new ordered dictionary to preserve the new order
        ordered_tasks = {}
        for task_data in self._tasks:
            task_name = task_data[0]
            if task_name in self._original_tasks:
                ordered_tasks[task_name] = self._original_tasks[task_name]
        self._original_tasks.clear()
        self._original_tasks.update(ordered_tasks)
        
        return True

    def get_tasks(self) -> Dict[str, Task]:
        """Get tasks as dictionary for saving."""
        tasks = {}
        
        # Include all tasks from original tasks, not just visible ones
        for task_name, task in self._original_tasks.items():
            if task_name in tasks:
                continue
                
            # Update task with current values if it's in the table
            for task_data in self._tasks:
                if task_data[0] == task_name:
                    task.min_count = task_data[1]
                    task.max_count = task_data[2]
                    task.active = task_data[3]
                    task.is_daily = task_data[4]
                    task.is_weekly = task_data[5]
                    task.count = task_data[6]
                    break
                    
            tasks[task_name] = task
            
        return tasks
