from dataclasses import dataclass
from typing import Optional, Dict, List
from .character_descriptions import description_manager

@dataclass
class StoryContent:
    """Represents the displayable content of a story node."""
    text: str
    node_key: str
    image_path: Optional[str] = None
    environment: Optional[str] = None
    event: Optional[str] = None
    npc_info: Optional[Dict] = None
    battle_info: Optional[Dict] = None
    choices: Optional[List[Dict]] = None
    image_prompt: Optional[str] = None

    def __post_init__(self):
        """Process image prompt after initialization to expand character descriptions"""
        if self.image_prompt:
            self.image_prompt = description_manager.expand_character_descriptions(self.image_prompt)

    @property
    def battle(self) -> bool:
        """Return True if this node contains battle content."""
        if isinstance(self.battle_info, dict):
            # Check if the dictionary has battle-related keys
            return bool(self.battle_info.get("battle") or 
                       self.battle_info.get("enemy") or 
                       self.battle_info.get("message"))
        return bool(self.battle_info)  # Handle True/False/None cases

    def to_html(self) -> str:
        """Convert content to HTML format for display."""
        html_parts = [f"<p>{self.text}</p>"]
        
        if self.environment:
            html_parts.append(f"<p><i>Environment:</i> {self.environment}</p>")
            
        if self.event:
            html_parts.append(f"<p><i>Event:</i> {self.event}</p>")
            
        if self.npc_info:
            html_parts.extend(self._generate_npc_html())
            
        if self.battle_info:
            html_parts.extend(self._generate_battle_html())
            
        return "\n".join(html_parts)

    def _generate_npc_html(self) -> List[str]:
        """Generate HTML for NPC interactions."""
        html_parts = []
        if isinstance(self.npc_info, list):
            for npc in self.npc_info:
                html_parts.append(self._format_npc_dialogue(npc))
        elif isinstance(self.npc_info, dict):
            html_parts.append(self._format_npc_dialogue(self.npc_info))
        return html_parts

    def _format_npc_dialogue(self, npc: Dict) -> str:
        """Format NPC dialogue."""
        name = npc.get("name", "Unknown NPC")
        dialogue = npc.get("dialogue", "")
        return f"<p><b>{name} says:</b> \"{dialogue}\"</p>"

    def _generate_battle_html(self) -> List[str]:
        """Generate HTML for battle information."""
        html_parts = []
        
        # Handle case where battle_info might be True/False
        if not isinstance(self.battle_info, dict):
            return html_parts
            
        battle_data = self.battle_info.get("battle", self.battle_info)
        message = battle_data.get("message", "An enemy appears!")
        enemy_name = battle_data.get("enemy", "Unknown Enemy")
        html_parts.append(f"<p><i>{message}</i></p>")
        html_parts.append(f"<p>A <b>{enemy_name}</b> appears!</p>")
        return html_parts
