# Agent Integration Guide

## 📋 Overview

This guide explains how to integrate AI agents with the Agent Task Manager system. The system supports multiple agent types with specialized roles and capabilities.

## 🤖 Agent Team

### Core Agent Team
| Agent | Role | Model | Capabilities |
|-------|------|-------|--------------|
| **Ren** (ren-grunt) | Infrastructure Sentinel | qwen-coder-local | Infrastructure, maintenance, cron jobs |
| **Aki** (aki-partner) | Chief of Staff | deepseek/deepseek-chat | Coordination, reporting, orchestration |
| **Kuro** (kuro-coder) | Systems Architect | deepseek/deepseek-chat | Development, architecture, security |
| **Shin** (shin-strategist) | Grand Vizier | deepseek/deepseek-chat | Planning, analysis, roadmapping |
| **Sora** (sora-creative) | The Muse | gemini | Brainstorming, innovation, design |

### Agent Characteristics
- **Persistent Sessions**: Agents run as persistent OpenClaw sessions
- **Specialized Models**: Each agent uses an appropriate model for their role
- **Clear Responsibilities**: Well-defined scope for each agent
- **Team Coordination**: Agents can hand off tasks to each other

## 🔄 Agent Workflow

### Task Lifecycle with Agents
```
1. Task created (backlog)
2. Task moves to todo
3. Agent picks up task
4. Agent moves to planning
5. Agent works (wip)
6. Human review (hitl_review)
7. Implementation
8. Completion (done)
```

### Crash Recovery Flow
```
1. Agent sends heartbeat every 30 seconds
2. If heartbeat stops for 35+ minutes
3. System detects stale task
4. Task reverts to todo status
5. Assignee cleared
6. Available for other agents
```

## 🚀 Getting Started

### 1. Configure Agent
```bash
# Set agent ID in CLI config
task config-set agent_id ren-grunt

# Or use environment variable
export AGENT_ID=ren-grunt
```

### 2. Test Connection
```bash
# Send test heartbeat
task heartbeat --agent ren-grunt

# Check agent appears in UI
# Open frontend and check Agents panel
```

### 3. Pick Up Task
```bash
# List available tasks
task list --status todo

# Assign task to yourself
task assign TASK_ID ren-grunt

# Move to planning
task move TASK_ID planning
```

## 📝 Agent Best Practices

### Task Selection
```bash
# Look for tasks matching your capabilities
task list --status todo | grep -i "infrastructure\|maintenance\|cron"

# Check priority
task list --status todo --json | jq '.[] | select(.priority == 2)'
```

### Regular Heartbeats
```bash
# Send heartbeat every 30 seconds when working
while true; do
    task heartbeat --task TASK_ID --agent ren-grunt
    sleep 30
done
```

### Status Updates
```bash
# Update status as you progress
task move TASK_ID planning    # Starting work
task move TASK_ID wip         # Actively working
task move TASK_ID hitl_review # Need human input
task move TASK_ID implemented # Work complete
task move TASK_ID done        # Verified complete
```

## 🔧 Technical Integration

### OpenClaw Agent Configuration
```yaml
# Example OpenClaw agent config
agents:
  ren-grunt:
    model: llamacpp/qwen2.5-coder-7b
    thinking: on
    skills:
      - infrastructure
      - maintenance
      - cron
    workspace: /home/pesu/.openclaw/pesulabs
```

### Agent Script Template
```python
#!/usr/bin/env python3
"""
Agent script template
"""

import subprocess
import json
import time
from datetime import datetime

class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.current_task = None
    
    def run_cli(self, args):
        """Run CLI command"""
        cmd = ["task"] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    
    def get_next_task(self):
        """Get next available task"""
        output = self.run_cli(["list", "--status", "todo", "--json"])
        tasks = json.loads(output)
        if tasks:
            return tasks[0]
        return None
    
    def work_on_task(self, task_id):
        """Work on a task"""
        self.current_task = task_id
        
        # Assign to self
        self.run_cli(["assign", task_id, self.agent_id])
        
        # Move to planning
        self.run_cli(["move", task_id, "planning"])
        
        # Start heartbeat in background
        self.start_heartbeat(task_id)
        
        # Do the work
        self.do_work(task_id)
        
        # Mark as implemented
        self.run_cli(["move", task_id, "implemented"])
        
        # Stop heartbeat
        self.current_task = None
    
    def start_heartbeat(self, task_id):
        """Start heartbeat thread"""
        import threading
        
        def heartbeat_loop():
            while self.current_task == task_id:
                self.run_cli(["heartbeat", "--task", task_id, "--agent", self.agent_id])
                time.sleep(30)
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()
    
    def do_work(self, task_id):
        """Actual work implementation"""
        # Get task details
        output = self.run_cli(["show", task_id, "--json"])
        task = json.loads(output)
        
        print(f"Working on: {task['title']}")
        print(f"Description: {task['description']}")
        
        # Implement your agent's specific work here
        # This is where the AI model would process the task
        
        time.sleep(5)  # Simulate work

# Usage
if __name__ == "__main__":
    agent = Agent("ren-grunt")
    
    while True:
        task = agent.get_next_task()
        if task:
            print(f"Found task: {task['title']}")
            agent.work_on_task(task['id'])
        else:
            print("No tasks available, waiting...")
            time.sleep(60)
```

