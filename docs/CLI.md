# CLI Reference

## 📋 Overview

The Agent Task Manager CLI (`task`) is a command-line interface for managing tasks, projects, and agents. It provides a rich terminal experience with color output, tables, and interactive prompts.

## 🚀 Installation

### Make CLI Executable
```bash
cd cli
chmod +x task_cli.py

# Create alias for easy access
alias task='python3 /path/to/agent-task-manager/cli/task_cli.py'
```

### Install Dependencies
```bash
pip install typer rich requests
```

## 🎯 Basic Usage

### Help
```bash
task --help
```

### Command Structure
```bash
task [COMMAND] [ARGUMENTS] [OPTIONS]
```

## 📁 Projects

### List Projects
```bash
task projects
```

**Output:**
```
┌─────────────────────────────────────────────────────────────┐
│                         Projects                            │
├─────────┬────────────────────┬──────────────┬───────────────┤
│ ID      │ Name               │ Description  │ Created       │
├─────────┼────────────────────┼──────────────┼───────────────┤
│ default │ Default Project    │ Main project │ 2026-03-01    │
│ agent-os│ Agent OS Development│ Building... │ 2026-03-01    │
└─────────┴────────────────────┴──────────────┴───────────────┘
```

## 📋 Tasks

### Create Task
```bash
task create "Task title" [OPTIONS]
```

**Options:**
- `--desc, -d TEXT`: Task description
- `--project, -p TEXT`: Project ID (default: "default")
- `--priority, -P INTEGER`: Priority (0=low, 1=medium, 2=high, default: 1)
- `--parent TEXT`: Parent task ID

**Examples:**
```bash
# Simple task
task create "Fix critical bug"

# With description and high priority
task create "Implement feature X" --desc "Detailed description" --priority 2

# In specific project
task create "Client task" --project client-a --priority 1
```

### List Tasks
```bash
task list [OPTIONS]
```

**Options:**
- `--project, -p TEXT`: Filter by project
- `--status, -s STATUS`: Filter by status
- `--assignee, -a TEXT`: Filter by assignee
- `--limit, -l INTEGER`: Maximum tasks to show (default: 50)

**Status Values:**
- `backlog`, `todo`, `planning`, `hitl_review`
- `wip`, `implemented`, `done`, `blocked`, `cancelled`

**Examples:**
```bash
# List all tasks
task list

# List todo tasks in specific project
task list --project agent-os --status todo

# List tasks assigned to specific agent
task list --assignee ren-grunt

# Show only 10 tasks
task list --limit 10
```

**Output:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Tasks (7)                                    │
├────────┬──────────────────────────────────┬────────┬─────────┬──────┬───────┤
│ ID     │ Title                            │ Status │ Assignee│ Prio │ Updated │
├────────┼──────────────────────────────────┼────────┼─────────┼──────┼───────┤
│ task-001│ Design database schema          │ done   │ ren-grunt│ High │ 2h     │
│ task-002│ Implement backend API           │ wip    │ aki-partner│ High │ 30m    │
│ task-003│ Build frontend UI               │ todo   │ -       │ Medium│ 1d     │
└────────┴──────────────────────────────────┴────────┴─────────┴──────┴───────┘
```

### Show Task Details
```bash
task show TASK_ID
```

**Example:**
```bash
task show task-001
```

**Output:**
```
┌─────────────────────────────────────────────────────────────┐
│                         Task Details                        │
├─────────────────────────────────────────────────────────────┤
│ Title: Design database schema                               │
│ ID: task-001                                                │
│ Status: done                                                │
│ Project: default                                            │
│ Assignee: ren-grunt                                         │
│ Priority: High                                              │
│ Created: 2026-03-01T17:04:00.123456                         │
│ Updated: 2026-03-01T17:05:00.123456                         │
│                                                             │
│ Description:                                                │
│ Design the SQLite database schema for tasks, projects, and  │
│ agents                                                      │
└─────────────────────────────────────────────────────────────┘
```

### Update Task
```bash
task update TASK_ID [OPTIONS]
```

**Options:**
- `--title, -t TEXT`: New title
- `--desc, -d TEXT`: New description
- `--status, -s STATUS`: New status
- `--assignee, -a TEXT`: New assignee
- `--priority, -P INTEGER`: New priority (0-2)

**Examples:**
```bash
# Update status
task update task-001 --status wip

# Assign to agent
task update task-002 --assignee kuro-coder

# Update multiple fields
task update task-003 --title "Updated title" --desc "New description" --priority 2
```

### Move Task (Shortcut)
```bash
task move TASK_ID STATUS
```

**Example:**
```bash
task move task-001 wip
```

### Assign Task
```bash
task assign TASK_ID AGENT_ID
```

**Example:**
```bash
task assign task-001 ren-grunt
```

## 🤖 Agents

### Send Heartbeat
```bash
task heartbeat [OPTIONS]
```

**Options:**
- `--task, -t TEXT`: Task ID (if working on a task)
- `--agent, -a TEXT`: Agent ID

**Examples:**
```bash
# Agent working on a task
task heartbeat --task task-001 --agent ren-grunt

# Agent idle
task heartbeat --agent aki-partner
```

## ⚙️ Configuration

### Show Configuration
```bash
task config-show
```

**Output:**
```
┌─────────────────────────────────────────────────────────────┐
│                        Configuration                        │
├─────────────────────────────────────────────────────────────┤
│ API Base URL: http://localhost:8000                         │
│ Default Project: default                                    │
│ Agent ID: ren-grunt                                         │
└─────────────────────────────────────────────────────────────┘
```

### Set Configuration
```bash
task config-set KEY VALUE
```

**Valid Keys:**
- `api_base_url`: API base URL (e.g., "http://localhost:8000")
- `default_project`: Default project ID
- `agent_id`: Default agent ID

**Examples:**
```bash
# Set API URL
task config-set api_base_url http://localhost:8000

