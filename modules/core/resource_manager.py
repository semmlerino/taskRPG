# modules/core/resource_manager.py

import weakref
import logging
from typing import Dict, Any, Optional, Callable
from collections import OrderedDict

class LRUCache:
    """Least Recently Used Cache implementation."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = OrderedDict()
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache, moving it to most recently used."""
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
        
    def put(self, key: str, value: Any):
        """Put item in cache, removing least recently used if necessary."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

class ResourceManager:
    """Manages application resources with automatic cleanup."""
    
    def __init__(self, max_cache_size: int = 100):
        self._resources = weakref.WeakValueDictionary()
        self._cache = LRUCache(max_cache_size)
        self._registered_cleanups: Dict[str, Callable] = {}
        
    def register_resource(self, resource_id: str, resource: Any, 
                         cleanup_handler: Optional[Callable] = None):
        """Register a resource with optional cleanup handler."""
        try:
            self._resources[resource_id] = resource
            if cleanup_handler:
                self._registered_cleanups[resource_id] = cleanup_handler
            logging.debug(f"Registered resource: {resource_id}")
        except Exception as e:
            logging.error(f"Error registering resource {resource_id}: {e}")
            
    def get_resource(self, resource_id: str) -> Optional[Any]:
        """Get a resource by ID."""
        # Check cache first
        if cached := self._cache.get(resource_id):
            return cached
            
        # Check resources
        resource = self._resources.get(resource_id)
        if resource:
            self._cache.put(resource_id, resource)
        return resource
        
    def cleanup_resource(self, resource_id: str):
        """Clean up a specific resource."""
        try:
            if cleanup_handler := self._registered_cleanups.get(resource_id):
                cleanup_handler(self._resources.get(resource_id))
            if resource_id in self._resources:
                del self._resources[resource_id]
            if resource_id in self._registered_cleanups:
                del self._registered_cleanups[resource_id]
            logging.debug(f"Cleaned up resource: {resource_id}")
        except Exception as e:
            logging.error(f"Error cleaning up resource {resource_id}: {e}")
            
    def cleanup_all(self):
        """Clean up all resources."""
        for resource_id in list(self._resources.keys()):
            self.cleanup_resource(resource_id)
        self._cache.cache.clear()
        logging.info("All resources cleaned up")
