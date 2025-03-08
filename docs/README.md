# TaskRPG Documentation

Welcome to the TaskRPG documentation! This guide provides comprehensive information about the TaskRPG application, its features, and how to use it effectively.

## What is TaskRPG?

TaskRPG is an innovative task management application that gamifies productivity by transforming your tasks into RPG-style battles. Instead of simply checking off items from a to-do list, you'll engage in turn-based combat where each task becomes an enemy to defeat.

## Application Flow

1. **Task Creation**: Create tasks with names, descriptions, priorities, and schedules
2. **Story Selection**: Choose a story adventure that provides context for your tasks
3. **Battle Engagement**: Tasks transform into enemies with HP based on complexity
4. **Task Completion**: Perform attacks to reduce enemy HP and complete task steps
5. **Rewards**: Earn XP and coins upon victory, level up your character
6. **Progression**: Advance through the story as you complete tasks

## Core Features

### Task Management System

- **Task Types**: One-time, daily, and weekly recurring tasks
- **Priority Levels**: Set importance and difficulty
- **Task Counts**: Configure how many times recurring tasks need completion
- **Automatic Scheduling**: Tasks activate based on their configured schedule
- **Manual Activation**: Force-activate tasks when needed

### Battle System

- **Turn-Based Combat**: Strategic task completion through battle mechanics
- **Attack Types**:
  - Normal Attack (D key): Standard damage (1 HP)
  - Heavy Attack (Shift+D): Higher damage (2-4 HP)
- **Enemy HP**: Based on task complexity and remaining steps
- **Victory Conditions**: Complete all steps to defeat the enemy
- **Battle Statistics**: Track attacks performed and turns taken

### Story Engine

- **Node-Based Structure**: Progress through interconnected story segments
- **Branching Narratives**: Make choices that affect your path
- **Battle Integration**: Encounter enemies within story context
- **Image Generation**: AI-generated visuals for story scenes
- **Story Selection**: Choose from multiple adventures

### Character Progression

- **Experience System**: Gain XP from completed battles
- **Leveling Mechanics**: Advance through levels as you earn XP
- **Economy**: Earn and spend coins for upgrades
- **Performance Bonuses**: Earn extra rewards for efficient task completion

### Image Generation

- **ComfyUI Integration**: Generate images based on story prompts
- **Custom Workflows**: Support for user-defined generation pipelines
- **Quality Settings**: Configure image detail and generation speed
- **Automatic Generation**: Create missing images for story nodes

### User Interface

- **Main Window**: Story display with player and enemy panels
- **Compact Mode**: Minimalist battle interface for focused work
- **Keyboard Shortcuts**: Quick access to common actions
- **Font Scaling**: Dynamic text sizing for different displays
- **Settings Dialog**: Comprehensive configuration options

## Technical Features

- **JSON-Based Storage**: Task and story data in human-readable format
- **Modular Architecture**: Separation of concerns for maintainability
- **Event-Driven Design**: Signal/slot pattern for component communication
- **State Management**: Consistent tracking of game and battle states
- **Error Handling**: Robust exception management and logging

## Documentation Structure

For more detailed information, please refer to these specialized guides:

- [**User Guide**](USER_GUIDE.md): Step-by-step instructions for using TaskRPG
- [**Architecture Guide**](ARCHITECTURE.md): Technical details about the application's structure

## Getting Started

To begin using TaskRPG:

1. Launch the application by running `taskRPG.bat` or `python main.py`
2. Select a story from the Story Selection dialog
3. Create tasks in the Settings dialog
4. Start completing tasks through the battle system
5. Progress through the story as you defeat task enemies

## Customization

TaskRPG offers extensive customization options:

- **Create Custom Stories**: Design your own adventures with JSON
- **Define Workflows**: Create custom image generation pipelines
- **Configure UI**: Adjust window size, position, and appearance
- **Tailor Task System**: Set up task patterns that match your workflow

## Support and Feedback

If you encounter issues or have suggestions for improvement, please:

1. Check the troubleshooting sections in the User Guide
2. Review the application logs for error messages
3. Consider contributing to the project with bug fixes or feature enhancements

---

Thank you for using TaskRPG! We hope it makes your task management more enjoyable and productive.