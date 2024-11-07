# modules/core/error_handler.py

import logging
import traceback
from typing import Dict, Callable, Type, Optional
from dataclasses import dataclass
from enum import Enum, auto

class ErrorSeverity(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class ErrorContext:
    """Context information for errors."""
    component: str
    operation: str
    state: Dict
    severity: ErrorSeverity

class ErrorHandler:
    """Centralized error handling with recovery strategies."""
    
    def __init__(self):
        self._recovery_handlers: Dict[Type[Exception], Callable] = {}
        self._fallback_handler: Optional[Callable] = None
        
    def register_handler(self, exception_type: Type[Exception], handler: Callable):
        """Register a recovery handler for an exception type."""
        self._recovery_handlers[exception_type] = handler
        
    def set_fallback_handler(self, handler: Callable):
        """Set the fallback handler for unhandled exceptions."""
        self._fallback_handler = handler
        
    def handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle an error with appropriate recovery strategy.
        
        Returns:
            bool: True if error was handled, False otherwise
        """
        try:
            # Log the error with context
            logging.error(
                f"Error in {context.component}.{context.operation}\n"
                f"Severity: {context.severity.name}\n"
                f"State: {context.state}\n"
                f"Error: {str(error)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            # Find and execute appropriate handler
            handler = self._recovery_handlers.get(type(error))
            if handler:
                handler(error, context)
                return True
                
            # Use fallback handler if available
            if self._fallback_handler:
                self._fallback_handler(error, context)
                return True
                
            return False
            
        except Exception as e:
            logging.critical(f"Error in error handler: {e}")
            return False
            
    def create_context(self, component: str, operation: str, 
                      state: Dict, severity: ErrorSeverity) -> ErrorContext:
        """Create an error context."""
        return ErrorContext(component, operation, state, severity)
