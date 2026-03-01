# Agent Task Manager - Architecture

## Overview
A custom, self-contained Kanban system for AI agent orchestration with real-time updates, crash recovery, and multi-project support.

## System Components

### 1. Backend (Python FastAPI)
- **API Server**: RESTful API with WebSocket/SSE for real-time updates
- **Database**: SQLite with migrations
- **Orchestrator**: Task assignment, agent coordination, crash recovery
- **Knowledge Base**: Semantic search for task context

### 2. Frontend (HTML/JS)
- **Kanban Board**: Drag-and-drop interface with real-time updates
- **Project Switcher**: Multi-project support with isolated boards
- **Task Details**: Full task information and history
- **Agent Monitor**: Live view of agent activity

### 3. CLI Tool (Python)
- **Task Operations**: Create, update, assign, list tasks
- **Agent Interface**: For AI agents to interact with the system
- **Project Management**: Create and switch between projects
- **OpenClaw Integration**: Skill for agent interaction

### 4. Database Schema
```
projects (id, name, description, created_at, updated_at)
tasks (id, project_id, title, description, status, assignee, priority, created_at, updated_at, parent_id)
agents (id, name, type, status, last_heartbeat, capabilities)
task_history (id, task_id, status_from, status_to, changed_by, timestamp)
logs (id, task_id, agent_id, message, level, timestamp)
knowledge_base (id, project_id, content, embedding, metadata, created_at)
```

## Status Flow
```
Backlog → Todo → Planning → HITL Review → WIP → Implemented → Done
              ↑           ↑              ↑
              └───────────┴──────────────┘
              (Human review loops)

Additional States:
- Blocked: Needs human intervention
- Cancelled: Task killed, all work stopped
```

## Key Features

### 1. Context Isolation
- Agents only receive task-specific context
- Semantic search from knowledge base
- Project-specific context isolation

### 2. Crash Recovery
- **Heartbeat**: Agents touch task `updated_at` every 30 seconds
- **Stale Detection**: Tasks revert to Todo after 35 minutes of inactivity
- **Auto-reassignment**: Stale tasks automatically reassigned

### 3. Real-time Updates
- **Server-Sent Events (SSE)**: Lightweight real-time updates
- **Change Detection**: Only push updates when something changes
- **Debounced Renders**: 150ms debounce on frontend

### 4. Multi-project Support
- Isolated project boards
- Project-specific knowledge bases
- Subtask inheritance (subtasks inherit parent's project)

### 5. Task CLI
- Unified interface for humans and agents
- OpenClaw skill integration
- Batch operations and scripting support

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite with SQLAlchemy ORM
- **Real-time**: Server-Sent Events (SSE)
- **Search**: Sentence Transformers for semantic search
- **Auth**: Simple token-based authentication

### Frontend
- **Core**: Vanilla JavaScript with ES6+
- **UI**: Custom CSS with Flexbox/Grid
- **Real-time**: EventSource API for SSE
- **Drag-drop**: Native HTML5 Drag and Drop API

### CLI
- **Framework**: Click or Typer
- **Integration**: OpenClaw skill system
- **Configuration**: TOML/YAML config files

## Deployment

### Development
```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && python -m http.server 8080

# CLI
pip install -e cli/
```

### Production
- **Single machine**: All components on one server
- **Docker**: Containerized deployment
- **Systemd**: Service management for backend

## Integration Points

### 1. OpenClaw Agents
- CLI tool used via OpenClaw skills
- Task assignment triggers agent spawning
- Progress reporting back to system

### 2. External Systems
- **GitHub**: PR creation and linking
- **File System**: Task artifacts and outputs
- **Notification**: Email/Slack for human reviews

## Security Considerations
- Local-only deployment by default
- Token-based authentication for API
- SQL injection protection via ORM
- Input validation and sanitization

## Monitoring and Logging
- Structured logging with JSON format
- Health check endpoints
- Performance metrics
- Error tracking and alerting

## Roadmap

### Phase 1: MVP (Week 1)
- Basic backend API with SQLite
- Simple HTML frontend
- Task CLI with basic operations
- Real-time updates via SSE

### Phase 2: Core Features (Week 2)
- Kanban board with drag-drop
- Crash recovery system
- Project management
- Knowledge base integration

### Phase 3: Advanced Features (Week 3)
- OpenClaw skill integration
- Advanced search and filtering
- Reporting and analytics
- Export/import functionality

### Phase 4: Production Ready (Week 4)
- Performance optimization
- Security hardening
- Documentation
- Deployment scripts