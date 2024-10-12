# modules/settings_dialog.py

import os
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QLineEdit, QSpinBox, QCheckBox, QMessageBox,
    QHeaderView
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from .game_logic import TaskManager
import json

class SettingsDialog(QDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(700, 550)  # Increased height to accommodate new settings
        self.task_manager = task_manager
        self.saved = False
        self.init_ui()
        self.load_additional_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Task Manager")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Task Table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["Task Name", "Min", "Max", "Active"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setFont(QFont("Arial", 12))
        self.task_table.itemChanged.connect(self.on_item_changed)
        self.refresh_task_table()
        layout.addWidget(QLabel("Tasks:"))
        layout.addWidget(self.task_table)

        # Buttons for Add, Edit, Delete
        buttons_layout = QHBoxLayout()
        for btn_text, btn_slot in [("Add Task", self.add_task), 
                                   ("Edit Task", self.edit_task), 
                                   ("Delete Task", self.delete_task),
                                   ("Reset to Default", self.reset_to_default)]:
            btn = QPushButton(btn_text)
            btn.setFont(QFont("Arial", 10))
            btn.clicked.connect(btn_slot)
            buttons_layout.addWidget(btn)
        layout.addLayout(buttons_layout)

        # Additional Settings
        additional_settings_group = QGroupBox("Additional Settings")
        additional_layout = QVBoxLayout()

        self.shake_animation_checkbox = QCheckBox("Enable Shaking Animation on Attack")
        self.shake_animation_checkbox.setFont(QFont("Arial", 12))
        additional_layout.addWidget(self.shake_animation_checkbox)

        additional_settings_group.setLayout(additional_layout)
        layout.addWidget(additional_settings_group)

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

    def refresh_task_table(self):
        self.task_table.blockSignals(True)
        self.task_table.setRowCount(0)
        for task_name, task_info in self.task_manager.tasks.items():
            row_position = self.task_table.rowCount()
            self.task_table.insertRow(row_position)

            # Task Name (not editable)
            name_item = QTableWidgetItem(task_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row_position, 0, name_item)

            # Min
            min_value = task_info.get('min')
            min_item = QTableWidgetItem(str(min_value) if min_value is not None else "")
            min_item.setFlags(min_item.flags() | Qt.ItemIsEditable)
            min_item.setToolTip("Enter a non-negative integer or leave blank for no minimum")
            self.task_table.setItem(row_position, 1, min_item)

            # Max
            max_value = task_info.get('max')
            max_item = QTableWidgetItem(str(max_value) if max_value is not None else "")
            max_item.setFlags(max_item.flags() | Qt.ItemIsEditable)
            max_item.setToolTip("Enter a non-negative integer or leave blank for no maximum")
            self.task_table.setItem(row_position, 2, max_item)

            # Active
            active_item = QTableWidgetItem()
            active_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            active_item.setCheckState(Qt.Checked if task_info.get('active', True) else Qt.Unchecked)
            self.task_table.setItem(row_position, 3, active_item)

        self.task_table.blockSignals(False)

    def on_item_changed(self, item):
        if item.column() in [1, 2]:  # Min or Max columns
            row = item.row()
            task_name = self.task_table.item(row, 0).text()
            min_item = self.task_table.item(row, 1)
            max_item = self.task_table.item(row, 2)
            
            try:
                min_value = int(min_item.text()) if min_item.text() else None
                max_value = int(max_item.text()) if max_item.text() else None
                
                if min_value is not None and max_value is not None and min_value > max_value:
                    raise ValueError("Min cannot be greater than Max")
                
                if self.confirm_significant_change(task_name, min_value, max_value):
                    self.task_manager.edit_task(task_name, task_name, min_value, max_value, 
                                                self.task_table.item(row, 3).checkState() == Qt.Checked)
                else:
                    self.refresh_task_table()  # Revert changes if not confirmed
            except ValueError as e:
                QMessageBox.warning(self, "Invalid Input", str(e))
                self.refresh_task_table()  # Revert changes if input is invalid
        elif item.column() == 3:  # Active column
            row = item.row()
            task_name = self.task_table.item(row, 0).text()
            min_item = self.task_table.item(row, 1)
            max_item = self.task_table.item(row, 2)
            min_value = int(min_item.text()) if min_item.text() else None
            max_value = int(max_item.text()) if max_item.text() else None
            active = item.checkState() == Qt.Checked
            self.task_manager.edit_task(task_name, task_name, min_value, max_value, active)

    def confirm_significant_change(self, task_name, new_min, new_max):
        old_task = self.task_manager.tasks.get(task_name, {})
        old_min, old_max = old_task.get('min'), old_task.get('max')
        
        if (old_min is not None and new_min is not None and abs(new_min - old_min) > (old_min * 0.5 if old_min else 0)) or \
           (old_max is not None and new_max is not None and abs(new_max - old_max) > (old_max * 0.5 if old_max else 0)):
            return QMessageBox.question(self, "Confirm Change", 
                                        f"You're making a significant change to the task '{task_name}'. Are you sure?",
                                        QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
        return True

    def add_task(self):
        dialog = TaskEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, min_hp, max_hp, active, no_number = dialog.get_task_data()
            if not name:
                QMessageBox.warning(self, "Invalid Input", "Task name cannot be empty.")
                return
            if not no_number and (min_hp is None or max_hp is None):
                QMessageBox.warning(self, "Invalid Input", "Both Min and Max must be set unless 'No Numbering' is selected.")
                return
            if not no_number and min_hp > max_hp:
                QMessageBox.warning(self, "Invalid Input", "Minimum attacks cannot exceed maximum attacks.")
                return
            if name in self.task_manager.tasks:
                QMessageBox.warning(self, "Duplicate Task", f"Task '{name}' already exists.")
                return
            self.task_manager.add_task(name, None if no_number else min_hp, 
                                       None if no_number else max_hp, active)
            self.refresh_task_table()

    def edit_task(self):
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a task to edit.")
            return
        row = self.task_table.currentRow()
        task_name = self.task_table.item(row, 0).text()
        min_hp_text = self.task_table.item(row, 1).text()
        max_hp_text = self.task_table.item(row, 2).text()
        active_state = self.task_table.item(row, 3).checkState()

        min_hp = int(min_hp_text) if min_hp_text.isdigit() else None
        max_hp = int(max_hp_text) if max_hp_text.isdigit() else None
        active = active_state == Qt.Checked

        no_number = (min_hp is None and max_hp is None)

        dialog = TaskEditDialog(self, task_name, min_hp, max_hp, active, no_number)
        if dialog.exec_() == QDialog.Accepted:
            new_name, new_min_hp, new_max_hp, new_active, new_no_number = dialog.get_task_data()
            if not new_name:
                QMessageBox.warning(self, "Invalid Input", "Task name cannot be empty.")
                return
            if not new_no_number and (new_min_hp is None or new_max_hp is None):
                QMessageBox.warning(self, "Invalid Input", "Both Min and Max must be set unless 'No Numbering' is selected.")
                return
            if not new_no_number and new_min_hp > new_max_hp:
                QMessageBox.warning(self, "Invalid Input", "Minimum attacks cannot exceed maximum attacks.")
                return
            if new_name != task_name and new_name in self.task_manager.tasks:
                QMessageBox.warning(self, "Duplicate Task", f"Task '{new_name}' already exists.")
                return
            self.task_manager.edit_task(task_name, new_name, 
                                        None if new_no_number else new_min_hp, 
                                        None if new_no_number else new_max_hp, 
                                        new_active)
            self.refresh_task_table()

    def delete_task(self):
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a task to delete.")
            return
        row = self.task_table.currentRow()
        task_name = self.task_table.item(row, 0).text()
        confirm = QMessageBox.question(self, "Confirm Deletion", 
                                       f"Are you sure you want to delete task '{task_name}'?", 
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.task_manager.delete_task(task_name)
            self.refresh_task_table()

    def reset_to_default(self):
        confirm = QMessageBox.question(self, "Confirm Reset", 
                                       "Are you sure you want to reset all tasks to their default values?", 
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.task_manager.reset_to_default()
            self.refresh_task_table()

    def load_additional_settings(self):
        """Loads additional settings from a settings file."""
        settings_dir = os.path.dirname(self.task_manager.filepath)
        settings_file = os.path.join(settings_dir, 'settings.json')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                shake_enabled = settings.get('shake_animation', True)
                self.shake_animation_checkbox.setChecked(shake_enabled)
            except Exception as e:
                logging.error(f"Failed to load additional settings. Using defaults. Error: {e}")
                self.shake_animation_checkbox.setChecked(True)
        else:
            self.shake_animation_checkbox.setChecked(True)

    def save_additional_settings(self):
        """Saves additional settings to a settings file."""
        settings = {
            'shake_animation': self.shake_animation_checkbox.isChecked()
        }
        # Use os.path.dirname to get the directory of the tasks.json file
        settings_dir = os.path.dirname(self.task_manager.filepath)
        settings_file = os.path.join(settings_dir, 'settings.json')
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            logging.info(f"Additional settings saved to {settings_file}.")
        except Exception as e:
            logging.error(f"Failed to save additional settings. Error: {e}")

    def save_and_close(self):
        self.save_additional_settings()
        self.task_manager.save_tasks()
        self.saved = True
        self.accept()
