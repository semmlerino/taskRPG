import os
import json
import logging
import sys
from typing import Dict

from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QWidget, QCheckBox, QApplication
)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QPoint
from PyQt5.QtGui import QFont, QDrag, QPainter, QPen, QCursor

# Assuming TaskManager and Task are defined in these modules
# from modules.tasks.task_manager import TaskManager
# from modules.tasks.task import Task

# For demonstration purposes, we'll define mock Task and TaskManager classes
class Task:
    def __init__(self, name, min_count, max_count, active, description=""):
        self.name = name
        self.min_count = min_count
        self.max_count = max_count
        self.active = active
        self.description = description

class TaskManager:
    def __init__(self, filepath='tasks.json'):
        self.filepath = filepath
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for task_data in data.get('tasks', []):
                    task = Task(
                        name=task_data['name'],
                        min_count=task_data['min_count'],
                        max_count=task_data['max_count'],
                        active=task_data['active'],
                        description=task_data.get('description', "")
                    )
                    self.tasks[task.name] = task

    def save_tasks(self) -> bool:
        try:
            data = {
                'tasks': [
                    {
                        'name': task.name,
                        'min_count': task.min_count,
                        'max_count': task.max_count,
                        'active': task.active,
                        'description': task.description
                    }
                    for task in self.tasks.values()
                ]
            }
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logging.debug("Tasks saved successfully.")
            return True
        except Exception as e:
            logging.exception("Failed to save tasks.")
            return False

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all levels of log messages
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("settings_dialog.log"),
        logging.StreamHandler()
    ]
)

def exception_hook(exctype, value, tb):
    """Global exception handler to log uncaught exceptions."""
    logging.critical("Unhandled exception occurred!", exc_info=(exctype, value, tb))
    # Show a QMessageBox to inform the user
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(None, "Critical Error", f"An unexpected error occurred:\n{value}")
    sys.exit(1)

sys.excepthook = exception_hook

class TaskTable(QTableWidget):
    """Custom table widget for handling task reordering with improved drag and drop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
            }
        """)
        self.source_row = None
        logging.debug("TaskTable initialized")

    def startDrag(self, supportedActions):
        """Start drag operation."""
        try:
            self.source_row = self.currentRow()
            logging.debug(f"Starting drag from row: {self.source_row}")
            super().startDrag(supportedActions)
        except Exception as e:
            logging.exception("Exception in startDrag")
            self.source_row = None

    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        event.accept()
        logging.debug("Drag enter accepted")

    def dragMoveEvent(self, event):
        """Handle drag move event."""
        event.accept()

    def dropEvent(self, event):
        """Handle drop event for row reordering."""
        try:
            target_row = self.rowAt(event.pos().y())
            if target_row == -1:
                target_row = self.rowCount()

            source_row = self.source_row
            if source_row is None or target_row == source_row:
                logging.debug("Invalid drop operation.")
                event.ignore()
                return

            # Adjust target row index if necessary
            if target_row > source_row:
                target_row -= 1

            # Extract items and widgets from the source row
            items = []
            widgets = []
            for column in range(self.columnCount()):
                item = self.takeItem(source_row, column)
                items.append(item)
                widget = self.cellWidget(source_row, column)
                if widget is not None:
                    # Remove the widget from the cell to prevent it from being deleted
                    self.removeCellWidget(source_row, column)
                widgets.append(widget)

            # Remove the source row
            self.removeRow(source_row)

            # Insert a new row at the target position
            self.insertRow(target_row)

            # Place the items and widgets into the new row
            for column, item in enumerate(items):
                if item is not None:
                    self.setItem(target_row, column, item)
            for column, widget in enumerate(widgets):
                if widget is not None:
                    self.setCellWidget(target_row, column, widget)

            self.setCurrentCell(target_row, 0)
            logging.debug(f"Successfully moved row from {source_row} to {target_row}")

            # Update parent's data structures
            if hasattr(self.parent(), 'save_current_table_state'):
                self.parent().save_current_table_state()
                if hasattr(self.parent(), 'save_settings'):
                    self.parent().save_settings(quiet=True)

            event.accept()
        except Exception as e:
            logging.exception("Exception in dropEvent")
            event.ignore()
        finally:
            self.source_row = None

    def mimeTypes(self):
        """Return supported mime types."""
        return ['application/x-qabstractitemmodeldatalist']

    def supportedDropActions(self):
        """Return supported drop actions."""
        return Qt.MoveAction

