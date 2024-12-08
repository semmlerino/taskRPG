"""Settings dialog for managing game settings and tasks."""
import os
import logging
from PyQt5.QtCore import (
    Qt, QByteArray, QModelIndex,
    QSettings, QSize
)
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QTableView, QHeaderView, QCheckBox, QMessageBox, QLineEdit, QSpinBox, QTextEdit, QMenu
)
from PyQt5.QtGui import QFont

from modules.tasks.task_manager import TaskManager
from modules.constants import DATA_DIR
from .task_table_model import TaskTableModel
from .delegates import CheckBoxHoverDelegate
from .settings_manager import SettingsManager
from . import styles

class SettingsDialog(QDialog):
    """Dialog for managing game settings and tasks."""

    def __init__(self, task_manager: TaskManager, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 400)
        self.task_manager = task_manager
        self.saved = False

        # Initialize settings manager
        os.makedirs(DATA_DIR, exist_ok=True)
        self.settings_file = os.path.join(DATA_DIR, 'settings.json')
        self.settings_manager = SettingsManager(self.settings_file)
        logging.info(f"Settings file path: {self.settings_file}")

        if parent:
            self.setWindowModality(Qt.WindowModal)

        # Load settings and initialize UI
        self.settings = self.settings_manager.load_settings()
        self.init_ui()
        self.apply_window_settings()

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

        # Task Table
        self.task_view = QTableView()
        self.task_view.setFont(QFont("Arial", 13))
        self.task_view.setStyleSheet(styles.TABLE_STYLE)
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

        # Set up the model and delegate
        self.task_model = TaskTableModel(self.task_manager.tasks, self)
        self.task_view.setModel(self.task_model)
        
        # Set custom delegate for hover effects and checkboxes
        self.task_view.setItemDelegate(CheckBoxHoverDelegate(self.task_view))
        
        # Enable mouse tracking for hover effects
        self.task_view.setMouseTracking(True)
        
        # Set up context menu
        self.task_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set up the header
        header = self.task_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)  # Important to show all columns
        header.setStyleSheet(styles.HEADER_STYLE)
        
        # Set column widths and alignment
        self.task_view.setColumnWidth(0, 200)  # Name
        self.task_view.setColumnWidth(1, 60)   # Min
        self.task_view.setColumnWidth(2, 60)   # Max
        self.task_view.setColumnWidth(3, 100)  # Active
        self.task_view.setColumnWidth(4, 100)  # Daily
        self.task_view.setColumnWidth(5, 100)  # Weekly
        self.task_view.setColumnWidth(6, 80)   # Count
        
        # Center align checkboxes and numeric columns
        for col in [1, 2, 3, 4, 5, 6]:  # Min, Max, Active, Daily, Weekly, Count
            self.task_model.setHeaderData(col, Qt.Horizontal, Qt.AlignCenter, Qt.TextAlignmentRole)
        
        # Set vertical header (row numbers)
        vertical_header = self.task_view.verticalHeader()
        vertical_header.setDefaultSectionSize(40)  # Increase row height
        vertical_header.setStyleSheet(styles.VERTICAL_HEADER_STYLE)
            
        layout.addWidget(self.task_view)

        # Task Management Buttons
        button_layout = QHBoxLayout()

        # Add Task Button
        add_button = QPushButton("Add Task")
        add_button.setFont(QFont("Arial", 13))
        add_button.setStyleSheet(styles.ADD_BUTTON_STYLE)
        add_button.clicked.connect(self.add_task)
        button_layout.addWidget(add_button)

        # Remove Task Button
        remove_button = QPushButton("Remove Selected")
        remove_button.setFont(QFont("Arial", 13))
        remove_button.setStyleSheet(styles.REMOVE_BUTTON_STYLE)
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
        self.shake_checkbox.setStyleSheet(styles.CHECKBOX_STYLE)
        self.load_shaking_setting()
        layout.addWidget(self.shake_checkbox)

        # Bottom buttons
        dialog_buttons = QHBoxLayout()

        # Save Button
        save_button = QPushButton("Save Changes")
        save_button.setFont(QFont("Arial", 13))
        save_button.setStyleSheet(styles.SAVE_BUTTON_STYLE)
        save_button.clicked.connect(self.save_settings)
        dialog_buttons.addWidget(save_button)

        # Cancel Button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 13))
        cancel_button.setStyleSheet(styles.CANCEL_BUTTON_STYLE)
        cancel_button.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_button)

        layout.addLayout(dialog_buttons)
        
        self.setLayout(layout)

    def load_shaking_setting(self):
        """Load shake animation setting from settings file."""
        shake_enabled = self.settings.get('shake_animation', True)
        self.shake_checkbox.setChecked(shake_enabled)

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
                    self.resize(800, 600)

            # Apply column widths
            if 'column_widths' in self.settings:
                try:
                    self.apply_column_widths(self.settings['column_widths'])
                except Exception as e:
                    logging.error(f"Error applying column widths: {e}")
                    self.apply_default_column_widths()

        except Exception as e:
            logging.error(f"Error applying window settings: {e}", exc_info=True)
            self.resize(800, 600)

    def apply_column_widths(self, col_widths):
        """Apply column widths with validation."""
        total_width = self.width() - 50  # Account for margins and scrollbar
        
        # Validate total width
        current_total = sum(col_widths)
        if current_total > total_width:
            # Scale down proportionally
            scale_factor = total_width / current_total
            col_widths = [int(w * scale_factor) for w in col_widths]
        
        # Ensure minimum widths
        min_widths = [100, 60, 60, 50, 50, 50, 50]  # Minimum widths for each column
        for i, (width, min_width) in enumerate(zip(col_widths, min_widths)):
            if i < self.task_view.model().columnCount():
                final_width = max(width, min_width)
                self.task_view.setColumnWidth(i, final_width)

    def apply_default_column_widths(self):
        """Apply default column widths."""
        default_widths = [200, 80, 80, 80, 80, 80, 80]  # Default widths for each column
        for i, width in enumerate(default_widths):
            if i < self.task_view.model().columnCount():
                self.task_view.setColumnWidth(i, width)

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

            # Create dialog for entering task details
            dialog = QDialog(self)
            dialog.setWindowTitle("Enter Task Details")
            layout = QVBoxLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(20, 20, 20, 20)

            # Task name
            name_label = QLabel("Task Name:")
            name_label.setFont(QFont("Arial", 13))
            layout.addWidget(name_label)
            name_edit = QLineEdit(new_task_name)
            name_edit.setFont(QFont("Arial", 13))
            layout.addWidget(name_edit)

            # Min count
            min_label = QLabel("Min Count:")
            min_label.setFont(QFont("Arial", 13))
            layout.addWidget(min_label)
            min_spin = QSpinBox()
            min_spin.setFont(QFont("Arial", 13))
            min_spin.setMinimum(1)
            min_spin.setValue(1)
            layout.addWidget(min_spin)

            # Max count
            max_label = QLabel("Max Count:")
            max_label.setFont(QFont("Arial", 13))
            layout.addWidget(max_label)
            max_spin = QSpinBox()
            max_spin.setFont(QFont("Arial", 13))
            max_spin.setMinimum(1)
            max_spin.setValue(3)
            layout.addWidget(max_spin)

            # Active
            active_checkbox = QCheckBox("Active")
            active_checkbox.setFont(QFont("Arial", 13))
            active_checkbox.setChecked(True)
            layout.addWidget(active_checkbox)

            # Daily
            daily_checkbox = QCheckBox("Daily")
            daily_checkbox.setFont(QFont("Arial", 13))
            layout.addWidget(daily_checkbox)

            # Weekly
            weekly_checkbox = QCheckBox("Weekly")
            weekly_checkbox.setFont(QFont("Arial", 13))
            layout.addWidget(weekly_checkbox)

            # Count
            count_label = QLabel("Count:")
            count_label.setFont(QFont("Arial", 13))
            layout.addWidget(count_label)
            count_spin = QSpinBox()
            count_spin.setFont(QFont("Arial", 13))
            count_spin.setMinimum(0)
            count_spin.setValue(0)
            layout.addWidget(count_spin)

            # Buttons
            buttons_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            ok_button.setFont(QFont("Arial", 13))
            ok_button.clicked.connect(dialog.accept)
            buttons_layout.addWidget(ok_button)
            cancel_button = QPushButton("Cancel")
            cancel_button.setFont(QFont("Arial", 13))
            cancel_button.clicked.connect(dialog.reject)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)

            dialog.setLayout(layout)

            if dialog.exec_() == QDialog.Accepted:
                # Add new task
                self.task_model.beginInsertRows(QModelIndex(), row_count, row_count)
                self.task_model._tasks.append((
                    name_edit.text(),   # name
                    min_spin.value(),   # min_count
                    max_spin.value(),   # max_count
                    active_checkbox.isChecked(),  # active
                    daily_checkbox.isChecked(),  # is_daily
                    weekly_checkbox.isChecked(),  # is_weekly
                    count_spin.value()  # count
                ))
                self.task_model.endInsertRows()

                # Select the new task
                index = self.task_model.index(row_count, 0)
                self.task_view.setCurrentIndex(index)
                self.task_view.edit(index)  # Start editing the name

                logging.info(f"Added new task: {name_edit.text()}")

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

    def validate_tasks(self) -> bool:
        """Validate tasks before saving."""
        try:
            tasks = self.task_model._tasks
            seen_names = set()
            
            for i, (name, min_count, max_count, active, is_daily, is_weekly, count) in enumerate(tasks):
                # Check for empty name
                if not name:
                    QMessageBox.warning(
                        self,
                        "Invalid Task",
                        f"Task at row {i + 1} has no name."
                    )
                    return False

                # Check for duplicate names
                if name in seen_names:
                    QMessageBox.warning(
                        self,
                        "Duplicate Task",
                        f"Task name '{name}' is used multiple times."
                    )
                    return False
                seen_names.add(name)

                # Check min/max values
                if min_count < 1:
                    QMessageBox.warning(
                        self,
                        "Invalid Min Count",
                        f"Task '{name}' has invalid min count: {min_count}"
                    )
                    return False

                if max_count < min_count:
                    QMessageBox.warning(
                        self,
                        "Invalid Max Count",
                        f"Task '{name}' has max count less than min count."
                    )
                    return False

                # Check count value
                if count < 0:
                    QMessageBox.warning(
                        self,
                        "Invalid Count",
                        f"Task '{name}' has negative count: {count}"
                    )
                    return False

            return True

        except Exception as e:
            logging.error(f"Error validating tasks: {e}")
            QMessageBox.critical(self, "Error", f"Failed to validate tasks: {str(e)}")
            return False

    def save_settings(self):
        """Save settings and tasks."""
        try:
            if not self.validate_tasks():
                return

            # Save tasks first
            new_tasks = self.task_model.get_tasks()  # Changed from get_tasks_dict()
            self.task_manager.tasks = new_tasks
            if not self.task_manager.save_tasks():
                raise Exception("Failed to save tasks")

            # Get window geometry using base64 encoding
            window_geometry = self.saveGeometry().toBase64().data().decode('utf-8')
            logging.debug(f"Window geometry (base64): {window_geometry}")

            # Prepare settings dictionary
            settings = {
                'shake_animation': bool(self.shake_checkbox.isChecked()),
                'window_geometry': window_geometry,
                'column_widths': [
                    int(self.task_view.columnWidth(i))
                    for i in range(self.task_view.model().columnCount())
                ]
            }

            # Save settings
            if self.settings_manager.save_settings(settings):
                self.saved = True
                QMessageBox.information(self, "Settings Saved",
                    "Settings have been saved successfully.")
                self.accept()
            else:
                raise Exception("Failed to save settings")

        except Exception as e:
            logging.error(f"Failed to save settings: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def closeEvent(self, event):
        """Handle dialog close event."""
        if not self.saved:
            reply = QMessageBox.question(
                self, "Save Changes?",
                "Do you want to save your changes?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_settings()
                if self.saved:  # Only accept if save was successful
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def show_context_menu(self, position):
        """Show context menu for task table"""
        try:
            index = self.task_view.indexAt(position)
            if not index.isValid():
                return
                
            row = index.row()
            task_name = self.task_model._tasks[row][0]
            task = self.task_manager.tasks[task_name]
            
            menu = QMenu(self)
            
            # Show current activation time if set
            if task.activation_time:
                time_str = f"{task.activation_time.hour:02d}:{task.activation_time.minute:02d}"
                current_time_action = menu.addAction(f"Current Activation Time: {time_str}")
                current_time_action.setEnabled(False)  # Make it non-clickable
                menu.addSeparator()
            
            set_time_action = menu.addAction("Set Activation Time")
            
            # Only show clear action if there's an activation time set
            clear_time_action = None
            if task.activation_time:
                clear_time_action = menu.addAction("Clear Activation Time")
            
            action = menu.exec_(self.task_view.viewport().mapToGlobal(position))
            
            if action == set_time_action:
                self.set_activation_time(row)
            elif clear_time_action and action == clear_time_action:
                self.clear_activation_time(row)
                
        except Exception as e:
            logging.error(f"Error showing context menu: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show context menu: {str(e)}")
            
    def set_activation_time(self, row):
        """Set activation time for task"""
        try:
            task_name = self.task_model._tasks[row][0]
            task = self.task_manager.tasks[task_name]
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Set Activation Time")
            layout = QVBoxLayout()
            
            # Time input
            time_label = QLabel("Enter time (HH:MM):")
            time_label.setFont(QFont("Arial", 13))
            layout.addWidget(time_label)
            
            time_edit = QLineEdit()
            time_edit.setFont(QFont("Arial", 13))
            time_edit.setPlaceholderText("14:30")
            if task.activation_time:
                time_edit.setText(f"{task.activation_time.hour:02d}:{task.activation_time.minute:02d}")
            layout.addWidget(time_edit)
            
            # Error label (hidden by default)
            error_label = QLabel()
            error_label.setStyleSheet("color: red;")
            error_label.hide()
            layout.addWidget(error_label)
            
            # Buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            def validate_time():
                """Validate time format and range"""
                time_str = time_edit.text().strip()
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if 0 <= hour < 24 and 0 <= minute < 60:
                        error_label.hide()
                        return True
                    else:
                        error_label.setText("Invalid time range")
                        error_label.show()
                except ValueError:
                    error_label.setText("Invalid time format (use HH:MM)")
                    error_label.show()
                return False
            
            def on_ok():
                if validate_time():
                    task.set_activation_time(time_edit.text().strip())
                    self.saved = False  # Mark settings as changed
                    dialog.accept()
            
            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)
            time_edit.textChanged.connect(lambda: ok_button.setEnabled(validate_time()))
            
            dialog.exec_()
            
        except Exception as e:
            logging.error(f"Error setting activation time: {e}")
            QMessageBox.critical(self, "Error", f"Failed to set activation time: {str(e)}")
            
    def clear_activation_time(self, row):
        """Clear activation time for task"""
        try:
            task_name = self.task_model._tasks[row][0]
            task = self.task_manager.tasks[task_name]
            task.set_activation_time(None)
            self.saved = False  # Mark settings as changed
            
        except Exception as e:
            logging.error(f"Error clearing activation time: {e}")
            QMessageBox.critical(self, "Error", f"Failed to clear activation time: {str(e)}")
