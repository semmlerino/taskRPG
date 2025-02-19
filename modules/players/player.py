import logging
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from modules.players.inventory import Inventory
import msvcrt  # Windows file locking
import time
from contextlib import contextmanager

@dataclass
class PlayerStats:
    """Player statistics."""
    level: int = 1
    experience: int = 0
    coins: int = 0  # New coin tracking
    experience_to_next_level: int = 100

@contextmanager
def file_lock(file_path):
    """Ensure exclusive access to file using Windows file locking."""
    start_time = time.time()
    timeout = 5  # 5 second timeout
    file_obj = None
    
    try:
        while True:
            try:
                file_obj = open(file_path, 'r+b' if Path(file_path).exists() else 'w+b')
                msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except IOError as e:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock on {file_path} after {timeout} seconds")
                time.sleep(0.1)
        yield file_obj
    finally:
        if file_obj:
            try:
                msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
            except IOError:
                pass  # Lock might already be released
            file_obj.close()

class Player:
    """Represents the player character."""
    def __init__(self):
        self.stats = PlayerStats()
        self.inventory = Inventory()
        self.save_path = Path("saves/player_state.json")
        self.load_state()  # Load existing state on initialization
        logging.info(f"Player loaded: Level {self.stats.level}, XP: {self.stats.experience}, Coins: {self.stats.coins}")

    def save_state(self):
        """Save player state to JSON file with file locking."""
        state = {
            'stats': asdict(self.stats),
            'inventory': self.inventory.items
        }
        
        try:
            self.save_path.parent.mkdir(exist_ok=True)
            lock_file = self.save_path.with_suffix('.lock')
            
            with file_lock(lock_file):
                # Read current state first
                current_state = {}
                if self.save_path.exists():
                    with open(self.save_path, 'r') as f:
                        current_state = json.load(f)
                
                # Merge states (keep higher values)
                if 'stats' in current_state:
                    state['stats']['coins'] = max(
                        state['stats']['coins'],
                        current_state['stats'].get('coins', 0)
                    )
                
                # Write merged state
                with open(self.save_path, 'w') as f:
                    json.dump(state, f, indent=4)
                
            logging.info("Player state saved successfully")
        except TimeoutError as e:
            logging.error(f"Timeout while saving player state: {str(e)}")
        except Exception as e:
            logging.error(f"Failed to save player state: {str(e)}")

    def load_state(self):
        """Load player state from JSON file with file locking."""
        if not self.save_path.exists():
            logging.info("No saved state found, using defaults")
            return

        try:
            lock_file = self.save_path.with_suffix('.lock')
            with file_lock(lock_file):
                with open(self.save_path, 'r') as f:
                    state = json.load(f)
                
                # Load stats
                stats = state.get('stats', {})
                self.stats.level = stats.get('level', 1)
                self.stats.experience = stats.get('experience', 0)
                self.stats.coins = stats.get('coins', 0)
                self.stats.experience_to_next_level = stats.get('experience_to_next_level', 100)
                
                # Load inventory
                self.inventory.items = state.get('inventory', [])
                
            logging.info("Player state loaded successfully")
        except TimeoutError as e:
            logging.error(f"Timeout while loading player state: {str(e)}")
        except Exception as e:
            logging.error(f"Failed to load player state: {str(e)}")
            # Keep default values on load failure

    def gain_experience(self, amount: int):
        """Add experience points and handle leveling."""
        self.stats.experience += amount
        logging.info(f"Player gains {amount} XP. Total XP: {self.stats.experience}")
        
        while self.stats.experience >= self.stats.experience_to_next_level:
            self.level_up()
        self.save_state()  # Save after XP changes

    def level_up(self):
        """Handle player level up."""
        self.stats.level += 1
        self.stats.experience -= self.stats.experience_to_next_level
        self.stats.experience_to_next_level = int(self.stats.experience_to_next_level * 1.5)
        logging.info(f"Player leveled up! New level: {self.stats.level}")
        self.save_state()  # Save after level up

    def get_level_progress(self) -> float:
        """Get level progress as a percentage."""
        return (self.stats.experience / self.stats.experience_to_next_level) * 100

    def earn_coins(self, amount: int):
        """Add coins to player balance."""
        self.stats.coins += amount
        logging.info(f"Player earned {amount} coins. Total: {self.stats.coins}")
        self.save_state()  # Save after earning coins

    def spend_coins(self, amount: int) -> bool:
        """Attempt to spend coins, returns True if successful."""
        if self.stats.coins >= amount:
            self.stats.coins -= amount
            logging.info(f"Spent {amount} coins. Remaining: {self.stats.coins}")
            self.save_state()  # Save after spending coins
            return True
        logging.warning(f"Insufficient coins to spend {amount}")
        return False

    def check_balance(self) -> int:
        """Return the current coin balance."""
        return self.stats.coins
