# modules/settings_dialog.py

import os
import json
import logging
from typing import Dict
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QCheckBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from .game_logic import TaskManager

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
        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel("Edit existing tasks or add new tasks.")
        instructions.setFont(QFont("Arial", 12))
        layout.addWidget(instructions)

        # Tasks Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Task Name", "Min", "Max", "Active"])
        self.table.setRowCount(len(self.updated_tasks))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, (task, details) in enumerate(self.updated_tasks.items()):
            self.table.setItem(row, 0, QTableWidgetItem(task))
            self.table.setItem(row, 1, QTableWidgetItem(str(details["min"]) if details["min"] is not None else ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(details["max"]) if details["max"] is not None else ""))

            active_checkbox = QTableWidgetItem()
            active_checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            active_checkbox.setCheckState(Qt.Checked if details.get("active", True) else Qt.Unchecked)
            self.table.setItem(row, 3, active_checkbox)

        layout.addWidget(self.table)

        # Buttons for Editing
        edit_buttons_layout = QHBoxLayout()

        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_task)
        edit_buttons_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_task)
        edit_buttons_layout.addWidget(self.delete_button)

        layout.addLayout(edit_buttons_layout)

        # Add New Task Section
        add_layout = QHBoxLayout()

        self.new_task_edit = QLineEdit()
        self.new_task_edit.setPlaceholderText("New Task Name")
        add_layout.addWidget(self.new_task_edit)

        self.new_min_spin = QSpinBox()
        self.new_min_spin.setRange(0, 1000)
        self.new_min_spin.setPrefix("Min: ")
        add_layout.addWidget(self.new_min_spin)

        self.new_max_spin = QSpinBox()
        self.new_max_spin.setRange(0, 1000)
        self.new_max_spin.setPrefix("Max: ")
        add_layout.addWidget(self.new_max_spin)

        self.add_active_checkbox = QCheckBox("Active")
        self.add_active_checkbox.setChecked(True)
        add_layout.addWidget(self.add_active_checkbox)

        self.add_button = QPushButton("Add Task")
        self.add_button.clicked.connect(self.add_task)
        add_layout.addWidget(self.add_button)

        layout.addLayout(add_layout)

        # Feedback Label
        self.feedback_label = QLabel("")
        self.feedback_label.setFont(QFont("Arial", 10))
        self.feedback_label.setStyleSheet("color: blue;")
        layout.addWidget(self.feedback_label)

        # Save and Close Buttons
        save_close_layout = QHBoxLayout()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_changes)
        save_close_layout.addWidget(self.save_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        save_close_layout.addWidget(self.close_button)

        layout.addLayout(save_close_layout)

        self.setLayout(layout)

    def edit_task(self):
        selected = self.table.currentRow()
        if selected < 0:
            self.feedback_label.setText("Please select a task to edit.")
            return

        task_name_item = self.table.item(selected, 0)
        min_item = self.table.item(selected, 1)
        max_item = self.table.item(selected, 2)
        active_item = self.table.item(selected, 3)

        task_name = task_name_item.text()
        current_min = min_item.text()
        current_max = max_item.text()
        is_active = active_item.checkState() == Qt.Checked

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Task: {task_name}")
        dialog.setFixedSize(300, 250)
        dialog_layout = QFormLayout()

        task_edit = QLineEdit(task_name)
        min_spin = QSpinBox()
        min_spin.setRange(0, 1000)
        if current_min:
            min_spin.setValue(int(current_min))
        else:
            min_spin.setValue(0)

        max_spin = QSpinBox()
        max_spin.setRange(0, 1000)
        if current_max:
            max_spin.setValue(int(current_max))
        else:
            max_spin.setValue(0)

        no_number_checkbox = QCheckBox("No Numbering")
        no_number_checkbox.setChecked(current_min == "" and current_max == "")
        no_number_checkbox.stateChanged.connect(lambda: self.toggle_numbering(no_number_checkbox, min_spin, max_spin))
        self.toggle_numbering(no_number_checkbox, min_spin, max_spin)

        active_checkbox = QCheckBox("Active")
        active_checkbox.setChecked(is_active)

        dialog_layout.addRow("Task Name:", task_edit)
        dialog_layout.addRow("Min:", min_spin)
        dialog_layout.addRow("Max:", max_spin)
        dialog_layout.addRow("", no_number_checkbox)
        dialog_layout.addRow("Active:", active_checkbox)

        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        dialog_layout.addRow(buttons_layout)
        dialog.setLayout(dialog_layout)

        if dialog.exec_() == QDialog.Accepted:
            new_task_name = task_edit.text().strip()
            new_min = min_spin.value()
            new_max = max_spin.value()
            no_number = no_number_checkbox.isChecked()
            new_active = active_checkbox.isChecked()

            if not new_task_name:
                self.feedback_label.setText("Task name cannot be empty.")
                return

            if not no_number:
                if new_min > new_max:
                    self.feedback_label.setText("Min cannot be greater than Max.")
                    return
                # If task name changed, handle renaming
                if new_task_name != task_name and new_task_name in self.updated_tasks:
                    self.feedback_label.setText("Task name already exists.")
                    return
                self.updated_tasks.pop(task_name)
                self.updated_tasks[new_task_name] = {
                    "min": new_min,
                    "max": new_max,
                    "active": new_active
                }
            else:
                self.updated_tasks.pop(task_name)
                self.updated_tasks[new_task_name] = {
                    "min": None,
                    "max": None,
                    "active": new_active
                }

            self.table.setItem(selected, 0, QTableWidgetItem(new_task_name))
            self.table.setItem(selected, 1, QTableWidgetItem("" if no_number else str(new_min)))
            self.table.setItem(selected, 2, QTableWidgetItem("" if no_number else str(new_max)))
            self.table.item(selected, 3).setCheckState(Qt.Checked if new_active else Qt.Unchecked)

            # If task name changed and is the current task, update it
            parent = self.parent()
            if parent.current_task == task_name:
                parent.current_task = new_task_name
                parent.display_label.setText(f"{parent.current_number} {new_task_name}" if parent.current_number else new_task_name)

            self.feedback_label.setText(f"Task '{task_name}' edited successfully.")

    def toggle_numbering(self, checkbox, min_spin, max_spin):
        if checkbox.isChecked():
            min_spin.setEnabled(False)
            max_spin.setEnabled(False)
        else:
            min_spin.setEnabled(True)
            max_spin.setEnabled(True)

    def delete_task(self):
        selected = self.table.currentRow()
        if selected < 0:
            self.feedback_label.setText("Please select a task to delete.")
            return

        task_name = self.table.item(selected, 0).text()
        # Confirm deletion silently by user interface
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("Confirm Delete")
        confirm_dialog.setFixedSize(250, 100)
        confirm_layout = QVBoxLayout()

        message = QLabel(f"Are you sure you want to delete '{task_name}'?")
        confirm_layout.addWidget(message)

        buttons_layout = QHBoxLayout()
        yes_btn = QPushButton("Yes")
        yes_btn.clicked.connect(confirm_dialog.accept)
        no_btn = QPushButton("No")
        no_btn.clicked.connect(confirm_dialog.reject)
        buttons_layout.addWidget(yes_btn)
        buttons_layout.addWidget(no_btn)

        confirm_layout.addLayout(buttons_layout)
        confirm_dialog.setLayout(confirm_layout)

        if confirm_dialog.exec_() == QDialog.Accepted:
            self.table.removeRow(selected)
            del self.updated_tasks[task_name]

            # If the deleted task is the current task, reset it
            parent = self.parent()
            if parent.current_task == task_name:
                parent.current_task = None
                parent.current_number = None
                parent.display_label.setText("Press Generate")
                parent.generate_button.setEnabled(True)
                parent.update_status()

            self.feedback_label.setText(f"Task '{task_name}' deleted successfully.")

    def add_task(self):
        task_name = self.new_task_edit.text().strip()
        min_val = self.new_min_spin.value()
        max_val = self.new_max_spin.value()
        is_active = self.add_active_checkbox.isChecked()

        if not task_name:
            self.feedback_label.setText("Task name cannot be empty.")
            return

        if task_name in self.updated_tasks:
            self.feedback_label.setText("Task already exists.")
            return

        if (min_val > 0 or max_val > 0):
            if min_val > max_val:
                self.feedback_label.setText("Min cannot be greater than Max.")
                return
            self.updated_tasks[task_name] = {"min": min_val, "max": max_val, "active": is_active}
        else:
            self.updated_tasks[task_name] = {"min": None, "max": None, "active": is_active}

        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(task_name))
        self.table.setItem(row_position, 1, QTableWidgetItem("" if min_val == 0 else str(min_val)))
        self.table.setItem(row_position, 2, QTableWidgetItem("" if max_val == 0 else str(max_val)))

        active_checkbox = QTableWidgetItem()
        active_checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        active_checkbox.setCheckState(Qt.Checked if is_active else Qt.Unchecked)
        self.table.setItem(row_position, 3, active_checkbox)

        self.new_task_edit.clear()
        self.new_min_spin.setValue(0)
        self.new_max_spin.setValue(0)
        self.add_active_checkbox.setChecked(True)

        self.feedback_label.setText(f"Task '{task_name}' added successfully.")

    def save_changes(self):
        # Update the 'active' status based on checkboxes
        for row in range(self.table.rowCount()):
            task_name = self.table.item(row, 0).text()
            active_state = self.table.item(row, 3).checkState()
            self.updated_tasks[task_name]["active"] = (active_state == Qt.Checked)

        # Update task_manager with the updated_tasks
        self.task_manager.tasks = self.updated_tasks
        self.task_manager.save_tasks()

        self.saved = True
        self.accept()

    def closeEvent(self, event):
        if not self.saved:
            reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                event.accept()
                logging.info('Window closed')
            else:
                event.ignore()
        else:
            event.accept()