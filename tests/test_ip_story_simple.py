from modules.image_generator import ImageGenerator
import asyncio
import os
import logging
import shutil

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_ip_story():
    """Test a simple story sequence using IP adapters."""
    
    # Create characters directory if it doesn't exist
    characters_dir = "characters"
    os.makedirs(characters_dir, exist_ok=True)
    
    # Check for reference image
    reference_path = os.path.join(characters_dir, "warrior_reference.png")
    if not os.path.exists(reference_path):
        logger.error(f"Please place a reference image at: {reference_path}")
        logger.error("The image should be a clear portrait/headshot of a warrior character")
        return
    
    # Initialize the image generator
    generator = ImageGenerator()
    
    # Define our main character
    hero = {
        "name": "Warrior",
        "description": "A brave warrior in shining armor",
        "reference_image": reference_path
    }
    
    # Define our story nodes with increasing complexity
    story_nodes = [
        {
            "title": "The Tavern",
            "description": "A warrior sits at a wooden table in a cozy tavern, warm lighting illuminates the scene",
            "characters": [
                {"character": hero, "weight": 0.8}
            ],
            "style": "warm lighting, cozy atmosphere, indoor scene",
            "quality": "ULTRA"
        },
        {
            "title": "The Forest Path",
            "description": "The warrior walks through a mystical forest path, sunbeams filtering through the leaves",
            "characters": [
                {"character": hero, "weight": 0.8}
            ],
            "style": "fantasy forest, mystical, nature, sunbeams",
            "quality": "ULTRA"
        },
        {
            "title": "The Ancient Ruins",
            "description": "Standing before ancient stone ruins, the warrior examines mysterious glowing runes",
            "characters": [
                {"character": hero, "weight": 0.8}
            ],
            "style": "ancient ruins, mysterious, glowing runes, dramatic lighting",
            "quality": "ULTRA"
        },
        {
            "title": "The Dragon's Cave",
            "description": "The warrior cautiously enters a dragon's cave filled with treasure and gleaming crystals",
            "characters": [
                {"character": hero, "weight": 0.8}
            ],
            "style": "cave interior, treasure, crystals, dramatic lighting",
            "quality": "ULTRA"
        },
        {
            "title": "The Final Battle",
            "description": "With sword raised high, the warrior faces off against a mighty dragon",
            "characters": [
                {"character": hero, "weight": 0.9}
            ],
            "style": "epic battle scene, dragon, fire effects, dramatic lighting",
            "quality": "ULTRA"
        }
    ]
    
    # Create output directory if it doesn't exist
    output_dir = "story_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate images for each story node
    for i, node in enumerate(story_nodes):
        try:
            logger.info(f"Generating image for node {i+1}: {node['title']}")
            
            # Prepare the structured prompt
            prompt_data = {
                "main": node["description"],
                "style": node["style"],
                "details": "masterpiece, intricate detail",
                "quality": node["quality"]
            }
            
            # Generate the scene with character
            image_path = await generator.generate_scene_with_characters(
                prompt_data=prompt_data,
                characters=node["characters"],
                output_path=os.path.join(output_dir, f"node_{i+1}.png")
            )
            
            if image_path:
                logger.info(f"Successfully generated image: {image_path}")
            else:
                logger.error(f"Failed to generate image for node {i+1}")
                
        except Exception as e:
            logger.error(f"Error generating image for node {i+1}: {e}")
            continue
            
    logger.info("Story generation complete!")

if __name__ == "__main__":
    asyncio.run(test_ip_story())
