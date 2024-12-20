from core.story.story_content import StoryContent
from core.story.character_descriptions import description_manager

def test_character_descriptions():
    # Test prompt with character names
    test_prompt = "zaljin_young and rakjin discuss battle plans while grexx watches from the shadows, with karga standing guard"
    
    # Create a story content object with the test prompt
    content = StoryContent(
        text="Test story node",
        node_key="test_node",
        image_prompt=test_prompt
    )
    
    # Print the original and expanded prompts
    print("\nOriginal prompt:")
    print(test_prompt)
    print("\nExpanded prompt:")
    print(content.image_prompt)

if __name__ == "__main__":
    test_character_descriptions()
