# API Reference

## 📋 Overview

The Agent Task Manager API is a RESTful API built with FastAPI. It provides endpoints for managing tasks, projects, agents, and real-time updates.

## 🔌 Base URL

```
http://localhost:8000
```

## 📊 Health & Status

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-01T17:04:00.123456"
}
```

## 📁 Projects

### List Projects
```http
GET /api/projects
```

**Query Parameters:**
- None

**Response:**
```json
[
  {
    "id": "default",
    "name": "Default Project",
    "description": "Main project for agent orchestration",
    "created_at": "2026-03-01T17:04:00.123456",
    "updated_at": "2026-03-01T17:04:00.123456"
  }
]
```

### Create Project
```http
POST /api/projects
```

**Request Body:**
```json
{
  "name": "Agent OS Development",
  "description": "Building the agent orchestration system"
}
```

**Response:**
```json
{
  "id": "agent-os",
  "name": "Agent OS Development",
  "description": "Building the agent orchestration system",
  "created_at": "2026-03-01T17:04:00.123456",
  "updated_at": "2026-03-01T17:04:00.123456"
}
```

## 📋 Tasks

### List Tasks
```http
GET /api/tasks
```

**Query Parameters:**
- `project_id` (optional): Filter by project
- `status` (optional): Filter by status
- `assignee` (optional): Filter by assignee

**Response:**
```json
[
  {
    "id": "task-001",
    "project_id": "default",
    "title": "Design database schema",
    "description": "Design the SQLite database schema",
    "status": "done",
    "assignee": "ren-grunt",
    "priority": 2,
    "created_at": "2026-03-01T17:04:00.123456",
    "updated_at": "2026-03-01T17:04:00.123456",
    "parent_id": null
  }
]
```

### Create Task
```http
POST /api/tasks
```

**Request Body:**
```json
{
  "title": "Implement feature X",
  "description": "Detailed description of the feature",
  "project_id": "default",
  "priority": 1,
  "parent_id": null
}
```

**Response:**
```json
{
  "id": "task-002",
  "project_id": "default",
  "title": "Implement feature X",
  "description": "Detailed description of the feature",
  "status": "backlog",
  "assignee": null,
  "priority": 1,
  "created_at": "2026-03-01T17:04:00.123456",
  "updated_at": "2026-03-01T17:04:00.123456",
  "parent_id": null
}
```

### Get Task
```http
GET /api/tasks/{task_id}
```

**Path Parameters:**
- `task_id`: Task identifier

**Response:**
```json
{
  "id": "task-001",
  "project_id": "default",
  "title": "Design database schema",
  "description": "Design the SQLite database schema",
  "status": "done",
  "assignee": "ren-grunt",
  "priority": 2,
  "created_at": "2026-03-01T17:04:00.123456",
  "updated_at": "2026-03-01T17:04:00.123456",
  "parent_id": null
}
```

### Update Task
```http
PUT /api/tasks/{task_id}
```

**Path Parameters:**
- `task_id`: Task identifier

**Request Body:**
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "status": "wip",
  "assignee": "aki-partner",
  "priority": 2
}
```

**Note:** All fields are optional. Only provided fields will be updated.

**Response:**
```json
{
  "id": "task-001",
  "project_id": "default",
  "title": "Updated title",
  "description": "Updated description",
  "status": "wip",
  "assignee": "aki-partner",
  "priority": 2,
  "created_at": "2026-03-01T17:04:00.123456",
  "updated_at": "2026-03-01T17:05:00.123456",
  "parent_id": null
}
```

### Task Heartbeat
```http
POST /api/tasks/{task_id}/heartbeat
```

**Path Parameters:**
- `task_id`: Task identifier

**Request Body:**
```json
{
  "agent_id": "ren-grunt",
  "task_id": "task-001"
}
```

**Response:**
```json
{
  "status": "heartbeat_received"
}
```

## 🔄 Real-time Events

### Server-Sent Events (SSE)
```http
GET /api/events
```

**Headers:**
- `Accept: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

**Response Stream:**
```
data: {"event": "state_change"}

data: {"event": "state_change"}

data: {"event": "state_change"}
```

**Events:**
- `state_change`: Triggered when any task is created, updated, or deleted

## 🎯 Task Status Flow

### Valid Status Values
```python
[
  "backlog",      # New tasks start here
  "todo",         # Ready to work on
  "planning",     # Agent is planning approach
  "hitl_review",  # Human-in-the-loop review needed
  "wip",          # Work in progress
  "implemented",  # Work completed, needs verification
  "done",         # Task completed and verified
  "blocked",      # Blocked by external dependency
  "cancelled"     # Task cancelled
]
```

### Typical Flow
```
backlog → todo → planning → hitl_review → wip → implemented → done
```

## 🔐 Authentication

Currently, the API has no authentication for local development. For production deployment, add authentication middleware.

## 📝 Error Handling

### Error Responses
```json
{
  "detail": "Error message here"
}
```

### Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## 🧪 Example Requests

### Using curl
```bash
# Health check
curl http://localhost:8000/health

# List tasks
curl http://localhost:8000/api/tasks

# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Test task","description":"API test","project_id":"default"}'

# Update task
curl -X PUT http://localhost:8000/api/tasks/task-001 \
  -H "Content-Type: application/json" \
  -d '{"status":"wip","assignee":"ren-grunt"}'

# Stream events
curl -N http://localhost:8000/api/events
```

### Using Python
```python
import requests

BASE_URL = "http://localhost:8000"

# Create task
response = requests.post(f"{BASE_URL}/api/tasks", json={
    "title": "Python API test",
    "description": "Testing from Python",
    "project_id": "default",
    "priority": 1
})

# Update task
response = requests.put(f"{BASE_URL}/api/tasks/task-001", json={
    "status": "done",
    "assignee": "aki-partner"
})

# Stream events
import sseclient
response = requests.get(f"{BASE_URL}/api/events", stream=True)
client = sseclient.SSEClient(response)
for event in client.events():
    print(event.data)
```

## 🔄 WebSocket Alternative

For more advanced real-time features, WebSocket support can be added:

```python
# Future WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message received: {data}")
```

## 📈 Performance

### Database Indexes
The API automatically creates indexes for:
- Task status
- Task project_id
- Task updated_at
- Task history task_id

### Caching
For production, consider adding Redis caching for:
- Frequently accessed tasks
- Project lists
- Agent status

## 🔍 Monitoring

### Health Metrics
```bash
# Check database size
ls -lh backend/agent_tasks.db

# Check active connections
sqlite3 backend/agent_tasks.db "SELECT COUNT(*) FROM tasks WHERE status IN ('wip', 'planning')"

# Check recent activity
sqlite3 backend/agent_tasks.db "SELECT COUNT(*) FROM task_history WHERE timestamp > datetime('now', '-1 hour')"
```

### Logging
Logs are available in:
- Console output
- `backend/logs/` directory
- Database logs table

## 🚀 Production Considerations

### Rate Limiting
Add rate limiting middleware for production:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
```

### CORS Configuration
Update CORS for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Production domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Database Backups
```bash
# Backup script
sqlite3 agent_tasks.db ".backup backup/agent_tasks_$(date +%Y%m%d).db"
```

## 📚 Additional Resources

- [OpenAPI Documentation](http://localhost:8000/docs) - Interactive API docs
- [Redoc Documentation](http://localhost:8000/redoc) - Alternative API docs
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Framework docs
- [SQLite Documentation](https://www.sqlite.org/docs.html) - Database docs