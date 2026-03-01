# Quick Start Guide

Get up and running with Agent Task Manager in under 5 minutes!

## 🚀 5-Minute Setup

### Step 1: Clone or Download
```bash
# Clone repository (if available)
git clone https://github.com/your-org/agent-task-manager.git
cd agent-task-manager

# Or use existing directory
cd agent-task-manager
```

### Step 2: Run Setup Script
```bash
python3 setup.py
```

This will:
- Create Python virtual environment
- Install dependencies
- Make CLI executable
- Create example data

### Step 3: Start Backend
```bash
cd backend
python3 main.py
```

You'll see:
```
Database initialized with 3 tables
Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 4: Open Frontend
Open `frontend/index.html` in your browser, or serve it:
```bash
cd frontend
python3 -m http.server 8080
# Open http://localhost:8080
```

### Step 5: Test CLI
```bash
cd cli
python3 task_cli.py --help
```

🎉 **You're ready to go!**

## 📋 First Tasks

### 1. Create Your First Task
```bash
# Via CLI
task create "My first task" --desc "Learning the system" --priority 1

# Or via web interface
# Click "New Task" button in the frontend
```

### 2. List Tasks
```bash
task list
```

### 3. Move Task Through Workflow
```bash
# Get task ID from list
task move <task-id> planning
task move <task-id> wip
task move <task-id> done
```

### 4. Assign to Agent
```bash
task assign <task-id> ren-grunt
```

## 🎮 Interactive Demo

Run the example workflow to see everything in action:
```bash
python3 examples/basic_workflow.py
```

This will:
1. Check API health
2. Create example project and tasks
3. Simulate a workflow
4. Show real-time updates
5. Generate a report

## 🤖 Agent Integration

### Test Ren Agent
```bash
python3 examples/ren_agent_example.py
```

This simulates Ren (Infrastructure Sentinel) agent:
- Looks for infrastructure tasks
- Assigns tasks to itself
- Works on tasks
- Sends heartbeats
- Completes tasks

### OpenClaw Integration
```bash
python3 examples/openclaw_skill.py
```

Shows how to create an OpenClaw skill for agents.

## 🌐 Web Interface Tour

1. **Kanban Board**: Drag and drop tasks between columns
2. **Project Tabs**: Switch between different projects
3. **New Task Form**: Create tasks with title, description, priority
4. **Real-time Updates**: See changes instantly across all clients
5. **Agent Status**: Monitor which agents are active

## 🔧 Common Workflows

### Daily Standup
```bash
# See what's in progress
task list --status wip

# See what's todo
task list --status todo

# See completed yesterday
task list --status done
```

### Agent Work Session
```bash
# Agent picks up task
task list --status todo
task assign <task-id> ren-grunt
task move <task-id> planning

# Work on task (send heartbeats)
task heartbeat --task <task-id> --agent ren-grunt

# Complete task
task move <task-id> implemented
task move <task-id> done
```

### Project Review
```bash
# See all tasks in project
task list --project agent-os

# Count by status
task list --project agent-os --json | jq 'group_by(.status) | map({status: .[0].status, count: length})'

# See high priority items
task list --project agent-os --json | jq '.[] | select(.priority == 2)'
```

## 🚨 Troubleshooting

### Backend Won't Start
```bash
# Check port 8000
netstat -tulpn | grep :8000

# Kill existing process
pkill -f "python3 main.py"

# Check Python version
python3 --version  # Should be 3.8+

# Check dependencies
cd backend
pip install -r requirements.txt
```

### Frontend Not Connecting
1. Check backend is running: `curl http://localhost:8000/health`
2. Check browser console for errors (F12 → Console)
3. Verify frontend API URL in `app.js`

### CLI Not Working
```bash
# Make executable
chmod +x cli/task_cli.py

# Test with full path
python3 cli/task_cli.py --help

# Check configuration
task config-show
```

## 📚 Next Steps

### Learn More
- Read the [Architecture Guide](ARCHITECTURE.md) to understand the system
- Explore the [API Documentation](docs/API.md) for programmatic access
- Study the [Agent Integration Guide](docs/AGENTS.md) for AI workflows

### Customize
1. Modify frontend styles in `frontend/style.css`
2. Add custom task fields in `backend/main.py`
3. Create new agent types in `docs/AGENTS.md`

### Deploy
- [Local deployment](docs/DEPLOYMENT.md#local-development) for personal use
- [Docker deployment](docs/DEPLOYMENT.md#docker-deployment) for containers
- [Production deployment](docs/DEPLOYMENT.md#production-deployment) for teams

## 🆘 Need Help?

### Quick Checks
```bash
# System health
task health

# Database size
ls -lh backend/agent_tasks.db

# Active tasks
sqlite3 backend/agent_tasks.db "SELECT COUNT(*) FROM tasks WHERE status IN ('wip', 'planning')"
```

### Common Questions

**Q: How do I reset the database?**
```bash
rm backend/agent_tasks.db
python3 backend/main.py  # Creates fresh database
```

**Q: Can I use multiple frontends?**
Yes! Open the frontend on multiple devices - they sync in real-time.

**Q: How do tasks revert on agent crash?**
Agents should send heartbeats every 30 seconds. Tasks without heartbeats for 35+ minutes revert to todo.

**Q: Can I backup the database?**
```bash
sqlite3 backend/agent_tasks.db ".backup backup.db"
```

## 🎯 Success Checklist

- [ ] Backend running on port 8000
- [ ] Frontend accessible in browser
- [ ] CLI commands working
- [ ] Created first task
- [ ] Moved task through workflow
- [ ] Tested agent heartbeat
- [ ] Seen real-time updates

---

**Congratulations!** You've successfully set up Agent Task Manager. 

Now explore:
- Create a project for your team
- Integrate with your AI agents
- Customize the workflow for your needs
- Deploy for production use

Happy task managing! 🎯