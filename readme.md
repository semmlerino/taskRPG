# Epic Quest RPG - Task Manager

## Description

Epic Quest RPG transforms your task management into a fun, interactive text-based RPG. Your tasks become enemies to defeat in epic battles. Each task or step you complete corresponds to an attack against an enemy.

## Features

- **Turn-Based Combat**: Attack enemies representing your tasks.
- **Normal and Heavy Attacks**: Use different attack types to deal damage.
  - Normal Attack (D key): Standard damage.
  - Heavy Attack (Shift+D): Higher damage, simulates clearing multiple task steps.
- **Dynamic Storyline**: Advance through a storyline loaded from external files.
- **Experience and Leveling**: Gain experience points (XP) and level up.
- **Customizable Enemies**: Add, edit, or remove enemies (tasks) in settings.
- **Interactive Interface**: Engaging UI with visual elements and color highlights.
- **Keyboard Shortcuts**: 
  - Normal Attack: D key
  - Heavy Attack: Shift+D
  - Next Story: G key
  - Navigate Back: Left Arrow
  - Navigate Forward: Right Arrow
  - Pause/Resume: # key

## Image Generation Workflows

The application supports custom ComfyUI workflows for image generation. You can add your own workflows by following these steps:

1. Export your workflow from ComfyUI as a JSON file
2. Place the workflow file in the `workflows` directory
3. In the settings dialog, select your workflow from the dropdown menu

The application comes with two workflows:
- Default Workflow: A basic workflow optimized for story illustrations
- Simple Flux Workflow: A more advanced workflow with improved quality settings

To create your own workflow:
1. Open ComfyUI and set up your desired image generation pipeline
2. Export the workflow as a JSON file
3. Place the JSON file in the `workflows` directory
4. Restart the application to see your workflow in the settings

Note: Custom workflows must be compatible with the application's prompt format. Ensure your workflow includes:
- A CLIPTextEncode node for the positive prompt
- A CLIPTextEncode node for the negative prompt
- A KSampler node for image generation
- A VAEDecode node for decoding the latent
- A SaveImage node for output

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/EpicQuestRPG.git
