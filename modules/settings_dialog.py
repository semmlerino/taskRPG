# modules/settings_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QLineEdit, QSpinBox, QCheckBox, QMessageBox,
    QHeaderView
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from .game_logic import TaskManager

class SettingsDialog(QDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(700, 500)
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
        
        if (old_min is not None and new_min is not None and abs(new_min - old_min) > old_min * 0.5) or \
           (old_max is not None and new_max is not None and abs(new_max - old_max) > old_max * 0.5):
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

    def save_and_close(self):
        self.task_manager.save_tasks()
        self.saved = True
        self.accept()

class TaskEditDialog(QDialog):
    def __init__(self, parent=None, name="", min_hp=1, max_hp=1, active=True, no_number=False):
        super().__init__(parent)
        self.setWindowTitle("Task Editor")
        self.setFixedSize(400, 350)
        self.init_ui(name, min_hp, max_hp, active, no_number)

    def init_ui(self, name, min_hp, max_hp, active, no_number):
        layout = QVBoxLayout()

        # Task Name
        name_label = QLabel("Task Name:")
        name_label.setFont(QFont("Arial", 12))
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        layout.addWidget(self.name_input)

        # No Numbering Checkbox
        self.no_number_checkbox = QCheckBox("No Numbering (Ignore Min and Max)")
        self.no_number_checkbox.setChecked(no_number)
        self.no_number_checkbox.setFont(QFont("Arial", 12))
        self.no_number_checkbox.stateChanged.connect(self.toggle_numbering)
        layout.addWidget(self.no_number_checkbox)

        # Minimum Attacks
        min_label = QLabel("Minimum Attacks:")
        min_label.setFont(QFont("Arial", 12))
        layout.addWidget(min_label)
        self.min_hp_input = QSpinBox()
        self.min_hp_input.setRange(0, 1000)
        self.min_hp_input.setValue(min_hp if min_hp is not None else 0)
        layout.addWidget(self.min_hp_input)

        # Maximum Attacks
        max_label = QLabel("Maximum Attacks:")
        max_label.setFont(QFont("Arial", 12))
        layout.addWidget(max_label)
        self.max_hp_input = QSpinBox()
        self.max_hp_input.setRange(0, 1000)
        self.max_hp_input.setValue(max_hp if max_hp is not None else 0)
        layout.addWidget(self.max_hp_input)

        # Active Checkbox
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(active)
        self.active_checkbox.setFont(QFont("Arial", 12))
        layout.addWidget(self.active_checkbox)

        # Buttons
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFont(QFont("Arial", 10))
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont("Arial", 10))
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)


        # Initialize numbering state
        if no_number:
            self.toggle_numbering()

    def toggle_numbering(self):
        """Enables or disables the min and max inputs based on the 'No Numbering' checkbox."""
        if self.no_number_checkbox.isChecked():
            self.min_hp_input.setEnabled(False)
            self.max_hp_input.setEnabled(False)
            self.min_hp_input.setValue(0)
            self.max_hp_input.setValue(0)
        else:
            self.min_hp_input.setEnabled(True)
            self.max_hp_input.setEnabled(True)

    def get_task_data(self):
        """Retrieves the entered task data."""
        name = self.name_input.text().strip()
        no_number = self.no_number_checkbox.isChecked()
        min_hp = self.min_hp_input.value() if not no_number else None
        max_hp = self.max_hp_input.value() if not no_number else None
        active = self.active_checkbox.isChecked()
        return name, min_hp, max_hp, active, no_number