## 🎯 Agent Specializations

### Ren (Infrastructure Sentinel)
```python
# ren_agent.py - Infrastructure specialist
class RenAgent(Agent):
    def do_work(self, task_id):
        task = self.get_task_details(task_id)
        
        if "cron" in task['title'].lower():
            self.handle_cron_task(task)
        elif "backup" in task['title'].lower():
            self.handle_backup_task(task)
        elif "monitor" in task['title'].lower():
            self.handle_monitoring_task(task)
        else:
            self.handle_general_infra_task(task)
    
    def handle_cron_task(self, task):
        print("Setting up cron job...")
        # Implement cron job setup
```

### Aki (Chief of Staff)
```python
# aki_agent.py - Coordination specialist
class AkiAgent(Agent):
    def do_work(self, task_id):
        task = self.get_task_details(task_id)
        
        if "report" in task['title'].lower():
            self.generate_report(task)
        elif "coordinate" in task['title'].lower():
            self.coordinate_team(task)
        elif "review" in task['title'].lower():
            self.review_progress(task)
```

### Kuro (Systems Architect)
```python
# kuro_agent.py - Development specialist
class KuroAgent(Agent):
    def do_work(self, task_id):
        task = self.get_task_details(task_id)
        
        if "implement" in task['title'].lower():
            self.implement_feature(task)
        elif "design" in task['title'].lower():
            self.design_architecture(task)
        elif "refactor" in task['title'].lower():
            self.refactor_code(task)
```

## 🔄 Task Handoff

### Between Agents
```python
def handoff_task(task_id, from_agent, to_agent, reason):
    """Hand off task to another agent"""
    # Update assignee
    subprocess.run(["task", "assign", task_id, to_agent])
    
    # Add comment about handoff
    subprocess.run([
        "task", "update", task_id,
        "--desc", f"{task['description']}\n\nHanded off from {from_agent} to {to_agent}: {reason}"
    ])
    
    # Move back to todo for new agent
    subprocess.run(["task", "move", task_id, "todo"])
```

### Example Handoff Scenarios
```python
# Ren to Kuro: Infrastructure task needs development
if "requires development" in task_analysis:
    handoff_task(task_id, "ren-grunt", "kuro-coder", "Requires development expertise")

# Kuro to Shin: Implementation needs strategic review
if "strategic implications" in task_analysis:
    handoff_task(task_id, "kuro-coder", "shin-strategist", "Needs strategic review")

# Any agent to Sora: Creative input needed
if "creative solution" in task_analysis:
    handoff_task(task_id, current_agent, "sora-creative", "Needs creative approach")
```

## 📊 Monitoring & Logging

### Agent Status Dashboard
```bash
# Check all agent statuses
task list --json | jq 'group_by(.assignee) | map({agent: .[0].assignee, count: length, tasks: map(.title)})'

# Monitor agent activity
watch -n 10 "task list --json | jq '[.[] | select(.assignee != null)] | group_by(.assignee) | map({agent: .[0].assignee, active: length})'"
```

### Agent Logs
```python
# Log agent actions
import logging

logging.basicConfig(
    filename=f'logs/agent_{agent_id}.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(agent_id)

def log_action(action, task_id, details=""):
    logger.info(f"{action} - Task: {task_id} - {details}")
```

## 🛡️ Error Handling

### Graceful Failure
```python
try:
    # Attempt work
    self.do_work(task_id)
except Exception as e:
    # Log error
    logger.error(f"Failed on task {task_id}: {str(e)}")
    
    # Move to blocked with error details
    self.run_cli(["move", task_id, "blocked"])
    self.run_cli([
        "update", task_id,
        "--desc", f"{task['description']}\n\n❌ Blocked due to error: {str(e)}"
    ])
    
    # Clear assignee so others can try
    self.run_cli(["update", task_id, "--assignee", ""])
```

