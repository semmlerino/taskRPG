import logging
from functools import wraps
from typing import Callable, Any
from PyQt5.QtWidgets import QMessageBox

def handle_errors(show_dialog: bool = True) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {str(e)}")
                if show_dialog:
                    QMessageBox.critical(
                        None,
                        "Error",
                        f"An error occurred: {str(e)}"
                    )
                return None
        return wrapper
    return decorator 