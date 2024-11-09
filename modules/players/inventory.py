import logging
from typing import List, Dict, Union

class Inventory:
    """Manages player inventory."""
    def __init__(self):
        self.items: List[Union[str, Dict]] = []

    def add_item(self, item: Union[str, Dict]):
        """Add an item to inventory."""
        if isinstance(item, dict) and 'name' in item:
            item_name = item['name']
        elif isinstance(item, str):
            item_name = item
        else:
            logging.error("Invalid item format. Item must be a string or a dict with a 'name' key.")
            return

        self.items.append(item)
        logging.info(f"Item added to inventory: {item_name}")

    def remove_item(self, item_name: str):
        """Remove an item from inventory."""
        for item in self.items[:]:  # Create a copy to iterate over
            if isinstance(item, dict) and item.get('name') == item_name:
                self.items.remove(item)
                logging.info(f"Item removed from inventory: {item_name}")
                return
            elif isinstance(item, str) and item == item_name:
                self.items.remove(item)
                logging.info(f"Item removed from inventory: {item_name}")
                return
        logging.warning(f"Attempted to remove non-existent item: {item_name}")

    def has_item(self, item_name: str) -> bool:
        """Check if an item exists in inventory."""
        return any(
            (item.get('name') == item_name if isinstance(item, dict) else item == item_name)
            for item in self.items
        )

    def get_items(self) -> List[Union[str, Dict]]:
        """Get all inventory items."""
        return self.items.copy()

    def clear(self):
        """Clear all items from inventory."""
        self.items.clear()
        logging.info("Inventory cleared")
