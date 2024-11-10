# modules/ui/dialogs/settings_dialog.py

import os
import json
import logging
from typing import Dict
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QCheckBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QSpinBox, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from modules.tasks.task_manager import TaskManager
from modules.tasks.task import Task

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
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        layout = QVBoxLayout()
        
        # Task Editing Section
        task_label = QLabel("Edit Tasks:")
        task_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(task_label)

        # Task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(['Name', 'Min', 'Max', 'Active'])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
            }
        """)
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

    def populate_tasks(self):
        """Populate task table with current tasks."""
        self.task_table.setRowCount(0)
        for task_name, task in self.updated_tasks.items():
            row_position = self.task_table.rowCount()
            self.task_table.insertRow(row_position)
            
            # Task name
            name_item = QTableWidgetItem(task_name)
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
            
            # Active checkbox
            active_checkbox = QCheckBox()
            active_checkbox.setChecked(task.active)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout()
            checkbox_layout.addWidget(active_checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_widget.setLayout(checkbox_layout)
            self.task_table.setCellWidget(row_position, 3, checkbox_widget)

    def add_task(self):
        """Add a new task."""
        new_task_name = f"Task_{len(self.updated_tasks) + 1}"
        counter = 1
        base_name = new_task_name
        while new_task_name in self.updated_tasks:
            new_task_name = f"{base_name}_{counter}"
            counter += 1

        self.updated_tasks[new_task_name] = Task(
            name=new_task_name,
            min_count=1,
            max_count=3,
            active=True
        )
        self.populate_tasks()

    def remove_task(self):
        """Remove selected task."""
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a task to remove.")
            return
            
        selected_row = selected_items[0].row()
        task_name = self.task_table.item(selected_row, 0).text()
        if task_name in self.updated_tasks:
            del self.updated_tasks[task_name]
            self.populate_tasks()

    def load_shaking_setting(self):
        """Load shake animation setting."""
        try:
            settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)
                self.shake_checkbox.setChecked(shake_enabled)
            else:
                self.shake_checkbox.setChecked(True)  # Default to enabled
        except Exception as e:
            logging.error(f"Error loading shake setting: {e}")
            self.shake_checkbox.setChecked(True)  # Default to enabled on error

    def save_settings(self):
        """Save settings and tasks."""
        try:
            new_tasks = {}
            for row in range(self.task_table.rowCount()):
                # Get task name
                name = self.task_table.item(row, 0).text().strip()
                if not name:
                    QMessageBox.warning(self, "Invalid Task Name", 
                                      f"Task name in row {row + 1} cannot be empty.")
                    return
                if name in new_tasks:
                    QMessageBox.warning(self, "Duplicate Task Name", 
                                      f"Task name '{name}' in row {row + 1} is duplicated.")
                    return
                
                # Get min/max values
                try:
                    min_val = int(self.task_table.item(row, 1).text())
                    max_val = int(self.task_table.item(row, 2).text())
                    if min_val < 1:
                        raise ValueError("Minimum value must be at least 1")
                    if max_val < min_val:
                        raise ValueError("Maximum value must be greater than or equal to minimum")
                except ValueError as e:
                    QMessageBox.warning(self, "Invalid Input", str(e))
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

                # Find the original task name for this row to preserve description
                original_name = list(self.updated_tasks.keys())[row]
                original_task = self.updated_tasks[original_name]

                # Create new task
                new_tasks[name] = Task(
                    name=name,
                    min_count=min_val,
                    max_count=max_val,
                    active=active,
                    description=original_task.description
                )

            # Update task manager
            self.task_manager.tasks = new_tasks
            if not self.task_manager.save_tasks():
                raise Exception("Failed to save tasks")

            # Save settings
            settings_file = os.path.join(
                os.path.dirname(self.task_manager.filepath), 
                'settings.json'
            )
            
            settings = {
                'shake_animation': self.shake_checkbox.isChecked(),
                'window': {
                    'width': self.parent().width(),
                    'height': self.parent().height()
                }
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            
            self.saved = True
            QMessageBox.information(self, "Settings Saved", 
                                  "Settings have been saved successfully.")
            self.accept()
            
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")