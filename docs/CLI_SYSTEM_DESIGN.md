# CLI System Design for Agent Task Manager
**Version**: 1.0  
**Date**: 2026-03-01  
**Status**: Implementation Plan  
**Author**: Claw (AI Assistant)

---

## Overview

This document outlines the design and implementation of the CLI-based agent integration system for the Agent Task Manager. The system enables AI agents (Ren, Aki, Kuro, Shin, Sora) to receive tasks from the kanban system, execute them via OpenClaw, and report results back.

## Design Principles

1. **Simplicity Over Complexity**: CLI tools instead of HTTP APIs where possible
2. **Local First**: Use local models (qwen-coder-local) for heartbeats to reduce costs
3. **Concurrent Safe**: Handle multiple agents accessing the same database
4. **Crash Resilient**: Automatic detection and recovery from agent failures
5. **Human + Agent Usable**: Both humans and agents can use the same CLI tools

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent CLI     │    │   Database      │    │   Mission       │
│   System        │◄──►│   (SQLite)      │◄──►│   Control       │
│                 │    │                 │    │   (Web UI)      │
│ • agent-cli.py  │    │ • tasks         │    │ • Kanban        │
│ • ren-agent     │    │ • agents        │    │ • Status        │
│ • aki-agent     │    │ • assignments   │    │ • Comments      │
│ • kuro-agent    │    │ • results       │    │ • Instructions  │
│ • shin-agent    │    │ • heartbeats    │    │                 │
│ • sora-agent    │    └─────────────────┘    └─────────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   OpenClaw      │
│   Agents        │
│                 │
│ • Execution     │
│ • Results       │
│ • Logging       │
└─────────────────┘
```

### Database Schema (SQLite)

```sql
-- Core tables
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT CHECK (status IN ('backlog', 'todo', 'in_progress', 'review', 'done', 'blocked')),
    priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    assignee TEXT,  -- 'ren', 'aki', 'kuro', 'shin', 'sora', or NULL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP,
    parent_task_id TEXT REFERENCES tasks(id)
);

CREATE TABLE agents (
    name TEXT PRIMARY KEY,  -- 'ren', 'aki', 'kuro', 'shin', 'sora'
    role TEXT NOT NULL,
    status TEXT CHECK (status IN ('idle', 'working', 'crashed', 'offline')),
    current_task_id TEXT REFERENCES tasks(id),
    last_heartbeat TIMESTAMP,
    capabilities JSON,
    model TEXT,  -- 'qwen-coder-local', 'deepseek-chat', 'gemini'
    config JSON
);

CREATE TABLE assignments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    agent_name TEXT NOT NULL REFERENCES agents(name),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT CHECK (status IN ('pending', 'started', 'completed', 'failed')),
    output TEXT,
    error TEXT,
    logs TEXT
);

CREATE TABLE heartbeats (
    agent_name TEXT NOT NULL REFERENCES agents(name),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK (status IN ('alive', 'warning', 'error'))
);

