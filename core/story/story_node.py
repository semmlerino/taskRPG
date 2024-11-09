from dataclasses import dataclass
from typing import Optional, Dict, List, Any

@dataclass
class StoryNode:
    """Represents a single node in the story."""
    key: str
    text: str
    image_prompt: Optional[str] = None
    environment: Optional[str] = None
    event: Optional[str] = None
    npc_info: Optional[Dict] = None
    battle_info: Optional[Dict] = None
    choices: Optional[List[Dict[str, Any]]] = None
    next_node: Optional[str] = None
    is_end: bool = False

    @staticmethod
    def from_dict(key: str, data: Dict[str, Any]) -> 'StoryNode':
        """Create a StoryNode from dictionary data."""
        return StoryNode(
            key=key,
            text=data.get('text', ''),
            image_prompt=data.get('image_prompt'),
            environment=data.get('environment'),
            event=data.get('event'),
            npc_info=data.get('npc'),
            battle_info=data.get('battle'),
            choices=data.get('choices'),
            next_node=data.get('next'),
            is_end=data.get('end', False)
        )

    def is_battle_node(self) -> bool:
        """Check if this is a battle node."""
        return self.battle_info is not None

    def is_choice_node(self) -> bool:
        """Check if this is a choice node."""
        return bool(self.choices)

    def get_next_node_key(self) -> Optional[str]:
        """Get the key of the next node."""
        return self.next_node if not self.is_end else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary format."""
        data = {
            'text': self.text
        }
        if self.image_prompt:
            data['image_prompt'] = self.image_prompt
        if self.environment:
            data['environment'] = self.environment
        if self.event:
            data['event'] = self.event
        if self.npc_info:
            data['npc'] = self.npc_info
        if self.battle_info:
            data['battle'] = self.battle_info
        if self.choices:
            data['choices'] = self.choices
        if self.next_node:
            data['next'] = self.next_node
        if self.is_end:
            data['end'] = True
        return data