# Set default project
task config-set default_project agent-os

# Set agent ID
task config-set agent_id ren-grunt
```

## 🔍 Monitoring

### Health Check
```bash
task health
```

**Output:**
```
┌─────────────────────────────────────────────────────────────┐
│                         Health Check                        │
├─────────────────────────────────────────────────────────────┤
│ ✓ API is healthy                                            │
│ Status: healthy                                             │
│ Timestamp: 2026-03-01T17:04:00.123456                       │
└─────────────────────────────────────────────────────────────┘
```

### Watch Real-time Updates
```bash
task watch [OPTIONS]
```

**Options:**
- `--project, -p TEXT`: Project to watch
- `--interval, -i INTEGER`: Update interval in seconds (default: 5)

**Example:**
```bash
task watch --project agent-os
```

**Output:**
```
Connecting to http://localhost:8000/api/events...
Press Ctrl+C to exit

17:04:00 State changed, tasks updated
17:04:05 State changed, tasks updated
17:04:10 State changed, tasks updated
```

## 🎨 Advanced Usage

### Using with Pipes
```bash
# Count tasks by status
task list | grep -c "Status:"

# Export tasks to JSON
task list --json > tasks.json

# Filter with jq
task list --json | jq '.[] | select(.status == "todo")'
```

### Scripting Examples
```bash
#!/bin/bash
# Create multiple tasks
task create "Task 1" --desc "First task"
task create "Task 2" --desc "Second task"
task create "Task 3" --desc "Third task"

# Move all todo tasks to wip
for task_id in $(task list --status todo --json | jq -r '.[].id'); do
    task move "$task_id" wip
done
```

### Python Integration
```python
import subprocess
import json

# Run CLI command
result = subprocess.run(
    ["task", "list", "--json"],
    capture_output=True,
    text=True
)
tasks = json.loads(result.stdout)

# Create task via CLI
subprocess.run([
    "task", "create",
    "Python created task",
    "--desc", "Created from Python script",
    "--priority", "2"
])
```

## 🔧 Troubleshooting

### Common Issues

**"Command not found: task"**
```bash
# Use full path
python3 /path/to/agent-task-manager/cli/task_cli.py --help

# Or create alias
alias task='python3 /path/to/agent-task-manager/cli/task_cli.py'
```

**"Connection refused"**
```bash
# Check backend is running
task health

# Or check manually
curl http://localhost:8000/health
```

**"Invalid status value"**
```bash
# Check valid status values
task list --help
```

### Debug Mode
```bash
# Enable verbose output
export TASK_DEBUG=1
task list

# Or use Python debug
python3 -m pdb task_cli.py list
```

## 🚀 Performance Tips

### Use JSON Output
```bash
# Faster parsing for scripts
task list --json

# Filter with jq
task list --json | jq 'length'
```

### Limit Results
```bash
# Only show what you need
task list --limit 10 --status todo
```

### Cache Configuration
```bash
# Set configuration once
task config-set api_base_url http://localhost:8000
task config-set default_project agent-os
```

## 📚 Examples

### Complete Workflow
```bash
# 1. Check system health
task health

# 2. Create a task
task create "Implement new feature" --desc "Add real-time notifications" --priority 2

# 3. List tasks
task list --status backlog

# 4. Assign to agent
task assign task-001 ren-grunt

# 5. Move to wip
task move task-001 wip

# 6. Send heartbeat (as agent)
task heartbeat --task task-001 --agent ren-grunt

# 7. Watch updates
task watch
```

### Agent Automation Script
```bash
#!/bin/bash
# agent_workflow.sh

# Get next todo task
task_id=$(task list --status todo --json | jq -r '.[0].id')

if [ -n "$task_id" ]; then
    # Assign to myself
    task assign "$task_id" ren-grunt
    
    # Move to wip
    task move "$task_id" wip
    
    # Work on task (simulated)
    echo "Working on task $task_id"
    sleep 60
    
    # Mark as done
    task move "$task_id" done
else
    echo "No tasks available"
fi
```

### Batch Operations
```bash
# Create multiple related tasks
for i in {1..5}; do
    task create "Subtask $i" --desc "Part of larger feature" --parent task-001
done

# Update all tasks in project
for task_id in $(task list --project agent-os --json | jq -r '.[].id'); do
    task update "$task_id" --priority 1
done
```

## 🔄 Integration with OpenClaw

### OpenClaw Skill Example
```python
# openclaw_skill.py
import subprocess
import json

class TaskManagerSkill:
    def handle(self, command, args):
        if command == "task":
            # Run CLI command
            result = subprocess.run(
                ["task"] + args,
                capture_output=True,
                text=True
            )
            return result.stdout
        
        elif command == "get_next_task":
            # Get next todo task
            result = subprocess.run(
                ["task", "list", "--status", "todo", "--json"],
                capture_output=True,
                text=True
            )
            tasks = json.loads(result.stdout)
            if tasks:
                return tasks[0]
            return "No tasks available"
```

### Agent Heartbeat Cron
```bash
# cron job for agent heartbeat
*/5 * * * * /usr/bin/task heartbeat --agent ren-grunt
```

## 📖 Additional Resources

- [API Reference](../docs/API.md) - Complete API documentation
- [Installation Guide](../docs/INSTALLATION.md) - Setup instructions
- [Agent Integration](../docs/AGENTS.md) - Guide for AI agents
- [Source Code](../cli/task_cli.py) - CLI implementation