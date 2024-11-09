from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QGroupBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class PlayerPanel(QWidget):
    """Displays player statistics and inventory."""
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        player_group = QGroupBox("Player Stats")
        player_layout = QVBoxLayout()
        
        self.level_label = QLabel(f"Level: {self.player.stats.level}")
        self.level_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.xp_label = QLabel(f"XP: {self.player.stats.experience}/{self.player.stats.experience_to_next_level}")
        self.xp_label.setFont(QFont("Arial", 14))
        
        player_layout.addWidget(self.level_label)
        player_layout.addWidget(self.xp_label)
        
        self.inventory_label = QLabel("Inventory: Empty")
        self.inventory_label.setFont(QFont("Arial", 12))
        self.inventory_label.setWordWrap(True)
        player_layout.addWidget(self.inventory_label)
        
        player_group.setLayout(player_layout)
        layout.addWidget(player_group)
        
        self.setLayout(layout)
    
    def update_panel(self):
        """Updates the player stats and inventory display."""
        self.level_label.setText(f"Level: {self.player.stats.level}")
        self.xp_label.setText(f"XP: {self.player.stats.experience}/{self.player.stats.experience_to_next_level}")
        inventory_items = self.player.inventory.get_items()
        if inventory_items:
            items_text = ', '.join(
                item['name'] if isinstance(item, dict) else item 
                for item in inventory_items
            )
            self.inventory_label.setText(f"Inventory: {items_text}")
        else:
            self.inventory_label.setText("Inventory: Empty")
