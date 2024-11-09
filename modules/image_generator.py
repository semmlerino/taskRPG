# modules/image_generator.py

import logging
from typing import Optional, Dict

class ImageGenerator:
    """
    Handles image path caching and management in memory.
    """
    def __init__(self):
        """Initialize the ImageGenerator with an empty cache."""
        self.image_cache: Dict[str, str] = {}
        logging.info("ImageGenerator initialized")

    def cache_image(self, key: str, image_path: str) -> None:
        """
        Add an image path to the cache.
        
        Args:
            key (str): Unique identifier for the image
            image_path (str): Path to the image file
        """
        self.image_cache[key] = image_path
        logging.debug(f"Cached image path for key: {key}")

    def get_cached_image(self, key: str) -> Optional[str]:
        """
        Retrieve an image path from the cache.
        
        Args:
            key (str): Unique identifier for the image
            
        Returns:
            Optional[str]: Path to the cached image or None if not found
        """
        return self.image_cache.get(key)

    def remove_from_cache(self, key: str) -> None:
        """
        Remove a specific image path from the cache.
        
        Args:
            key (str): Unique identifier for the image to remove
        """
        if key in self.image_cache:
            del self.image_cache[key]
            logging.debug(f"Removed image path from cache for key: {key}")

    def clear_cache(self) -> None:
        """Clear the entire image cache from memory."""
        self.image_cache.clear()
        logging.info("Image cache cleared")

    def __del__(self):
        """Cleanup when object is deleted."""
        self.clear_cache()