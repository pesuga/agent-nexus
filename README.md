# Agent Task Manager 🎯

A custom, self-contained Kanban system for AI agent orchestration with real-time updates, crash recovery, and multi-project support.

## 📋 Table of Contents
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📁 Project Structure](#-project-structure)
- [🔧 Configuration](#-configuration)
- [🎮 Usage Examples](#-usage-examples)
- [🤖 Agent Integration](#-agent-integration)
- [🛡️ Crash Recovery](#️-crash-recovery)
- [🚢 Deployment](#-deployment)
- [📊 API Reference](#-api-reference)
- [🧪 Testing](#-testing)
- [🔄 Development](#-development)
- [📈 Roadmap](#-roadmap)
- [🆘 Troubleshooting](#-troubleshooting)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

## ✨ Features

### Core Features
- **Custom Kanban Board**: Drag-and-drop interface with real-time updates
- **Multi-project Support**: Isolated project boards with task inheritance
- **Agent Coordination**: Assign tasks to AI agents (Ren, Aki, Kuro, Shin, Sora)
- **Crash Recovery**: Heartbeat system with stale task detection
- **Context Isolation**: Agents only receive task-specific context
- **Real-time Updates**: Server-Sent Events (SSE) for live updates

### Status Flow
```
Backlog → Todo → Planning → HITL Review → WIP → Implemented → Done
              ↑           ↑              ↑
              └───────────┴──────────────┘
              (Human review loops)

Additional States: Blocked, Cancelled
```

### Integration
- **OpenClaw Ready**: CLI tool works with OpenClaw agents
- **Simple API**: RESTful API with FastAPI backend
- **No External Dependencies**: Self-contained SQLite database
- **Easy Deployment**: Single machine or containerized

## 🚀 Quick Start

> **For a detailed 5-minute guide, see [QUICKSTART.md](QUICKSTART.md)**

### 1. Setup
```bash
# Clone and setup
cd agent-task-manager
python3 setup.py

# Or manually:
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Backend
```bash
cd backend
python3 main.py
# API available at http://localhost:8000
```

### 3. Open Frontend
```bash
# Open in browser
open frontend/index.html

# Or serve with Python
cd frontend
python3 -m http.server 8080
# Open http://localhost:8080
```

### 4. Use CLI
```bash
cd cli
python3 task_cli.py --help

# Create a task
python3 task_cli.py create "Implement feature X" --desc "Detailed description" --priority 2

# List tasks
python3 task_cli.py list --status todo

# Move task
python3 task_cli.py move <task-id> wip
```

## 📁 Project Structure

```
agent-task-manager/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main application
│   ├── requirements.txt    # Python dependencies
│   ├── requirements-dev.txt # Development dependencies
│   └── agent_tasks.db      # SQLite database (created on first run)
├── frontend/               # HTML/JS frontend
│   ├── index.html          # Main interface
│   ├── app.js              # Frontend logic
│   └── style.css           # CSS styles
├── cli/                    # Command-line interface
│   └── task_cli.py         # CLI tool
├── database/               # Database scripts
│   ├── schema.sql          # Database schema
│   └── migrations/         # Migration scripts
├── docs/                   # Comprehensive documentation
│   ├── API.md              # Complete REST API reference
│   ├── CLI.md              # Command-line interface guide
│   ├── INSTALLATION.md     # Step-by-step installation
│   ├── AGENTS.md           # AI agent integration guide
│   ├── DEPLOYMENT.md       # Production deployment guide
│   └── ...                 # Additional documentation
├── examples/               # Example code and scripts
│   ├── basic_workflow.py   # Complete workflow example
│   ├── ren_agent_example.py # Ren agent simulation
│   ├── openclaw_skill.py   # OpenClaw skill example
│   └── ...                 # More examples
├── tests/                  # Test suite
├── ARCHITECTURE.md         # System architecture
├── CONTRIBUTING.md         # Contribution guidelines
├── CHANGELOG.md           # Version history
├── QUICKSTART.md          # 5-minute getting started
├── LICENSE                # MIT License
├── setup.py              # Setup script
└── README.md             # This file
```

## 🔧 Configuration

### Backend Configuration
The backend uses SQLite by default. No configuration needed for development.

### CLI Configuration
```bash
# Show current config
task config-show

# Set API URL
task config-set api_base_url http://localhost:8000

# Set default project
task config-set default_project agent-os

# Set agent ID
task config-set agent_id ren-grunt
```

## 🎮 Usage Examples

### Web Interface
1. Open `frontend/index.html` in your browser
2. Create tasks using the form
3. Drag and drop tasks between columns
4. Switch between projects using tabs
5. Monitor agent status in real-time

### CLI Examples
```bash
# Create a high-priority task
task create "Fix critical bug" --desc "Bug in agent spawning" --priority 2

# List all tasks in planning
task list --status planning

# Assign task to agent
task assign <task-id> ren-grunt

# Move task to WIP
task move <task-id> wip

# Send heartbeat (for agents)
task heartbeat --task <task-id> --agent ren-grunt

# Watch real-time updates
task watch --interval 5
```

### API Examples
```bash
# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Test task","description":"API test","project_id":"default"}'

# List tasks
curl http://localhost:8000/api/tasks?status=todo

# Update task
curl -X PUT http://localhost:8000/api/tasks/<task-id> \
  -H "Content-Type: application/json" \
  -d '{"status":"wip","assignee":"ren-grunt"}'

# Stream events (SSE)
curl -N http://localhost:8000/api/events
```

## 🤖 Agent Integration

### OpenClaw Skill
Create an OpenClaw skill for agents to interact with the task manager:

```python
# Example skill for agents
from openclaw.skill import Skill

class TaskManagerSkill(Skill):
    def handle(self, command, args):
        if command == "task":
            # Use the CLI tool
            import subprocess
            result = subprocess.run(["task"] + args, capture_output=True, text=True)
            return result.stdout
```

### Agent Workflow
1. Agent picks up task from Todo queue
2. Agent sends heartbeat every 30 seconds
3. Agent completes work and updates task status
4. If agent crashes, task reverts to Todo after 35 minutes
5. Task moves through review stages to completion

## 🛡️ Crash Recovery

### Heartbeat System
- Agents touch task `updated_at` every 30 seconds
- Stale detector runs every minute
- Tasks inactive for 35+ minutes revert to Todo
- Auto-reassignment for stale tasks

### Monitoring
- Real-time agent status in UI
- Task history tracking
- System logs for debugging
- Health check endpoint

## 🚢 Deployment

### Development
```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && python3 -m http.server 8080
```

### Production
```bash
# Run backend as service
cd backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &

# Or use systemd
sudo cp agent-task-manager.service /etc/systemd/system/
sudo systemctl enable agent-task-manager
sudo systemctl start agent-task-manager
```

### Docker (Coming Soon)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 API Reference

### Endpoints
- `GET /health` - Health check
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/tasks` - List tasks (filter by project, status, assignee)
- `POST /api/tasks` - Create task
- `PUT /api/tasks/{id}` - Update task
- `POST /api/tasks/{id}/heartbeat` - Send heartbeat
- `GET /api/events` - Server-Sent Events stream

### Models
```python
# Task model
{
    "id": "uuid",
    "project_id": "string",
    "title": "string",
    "description": "string",
    "status": "backlog|todo|planning|hitl_review|wip|implemented|done|blocked|cancelled",
    "assignee": "string|null",
    "priority": 0|1|2,
    "created_at": "iso8601",
    "updated_at": "iso8601",
    "parent_id": "string|null"
}
```

## 🧪 Testing

### Run Tests
```bash
cd tests
python3 -m pytest
```

### Test Coverage
- API endpoints
- Database operations
- Real-time updates
- Crash recovery
- CLI commands

## 🔄 Development

### Adding Features
1. Update database schema in `backend/main.py`
2. Add API endpoints
3. Update frontend UI
4. Extend CLI commands
5. Write tests

### Code Style
- Python: Black formatting, type hints
- JavaScript: ES6+, no frameworks
- SQL: SQLite-compatible
- Documentation: Inline comments, README updates

## 📈 Roadmap

### Phase 1: MVP ✓
- [x] Basic backend API
- [x] Simple frontend
- [x] Task CLI
- [x] Real-time updates

### Phase 2: Core Features
- [ ] Advanced search and filtering
- [ ] Knowledge base integration
- [ ] OpenClaw skill
- [ ] Reporting and analytics

### Phase 3: Advanced Features
- [ ] File attachments
- [ ] Comments and discussions
- [ ] Advanced permissions
- [ ] Export/import

### Phase 4: Production Ready
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Backup system
- [ ] Monitoring dashboard

## 🆘 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check dependencies
pip install -r backend/requirements.txt

# Check port availability
netstat -tulpn | grep :8000
```

**Frontend not updating:**
- Check backend is running
- Check browser console for errors
- Verify SSE connection in Network tab

**CLI not working:**
```bash
# Make executable
chmod +x cli/task_cli.py

# Check Python path
which python3

# Check configuration
task config-show
```

### Logs
- Backend logs: Check console output or `server.log`
- Database: `backend/agent_tasks.db`
- Frontend: Browser developer tools

## 📚 Documentation

### Core Documentation
- [**Architecture**](ARCHITECTURE.md) - System design and components
- [**Product Requirements**](docs/PRD.md) - Complete product specifications and vision
- [**Project Assessment**](docs/ASSESSMENT.md) - Current status and gap analysis
- [**API Reference**](docs/API.md) - Complete REST API documentation with examples
- [**CLI Guide**](docs/CLI.md) - Complete command-line interface reference
- [**Installation Guide**](docs/INSTALLATION.md) - Step-by-step setup instructions
- [**Agent Integration**](docs/AGENTS.md) - Guide for AI agent workflows and coordination
- [**Deployment Guide**](docs/DEPLOYMENT.md) - Production deployment and scaling

### Examples & Tutorials
- [**Basic Workflow**](examples/basic_workflow.py) - Complete Python example
- [**Quick Start Guide**](QUICKSTART.md) - 5-minute getting started guide
- [**Ren Agent Example**](examples/ren_agent_example.py) - Infrastructure agent simulation
- [**OpenClaw Skill**](examples/openclaw_skill.py) - OpenClaw integration example
- [**Usage Examples**](#-usage-examples) - Common workflows and patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- Inspired by Vibe Kanban and Plane.so
- Built for OpenClaw agent orchestration
- Designed for simplicity and control

---

**Happy task managing!** 🎯

*Built with ❤️ for AI agent orchestration*