### Health Checks
```python
def check_agent_health():
    """Check if agent can perform work"""
    # Check CLI access
    try:
        subprocess.run(["task", "health"], check=True, capture_output=True)
        return True
    except:
        return False
    
    # Check model availability
    # Check workspace access
    # Check network connectivity
```

## 🔄 Integration with External Systems

### OpenClaw Integration
```python
# Spawn OpenClaw agent for complex tasks
def spawn_openclaw_agent(task):
    """Spawn OpenClaw agent for this task"""
    cmd = [
        "openclaw", "sessions:spawn",
        "--agent", "ren-grunt",
        "--model", "qwen-coder-local",
        "--message", f"Work on task: {task['title']}\n\n{task['description']}"
    ]
    
    subprocess.run(cmd)
```

### Plane.so Integration
```python
# Sync with Plane.so (if configured)
def sync_with_plane(task_id):
    """Sync task status with Plane.so"""
    plane_api.update_issue(
        issue_id=task['external_id'],
        status=task['status'],
        assignee=task['assignee']
    )
```

## 🧪 Testing Agent Integration

### Test Script
```bash
#!/bin/bash
# test_agent_integration.sh

echo "Testing Agent Integration..."
echo "============================"

# 1. Test CLI access
echo "1. Testing CLI access..."
task health

# 2. Create test task
echo "2. Creating test task..."
task create "Agent Integration Test" --desc "Test task for agent integration" --priority 2

# 3. Get task ID
TASK_ID=$(task list --json | jq -r '.[0].id')
echo "Task ID: $TASK_ID"

# 4. Assign to agent
echo "4. Assigning to agent..."
task assign "$TASK_ID" ren-grunt

# 5. Send heartbeat
echo "5. Sending heartbeat..."
task heartbeat --task "$TASK_ID" --agent ren-grunt

# 6. Move through workflow
echo "6. Moving through workflow..."
task move "$TASK_ID" planning
task move "$TASK_ID" wip
task move "$TASK_ID" implemented
task move "$TASK_ID" done

echo "✅ Agent integration test complete!"
```

### Automated Testing
```python
# test_agents.py
import unittest
import subprocess
import json

class TestAgentIntegration(unittest.TestCase):
    def setUp(self):
        self.agent_id = "ren-grunt"
    
    def test_heartbeat(self):
        result = subprocess.run(
            ["task", "heartbeat", "--agent", self.agent_id],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
    
    def test_task_assignment(self):
        # Create test task
        subprocess.run([
            "task", "create",
            "Test Assignment",
            "--desc", "Test task assignment"
        ])
        
        # Get task ID
        result = subprocess.run(
            ["task", "list", "--json"],
            capture_output=True,
            text=True
        )
        tasks = json.loads(result.stdout)
        task_id = tasks[0]['id']
        
        # Assign to agent
        subprocess.run(["task", "assign", task_id, self.agent_id])
        
        # Verify assignment
        result = subprocess.run(
            ["task", "show", task_id, "--json"],
            capture_output=True,
            text=True
        )
        task = json.loads(result.stdout)
        self.assertEqual(task['assignee'], self.agent_id)

if __name__ == "__main__":
    unittest.main()
```

## 📈 Performance Optimization

### Batch Operations
```python
# Process multiple tasks efficiently
def process_tasks_batch(task_ids):
    """Process multiple tasks in batch"""
    for task_id in task_ids:
        # Quick status update
        subprocess.run(["task", "move", task_id, "planning"])
        
        # Batch heartbeats
        if time.time() % 30 < 1:  # Every 30 seconds
            subprocess.run(["task", "heartbeat", "--task", task_id, "--agent", self.agent_id])
```

### Caching
```python
# Cache task details
from functools import lru_cache

@lru_cache(maxsize=100)
def get_task_details_cached(task_id):
    return self.get_task_details(task_id)
```

## 🚀 Production Deployment

### Systemd Service
```ini
# /etc/systemd/system/ren-agent.service
[Unit]
Description=Ren Agent Service
After=network.target

[Service]
Type=simple
User=pesu
WorkingDirectory=/home/pesu/.openclaw/pesulabs
ExecStart=/usr/bin/python3 /path/to/ren_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker Container
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ren_agent.py .

CMD ["python3", "ren_agent.py"]
```

## 📚 Additional Resources

- [CLI Reference](../docs/CLI.md) - Complete CLI documentation
- [API Reference](../docs/API.md) - API endpoints for programmatic access
- [OpenClaw Documentation](https://docs.openclaw.ai) - OpenClaw agent framework
- [Example Agents](../examples/agents/) - Sample agent implementations