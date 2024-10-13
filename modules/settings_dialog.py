# modules/settings_dialog.py

import os
import json
import logging
from typing import Dict
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QCheckBox, QMessageBox, QListWidget,
    QListWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import Qt
from .game_logic import TaskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TaskEditDialog(QDialog):
    """
    Dialog for adding or editing a task.
    """
    def __init__(self, parent=None, task_name: str = "", min_hp: int = 1, max_hp: int = 5, active: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Edit Task")
        self.setFixedSize(300, 200)
        self.task_name = task_name
        self.min_hp = min_hp
        self.max_hp = max_hp
        self.active = active
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.name_edit = QLineEdit(self.task_name)
        form_layout.addRow("Task Name:", self.name_edit)

        self.min_hp_edit = QLineEdit(str(self.min_hp))
        form_layout.addRow("Min HP:", self.min_hp_edit)

        self.max_hp_edit = QLineEdit(str(self.max_hp))
        form_layout.addRow("Max HP:", self.max_hp_edit)

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(self.active)
        form_layout.addRow("", self.active_checkbox)

        layout.addLayout(form_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def save(self):
        name = self.name_edit.text().strip()
        try:
            min_hp = int(self.min_hp_edit.text())
            max_hp = int(self.max_hp_edit.text())
            active = self.active_checkbox.isChecked()

            if not name:
                raise ValueError("Task name cannot be empty.")
            if min_hp < 1 or max_hp < min_hp:
                raise ValueError("Invalid HP values.")

            self.task_name = name
            self.min_hp = min_hp
            self.max_hp = max_hp
            self.active = active

            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))

class SettingsDialog(QDialog):
    """
    Dialog for editing tasks and additional settings.
    """
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 400)
        self.task_manager = task_manager
        self.saved = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Task List
        self.task_list = QListWidget()
        self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.load_tasks()
        layout.addWidget(QLabel("Tasks:"))
        layout.addWidget(self.task_list)

        # Buttons for Task Management
        task_buttons_layout = QHBoxLayout()
        add_button = QPushButton("Add Task")
        add_button.clicked.connect(self.add_task)
        edit_button = QPushButton("Edit Task")
        edit_button.clicked.connect(self.edit_task)
        delete_button = QPushButton("Delete Task")
        delete_button.clicked.connect(self.delete_task)
        task_buttons_layout.addWidget(add_button)
        task_buttons_layout.addWidget(edit_button)
        task_buttons_layout.addWidget(delete_button)
        layout.addLayout(task_buttons_layout)

        # Additional Settings
        settings_group = QVBoxLayout()
        self.shake_animation_checkbox = QCheckBox("Enable Shake Animation")
        self.shake_animation_checkbox.setChecked(True)
        settings_group.addWidget(self.shake_animation_checkbox)
        layout.addWidget(QLabel("Additional Settings:"))
        layout.addLayout(settings_group)

        # Save and Cancel Buttons
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def load_tasks(self):
        """Loads tasks into the QListWidget."""
        self.task_list.clear()
        for task_name, details in self.task_manager.tasks.items():
            item = QListWidgetItem(task_name)
            status = "Active" if details.get("active", True) else "Inactive"
            item.setToolTip(f"HP Range: {details.get('min')} - {details.get('max')}, Status: {status}")
            self.task_list.addItem(item)

    def add_task(self):
        """Opens the TaskEditDialog to add a new task."""
        dialog = TaskEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_task_name = dialog.task_name
            if new_task_name in self.task_manager.tasks:
                QMessageBox.warning(self, "Duplicate Task", "A task with this name already exists.")
                return
            self.task_manager.add_task(new_task_name, dialog.min_hp, dialog.max_hp, dialog.active)
            self.load_tasks()

    def edit_task(self):
        """Opens the TaskEditDialog to edit the selected task."""
        selected_item = self.task_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a task to edit.")
            return
        original_name = selected_item.text()
        details = self.task_manager.tasks.get(original_name, {})
        dialog = TaskEditDialog(
            self,
            task_name=original_name,
            min_hp=details.get("min", 1),
            max_hp=details.get("max", 5),
            active=details.get("active", True)
        )
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.task_name
            self.task_manager.edit_task(
                original_name,
                new_name,
                dialog.min_hp,
                dialog.max_hp,
                dialog.active
            )
            self.load_tasks()

    def delete_task(self):
        """Deletes the selected task."""
        selected_item = self.task_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a task to delete.")
            return
        task_name = selected_item.text()
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the task '{task_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.task_manager.delete_task(task_name)
            self.load_tasks()

    def save_and_close(self):
        """Saves additional settings and closes the dialog."""
        # Save shake animation setting
        settings = {
            'shake_animation': self.shake_animation_checkbox.isChecked()
        }
        settings_file = os.path.join(os.path.dirname(self.task_manager.filepath), 'settings.json')
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            logging.info(f"Additional settings saved to {settings_file}.")
        except Exception as e:
            logging.error(f"Failed to save additional settings. Error: {e}")
            QMessageBox.critical(self, "Error", "Failed to save settings.")
            return

        # Save tasks
        self.task_manager.save_tasks()

        self.saved = True
        self.accept()
