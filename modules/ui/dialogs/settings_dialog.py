import os
import json
import logging
import base64
from typing import Dict, Optional, Tuple, List

from PyQt5.QtCore import Qt, QModelIndex, QAbstractTableModel, pyqtSignal, QByteArray, QMimeData
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QTableView, QHeaderView, QWidget, QCheckBox, QMessageBox,
    QSizePolicy
)
from PyQt5.QtGui import QFont, QColor

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
        self._tasks: List[Tuple[str, int, int, bool, Optional[str]]] = []
        self._headers = ['Name', 'Min', 'Max', 'Active']
        self._original_tasks = tasks
        self._drag_source_row = -1
        self._drag_in_progress = False
        
        # Convert tasks dictionary to list while preserving all attributes
        for name, task in tasks.items():
            self._tasks.append((
                name,
                task.min_count,
                task.max_count,
                task.active,
                task.description
            ))
        logging.debug(f"TaskTableModel initialized with {len(self._tasks)} tasks")

    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows in the model."""
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns in the model."""
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Optional[str]:
        """Return the data for the given role at the specified index."""
        if not index.isValid():
            return None

        row, col = index.row(), index.column()

        if role == Qt.DisplayRole:
            if col < 3:  # Name, Min, Max columns
                return str(self._tasks[row][col])
            return None

        elif role == Qt.CheckStateRole and col == 3:  # Active column
            return Qt.Checked if self._tasks[row][3] else Qt.Unchecked

        elif role == Qt.TextAlignmentRole:
            if col in [1, 2, 3]:  # Min/Max/Active columns
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
        """Set the data at the specified index."""
        if not index.isValid():
            return False

        row, col = index.row(), index.column()

        try:
            if col == 3 and role == Qt.CheckStateRole:  # Handle checkbox changes
                task_data = list(self._tasks[row])
                task_data[3] = bool(value == Qt.Checked)
                self._tasks[row] = tuple(task_data)
                self.dataChanged.emit(index, index)
                logging.debug(f"Checkbox state changed for task {task_data[0]}: {task_data[3]}")
                return True

            elif role == Qt.EditRole and col < 3:  # Handle other edits
                task_data = list(self._tasks[row])
                if col == 0:  # Name column
                    new_name = str(value).strip()
                    if not new_name or (new_name != task_data[0] and 
                                      any(t[0] == new_name for t in self._tasks)):
                        return False
                    task_data[col] = new_name
                else:  # Min/Max columns
                    try:
                        val = int(value)
                        if val < 1:
                            return False
                        if col == 1 and val > task_data[2]:  # Min > Max
                            return False
                        if col == 2 and val < task_data[1]:  # Max < Min
                            return False
                        task_data[col] = val
                    except ValueError:
                        return False

                self._tasks[row] = tuple(task_data)
                self.dataChanged.emit(index, index)
                return True

            return False

        except Exception as e:
            logging.error(f"Error setting data: {e}")
            return False

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole) -> Optional[str]:
        """Return the header data for the given role and section."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def flags(self, index):
        """Set flags to enable drag and drop."""
        if not index.isValid():
            return Qt.ItemIsDropEnabled

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        
        if index.column() == 3:  # Active column
            flags |= Qt.ItemIsUserCheckable
        else:
            flags |= Qt.ItemIsEditable
            
        return flags

    def supportedDropActions(self):
        """Specify supported drop actions."""
        return Qt.MoveAction

    def mimeTypes(self):
        """Return supported mime types."""
        return ['text/plain']

    def mimeData(self, indexes):
        """Create mime data for drag operation."""
        try:
            if not indexes:
                return None
                
            row = indexes[0].row()
            if not (0 <= row < len(self._tasks)):
                return None
                
            self._drag_source_row = row
            self._drag_in_progress = True
            
            mime = QMimeData()
            mime.setText(str(row))
            logging.debug(f"Starting drag from row {row}")
            return mime
            
        except Exception as e:
            logging.error(f"Error in mimeData: {e}")
            self._resetDragState()
            return None

    def _resetDragState(self):
        """Reset drag and drop state."""
        self._drag_source_row = -1
        self._drag_in_progress = False
        logging.debug("Reset drag state")

    def canDropMimeData(self, data, action, row, column, parent):
        """Check if drop is allowed."""
        try:
            if not self._drag_in_progress:
                return False

            if not data.hasText():
                return False
            
            if action == Qt.IgnoreAction:
                return True

            # Get target row
            target_row = row if row != -1 else self.rowCount()
            if parent.isValid():
                target_row = parent.row()
                
            # Get source row
            try:
                source_row = int(data.text())
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
        """Handle drop event."""
        try:
            if not self._drag_in_progress or not data.hasText():
                return False

            # Get source row
            try:
                source_row = int(data.text())
            except ValueError:
                return False

            if not (0 <= source_row < len(self._tasks)):
                return False

            # Get target row
            target_row = row if row != -1 else self.rowCount()
            if parent.isValid():
                target_row = parent.row()

            # Validate target row
            if not (0 <= target_row <= len(self._tasks)):
                target_row = len(self._tasks)

            # Don't move to same position
            if target_row == source_row or target_row == source_row + 1:
                return False

            # Adjust target row if moving down
            if target_row > source_row:
                target_row -= 1

            logging.debug(f"Moving row {source_row} to {target_row}")

            try:
                # Begin move operation
                self.beginMoveRows(QModelIndex(), source_row, source_row, 
                                 QModelIndex(), target_row)
                
                # Perform the move
                item = self._tasks.pop(source_row)
                self._tasks.insert(target_row, item)
                
                self.endMoveRows()
                logging.debug(f"Successfully moved row from {source_row} to {target_row}")
                return True

            except Exception as e:
                logging.error(f"Error during move operation: {e}")
                return False

        except Exception as e:
            logging.error(f"Error in dropMimeData: {e}")
            return False
            
        finally:
            self._resetDragState()

    def get_tasks_dict(self) -> Dict[str, Task]:
        """Convert internal list representation back to task dictionary."""
        try:
            tasks_dict = {}
            for name, min_count, max_count, active, description in self._tasks:
                tasks_dict[name] = Task(
                    name=name,
                    min_count=min_count,
                    max_count=max_count,
                    active=active,
                    description=description
                )
            return tasks_dict
        except Exception as e:
            logging.error(f"Error converting to tasks dictionary: {e}")
            raise


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
                    min_widths = [100, 60, 60, 50]  # Minimum widths for each column
                    for i, (width, min_width) in enumerate(zip(col_widths, min_widths)):
                        if i < self.task_view.model().columnCount():
                            final_width = max(width, min_width)
                            self.task_view.setColumnWidth(i, final_width)
                            
                    logging.info(f"Applied adjusted column widths: {[self.task_view.columnWidth(i) for i in range(self.task_view.model().columnCount())]}")
                except Exception as e:
                    logging.error(f"Error applying column widths: {e}")
                    # Set default column widths
                    default_widths = [200, 80, 80, 80]
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
                                         [100, 60, 60, 50][i])  # Minimum widths
                            self.task_view.setColumnWidth(i, new_width)
        except Exception as e:
            logging.error(f"Error in resizeEvent: {e}")

    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title - increased from 16 to 18
        title_label = QLabel("Task RPG Settings")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Task Editing Section - increased from 14 to 16
        task_label = QLabel("Manage Tasks:")
        task_label.setFont(QFont("Arial", 16))
        layout.addWidget(task_label)

        self.task_view = QTableView()
        self.task_view.setSelectionMode(QTableView.SingleSelection)
        self.task_view.setSelectionBehavior(QTableView.SelectRows)
        self.task_view.setDragEnabled(True)
        self.task_view.setAcceptDrops(True)
        self.task_view.setDragDropMode(QTableView.InternalMove)
        self.task_view.setDropIndicatorShown(True)
        self.task_view.setShowGrid(True)
        self.task_view.setAlternatingRowColors(True)
        
        # Set the drag drop overlay mode to always show between items
        self.task_view.setDragDropOverwriteMode(False)
        
        # Style the view to make drop indicator more visible
        self.task_view.setStyleSheet("""
            QTableView {
                selection-background-color: #E3F2FD;
                selection-color: black;
                alternate-background-color: #FAFAFA;
                background-color: white;
            }
            QTableView::item:selected {
                background-color: #E3F2FD;
            }
            QTableView::item:hover {
                background-color: #F5F5F5;
            }
            QTableView::indicator {
                width: 20px;
                height: 20px;
            }
            QTableView::indicator:checked {
                background-color: #2196F3;
                border: 2px solid #2196F3;
                border-radius: 4px;
            }
            QTableView::indicator:unchecked {
                background-color: white;
                border: 2px solid #BDBDBD;
                border-radius: 4px;
            }
        """)
        
        # Set up the model
        self.task_model = TaskTableModel(self.task_manager.tasks, self)
        self.task_view.setModel(self.task_model)
            
        # Set up the header
        header = self.task_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 4px;
                border: 1px solid #E0E0E0;
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

        # Add Task Button - increased from 12 to 13
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

        # Remove Task Button - increased from 12 to 13
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

        # Game Settings Section - increased from 14 to 16
        settings_label = QLabel("Game Settings:")
        settings_label.setFont(QFont("Arial", 16))
        layout.addWidget(settings_label)

        # Shake Animation Toggle - increased from 12 to 13
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
            }
            QCheckBox::indicator:unchecked {
                background-color: white;
                border: 2px solid #BDBDBD;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #90CAF9;
                border: 2px solid #90CAF9;
                border-radius: 4px;
            }
            QCheckBox::indicator:hover {
                border-color: #64B5F6;
            }
        """)
        self.load_shaking_setting()
        layout.addWidget(self.shake_checkbox)

        # Bottom buttons - increased from 12 to 13
        dialog_buttons = QHBoxLayout()

        # Save Button - increased from 12 to 13
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

        # Cancel Button - increased from 12 to 13
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
                ""              # description
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

        for i, (name, min_count, max_count, active, _) in enumerate(tasks):
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
