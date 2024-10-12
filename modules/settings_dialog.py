# modules/settings_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QSpinBox, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt  # Add this import
from .game_logic import TaskManager


class SettingsDialog(QDialog):
    """
    Dialog for managing tasks (enemies).
    Allows adding, editing, and deleting tasks.
    """
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(700, 500)  # Increased size for better visibility
        self.task_manager = task_manager
        self.saved = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Task Manager")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Task List
        self.task_list = QListWidget()
        self.task_list.setAlternatingRowColors(True)
        self.task_list.setFont(QFont("Arial", 12))
        self.refresh_task_list()
        layout.addWidget(QLabel("Tasks:"))
        layout.addWidget(self.task_list)

        # Buttons for Add, Edit, Delete
        buttons_layout = QHBoxLayout()
        for btn_text, btn_slot in [("Add Task", self.add_task), 
                                   ("Edit Task", self.edit_task), 
                                   ("Delete Task", self.delete_task)]:
            btn = QPushButton(btn_text)
            btn.setFont(QFont("Arial", 10))
            btn.clicked.connect(btn_slot)
            buttons_layout.addWidget(btn)
        layout.addLayout(buttons_layout)

        # Save and Cancel Buttons
        save_cancel_layout = QHBoxLayout()
        for btn_text, btn_slot in [("Save", self.save_and_close), 
                                   ("Cancel", self.reject)]:
            btn = QPushButton(btn_text)
            btn.setFont(QFont("Arial", 10))
            btn.clicked.connect(btn_slot)
            save_cancel_layout.addWidget(btn)
        layout.addLayout(save_cancel_layout)

        self.setLayout(layout)

    def refresh_task_list(self):
        """Refreshes the task list display."""
        self.task_list.clear()
        for task_name, task_info in self.task_manager.tasks.items():
            item_text = f"{task_name:<20} | Min: {task_info['min']:<3} | Max: {task_info['max']:<3} | {'Active' if task_info['active'] else 'Inactive'}"
            item = QListWidgetItem(item_text)
            self.task_list.addItem(item)

    def add_task(self):
        """Opens a dialog to add a new task."""
        dialog = TaskEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, min_hp, max_hp, active = dialog.get_task_data()
            if not name:
                QMessageBox.warning(self, "Invalid Input", "Task name cannot be empty.")
                return
            if min_hp > max_hp:
                QMessageBox.warning(self, "Invalid Input", "Minimum attacks cannot exceed maximum attacks.")
                return
            if name in self.task_manager.tasks:
                QMessageBox.warning(self, "Duplicate Task", f"Task '{name}' already exists.")
                return
            self.task_manager.add_task(name, min_hp, max_hp, active)
            self.refresh_task_list()

    def edit_task(self):
        """Opens a dialog to edit the selected task."""
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a task to edit.")
            return
        item_text = selected_items[0].text()
        original_name = item_text.split(" (")[0]
        task_info = self.task_manager.tasks.get(original_name, {})
        dialog = TaskEditDialog(self, original_name, task_info.get("min", 1), task_info.get("max", 1), task_info.get("active", True))
        if dialog.exec_() == QDialog.Accepted:
            new_name, min_hp, max_hp, active = dialog.get_task_data()
            if not new_name:
                QMessageBox.warning(self, "Invalid Input", "Task name cannot be empty.")
                return
            if min_hp > max_hp:
                QMessageBox.warning(self, "Invalid Input", "Minimum attacks cannot exceed maximum attacks.")
                return
            if new_name != original_name and new_name in self.task_manager.tasks:
                QMessageBox.warning(self, "Duplicate Task", f"Task '{new_name}' already exists.")
                return
            self.task_manager.edit_task(original_name, new_name, min_hp, max_hp, active)
            self.refresh_task_list()

    def delete_task(self):
        """Deletes the selected task."""
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a task to delete.")
            return
        item_text = selected_items[0].text()
        task_name = item_text.split(" (")[0]
        confirm = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete task '{task_name}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.task_manager.delete_task(task_name)
            self.refresh_task_list()

    def save_and_close(self):
        """Saves the tasks and closes the dialog."""
        self.task_manager.save_tasks()
        self.saved = True
        self.accept()


class TaskEditDialog(QDialog):
    """
    Dialog for adding or editing a task.
    """
    def __init__(self, parent=None, name="", min_hp=1, max_hp=1, active=True):
        super().__init__(parent)
        self.setWindowTitle("Task Editor")
        self.setFixedSize(300, 250)
        self.init_ui(name, min_hp, max_hp, active)

    def init_ui(self, name, min_hp, max_hp, active):
        layout = QVBoxLayout()

        # Task Name
        layout.addWidget(QLabel("Task Name:"))
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        layout.addWidget(self.name_input)

        # Minimum HP
        layout.addWidget(QLabel("Minimum Attacks:"))
        self.min_hp_input = QSpinBox()
        self.min_hp_input.setRange(1, 1000)
        self.min_hp_input.setValue(min_hp)
        layout.addWidget(self.min_hp_input)

        # Maximum HP
        layout.addWidget(QLabel("Maximum Attacks:"))
        self.max_hp_input = QSpinBox()
        self.max_hp_input.setRange(1, 1000)
        self.max_hp_input.setValue(max_hp)
        layout.addWidget(self.max_hp_input)

        # Active Checkbox
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(active)
        layout.addWidget(self.active_checkbox)

        # Buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def get_task_data(self):
        """Retrieves the entered task data."""
        name = self.name_input.text().strip()
        min_hp = self.min_hp_input.value()
        max_hp = self.max_hp_input.value()
        active = self.active_checkbox.isChecked()
        return name, min_hp, max_hp, active