class SettingsDialog(QDialog):
    """Dialog for managing game settings and tasks."""

    def __init__(self, task_manager: TaskManager, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(600, 500)
        self.task_manager = task_manager
        self.saved = False
        self.updated_tasks = {k: v for k, v in task_manager.tasks.items()}
        self.task_order = list(self.updated_tasks.keys())
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        logging.debug("Initializing UI components.")
        try:
            # Main layout
            layout = QVBoxLayout()

            # Task Editing Section
            task_label = QLabel("Edit Tasks:")
            task_label.setFont(QFont("Arial", 14, QFont.Bold))
            layout.addWidget(task_label)

            # Task table
            self.task_table = TaskTable(self)
            self.task_table.setColumnCount(4)
            self.task_table.setHorizontalHeaderLabels(['Name', 'Min', 'Max', 'Active'])
            self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.task_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
            layout.addWidget(self.task_table)

            # Populate tasks
            self.populate_tasks()

            # Button layout for Add/Remove
            buttons_layout = QHBoxLayout()

            # Add task button
            add_task_button = QPushButton("Add Task")
            add_task_button.setFont(QFont("Arial", 12))
            add_task_button.clicked.connect(self.add_task)
            buttons_layout.addWidget(add_task_button)

            # Remove task button
            remove_task_button = QPushButton("Remove Selected Task")
            remove_task_button.setFont(QFont("Arial", 12))
            remove_task_button.clicked.connect(self.remove_task)
            buttons_layout.addWidget(remove_task_button)

            layout.addLayout(buttons_layout)

            # Shake animation toggle
            shake_layout = QHBoxLayout()
            self.shake_checkbox = QCheckBox("Enable Shaking Animation")
            self.shake_checkbox.setFont(QFont("Arial", 12))
            self.load_shaking_setting()
            shake_layout.addWidget(self.shake_checkbox)
            layout.addLayout(shake_layout)

            # Save/Cancel buttons
            save_cancel_layout = QHBoxLayout()

            save_button = QPushButton("Save")
            save_button.setFont(QFont("Arial", 14))
            save_button.clicked.connect(self.save_settings)
            save_cancel_layout.addWidget(save_button)

            cancel_button = QPushButton("Cancel")
            cancel_button.setFont(QFont("Arial", 14))
            cancel_button.clicked.connect(self.reject)
            save_cancel_layout.addWidget(cancel_button)

            layout.addLayout(save_cancel_layout)

            # Set the layout
            self.setLayout(layout)
            logging.debug("UI components initialized successfully.")

        except Exception as e:
            logging.exception("Exception occurred during UI initialization.")
            QMessageBox.critical(self, "Initialization Error", f"An error occurred while initializing the UI:\n{str(e)}")
            self.reject()

    def create_cell_widget(self, is_active):
        """Create a consistent cell widget for the active checkbox."""
        try:
            checkbox = QCheckBox()
            checkbox.setChecked(is_active)
            widget = QWidget()
            layout = QHBoxLayout()
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            return widget
        except Exception as e:
            logging.exception("Failed to create cell widget.")
            raise e

    def populate_tasks(self):
        """Populate task table with current tasks."""
        logging.debug("Populating task table with current tasks.")
        try:
            # Store current scroll position
            scrollbar = self.task_table.verticalScrollBar()
            current_scroll = scrollbar.value()

            self.task_table.setRowCount(0)
            for task_name in self.task_order:
                task = self.updated_tasks[task_name]
                row_position = self.task_table.rowCount()
                self.task_table.insertRow(row_position)

                # Task name
                name_item = QTableWidgetItem(task.name)
                name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.task_table.setItem(row_position, 0, name_item)

                # Min value
                min_item = QTableWidgetItem(str(task.min_count))
                min_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.task_table.setItem(row_position, 1, min_item)

                # Max value
                max_item = QTableWidgetItem(str(task.max_count))
                max_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.task_table.setItem(row_position, 2, max_item)

                # Active checkbox using consistent widget creation
                checkbox_widget = self.create_cell_widget(task.active)
                self.task_table.setCellWidget(row_position, 3, checkbox_widget)

            # Restore scroll position
            scrollbar.setValue(current_scroll)
            logging.debug("Task table populated successfully.")

        except Exception as e:
            logging.exception("Failed to populate task table.")
            QMessageBox.critical(self, "Population Error", f"An error occurred while populating tasks:\n{str(e)}")
            self.reject()

    def save_current_table_state(self):
        """Save the current state of the task table."""
        logging.debug("Saving current table state.")
        new_tasks = {}
        new_task_order = []
        try:
            for row in range(self.task_table.rowCount()):
                name_item = self.task_table.item(row, 0)
                min_item = self.task_table.item(row, 1)
                max_item = self.task_table.item(row, 2)

                # Check if items are not None
                if not all([name_item, min_item, max_item]):
                    QMessageBox.warning(self, "Incomplete Data", f"Row {row + 1} has incomplete data.")
                    logging.warning(f"Row {row + 1} has incomplete data.")
                    return

                name = name_item.text().strip()
                if not name:
                    QMessageBox.warning(self, "Invalid Task Name", f"Task name in row {row + 1} cannot be empty.")
                    logging.warning(f"Task name in row {row + 1} is empty.")
                    return

                # Ensure no duplicate task names
                if name in new_tasks:
                    QMessageBox.warning(self, "Duplicate Task Name",
                                        f"Task name '{name}' in row {row + 1} is duplicated.")
                    logging.warning(f"Duplicate task name '{name}' found in row {row + 1}.")
                    return

                min_val = min_item.text()
                max_val = max_item.text()

                # Convert min and max values safely
                try:
                    min_val = int(min_val)
                    max_val = int(max_val)
                    if min_val < 1:
                        raise ValueError("Minimum value must be at least 1")
                    if max_val < min_val:
                        raise ValueError("Maximum value must be greater than or equal to minimum")
                except ValueError as e:
                    QMessageBox.warning(self, "Invalid Input", f"Error in row {row + 1}: {str(e)}")
                    logging.warning(f"Invalid input in row {row + 1}: {str(e)}")
                    return

                # Get active state
                active_widget = self.task_table.cellWidget(row, 3)
                active = False
                if isinstance(active_widget, QWidget):
                    layout = active_widget.layout()
                    if layout and layout.count() > 0:
                        checkbox = layout.itemAt(0).widget()
                        if isinstance(checkbox, QCheckBox):
                            active = checkbox.isChecked()

                # Preserve description if exists
                original_task = self.updated_tasks.get(name)
                description = original_task.description if original_task else ""

                # Create new task
                new_tasks[name] = Task(
                    name=name,
                    min_count=min_val,
                    max_count=max_val,
                    active=active,
                    description=description
                )
                new_task_order.append(name)

            self.updated_tasks = new_tasks
            self.task_order = new_task_order
            logging.debug("Table state saved successfully.")

        except Exception as e:
            logging.exception("Failed to save table state.")
            QMessageBox.critical(self, "Save Error", f"An error occurred while saving table state:\n{str(e)}")
            self.reject()

    def add_task(self):
        """Add a new task."""
        logging.debug("Adding a new task.")
        try:
            self.save_current_table_state()

            base_name = "New Task"
            new_task_name = base_name
            counter = 1
            existing_names = set(self.updated_tasks.keys())
            while new_task_name in existing_names:
                new_task_name = f"{base_name} {counter}"
                counter += 1

            # Add new row directly instead of repopulating
            row_position = self.task_table.rowCount()
            self.task_table.insertRow(row_position)
            logging.debug(f"Inserted new row at position: {row_position}")

            # Add the new task items
            name_item = QTableWidgetItem(new_task_name)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.task_table.setItem(row_position, 0, name_item)

            min_item = QTableWidgetItem("1")
            min_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.task_table.setItem(row_position, 1, min_item)

            max_item = QTableWidgetItem("3")
            max_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.task_table.setItem(row_position, 2, max_item)

            # Add checkbox using consistent widget creation
            checkbox_widget = self.create_cell_widget(True)
            self.task_table.setCellWidget(row_position, 3, checkbox_widget)

            # After adding the new row and setting it up, scroll to make it visible
            self.task_table.scrollToItem(name_item)
            logging.debug(f"New task '{new_task_name}' added successfully.")

            # Add to updated_tasks and task_order
            self.updated_tasks[new_task_name] = Task(
                name=new_task_name,
                min_count=1,
                max_count=3,
                active=True,
                description=""  # New task has no description initially
            )
            self.task_order.append(new_task_name)

            self.save_settings(quiet=True)
            logging.debug(f"Task '{new_task_name}' saved to settings.")

        except Exception as e:
            logging.exception("Failed to add a new task.")
            QMessageBox.critical(self, "Add Task Error", f"An error occurred while adding a new task:\n{str(e)}")
            self.reject()

    def remove_task(self):
        """Remove selected task."""
        logging.debug("Attempting to remove selected task.")
        try:
            self.save_current_table_state()

            selected_items = self.task_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "No Selection", "Please select a task to remove.")
                logging.warning("No task selected for removal.")
                return

            selected_row = selected_items[0].row()
            task_name = self.task_table.item(selected_row, 0).text()
            if task_name in self.updated_tasks:
                del self.updated_tasks[task_name]
                self.task_order.remove(task_name)
                self.task_table.removeRow(selected_row)  # Remove just the selected row
                logging.debug(f"Task '{task_name}' removed successfully.")
                self.save_settings(quiet=True)
            else:
                QMessageBox.warning(self, "Task Not Found", f"The task '{task_name}' was not found.")
                logging.warning(f"Task '{task_name}' not found in updated_tasks.")

        except Exception as e:
            logging.exception("Failed to remove the selected task.")
            QMessageBox.critical(self, "Remove Task Error", f"An error occurred while removing the task:\n{str(e)}")
            self.reject()

    def load_shaking_setting(self):
        """Load shake animation setting."""
        logging.debug("Loading shaking animation setting.")
        try:
            if hasattr(self.task_manager, 'filepath') and self.task_manager.filepath:
                settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
                logging.debug(f"Settings file path: {settings_file}")
            else:
                settings_file = 'settings.json'  # Default path or handle accordingly
                logging.debug("Settings file path not found in TaskManager. Using default path.")

            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)
                self.shake_checkbox.setChecked(shake_enabled)
                logging.debug(f"Shaking animation enabled: {shake_enabled}")
            else:
                self.shake_checkbox.setChecked(True)  # Default to enabled
                logging.debug("Settings file does not exist. Defaulting shaking animation to enabled.")

        except Exception as e:
            logging.exception("Error loading shake setting.")
            self.shake_checkbox.setChecked(True)  # Default to enabled on error

    def save_settings(self, quiet=False):
        """Save settings and tasks."""
        logging.debug("Saving settings and tasks.")
        try:
            self.save_current_table_state()

            # Update task manager
            self.task_manager.tasks = self.updated_tasks
            if not self.task_manager.save_tasks():
                raise Exception("Failed to save tasks")
            logging.debug("Tasks saved to TaskManager successfully.")

            # Save settings
            if hasattr(self.task_manager, 'filepath') and self.task_manager.filepath:
                settings_file = os.path.join(
                    os.path.dirname(self.task_manager.filepath),
                    'settings.json'
                )
                logging.debug(f"Saving settings to: {settings_file}")
            else:
                settings_file = 'settings.json'  # Default path or handle accordingly
                logging.debug("TaskManager does not have a filepath. Saving settings to default path.")

            settings = {
                'shake_animation': self.shake_checkbox.isChecked(),
                'window': {}
            }

            if self.parent():
                settings['window']['width'] = self.parent().width()
                settings['window']['height'] = self.parent().height()
                logging.debug(f"Window size - Width: {settings['window']['width']}, Height: {settings['window']['height']}")
            else:
                # Provide default values or handle accordingly
                settings['window']['width'] = 800
                settings['window']['height'] = 600
                logging.debug("Parent widget not found. Using default window size.")

            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            logging.debug("Settings saved successfully.")

            self.saved = True

            # Only show message and exit if not quiet
            if not quiet:
                QMessageBox.information(self, "Settings Saved",
                                        "Settings have been saved successfully.")
                logging.info("Settings saved and user notified.")
                self.accept()

        except Exception as e:
            logging.exception("Failed to save settings.")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            self.reject()

# For testing purposes, we'll create a main function
def main():
    app = QApplication(sys.argv)
    task_manager = TaskManager()
    dialog = SettingsDialog(task_manager)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
