import os
import subprocess
import logging

def open_file_in_editor(file_path):
    """
    Opens a file in the default editor for the system.
    
    Args:
        file_path: The path to the file to open
    """
    try:
        if os.path.exists(file_path):
            # Use the appropriate command based on the OS
            # For Windows, we use 'start' command
            subprocess.Popen(['start', '', file_path], shell=True)
            logging.info(f"Opening file in editor: {file_path}")
        else:
            logging.error(f"File not found: {file_path}")
    except Exception as e:
        logging.error(f"Error opening file in editor: {e}")