-- File locking table for SQLite concurrency
CREATE TABLE locks (
    resource TEXT PRIMARY KEY,
    owner TEXT,
    acquired_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

## CLI Tool Design

### 1. Core CLI (`agent-cli.py`)

**Location**: `agent-task-manager/cli/agent-cli.py`

**Commands**:
```bash
# Core commands
agent-cli.py poll --agent <name>           # Check for assigned tasks
agent-cli.py execute --task <id>           # Execute a specific task
agent-cli.py status --task <id>            # Report task status
agent-cli.py heartbeat --agent <name>      # Send heartbeat
agent-cli.py results --task <id> --output  # Submit task results

# Administrative commands
agent-cli.py agents list                   # List all agents
agent-cli.py agents status                 # Show agent statuses
agent-cli.py tasks list --agent <name>     # List tasks for agent
agent-cli.py tasks create --title "..."    # Create new task
```

**Key Features**:
- **File locking**: Prevent concurrent database access issues
- **Model selection**: Use appropriate model for each agent
- **Error handling**: Retry logic and graceful failure
- **Logging**: Comprehensive logs for debugging

### 2. Agent-Specific Wrappers

**Ren Agent** (`ren-agent`):
```bash
#!/bin/bash
# ren-agent wrapper
python3 /path/to/agent-cli.py \
  --agent ren \
  --role "infrastructure & maintenance" \
  --model "qwen-coder-local" \
  --capabilities '["shell", "file_ops", "monitoring"]' \
  "$@"
```

**Aki Agent** (`aki-agent`):
```bash
#!/bin/bash
# aki-agent wrapper (main coordinator)
python3 /path/to/agent-cli.py \
  --agent aki \
  --role "coordination & reporting" \
  --model "deepseek-chat" \
  --capabilities '["coordination", "reporting", "delegation"]' \
  "$@"
```

**Other agents**: Similar wrappers for kuro, shin, sora

### 3. Systemd Services (Optional)

Example service file for Ren agent:
```ini
# /etc/systemd/system/ren-agent.service
[Unit]
Description=Ren Agent Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pesu
WorkingDirectory=/home/pesu/.openclaw/pesulabs/agent-task-manager
ExecStart=/home/pesu/.openclaw/pesulabs/agent-task-manager/agents/ren-agent --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Task Assignment Logic

### Algorithm
```python
def get_next_task(agent_name):
    """
    Get next task for agent based on assignment rules
    """
    # 1. Check for tasks specifically assigned to this agent
    specific_tasks = get_assigned_tasks(agent_name, status='todo')
    
    # 2. If Aki, also check for unassigned tasks
    if agent_name == 'aki' and not specific_tasks:
        unassigned_tasks = get_unassigned_tasks(status='todo')
        if unassigned_tasks:
            return unassigned_tasks[0]
    
    # 3. Return the highest priority task
    return sort_by_priority(specific_tasks)[0] if specific_tasks else None

def assign_task_to_agent(task_id, agent_name):
    """
    Assign a task to an agent with proper locking
    """
    with acquire_lock(f"task_{task_id}"):
        # Check if agent is available
        agent_status = get_agent_status(agent_name)
        if agent_status != 'idle':
            return False  # Agent busy
        
        # Update task and agent status
        update_task_status(task_id, 'in_progress', assignee=agent_name)
        update_agent_status(agent_name, 'working', current_task=task_id)
        create_assignment_record(task_id, agent_name)
        
        return True
```

### Priority Rules
1. **Assigned tasks** > Unassigned tasks
2. **Higher priority** (critical > high > medium > low)
3. **Older tasks** (FIFO within same priority)
4. **Agent specialization** (match task requirements to agent capabilities)

## Heartbeat System

### Design
- **Frequency**: Every 30 seconds when idle, every 60 seconds when working
- **Model**: Always use `qwen-coder-local` (local GPU, no cost)
- **Prompt**: Minimal "ALIVE" check
- **Detection**: 2 minutes without heartbeat → mark as crashed
- **Recovery**: Automatic task reassignment after crash detection

### Implementation
```python
def send_heartbeat(agent_name):
    """Send heartbeat using local model only"""
    # Simple prompt for local model
    prompt = "You are agent {agent_name}. Respond with 'ALIVE' if functioning normally."
    
    try:
        # Call local qwen-coder model (port 8082)
        response = call_local_llm(
            model="llamacpp/qwen2.5-coder-7b",
            prompt=prompt,
            max_tokens=10,
            temperature=0.1
        )
        
        if "ALIVE" in response.upper():
            update_heartbeat(agent_name, 'alive')
            return True
        else:
            update_heartbeat(agent_name, 'warning')
            return False
            
    except Exception as e:
        update_heartbeat(agent_name, 'error', str(e))
        return False

def check_agent_health():
    """Check all agents for crashes"""
    agents = get_all_agents()
    for agent in agents:
        last_heartbeat = agent['last_heartbeat']
        if time_since(last_heartbeat) > timedelta(minutes=2):
            # Agent crashed
            mark_agent_crashed(agent['name'])
            reassign_tasks(agent['name'])
            notify_system(f"Agent {agent['name']} crashed, tasks reassigned")
```

## File Locking for SQLite Concurrency

### Problem
SQLite doesn't handle concurrent writes well. Multiple agents trying to update the database simultaneously will cause errors.

### Solution: Advisory File Locking
```python
import fcntl
import time

class SQLiteLock:
    def __init__(self, db_path):
        self.lock_file = db_path + '.lock'
        
    def acquire(self, timeout=30):
        """Acquire lock with timeout"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.fd = open(self.lock_file, 'w')
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except BlockingIOError:
                time.sleep(0.1)
        return False
    
    def release(self):
        """Release lock"""
        if hasattr(self, 'fd'):
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()

# Usage
def update_task_with_lock(task_id, updates):
    lock = SQLiteLock('agent_tasks.db')
    if lock.acquire():
        try:
            # Perform database operations
            conn = sqlite3.connect('agent_tasks.db')
            # ... update task ...
            conn.commit()
        finally:
            lock.release()
```

## Implementation Plan

### Step 1: Database Setup
1. Create enhanced SQLite schema with locking support
2. Seed initial agent records (ren, aki, kuro, shin, sora)
3. Create migration script from existing database

### Step 2: Core CLI Tool
1. Implement `agent-cli.py` with basic commands
2. Add file locking for database access
3. Implement task polling and assignment logic
4. Add heartbeat system using local model

### Step 3: Agent Wrappers
1. Create agent-specific wrapper scripts
2. Configure agent capabilities and models
3. Test each agent independently

### Step 4: Integration Testing
1. Test task assignment flow (human → kanban → agent)
2. Test heartbeat and crash detection
3. Test concurrent agent execution
4. Test recovery from failures

### Step 5: Mission Control Integration
1. Update FastAPI backend to work with new schema
2. Add agent status endpoints
3. Enhance frontend to show agent status
4. Add administrative controls

## Security Considerations

1. **Database Access**: CLI tools run with user permissions only
2. **No Network Exposure**: All communication via local files/database
3. **Input Validation**: Validate all task descriptions and commands
4. **Logging**: Comprehensive logs for audit trail
5. **Backup**: Regular database backups

## Performance Considerations

1. **Database Indexes**: Add indexes on frequently queried columns
2. **Connection Pooling**: Reuse database connections
3. **Batch Operations**: Batch heartbeats and status updates
4. **Caching**: Cache agent status and task lists
5. **Optimistic Locking**: Reduce lock contention

## Monitoring & Debugging

### Log Files
- `logs/agent-cli.log`: General CLI operations
- `logs/ren-agent.log`: Ren agent specific logs
- `logs/heartbeats.log`: Heartbeat system logs
- `logs/errors.log`: Error and crash reports

### Status Commands
```bash
# Check system status
agent-cli.py system status

# View agent logs
agent-cli.py logs --agent ren --lines 50

# Monitor heartbeats
agent-cli.py heartbeats monitor --realtime

# Check for stuck tasks
agent-cli.py tasks stuck --fix
```

## Migration Path to PostgreSQL

### When to Migrate
- Concurrent agents > 5
- Task volume > 1000 tasks/day
- Need for advanced queries or reporting
- Requirement for high availability

### Migration Strategy
1. **Dual-write**: Write to both SQLite and PostgreSQL during transition
2. **Data migration**: Script to copy existing data
3. **Feature flag**: Switch between databases via configuration
4. **Rollback plan**: Revert to SQLite if issues arise

## Success Criteria

1. ✅ Ren agent can receive and execute tasks from kanban
2. ✅ Heartbeat system detects agent crashes within 2 minutes
3. ✅ Multiple agents can work concurrently without database errors
4. ✅ Task assignment logic works correctly (specific vs Aki assignment)
5. ✅ Mission Control shows real-time agent status
6. ✅ System recovers automatically from agent failures
7. ✅ Local model used for heartbeats (no external API costs)

## Next Steps

1. **Immediate**: Create database schema and migration script
2. **Today**: Implement core `agent-cli.py` with file locking
3. **Tomorrow**: Test with Ren agent and basic tasks
4. **This week**: Integrate with Mission Control web UI
5. **Next week**: Add advanced features and optimization

---

## Appendix A: Agent Configuration

### Ren Agent
```json
{
  "name": "ren",
  "role": "infrastructure & maintenance",
  "model": "qwen-coder-local",
  "capabilities": ["shell", "file_ops", "monitoring", "cron"],
  "default_workdir": "/home/pesu/.openclaw/pesulabs",
  "heartbeat_interval": 30
}
```

### Aki Agent
```json
{
  "name": "aki", 
  "role": "coordination & reporting",
  "model": "deepseek-chat",
  "capabilities": ["coordination", "reporting", "delegation", "analysis"],
  "can_claim_unassigned": true,
  "heartbeat_interval": 30
}
```

### Other Agents
Similar configurations for kuro (technical), shin (strategy), sora (creative).

## Appendix B: Example Workflow

```bash
# 1. Human creates task in Mission Control web UI
#    - Task: "Update documentation"
#    - Assignee: ren
#    - Priority: medium

# 2. Ren agent polls for tasks
ren-agent --poll
# → Finds assigned task, marks as in_progress

# 3. Ren executes task
ren-agent --execute --task TASK-123
# → Runs: openclaw agent --agent ren-grunt --message "Update documentation..."

# 4. Ren reports results
ren-agent --results --task TASK-123 --output "Documentation updated successfully"

# 5. System updates task status
#    - Task marked as 'done'
#    - Ren status back to 'idle'
#    - Results stored in database
```

## Appendix C: Troubleshooting Guide

### Common Issues

1. **Database locked errors**
   - Solution: Check for stuck locks, increase lock timeout
   - Command: `agent-cli.py locks cleanup`

2. **Agent not responding to heartbeats**
   - Solution: Check agent process, restart if needed
   - Command: `agent-cli.py agents restart --agent ren`

3. **Tasks stuck in 'in_progress'**
   - Solution: Check for crashed agents, reassign tasks
   - Command: `agent-cli.py tasks stuck --fix`

4. **Local model unavailable**
   - Solution: Check llamacpp-qwen service status
   - Command: `systemctl status llamacpp-qwen`

### Recovery Procedures

1. **Agent crash recovery**:
   ```bash
   # Detect crashed agents
   agent-cli.py agents detect-crashes
   
   # Reassign their tasks
   agent-cli.py tasks reassign --from ren --to aki
   
   # Restart agent
   systemctl restart ren-agent
   ```

2. **Database corruption recovery**:
   ```bash
   # Restore from backup
   agent-cli.py db restore --backup latest
   
   # Replay recent operations from logs
   agent-cli.py db replay-logs --since "2 hours ago"
   ```

3. **Complete system reset**:
   ```bash
   # Stop all agents
   agent-cli.py agents stop --all
   
   # Reset database (DANGEROUS - backup first)
   agent-cli.py db reset --confirm
   
   # Rest