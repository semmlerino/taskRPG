# TaskRPG User Guide

## Introduction

Welcome to TaskRPG, an innovative task management application that transforms your productivity into an engaging RPG adventure! This guide will walk you through all features and help you get the most out of your TaskRPG experience.

## Getting Started

### Installation

1. Ensure you have Python installed on your system
2. Launch the application by running `taskRPG.bat` or `python main.py`
3. On first launch, the application will create necessary directories and default settings

### Initial Setup

1. When you first start TaskRPG, you'll be prompted to select a story
2. If no stories exist, you'll be offered to create a default story
3. The application will check for missing story images and offer to generate them

## Core Features

### Task Management

#### Creating Tasks

1. Access the Settings dialog by clicking the "Settings" button
2. Navigate to the Tasks tab
3. Click "Add Task" to create a new task
4. Fill in the task details:
   - Name: A descriptive title for your task
   - Description: Details about what needs to be done
   - Priority: How important the task is (affects battle difficulty)
   - Count: For recurring tasks, how many times it needs to be completed
   - Schedule: One-time, daily, or weekly

#### Managing Tasks

- **Edit Task**: Select a task and click "Edit" to modify its details
- **Delete Task**: Select a task and click "Delete" to remove it
- **Activate/Deactivate**: Toggle tasks on/off manually
- **Task Scheduling**: Daily and weekly tasks automatically reactivate based on their schedule

### Battle System

#### Starting Battles

Battles occur in two ways:
1. **Story-Triggered**: When you reach a battle node in the story
2. **Task-Based**: When a task becomes active and you engage with it

#### Combat Controls

- **Normal Attack (D key)**: Standard attack that deals 1 damage
- **Heavy Attack (Shift+D)**: Powerful attack that deals 2-4 damage
- **Pause Battle (#)**: Temporarily pause the current battle

#### Battle Interface

- **Enemy Panel**: Shows the current enemy (task) and its remaining HP
- **Player Panel**: Displays your level, XP, and coins
- **Tasks Left**: Indicates how many steps remain to complete the task
- **Action Buttons**: Provides clickable buttons for attacks

#### Victory Conditions

- Reduce enemy HP to zero by completing task steps
- Earn XP and coins upon victory
- Task count decreases by one (for recurring tasks)
- Daily/weekly tasks deactivate until their next scheduled activation

### Story Progression

#### Story Navigation

- **Next Story (G key)**: Advance to the next story segment
- **Back (Left Arrow)**: Return to previous story node
- **Forward (Right Arrow)**: Move to next story node if available

#### Story Selection

1. Launch the Story Selection dialog at startup
2. Browse available stories grouped by title
3. Preview story details including node count and battle content
4. Select a story to begin your adventure

#### Story Features

- **Branching Narratives**: Make choices that affect your story path
- **Battle Integration**: Encounter enemies within the story context
- **Image Generation**: Visualize story scenes with AI-generated images
- **NPC Interactions**: Engage with characters in the story

### Character Progression

#### Experience System

- Gain XP by completing battles (defeating tasks)
- XP rewards scale with task complexity
- Earn bonus XP for efficient battle completion
- Level up as you accumulate experience

#### Economy

- Earn coins from battle victories (6 coins per victory)
- Use coins to purchase items and upgrades
- Track your coin balance in the player panel

## Advanced Features

### Image Generation

#### Quality Settings

1. Access Settings dialog
2. Select your preferred image quality:
   - Low: Faster generation, less detail
   - Medium: Balanced performance and quality
   - High: Maximum quality, slower generation

#### Custom Workflows

1. Export your workflow from ComfyUI as a JSON file
2. Place the workflow file in the `workflows` directory
3. Select your workflow from the Settings dialog

### Compact Mode

- A minimalist battle interface for focused task completion
- Automatically appears during battles
- Shows essential information: enemy name, HP, and tasks remaining

### Font Scaling

- Dynamically adjusts text size based on window dimensions
- Ensures readability across different display configurations
- Maintains consistent UI appearance

## Customization

### Settings Dialog

Access comprehensive settings by clicking the "Settings" button:

#### General Settings

- Window size and position preferences
- UI customization options
- Keyboard shortcut configuration

#### Image Generation Settings

- ComfyUI server connection
- Workflow selection
- Image quality configuration

#### Task Management

- Add, edit, and delete tasks
- Configure task activation patterns
- Set task priorities and counts

## Tips and Tricks

### Productivity Optimization

- Break down large tasks into smaller, manageable steps
- Use daily tasks for habit formation
- Set realistic task counts for recurring items
- Balance task difficulty with your available time

### Battle Efficiency

- Use normal attacks for simple, quick tasks
- Save heavy attacks for when you complete multiple steps at once
- Monitor your task list regularly to keep battles manageable
- Use keyboard shortcuts for faster interaction

### Story Creation

- Create your own stories using the JSON format
- Include image prompts for scene visualization
- Design branching paths for replayability
- Integrate battles at key narrative points

## Troubleshooting

### Common Issues

#### Image Generation Problems

- Ensure ComfyUI is running and accessible
- Check that your selected workflow is compatible
- Verify you have sufficient disk space for images

#### Battle System Issues

- If no battles appear, check that you have active tasks
- Verify keyboard shortcuts are working correctly
- Restart the application if battle state becomes inconsistent

#### Story Navigation Problems

- Ensure story files are properly formatted JSON
- Check that story nodes have valid connections
- Verify image paths exist if using pre-generated images

## Conclusion

TaskRPG transforms mundane task management into an exciting adventure. By combining productivity tools with engaging gameplay elements, it makes task completion more enjoyable and rewarding. Use this guide to explore all features and maximize your productivity while having fun along the way!

---

*For technical details about TaskRPG's architecture and implementation, please refer to the ARCHITECTURE.md document.*