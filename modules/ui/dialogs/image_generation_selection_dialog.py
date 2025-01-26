from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt
import logging


class ImageGenerationSelectionDialog(QDialog):
    """Dialog for selecting which stories to generate images for."""

    def __init__(self, story_data_map, parent=None):
        """Initialize the dialog with story data.
        
        Args:
            story_data_map: Dictionary mapping story names to their missing image counts
            parent: Parent widget
        """
        super().__init__(parent)
        self.story_data_map = story_data_map
        self.selected_stories = []
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Select Stories for Image Generation")
        layout = QVBoxLayout()

        # Add description label
        desc_label = QLabel(
            "Select the stories you want to generate images for:"
        )
        layout.addWidget(desc_label)

        # Create list widget for stories
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.NoSelection)

        # Add stories to list with checkboxes
        total_missing = 0
        for story_name, data in self.story_data_map.items():
            missing_count = len(data.get('missing_images', []))
            if missing_count > 0:
                total_missing += missing_count
                item = QListWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)  # Default to checked
                item.setText(f"{story_name} ({missing_count} missing images)")
                item.setData(Qt.UserRole, story_name)
                self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # Add total count label
        total_label = QLabel(f"Total missing images: {total_missing}")
        layout.addWidget(total_label)

        # Add select all/none buttons
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_none_btn = QPushButton("Select None")
        select_all_btn.clicked.connect(self.select_all)
        select_none_btn.clicked.connect(self.select_none)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(select_none_btn)
        layout.addLayout(select_layout)

        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def select_all(self):
        """Select all stories in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def select_none(self):
        """Deselect all stories in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)

    def accept(self):
        """Handle dialog acceptance by collecting selected stories."""
        self.selected_stories = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                story_name = item.data(Qt.UserRole)
                self.selected_stories.append(story_name)
        super().accept()
