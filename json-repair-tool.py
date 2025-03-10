#!/usr/bin/env python3
# json_repair_tool.py

import os
import json
import re
import argparse
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("json_repair.log")
    ]
)

class JsonRepairTool:
    """
    Tool to scan a directory for JSON files, identify parsing errors,
    and repair them with user approval.
    """
    
    def __init__(self, directory: str, backup: bool = True):
        """
        Initialize the repair tool.
        
        Args:
            directory: The directory to scan for JSON files
            backup: Whether to create backups of files before repairing
        """
        self.directory = os.path.abspath(directory)
        self.backup = backup
        self.invalid_files = []
        self.fixed_files = []
        self.failed_files = []
    
    def scan_directory(self) -> List[str]:
        """
        Scan the directory for JSON files and return a list of invalid ones.
        
        Returns:
            List of paths to invalid JSON files
        """
        print(f"\nScanning directory: {self.directory}")
        json_files = []
        invalid_files = []
        
        # Find all JSON files
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        print(f"Found {len(json_files)} JSON files.")
        
        # Check each JSON file for validity
        for file_path in json_files:
            if not self.is_valid_json(file_path):
                invalid_files.append(file_path)
        
        self.invalid_files = invalid_files
        return invalid_files
    
    def is_valid_json(self, file_path: str) -> bool:
        """
        Check if a file contains valid JSON.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            True if the file contains valid JSON, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except Exception as e:
            relative_path = os.path.relpath(file_path, self.directory)
            logging.info(f"Found invalid JSON in: {relative_path} - Error: {str(e)}")
            return False
    
    def repair_json_file(self, file_path: str) -> bool:
        """
        Attempt to repair a malformed JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            True if repair was successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create backup if enabled
            if self.backup:
                backup_path = f"{file_path}.bak"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logging.info(f"Created backup at: {backup_path}")
            
            # Attempt to repair the file
            repaired_content = self.fix_unescaped_quotes(content)
            
            # Test if the repair worked
            try:
                repaired_json = json.loads(repaired_content)
                
                # Write the repaired content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(repaired_json, f, indent=4, ensure_ascii=False)
                
                relative_path = os.path.relpath(file_path, self.directory)
                logging.info(f"Successfully repaired: {relative_path}")
                return True
                
            except Exception as e:
                logging.error(f"Repair attempt failed for {file_path}: {str(e)}")
                return False
        
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")
            return False
    
    def fix_unescaped_quotes(self, content: str) -> str:
        """
        Fix unescaped quotes in JSON content.
        
        Args:
            content: JSON content as a string
            
        Returns:
            Repaired JSON content
        """
        # Method 1: Fix quotes in string values using regex
        pattern = r':\s*"(.*?)"([^,}\]])'
        
        def replace_match(match):
            text = match.group(1)
            ending = match.group(2)
            
            # Escape any quotes that appear within the string
            fixed_text = text.replace('"', '\\"')
            return f': "{fixed_text}"{ending}'
        
        content = re.sub(pattern, replace_match, content)
        
        # Method 2: Line-by-line analysis
        lines = content.split('\n')
        for i in range(len(lines)):
            line = lines[i]
            # Count quotes in the line to detect odd numbers
            quote_count = line.count('"')
            if quote_count % 2 != 0:
                # Try to fix potential unescaped quotes in this line
                in_string = False
                fixed_line = ""
                for j in range(len(line)):
                    char = line[j]
                    prev_char = line[j-1] if j > 0 else None
                    
                    if char == '"' and prev_char != '\\':
                        in_string = not in_string
                    
                    # If we're in a string and find an unescaped quote, escape it
                    if in_string and char == '"' and prev_char != '\\' and j < len(line) - 1:
                        # Only escape this quote if it's not the closing quote
                        if j < len(line) - 1 and line[j+1] not in [',', '}', ']', ':']:
                            fixed_line += '\\'
                    
                    fixed_line += char
                
                lines[i] = fixed_line
        
        # Method 3: Fix common multi-line string issues
        content = '\n'.join(lines)
        
        # Replace multi-line strings that may cause issues
        content = re.sub(r':\s*"(.*?)[\n\r](.*?)"', 
                      lambda m: f': "{m.group(1)} {m.group(2)}"', 
                      content, flags=re.DOTALL)
        
        return content
    
    def interactive_repair(self):
        """
        Interactive mode to let the user choose which files to repair.
        """
        if not self.invalid_files:
            print("No invalid JSON files found. Everything looks good!")
            return
        
        print(f"\nFound {len(self.invalid_files)} invalid JSON files:")
        for i, file_path in enumerate(self.invalid_files, 1):
            relative_path = os.path.relpath(file_path, self.directory)
            print(f"{i}. {relative_path}")
        
        while True:
            choice = input("\nChoose an option:\n"
                          "1. Repair all files\n"
                          "2. Choose specific files to repair\n"
                          "3. Exit without repairing\n"
                          "Your choice (1-3): ")
            
            if choice == '1':
                self.repair_all_files()
                break
            elif choice == '2':
                self.repair_selected_files()
                break
            elif choice == '3':
                print("Exiting without making any changes.")
                break
            else:
                print("Invalid choice. Please try again.")
    
    def repair_all_files(self):
        """
        Repair all invalid JSON files.
        """
        print(f"\nRepairing all {len(self.invalid_files)} files...")
        
        for file_path in self.invalid_files:
            relative_path = os.path.relpath(file_path, self.directory)
            print(f"Repairing: {relative_path}... ", end="")
            
            if self.repair_json_file(file_path):
                self.fixed_files.append(file_path)
                print("SUCCESS")
            else:
                self.failed_files.append(file_path)
                print("FAILED")
        
        self.print_summary()
    
    def repair_selected_files(self):
        """
        Let the user select specific files to repair.
        """
        while True:
            selection = input("\nEnter file numbers to repair (comma-separated) or 'all': ")
            
            if selection.lower() == 'all':
                self.repair_all_files()
                break
                
            try:
                # Parse selected indices
                indices = [int(idx.strip()) for idx in selection.split(',')]
                
                # Validate indices
                invalid_indices = [idx for idx in indices if idx < 1 or idx > len(self.invalid_files)]
                if invalid_indices:
                    print(f"Invalid file numbers: {', '.join(map(str, invalid_indices))}")
                    continue
                
                # Repair selected files
                print("\nRepairing selected files...")
                for idx in indices:
                    file_path = self.invalid_files[idx-1]
                    relative_path = os.path.relpath(file_path, self.directory)
                    print(f"Repairing: {relative_path}... ", end="")
                    
                    if self.repair_json_file(file_path):
                        self.fixed_files.append(file_path)
                        print("SUCCESS")
                    else:
                        self.failed_files.append(file_path)
                        print("FAILED")
                
                self.print_summary()
                break
                
            except ValueError:
                print("Invalid input. Please enter comma-separated numbers or 'all'.")
    
    def print_summary(self):
        """
        Print a summary of the repair operation.
        """
        print("\n----- REPAIR SUMMARY -----")
        print(f"Total invalid files: {len(self.invalid_files)}")
        print(f"Successfully repaired: {len(self.fixed_files)}")
        print(f"Failed to repair: {len(self.failed_files)}")
        
        if self.failed_files:
            print("\nThe following files could not be automatically repaired:")
            for file_path in self.failed_files:
                relative_path = os.path.relpath(file_path, self.directory)
                print(f"- {relative_path}")
            print("\nThese files may require manual intervention.")
        
        if self.fixed_files:
            print("\nRepaired files:")
            for file_path in self.fixed_files:
                relative_path = os.path.relpath(file_path, self.directory)
                print(f"- {relative_path}")
            
            if self.backup:
                print("\nBackups were created with .bak extension.")

def main():
    """
    Main function to run the JSON repair tool.
    """
    parser = argparse.ArgumentParser(description="Repair invalid JSON files in a directory")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to scan (default: current directory)")
    parser.add_argument("--no-backup", action="store_true", help="Don't create backups before repairing")
    args = parser.parse_args()
    
    # Create and run the repair tool
    repair_tool = JsonRepairTool(args.directory, not args.no_backup)
    repair_tool.scan_directory()
    repair_tool.interactive_repair()

if __name__ == "__main__":
    main()
