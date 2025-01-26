from dataclasses import dataclass
from typing import Optional, Dict, List
from .character_descriptions import description_manager
import logging

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
        try:
            html_parts = []
            
            # Convert plain text to HTML paragraphs
            if self.text:
                text_parts = self.text.split('\n')
                html_parts.extend([f"<p>{part}</p>" if part.strip() else "<br>" for part in text_parts])
            
            if self.environment:
                html_parts.append(f"<p><i>Environment:</i> {self.environment}</p>")
                
            if self.event:
                html_parts.append(f"<p><i>Event:</i> {self.event}</p>")
                
            if self.npc_info:
                npc_html = self._generate_npc_html()
                if npc_html:
                    html_parts.extend(npc_html)
                
            if self.battle_info:
                battle_html = self._generate_battle_html()
                if battle_html:
                    html_parts.extend(battle_html)
            
            # Join with newlines and wrap in a div with proper styling
            html_content = f"""
            <div style='font-family: Arial, sans-serif; line-height: 1.6; color: #333333;'>
                {"\n".join(html_parts)}
            </div>
            """
            
            logging.info(f"Generated HTML content length: {len(html_content)}")
            logging.info(f"HTML parts count: {len(html_parts)}")
            return html_content

        except Exception as e:
            logging.error(f"Error generating HTML: {e}")
            return f"<p style='color: red;'>Error generating content: {str(e)}</p>"

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
        try:
            html_parts = []
            
            if not self.battle_info:
                return html_parts
                
            # Extract battle information
            battle_data = self.battle_info
            if isinstance(battle_data, dict):
                enemy_name = battle_data.get("enemy", "Unknown Enemy")
                message = battle_data.get("message", "")
                
                # Add battle message if present
                if message:
                    html_parts.append(f"""
                        <div style='margin: 10px 0; padding: 10px; background-color: rgba(255, 0, 0, 0.1); border-left: 4px solid #ff0000;'>
                            <p style='font-style: italic; margin: 5px 0;'>{message}</p>
                            <p style='font-weight: bold; margin: 5px 0;'>Encountered: <span style='color: #ff0000'>{enemy_name}</span>!</p>
                        </div>
                    """)
                
            logging.info(f"Generated battle HTML parts: {len(html_parts)}")
            return html_parts

        except Exception as e:
            logging.error(f"Error generating battle HTML: {e}")
            return [f"<p style='color: red;'>Error in battle content: {str(e)}</p>"]
