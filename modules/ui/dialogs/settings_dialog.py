# modules/ui/dialogs/settings_dialog.py

import os
import json
import logging
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QCheckBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QSpinBox, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from modules.game_logic import TaskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SettingsDialog(QDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(600, 500)
        self.task_manager = task_manager
        self.saved = False
        
        # Handle both list and dictionary cases
        if isinstance(task_manager.tasks, dict):
            self.updated_tasks = {k: v.copy() for k, v in task_manager.tasks.items()}
        elif isinstance(task_manager.tasks, list):
            self.updated_tasks = {task['name']: task.copy() for task in task_manager.tasks}
        else:
            self.updated_tasks = {}  # Initialize as empty if neither list nor dict
        
        self.init_ui()

    def init_ui(self):
        """Initializes the settings dialog UI."""
        layout = QVBoxLayout()

        # Task Editing Section
        task_label = QLabel("Edit Tasks:")
        task_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(task_label)

        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(['Name', 'Min', 'Max', 'Active'])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        
        # Enable alternating row colors
        self.task_table.setAlternatingRowColors(True)
        # Set custom stylesheet for alternating row colors
        self.task_table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
            }
        """)
        
        self.populate_tasks()
        layout.addWidget(self.task_table)

        # Add and Remove Task Buttons
        buttons_layout = QHBoxLayout()
        add_task_button = QPushButton("Add Task")
        add_task_button.setFont(QFont("Arial", 12))
        add_task_button.clicked.connect(self.add_task)
        remove_task_button = QPushButton("Remove Selected Task")
        remove_task_button.setFont(QFont("Arial", 12))
        remove_task_button.clicked.connect(self.remove_task)
        buttons_layout.addWidget(add_task_button)
        buttons_layout.addWidget(remove_task_button)
        layout.addLayout(buttons_layout)

        # Shaking Animation Toggle
        shake_layout = QHBoxLayout()
        self.shake_checkbox = QCheckBox("Enable Shaking Animation")
        self.shake_checkbox.setFont(QFont("Arial", 12))
        self.load_shaking_setting()
        shake_layout.addWidget(self.shake_checkbox)
        layout.addLayout(shake_layout)

        # Save and Cancel Buttons
        save_cancel_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setFont(QFont("Arial", 14))
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 14))
        cancel_button.clicked.connect(self.reject)
        save_cancel_layout.addWidget(save_button)
        save_cancel_layout.addWidget(cancel_button)
        layout.addLayout(save_cancel_layout)

        self.setLayout(layout)

    def populate_tasks(self):
        """Populates the task table with existing tasks."""
        self.task_table.setRowCount(0)
        for row_index, (task_name, task) in enumerate(self.updated_tasks.items()):
            row_position = self.task_table.rowCount()
            self.task_table.insertRow(row_position)

            # Name
            name_item = QTableWidgetItem(task_name)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.task_table.setItem(row_position, 0, name_item)

            # Min
            min_item = QTableWidgetItem(str(task.get('min', 1)))
            min_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.task_table.setItem(row_position, 1, min_item)

            # Max
            max_item = QTableWidgetItem(str(task.get('max', 10)))
            max_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.task_table.setItem(row_position, 2, max_item)

            # Active - Use QCheckBox instead of Yes/No text
            active_checkbox = QCheckBox()
            active_checkbox.setChecked(task.get('active', True))
            # Create a QWidget to center the checkbox
            widget = QWidget()
            layout = QHBoxLayout()
            layout.addWidget(active_checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to better center
            widget.setLayout(layout)
            self.task_table.setCellWidget(row_position, 3, widget)

    def add_task(self):
        """Adds a new empty task to the table."""
        new_task_name = f"Task_{len(self.updated_tasks) + 1}"
        # Ensure unique task names
        counter = 1
        base_name = new_task_name
        while new_task_name in self.updated_tasks:
            new_task_name = f"{base_name}_{counter}"
            counter += 1
        self.updated_tasks[new_task_name] = {'min': 1, 'max': 10, 'active': True}
        self.populate_tasks()

    def remove_task(self):
        """Removes the selected task from the table."""
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a task to remove.")
            return
        selected_row = selected_items[0].row()
        task_name = self.task_table.item(selected_row, 0).text()
        del self.updated_tasks[task_name]
        self.populate_tasks()

    def load_shaking_setting(self):
        """Loads the shaking animation setting from the settings file."""
        settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)
                self.shake_checkbox.setChecked(shake_enabled)
            except Exception as e:
                logging.error(f"Failed to load shaking setting. Error: {e}")
                self.shake_checkbox.setChecked(True)  # Default to enabled
        else:
            self.shake_checkbox.setChecked(True)  # Default to enabled

    def save_settings(self):
        """Saves the updated tasks and settings."""
        # Update tasks from table
        new_tasks = {}
        for row in range(self.task_table.rowCount()):
            name = self.task_table.item(row, 0).text().strip()
            if not name:
                QMessageBox.warning(self, "Invalid Task Name", f"Task name in row {row + 1} cannot be empty.")
                return
            if name in new_tasks:
                QMessageBox.warning(self, "Duplicate Task Name", f"Task name '{name}' in row {row + 1} is duplicated.")
                return
            try:
                min_val = int(self.task_table.item(row, 1).text())
                max_val = int(self.task_table.item(row, 2).text())
                # Retrieve the state from the checkbox
                active_widget = self.task_table.cellWidget(row, 3)
                if isinstance(active_widget, QWidget):
                    layout = active_widget.layout()
                    if layout is not None and layout.count() > 0:
                        active_checkbox = layout.itemAt(0).widget()
                        if isinstance(active_checkbox, QCheckBox):
                            active = active_checkbox.isChecked()
                        else:
                            active = True
                    else:
                        active = True
                else:
                    # Fallback to True if widget is not found
                    active = True
                new_tasks[name] = {'min': min_val, 'max': max_val, 'active': active}
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", f"Min and Max values in row {row + 1} must be integers.")
                return

        self.updated_tasks = new_tasks

        # Save tasks back to TaskManager
        self.task_manager.tasks = self.updated_tasks

        # Save settings
        shake_enabled = self.shake_checkbox.isChecked()
        settings = {'shake_animation': shake_enabled}
        settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            self.saved = True
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            self.accept()
        except Exception as e:
            logging.error(f"Failed to save settings. Error: {e}")
            QMessageBox.critical(self, "Error", "Failed to save settings.")
