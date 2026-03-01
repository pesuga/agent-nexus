"""
Agent Task Manager - Backend API Server
FastAPI application with real-time updates via Server-Sent Events
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import sqlite3
import threading

# Database setup
DB_PATH = "agent_tasks.db"

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'backlog',
        assignee TEXT,
        priority INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parent_id TEXT,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (parent_id) REFERENCES tasks (id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT DEFAULT 'idle',
        last_heartbeat TIMESTAMP,
        capabilities TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        status_from TEXT,
        status_to TEXT NOT NULL,
        changed_by TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        agent_id TEXT,
        message TEXT NOT NULL,
        level TEXT DEFAULT 'info',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id),
        FOREIGN KEY (agent_id) REFERENCES agents (id)
    )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_history_task ON task_history(task_id)")
    
    # Insert default project if none exists
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO projects (id, name, description) 
        VALUES ('default', 'Default Project', 'Main project for agent orchestration')
        """)
    
    conn.commit()
    conn.close()

# Pydantic models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: str = "default"
    priority: int = 0
    parent_id: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[int] = None

class TaskResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str]
    status: str
    assignee: Optional[str]
    priority: int
    created_at: str
    updated_at: str
    parent_id: Optional[str]

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

class AgentHeartbeat(BaseModel):
    agent_id: str
    task_id: Optional[str] = None

# Global state for SSE
sse_clients: Set[asyncio.Queue] = set()
last_state_hash: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("Database initialized")
    
    # Start stale task detector
    asyncio.create_task(stale_task_detector())
    
    yield
    
    # Cleanup
    for queue in sse_clients:
        await queue.put(None)

app = FastAPI(
    title="Agent Task Manager API",
    description="Custom Kanban system for AI agent orchestration",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Helper functions
def generate_id():
    import uuid
    return str(uuid.uuid4())

def get_state_hash(conn):
    """Generate a hash of the current state for change detection"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(updated_at) as latest, COUNT(*) as cnt 
        FROM tasks WHERE status != 'cancelled'
    """)
    row = cursor.fetchone()
    return f"{row['latest']}:{row['cnt']}" if row else "0:0"

async def notify_clients():
    """Notify all SSE clients of state change"""
    for queue in sse_clients:
        await queue.put("state_changed")

# SSE endpoint
@app.get("/api/events")
async def event_stream():
    async def event_generator():
        queue = asyncio.Queue()
        sse_clients.add(queue)
        try:
            while True:
                message = await queue.get()
                if message is None:
                    break
                yield f"data: {json.dumps({'event': 'state_change'})}\n\n"
                await asyncio.sleep(0.1)  # Prevent tight loop
        finally:
            sse_clients.remove(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Projects endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
async def get_projects(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    projects = cursor.fetchall()
    return [dict(project) for project in projects]

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate, 
    conn: sqlite3.Connection = Depends(get_db)
):
    project_id = generate_id()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (id, name, description)
        VALUES (?, ?, ?)
    """, (project_id, project.name, project.description))
    conn.commit()
    
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    created = cursor.fetchone()
    
    await notify_clients()
    return dict(created)

# Tasks endpoints
@app.get("/api/tasks", response_model=List[TaskResponse])
async def get_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db)
):
    cursor = conn.cursor()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if assignee:
        query += " AND assignee = ?"
        params.append(assignee)
    
    query += " ORDER BY priority DESC, created_at DESC"
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    return [dict(task) for task in tasks]

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate, 
    conn: sqlite3.Connection = Depends(get_db)
):
    task_id = generate_id()
    cursor = conn.cursor()
    
    # Verify project exists
    cursor.execute("SELECT id FROM projects WHERE id = ?", (task.project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    
    cursor.execute("""
        INSERT INTO tasks (id, project_id, title, description, priority, parent_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (task_id, task.project_id, task.title, task.description, task.priority, task.parent_id))
    
    # Log status change
    cursor.execute("""
        INSERT INTO task_history (task_id, status_from, status_to, changed_by)
        VALUES (?, NULL, 'backlog', 'system')
    """, (task_id,))
    
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    created = cursor.fetchone()
    
    await notify_clients()
    return dict(created)

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    update: TaskUpdate,
    conn: sqlite3.Connection = Depends(get_db)
):
    cursor = conn.cursor()
    
    # Get current task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Build update query
    updates = []
    params = []
    
    if update.title is not None:
        updates.append("title = ?")
        params.append(update.title)
    
    if update.description is not None:
        updates.append("description = ?")
        params.append(update.description)
    
    if update.status is not None:
        # Log status change
        cursor.execute("""
            INSERT INTO task_history (task_id, status_from, status_to, changed_by)
            VALUES (?, ?, ?, 'system')
        """, (task_id, task['status'], update.status))
        updates.append("status = ?")
        params.append(update.status)
    
    if update.assignee is not None:
        updates.append("assignee = ?")
        params.append(update.assignee)
    
    if update.priority is not None:
        updates.append("priority = ?")
        params.append(update.priority)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        params.append(task_id)
        cursor.execute(query, params)
        conn.commit()
    
    # Get updated task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    
    await notify_clients()
    return dict(updated)

@app.post("/api/tasks/{task_id}/heartbeat")
async def task_heartbeat(
    task_id: str,
    heartbeat: AgentHeartbeat,
    conn: sqlite3.Connection = Depends(get_db)
):
    cursor = conn.cursor()
    
    # Update task timestamp
    cursor.execute("""
        UPDATE tasks 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (task_id,))
    
    # Update agent heartbeat
    cursor.execute("""
        UPDATE agents 
        SET last_heartbeat = CURRENT_TIMESTAMP,
            status = CASE 
                WHEN ? IS NOT NULL THEN 'working' 
                ELSE 'idle' 
            END
        WHERE id = ?
    """, (heartbeat.task_id, heartbeat.agent_id))
    
    conn.commit()
    return {"status": "heartbeat_received"}

# Stale task detection
async def stale_task_detector():
    """Background task to detect and recover stale tasks"""
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find tasks that haven't been updated in 35 minutes
            stale_time = datetime.now() - timedelta(minutes=35)
            cursor.execute("""
                SELECT id, status, assignee 
                FROM tasks 
                WHERE status IN ('planning', 'wip') 
                AND updated_at < ?
            """, (stale_time.isoformat(),))
            
            stale_tasks = cursor.fetchall()
            
            for task in stale_tasks:
                print(f"Detected stale task: {task['id']} (status: {task['status']})")
                
                # Revert to Todo and clear assignee
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'todo', 
                        assignee = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (task['id'],))
                
                # Log the change
                cursor.execute("""
                    INSERT INTO task_history (task_id, status_from, status_to, changed_by)
                    VALUES (?, ?, 'todo', 'stale_detector')
                """, (task['id'], task['status']))
                
                # Log the event
                cursor.execute("""
                    INSERT INTO logs (task_id, message, level)
                    VALUES (?, ?, 'warning')
                """, (task['id'], f"Task reverted to todo due to inactivity (stale for 35+ minutes)"))
            
            if stale_tasks:
                conn.commit()
                await notify_clients()
            
            conn.close()
            
        except Exception as e:
            print(f"Error in stale task detector: {e}")
        
        await asyncio.sleep(60)  # Check every minute

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)