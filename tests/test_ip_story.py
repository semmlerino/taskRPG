from modules.image_generator import ImageGenerator, PromptEnhancer
import asyncio
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_ip_story():
    """Test a story sequence using IP adapters for character consistency."""
    
    # Initialize the image generator
    generator = ImageGenerator()
    
    # Define our main characters
    hero = {
        "name": "Aria",
        "description": "A young female warrior with long silver hair, wearing ornate armor",
        "reference_image": "characters/aria_reference.png"  # You'll need to provide this
    }
    
    companion = {
        "name": "Marcus",
        "description": "A wise old mage with a flowing white beard and blue robes",
        "reference_image": "characters/marcus_reference.png"  # You'll need to provide this
    }
    
    # Define our story nodes
    story_nodes = [
        {
            "title": "The Ancient Library",
            "description": "Aria and Marcus explore a vast magical library filled with floating books and glowing crystals",
            "characters": [
                {"character": hero, "weight": 0.8},
                {"character": companion, "weight": 0.7}
            ],
            "style": "magical, mystical, indoor scene, warm lighting",
            "quality": "ULTRA"
        },
        {
            "title": "The Dark Portal",
            "description": "The duo discovers a mysterious dark portal crackling with purple energy",
            "characters": [
                {"character": hero, "weight": 0.8},
                {"character": companion, "weight": 0.8}
            ],
            "style": "dark fantasy, ominous, dramatic lighting, purple energy effects",
            "quality": "ULTRA"
        },
        {
            "title": "Battle with Shadow Creatures",
            "description": "Aria draws her sword while Marcus prepares a spell as shadow creatures emerge from the portal",
            "characters": [
                {"character": hero, "weight": 0.9},
                {"character": companion, "weight": 0.8}
            ],
            "style": "dynamic action scene, intense, dramatic lighting, magical effects",
            "quality": "ULTRA"
        },
        {
            "title": "The Ancient Mechanism",
            "description": "Marcus examines an intricate magical mechanism while Aria stands guard",
            "characters": [
                {"character": hero, "weight": 0.7},
                {"character": companion, "weight": 0.9}
            ],
            "style": "detailed mechanical elements, magical runes, steampunk influences",
            "quality": "ULTRA"
        },
        {
            "title": "Sealing the Portal",
            "description": "Together they perform a powerful ritual to seal the dark portal",
            "characters": [
                {"character": hero, "weight": 0.85},
                {"character": companion, "weight": 0.85}
            ],
            "style": "epic magical scene, swirling energies, dramatic lighting, ritual circle",
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
            
            # Generate the scene with characters
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
