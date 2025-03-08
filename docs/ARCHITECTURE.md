# TaskRPG Architecture and Features Guide

## Overview
TaskRPG is an innovative task management application that gamifies productivity by transforming tasks into RPG-style battles. It combines task management with engaging gameplay elements to make task completion more enjoyable and rewarding.

## Core Components

### 1. Task Management System
- Task creation and tracking
- Dynamic task activation based on schedules
- Support for one-time, daily, and weekly tasks
- Task priority and complexity management
- Task count system for recurring tasks

### 2. Battle System
- Turn-based combat mechanics
- Two attack types:
  - Normal Attack (D key): Standard damage
  - Heavy Attack (Shift+D): Higher damage for multiple task steps
- Dynamic enemy HP based on task complexity
- Victory conditions tied to task completion
- XP and coin rewards for victories

### 3. Story Engine
- Dynamic storyline progression
- Node-based story structure
- Support for branching narratives
- Battle integration within story context
- Image generation for story scenes

### 4. Character Progression
- Experience-based leveling system
- Coin-based economy
- Inventory management
- Character statistics tracking

### 5. UI Components
- Main game window with story display
- Enemy and player panels
- Action buttons for combat
- Task progress indicators
- Settings management interface

## Key Features

### Story Management
- JSON-based story file format
- Story grouping and organization
- Story preview system
- Battle node integration
- Image generation for story scenes

### Image Generation
- Integration with ComfyUI
- Custom workflow support
- Multiple quality settings
- Automatic image generation for story nodes
- Workflow management system

### Battle Mechanics
- Task-to-enemy conversion
- Dynamic difficulty scaling
- Performance-based rewards
- Victory animations and effects
- Battle state management

### User Interface
- Modern, intuitive design
- Keyboard shortcuts for actions:
  - Normal Attack: D key
  - Heavy Attack: Shift+D
  - Next Story: G key
  - Navigate Back: Left Arrow
  - Navigate Forward: Right Arrow
  - Pause/Resume: # key
- Real-time status updates
- Progress tracking displays

### Settings and Customization
- Image quality configuration
- Workflow selection
- UI customization options
- Window management preferences
- Font scaling system

## Data Flow

1. Task Creation → Task Manager → Battle System
2. Story Selection → Story Manager → UI Display
3. User Action → Battle Manager → Task/Story Update
4. Victory → Experience/Coin Award → Player Progress

## File Structure

```
/taskRPG
├── modules/           # Core application modules
│   ├── battle/       # Battle system implementation
│   ├── tasks/        # Task management system
│   ├── ui/           # User interface components
│   └── players/      # Player management
├── data/             # Application data storage
├── stories/          # Story content files
├── workflows/        # ComfyUI workflow definitions
└── assets/           # Game assets and images
```

## Technical Implementation

### Battle Manager
- Coordinates between task system and UI
- Manages battle state and progression
- Handles attack calculations and victory conditions
- Updates UI components in real-time

### Story Manager
- Loads and parses story files
- Manages story progression
- Coordinates image generation
- Handles battle integration

### Task Manager
- Maintains task database
- Handles task activation/deactivation
- Manages task completion status
- Coordinates with battle system

## Extensibility

### Custom Workflows
1. Export workflow from ComfyUI
2. Place in workflows directory
3. Select through settings dialog
4. Automatic integration with story system

### Story Creation
1. Create JSON story file
2. Define nodes and connections
3. Add battle configurations
4. Include image generation prompts
5. Place in stories directory

## Best Practices

### Task Management
- Break down complex tasks into smaller steps
- Use appropriate task types (daily/weekly/one-time)
- Set realistic task counts for recurring items
- Monitor task activation patterns

### Battle Strategy
- Use normal attacks for simple task steps
- Save heavy attacks for multiple completions
- Monitor enemy HP for progress tracking
- Utilize keyboard shortcuts for efficiency

### Story Development
- Create engaging narrative flows
- Balance story and battle nodes
- Provide clear choice paths
- Use descriptive image prompts

## Performance Considerations

### Image Generation
- Select appropriate quality settings
- Monitor workflow complexity
- Consider storage requirements
- Manage generation queue

### UI Responsiveness
- Efficient update batching
- Proper window state management
- Optimized animation handling
- Font scaling optimization

## Future Expansion

### Planned Features
- Enhanced character customization
- Additional battle mechanics
- Extended story capabilities
- Advanced task patterns
- Improved UI customization

## Troubleshooting

### Common Issues
1. Image Generation
   - Check ComfyUI connection
   - Verify workflow compatibility
   - Monitor storage space

2. Battle System
   - Validate task availability
   - Check keyboard bindings
   - Monitor battle state

3. Story Progression
   - Verify story file format
   - Check node connections
   - Validate battle configurations

## Conclusion
TaskRPG provides a unique approach to task management by combining productive tools with engaging gameplay elements. Its modular architecture and extensive feature set create an immersive experience while maintaining practical task management capabilities.