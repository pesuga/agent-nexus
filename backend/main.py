"""
Agent Task Manager - Backend API Server
FastAPI application with real-time updates via Server-Sent Events
"""

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager
from enum import Enum
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
import sqlite3
from dispatcher import build_dispatch_decision, load_agent_profiles

# Database setup
ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DISPATCH_DB_PATH", str(ROOT_DIR / "database" / "agent_tasks.db"))).resolve()
ARTIFACTS_DIR = ROOT_DIR / "tmp" / "task-artifacts"
AGENT_DEFINITIONS_DIR = ROOT_DIR / "agents"


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    PLANNING = "planning"
    HITL_REVIEW = "hitl_review"
    WORKING = "working"
    READY_TO_IMPLEMENT = "ready_to_implement"
    APPROVAL = "approval"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


ACTIVE_WORK_STATUSES = (TaskStatus.PLANNING.value, TaskStatus.WORKING.value)

ALLOWED_TRANSITIONS = {
    TaskStatus.BACKLOG.value: {TaskStatus.TODO.value, TaskStatus.CANCELLED.value},
    TaskStatus.TODO.value: {TaskStatus.BACKLOG.value, TaskStatus.PLANNING.value, TaskStatus.BLOCKED.value, TaskStatus.CANCELLED.value},
    TaskStatus.PLANNING.value: {TaskStatus.HITL_REVIEW.value, TaskStatus.BLOCKED.value, TaskStatus.CANCELLED.value},
    TaskStatus.HITL_REVIEW.value: {TaskStatus.WORKING.value, TaskStatus.PLANNING.value, TaskStatus.BLOCKED.value, TaskStatus.CANCELLED.value},
    TaskStatus.WORKING.value: {TaskStatus.READY_TO_IMPLEMENT.value, TaskStatus.BLOCKED.value, TaskStatus.CANCELLED.value},
    TaskStatus.READY_TO_IMPLEMENT.value: {TaskStatus.APPROVAL.value, TaskStatus.WORKING.value, TaskStatus.BLOCKED.value, TaskStatus.CANCELLED.value},
    TaskStatus.APPROVAL.value: {TaskStatus.COMPLETED.value, TaskStatus.WORKING.value, TaskStatus.BLOCKED.value, TaskStatus.CANCELLED.value},
    TaskStatus.BLOCKED.value: {TaskStatus.TODO.value, TaskStatus.PLANNING.value, TaskStatus.CANCELLED.value},
    TaskStatus.COMPLETED.value: set(),
    TaskStatus.CANCELLED.value: set(),
}

REVIEWER_ROLES = {"human_reviewer", "human_admin"}
OVERRIDE_ROLES = {"human_admin"}

ROLE_PERMISSIONS = {
    "human_admin": [
        "task:update",
        "dispatch:execute",
        "dispatch:pause",
        "dispatch:reassign",
        "dispatch:override",
        "hitl:approve",
        "hitl:reject",
    ],
    "human_reviewer": [
        "hitl:approve",
        "hitl:reject",
    ],
    "agent_runner": [
        "task:heartbeat",
    ],
}


def hash_password(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()


# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        global_role TEXT NOT NULL DEFAULT 'member',
        disabled INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_memberships (
        project_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (project_id, user_id),
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dispatch_decisions (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        task_status TEXT NOT NULL,
        selected_agent TEXT NOT NULL,
        selected_model TEXT NOT NULL,
        provider TEXT NOT NULL,
        confidence REAL NOT NULL,
        rationale TEXT NOT NULL,
        prompt_pack TEXT NOT NULL,
        candidate_scores TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_comments (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        author TEXT,
        comment TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_artifacts (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        path TEXT NOT NULL,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    """)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS model_registry (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            provider TEXT NOT NULL,
            model_name TEXT NOT NULL,
            api_base TEXT,
            is_default INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_profiles (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            system_prompt TEXT,
            model_id TEXT,
            provider TEXT,
            tools_json TEXT NOT NULL DEFAULT '[]',
            skills_json TEXT NOT NULL DEFAULT '[]',
            context_policy_json TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (model_id) REFERENCES model_registry (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runtime_instances (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            profile_id TEXT,
            container_name TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            task_id TEXT,
            started_at TIMESTAMP,
            last_heartbeat TIMESTAMP,
            stopped_at TIMESTAMP,
            exit_code INTEGER,
            meta_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (profile_id) REFERENCES agent_profiles (id),
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_activity_events (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            instance_id TEXT,
            agent_id TEXT,
            task_id TEXT,
            level TEXT NOT NULL DEFAULT 'info',
            message TEXT NOT NULL,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            meta_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (instance_id) REFERENCES agent_runtime_instances (id),
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        """
    )
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_history_task ON task_history(task_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispatch_task_created ON dispatch_decisions(task_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_comments_task_created ON task_comments(task_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_artifacts_task_created ON task_artifacts(task_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memberships_user ON project_memberships(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memberships_project ON project_memberships(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_registry_default ON model_registry(is_default)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_profiles_project ON agent_profiles(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runtime_project ON agent_runtime_instances(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runtime_task ON agent_runtime_instances(task_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_activity_project_ts ON agent_activity_events(project_id, ts)")
    
    # Insert default project if none exists
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO projects (id, name, description) 
        VALUES ('default', 'Default Project', 'Main project for agent orchestration')
        """)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_id = "local-admin"
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, display_name, global_role, disabled)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                admin_id,
                "admin@dispatch.local",
                hash_password("admin"),
                "Local Admin",
                "admin",
            ),
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO project_memberships (project_id, user_id, role)
            VALUES ('default', ?, 'owner')
            """,
            (admin_id,),
        )
    
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
    status: Optional[TaskStatus] = None
    assignee: Optional[str] = None
    priority: Optional[int] = None

class TaskResponse(BaseModel):
    id: str
    project_id: Optional[str]
    title: str
    description: Optional[str]
    status: str
    assignee: Optional[str]
    priority: int
    created_at: Optional[str]
    updated_at: Optional[str]
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


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None
    global_role: str = "member"


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    global_role: Optional[str] = None
    disabled: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    global_role: str
    disabled: bool
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    actor_id: str
    actor_role: str
    email: str
    display_name: Optional[str]


class ProjectMembershipCreate(BaseModel):
    user_id: str
    role: str = "member"


class ProjectMembershipResponse(BaseModel):
    project_id: str
    user_id: str
    role: str
    created_at: str


class AgentHeartbeat(BaseModel):
    agent_id: str
    task_id: Optional[str] = None


class DispatchRequest(BaseModel):
    execute: bool = True
    context_file: Optional[str] = None
    context_bundle: Optional[Dict] = None


class DispatchDecisionResponse(BaseModel):
    task_id: str
    selected_agent: str
    selected_model: str
    provider: str
    confidence: float
    rationale: str
    prompt_pack: Dict
    candidate_scores: List[Dict]
    executed: bool
    resulting_status: str


class HitlApproveRequest(BaseModel):
    comment: Optional[str] = None


class HitlRejectRequest(BaseModel):
    comment: Optional[str] = None
    target_status: Optional[TaskStatus] = None


class DispatchPauseRequest(BaseModel):
    reason: Optional[str] = None


class DispatchOverrideRequest(BaseModel):
    agent_id: str
    reason: Optional[str] = None
    move_to_planning: bool = False


class DispatchReassignRequest(BaseModel):
    agent_id: str
    reason: Optional[str] = None


class TaskCommentCreate(BaseModel):
    comment: str


class TaskArtifactCreate(BaseModel):
    stage: str
    path: str


class TaskArtifactContentCreate(BaseModel):
    stage: str
    content: str
    filename: Optional[str] = None


class TaskArtifactContentUpdate(BaseModel):
    content: str


class StageSubmitRequest(BaseModel):
    stage: str
    to_status: TaskStatus
    note: Optional[str] = None


class StageCheckResponse(BaseModel):
    task_id: str
    stage: str
    task_status: Optional[str]
    to_status: Optional[str]
    transition_valid: bool
    artifact_path: Optional[str]
    artifact_exists: bool
    artifact_quality_ok: bool
    ready: bool
    reason: Optional[str]
    detail: str


class ModelRegistryCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    label: str
    provider: str
    model_name: str
    api_base: Optional[str] = None
    is_default: bool = False
    enabled: bool = True
    config: Optional[Dict[str, Any]] = None


class ModelRegistryUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    label: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_base: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ModelRegistryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    label: str
    provider: str
    model_name: str
    api_base: Optional[str]
    is_default: bool
    enabled: bool
    config: Dict[str, Any]
    created_at: str
    updated_at: str


class AgentProfileCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str
    type: str
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    provider: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    context_policy: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AgentProfileUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: Optional[str] = None
    type: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    provider: Optional[str] = None
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    context_policy: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class AgentProfileResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    project_id: str
    name: str
    type: str
    system_prompt: Optional[str]
    model_id: Optional[str]
    provider: Optional[str]
    tools: List[str]
    skills: List[str]
    context_policy: Dict[str, Any]
    enabled: bool
    created_at: str
    updated_at: str


class AgentInstanceCreate(BaseModel):
    profile_id: Optional[str] = None
    container_name: Optional[str] = None
    task_id: Optional[str] = None
    status: str = "pending"
    meta: Dict[str, Any] = Field(default_factory=dict)


class AgentInstanceUpdate(BaseModel):
    status: Optional[str] = None
    task_id: Optional[str] = None
    container_name: Optional[str] = None
    exit_code: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None
    heartbeat: bool = False


class AgentInstanceResponse(BaseModel):
    id: str
    project_id: str
    profile_id: Optional[str]
    container_name: Optional[str]
    status: str
    task_id: Optional[str]
    started_at: Optional[str]
    last_heartbeat: Optional[str]
    stopped_at: Optional[str]
    exit_code: Optional[int]
    meta: Dict[str, Any]
    created_at: str
    updated_at: str


class AgentActivityCreate(BaseModel):
    instance_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    level: str = "info"
    message: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class AgentActivityResponse(BaseModel):
    id: str
    project_id: str
    instance_id: Optional[str]
    agent_id: Optional[str]
    task_id: Optional[str]
    level: str
    message: str
    ts: str
    meta: Dict[str, Any]


class ContextEstimateRequest(BaseModel):
    comments_limit: int = 20
    artifacts_limit: int = 20
    activity_limit: int = 30
    prompt_template: Optional[str] = None


class ContextEstimateResponse(BaseModel):
    task_id: str
    counts: Dict[str, int]
    chars: Dict[str, int]
    estimated_tokens: Dict[str, int]
    total_estimated_tokens: int

# Global state for SSE
sse_clients: Set[asyncio.Queue] = set()
last_state_hash: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    boot_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    boot_conn.row_factory = sqlite3.Row
    try:
        boot_cursor = boot_conn.cursor()
        boot_cursor.execute("SELECT id FROM projects")
        for row in boot_cursor.fetchall():
            project_id = str(row["id"])
            sync_result = sync_agent_profiles_from_files(boot_conn, project_id, overwrite_existing=False)
            sync_project_agent_profiles_to_files(boot_conn, project_id)
            if sync_result.get("inserted"):
                print(f"Synced {sync_result['inserted']} agent profiles from files into project {project_id}")
    finally:
        boot_conn.close()
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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Helper functions
def generate_id():
    import uuid
    return str(uuid.uuid4())


def _normalize_string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for item in values:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def _infer_agent_profile_type(capabilities: List[str], agent_name: str) -> str:
    caps = {c.strip().lower() for c in capabilities if str(c).strip()}
    if "coding" in caps or "architecture" in caps or "debugging" in caps or "system_design" in caps:
        return "coder"
    if "strategy" in caps or "planning" in caps or "analysis" in caps:
        return "strategist"
    if "creativity" in caps or "design" in caps or "innovation" in caps:
        return "creative"
    if "infrastructure" in caps or "maintenance" in caps or "automation" in caps:
        return "operator"
    if "coordination" in caps or "project_management" in caps or "reporting" in caps:
        return "coordinator"
    fallback = agent_name.strip().lower()
    if fallback == "kuro":
        return "coder"
    if fallback == "shin":
        return "strategist"
    if fallback == "sora":
        return "creative"
    if fallback == "ren":
        return "operator"
    if fallback == "aki":
        return "coordinator"
    return "generalist"


def load_agent_profiles_from_files() -> List[Dict[str, Any]]:
    if not AGENT_DEFINITIONS_DIR.exists():
        return []

    nanobot_path = AGENT_DEFINITIONS_DIR / "nanobot_profiles.json"
    nanobot_map: Dict[str, Dict[str, Any]] = {}
    if nanobot_path.exists():
        try:
            raw = json.loads(nanobot_path.read_text(encoding="utf-8"))
            agents_map = raw.get("agents", {}) if isinstance(raw, dict) else {}
            if isinstance(agents_map, dict):
                for key, value in agents_map.items():
                    if isinstance(value, dict):
                        nanobot_map[str(key).strip().lower()] = value
        except Exception:
            nanobot_map = {}

    profiles: List[Dict[str, Any]] = []
    for path in sorted(AGENT_DEFINITIONS_DIR.glob("*.json")):
        if path.name in {"agent-schema.json", "nanobot_profiles.json"}:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue

        name = str(data.get("name", "")).strip()
        if not name:
            continue
        key = name.lower()
        nanobot_data = nanobot_map.get(key, {})

        file_skills = _normalize_string_list(data.get("skills", []))
        nanobot_skills = _normalize_string_list(nanobot_data.get("skills", []))
        combined_skills = _normalize_string_list(file_skills + nanobot_skills)
        allowed_tools = _normalize_string_list(nanobot_data.get("allowed_tools", []))
        run_states = _normalize_string_list(nanobot_data.get("run_states", []))
        workflow_states = _normalize_string_list(data.get("workflow_states", []))
        capabilities = _normalize_string_list(data.get("capabilities", []))

        identity = str(data.get("identity", "")).strip()
        soul = str(data.get("soul", "")).strip()
        focus = str(nanobot_data.get("focus", "")).strip()
        system_prompt_lines = [line for line in [identity, soul, focus] if line]
        system_prompt = "\n\n".join(system_prompt_lines) if system_prompt_lines else None

        context_policy = {
            "avatar": data.get("avatar"),
            "identity": identity or None,
            "soul": soul or None,
            "focus": focus or None,
            "capabilities": capabilities,
            "mcps": _normalize_string_list(data.get("mcps", [])),
            "workflow_states": workflow_states,
            "run_states": run_states,
            "max_concurrent_tasks": int(data.get("max_concurrent_tasks", 3) or 3),
            "priority": int(data.get("priority", 5) or 5),
            "openclaw_integration": data.get("openclaw_integration", {}) if isinstance(data.get("openclaw_integration"), dict) else {},
            "metadata": data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {},
            "source": "agents-json",
        }

        profiles.append(
            {
                "name": name,
                "type": _infer_agent_profile_type(capabilities, name),
                "system_prompt": system_prompt,
                "provider": str(data.get("provider", "")).strip() or str(nanobot_data.get("provider", "")).strip() or None,
                "model_name": str(data.get("model", "")).strip() or str(nanobot_data.get("model", "")).strip() or None,
                "tools": allowed_tools,
                "skills": combined_skills,
                "context_policy": context_policy,
                "enabled": True,
            }
        )
    return profiles


def sync_agent_profiles_from_files(
    conn: sqlite3.Connection,
    project_id: str,
    overwrite_existing: bool = False,
) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")

    file_profiles = load_agent_profiles_from_files()
    if not file_profiles:
        return {"project_id": project_id, "scanned": 0, "inserted": 0, "updated": 0, "skipped": 0}

    cursor.execute("SELECT * FROM agent_profiles WHERE project_id = ?", (project_id,))
    existing_rows = cursor.fetchall()
    existing_by_name = {str(row["name"]).strip().lower(): row for row in existing_rows}

    cursor.execute("SELECT id, provider, model_name FROM model_registry")
    model_lookup: Dict[tuple[str, str], str] = {}
    for row in cursor.fetchall():
        provider = str(row["provider"] or "").strip().lower()
        model_name = str(row["model_name"] or "").strip()
        if provider and model_name:
            model_lookup[(provider, model_name)] = str(row["id"])

    inserted = 0
    updated = 0
    skipped = 0
    synced_names: List[str] = []

    for profile in file_profiles:
        name = str(profile["name"]).strip()
        if not name:
            skipped += 1
            continue
        key = name.lower()
        provider = str(profile.get("provider") or "").strip()
        model_name = str(profile.get("model_name") or "").strip()
        model_id = model_lookup.get((provider.lower(), model_name)) if provider and model_name else None
        existing = existing_by_name.get(key)

        if existing:
            if not overwrite_existing:
                skipped += 1
                continue
            cursor.execute(
                """
                UPDATE agent_profiles
                SET type = ?, system_prompt = ?, model_id = ?, provider = ?, tools_json = ?, skills_json = ?, context_policy_json = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    str(profile.get("type") or "generalist"),
                    profile.get("system_prompt"),
                    model_id,
                    provider or None,
                    json.dumps(profile.get("tools") or []),
                    json.dumps(profile.get("skills") or []),
                    json.dumps(profile.get("context_policy") or {}),
                    1 if profile.get("enabled", True) else 0,
                    str(existing["id"]),
                ),
            )
            updated += 1
            synced_names.append(name)
            continue

        cursor.execute(
            """
            INSERT INTO agent_profiles
            (id, project_id, name, type, system_prompt, model_id, provider, tools_json, skills_json, context_policy_json, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generate_id(),
                project_id,
                name,
                str(profile.get("type") or "generalist"),
                profile.get("system_prompt"),
                model_id,
                provider or None,
                json.dumps(profile.get("tools") or []),
                json.dumps(profile.get("skills") or []),
                json.dumps(profile.get("context_policy") or {}),
                1 if profile.get("enabled", True) else 0,
            ),
        )
        inserted += 1
        synced_names.append(name)

    conn.commit()
    return {
        "project_id": project_id,
        "scanned": len(file_profiles),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "synced_profiles": synced_names,
    }

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


def serialize_task_row(row: sqlite3.Row) -> Dict:
    """Normalize task rows to avoid response model failures on legacy/null data."""
    task = dict(row)
    if not task.get("id"):
        task["id"] = generate_id()
    if not task.get("project_id"):
        task["project_id"] = "default"
    if not task.get("title"):
        task["title"] = "(untitled)"
    if not task.get("status"):
        task["status"] = TaskStatus.BACKLOG.value
    else:
        task["status"] = str(task["status"]).strip().lower()
    if task.get("priority") is None:
        task["priority"] = 0
    task["parent_id"] = task.get("parent_id") or None
    if task.get("created_at") is not None:
        task["created_at"] = str(task["created_at"])
    if task.get("updated_at") is not None:
        task["updated_at"] = str(task["updated_at"])
    return task


def ensure_actor_role(actor_role: Optional[str], allowed_roles: set, action_name: str):
    role = (actor_role or "").strip().lower()
    if role not in allowed_roles:
        allowed = ", ".join(sorted(allowed_roles))
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: {action_name} requires role in [{allowed}] via X-Actor-Role header",
        )


def is_admin_actor(actor_role: Optional[str]) -> bool:
    role = (actor_role or "").strip().lower()
    return role in {"human_admin", "admin"}


def get_authorized_project_ids(
    conn: sqlite3.Connection,
    actor_role: Optional[str],
    actor_id: Optional[str],
) -> Optional[set[str]]:
    if is_admin_actor(actor_role):
        return None
    uid = (actor_id or "").strip()
    if not uid:
        return set()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT project_id
        FROM project_memberships
        WHERE user_id = ?
        """,
        (uid,),
    )
    return {str(row["project_id"]) for row in cursor.fetchall()}


def assert_project_visible(
    conn: sqlite3.Connection,
    project_id: str,
    actor_role: Optional[str],
    actor_id: Optional[str],
):
    allowed = get_authorized_project_ids(conn, actor_role, actor_id)
    if allowed is None:
        return
    if project_id not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden: project access denied")


def ensure_api_token(api_token: Optional[str], action_name: str):
    expected = os.getenv("DISPATCH_API_TOKEN")
    if not expected:
        return
    provided = (api_token or "").strip()
    if provided != expected:
        raise HTTPException(
            status_code=401,
            detail=f"Unauthorized: {action_name} requires valid X-API-Token",
        )


def parse_json_object(raw: Optional[str]) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_json_list(raw: Optional[str]) -> List[Any]:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _default_capabilities_for_type(agent_type: str) -> List[str]:
    key = (agent_type or "").strip().lower()
    mapping = {
        "coder": ["coding", "architecture", "debugging", "system_design"],
        "strategist": ["analysis", "planning", "strategy", "decision_making"],
        "creative": ["creativity", "design", "innovation", "brainstorming"],
        "operator": ["infrastructure", "maintenance", "automation", "testing"],
        "coordinator": ["coordination", "communication", "project_management", "reporting"],
        "generalist": ["analysis", "coordination", "documentation"],
    }
    return mapping.get(key, mapping["generalist"])


def _default_focus_for_type(agent_type: str) -> str:
    key = (agent_type or "").strip().lower()
    mapping = {
        "coder": "Code implementation, architecture, and debugging.",
        "strategist": "Planning quality, risk management, and decision support.",
        "creative": "UX/content ideation, narrative clarity, and creative options.",
        "operator": "Infrastructure reliability, deployments, and operational fixes.",
        "coordinator": "Coordination, state transitions, and stakeholder communication.",
    }
    return mapping.get(key, "General execution support.")


def _agent_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug or "agent"


def _read_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json_file(path: Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _find_agent_json_path_by_name(name: str) -> Optional[Path]:
    target = (name or "").strip().lower()
    if not target:
        return None
    for path in AGENT_DEFINITIONS_DIR.glob("*.json"):
        if path.name in {"agent-schema.json", "nanobot_profiles.json"}:
            continue
        data = _read_json_file(path, {})
        if isinstance(data, dict) and str(data.get("name", "")).strip().lower() == target:
            return path
    return None


def _get_profile_with_model(conn: sqlite3.Connection, profile_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ap.*, mr.model_name AS resolved_model_name, mr.provider AS resolved_model_provider
        FROM agent_profiles ap
        LEFT JOIN model_registry mr ON mr.id = ap.model_id
        WHERE ap.id = ?
        """,
        (profile_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    base = serialize_agent_profile_row(row)
    raw = dict(row)
    base["_resolved_model_name"] = raw.get("resolved_model_name")
    base["_resolved_model_provider"] = raw.get("resolved_model_provider")
    return base


def sync_agent_profile_to_files(conn: sqlite3.Connection, profile_id: str):
    profile = _get_profile_with_model(conn, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    name = str(profile.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Agent profile name cannot be empty")

    context_policy = _as_dict(profile.get("context_policy"))
    skills = _normalize_string_list(profile.get("skills", []))
    tools = _normalize_string_list(profile.get("tools", []))
    capabilities = _normalize_string_list(context_policy.get("capabilities", []))
    if not capabilities:
        capabilities = _default_capabilities_for_type(str(profile.get("type") or "generalist"))

    workflow_states = _normalize_string_list(context_policy.get("workflow_states", []))
    run_states = _normalize_string_list(context_policy.get("run_states", []))
    if not run_states:
        run_states = [state for state in workflow_states if state in {"planning", "working"}] or ["planning", "working"]
    if not workflow_states:
        workflow_states = run_states

    system_prompt = str(profile.get("system_prompt") or "").strip()
    prompt_parts = [part.strip() for part in re.split(r"\n\s*\n", system_prompt) if part.strip()]
    identity = str(context_policy.get("identity") or (prompt_parts[0] if len(prompt_parts) > 0 else f"{name} agent")).strip()
    soul = str(context_policy.get("soul") or (prompt_parts[1] if len(prompt_parts) > 1 else "")).strip()
    focus = str(context_policy.get("focus") or (prompt_parts[2] if len(prompt_parts) > 2 else _default_focus_for_type(str(profile.get("type") or "")))).strip()

    model_name = str(profile.get("_resolved_model_name") or "").strip() or "gpt-5.3-codex"
    provider = str(profile.get("provider") or profile.get("_resolved_model_provider") or "openai").strip() or "openai"

    agent_payload = {
        "name": name,
        "avatar": context_policy.get("avatar") or "bot",
        "identity": identity,
        "soul": soul,
        "model": model_name,
        "provider": provider,
        "capabilities": capabilities,
        "skills": skills,
        "mcps": _normalize_string_list(context_policy.get("mcps", [])),
        "workflow_states": workflow_states,
        "max_concurrent_tasks": int(context_policy.get("max_concurrent_tasks", 3) or 3),
        "priority": int(context_policy.get("priority", 5) or 5),
        "openclaw_integration": _as_dict(context_policy.get("openclaw_integration")),
        "metadata": {
            **_as_dict(context_policy.get("metadata")),
            "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        },
    }

    existing_path = _find_agent_json_path_by_name(name)
    target_path = existing_path or (AGENT_DEFINITIONS_DIR / f"{_agent_slug(name)}.json")
    _write_json_file(target_path, agent_payload)

    nanobot_path = AGENT_DEFINITIONS_DIR / "nanobot_profiles.json"
    nanobot_payload = _read_json_file(nanobot_path, {})
    if not isinstance(nanobot_payload, dict):
        nanobot_payload = {}
    agents_map = nanobot_payload.get("agents")
    if not isinstance(agents_map, dict):
        agents_map = {}
    agents_map[name.lower()] = {
        "display_name": name,
        "identity": identity,
        "model": model_name,
        "provider": provider,
        "skills": skills,
        "allowed_tools": tools,
        "run_states": run_states,
        "focus": focus,
    }
    nanobot_payload["agents"] = agents_map
    _write_json_file(nanobot_path, nanobot_payload)


def sync_agent_profile_name_removal_from_files(conn: sqlite3.Connection, removed_name: str):
    key = (removed_name or "").strip().lower()
    if not key:
        return

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM agent_profiles
        WHERE LOWER(name) = ?
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        """,
        (key,),
    )
    remaining = cursor.fetchone()
    if remaining:
        sync_agent_profile_to_files(conn, str(remaining["id"]))
        return

    existing_path = _find_agent_json_path_by_name(removed_name)
    if existing_path and existing_path.exists():
        existing_path.unlink()
    else:
        fallback_path = AGENT_DEFINITIONS_DIR / f"{_agent_slug(removed_name)}.json"
        if fallback_path.exists():
            fallback_path.unlink()

    nanobot_path = AGENT_DEFINITIONS_DIR / "nanobot_profiles.json"
    nanobot_payload = _read_json_file(nanobot_path, {})
    if isinstance(nanobot_payload, dict):
        agents_map = nanobot_payload.get("agents")
        if isinstance(agents_map, dict) and key in agents_map:
            del agents_map[key]
            nanobot_payload["agents"] = agents_map
            _write_json_file(nanobot_path, nanobot_payload)


def sync_project_agent_profiles_to_files(conn: sqlite3.Connection, project_id: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM agent_profiles
        WHERE project_id = ?
        ORDER BY updated_at DESC, created_at DESC
        """,
        (project_id,),
    )
    profile_ids = [str(row["id"]) for row in cursor.fetchall()]
    for profile_id in profile_ids:
        sync_agent_profile_to_files(conn, profile_id)
    return {"project_id": project_id, "synced": len(profile_ids)}


def serialize_model_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["is_default"] = bool(data.get("is_default"))
    data["enabled"] = bool(data.get("enabled", 1))
    data["config"] = parse_json_object(data.get("config_json"))
    data.pop("config_json", None)
    data["created_at"] = str(data.get("created_at")) if data.get("created_at") is not None else None
    data["updated_at"] = str(data.get("updated_at")) if data.get("updated_at") is not None else None
    return data


def serialize_agent_profile_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["tools"] = [str(x) for x in parse_json_list(data.get("tools_json"))]
    data["skills"] = [str(x) for x in parse_json_list(data.get("skills_json"))]
    data["context_policy"] = parse_json_object(data.get("context_policy_json"))
    data["enabled"] = bool(data.get("enabled", 1))
    data.pop("tools_json", None)
    data.pop("skills_json", None)
    data.pop("context_policy_json", None)
    data["created_at"] = str(data.get("created_at")) if data.get("created_at") is not None else None
    data["updated_at"] = str(data.get("updated_at")) if data.get("updated_at") is not None else None
    return data


def serialize_agent_instance_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["meta"] = parse_json_object(data.get("meta_json"))
    data.pop("meta_json", None)
    for key in ("started_at", "last_heartbeat", "stopped_at", "created_at", "updated_at"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


def serialize_agent_activity_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["meta"] = parse_json_object(data.get("meta_json"))
    data.pop("meta_json", None)
    if data.get("ts") is not None:
        data["ts"] = str(data["ts"])
    return data


def estimate_tokens_from_text(text: str) -> int:
    # Fast approximation suitable for pre-dispatch sizing in UI.
    return (len(text) + 3) // 4


def collect_task_context_components(
    cursor: sqlite3.Cursor,
    task_id: str,
    comments_limit: int,
    artifacts_limit: int,
    activity_limit: int,
) -> Dict[str, Any]:
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    cursor.execute(
        """
        SELECT id, task_id, author, comment, created_at
        FROM task_comments
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (task_id, comments_limit),
    )
    comments = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT id, task_id, stage, path, created_by, created_at
        FROM task_artifacts
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (task_id, artifacts_limit),
    )
    artifacts = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT *
        FROM (
            SELECT
                'history' AS source,
                th.timestamp AS ts,
                th.status_from AS status_from,
                th.status_to AS status_to,
                th.changed_by AS changed_by,
                NULL AS level,
                NULL AS message
            FROM task_history th
            WHERE th.task_id = ?

            UNION ALL

            SELECT
                'log' AS source,
                l.timestamp AS ts,
                NULL AS status_from,
                NULL AS status_to,
                l.agent_id AS changed_by,
                l.level AS level,
                l.message AS message
            FROM logs l
            WHERE l.task_id = ?
        )
        ORDER BY ts DESC
        LIMIT ?
        """,
        (task_id, task_id, activity_limit),
    )
    activity = [dict(row) for row in cursor.fetchall()]

    return {
        "task": serialize_task_row(task),
        "comments": comments,
        "artifacts": artifacts,
        "activity": activity,
    }


def scan_skills_catalog() -> List[Dict[str, str]]:
    roots = [
        Path(__file__).resolve().parents[1] / ".nanobot" / "workspace" / "skills",
        Path.home() / ".nanobot" / "workspace" / "skills",
        Path.home() / ".codex" / "skills",
    ]
    skills: Dict[str, Dict[str, str]] = {}
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for skill_md in root.rglob("SKILL.md"):
            skill_dir = skill_md.parent
            name = skill_dir.name.strip()
            if not name:
                continue
            key = str(skill_dir.resolve())
            skills[key] = {
                "id": name,
                "name": name,
                "path": str(skill_dir),
                "source": str(root),
            }
    return sorted(skills.values(), key=lambda s: (s["name"].lower(), s["path"]))


def insert_task_comment(
    cursor: sqlite3.Cursor,
    task_id: str,
    author: str,
    comment: Optional[str],
):
    text = (comment or "").strip()
    if not text:
        return
    cursor.execute(
        """
        INSERT INTO task_comments (id, task_id, author, comment)
        VALUES (?, ?, ?, ?)
        """,
        (str(uuid4()), task_id, author, text),
    )


def write_stage_markdown(task_id: str, stage: str, title: str, description: Optional[str]) -> str:
    """Create a markdown artifact file for planning/working stages."""
    stage = stage.strip().lower()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_dir = ARTIFACTS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    file_path = task_dir / f"{ts}-{stage}.md"
    content = (
        f"# Task {task_id} - {stage}\n\n"
        f"## Title\n{title or '(untitled)'}\n\n"
        f"## Description\n{description or '(none)'}\n\n"
        f"## Notes\n"
        f"- Add plan/work details here.\n"
        f"- Keep this file updated for review cycles.\n"
    )
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


def sanitize_artifact_filename(filename: Optional[str], stage: str) -> str:
    raw = (filename or "").strip()
    if not raw:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        raw = f"{ts}-{stage}.md"
    if not raw.lower().endswith(".md"):
        raw = f"{raw}.md"
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-")
    return safe or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{stage}.md"


def write_artifact_content_file(task_id: str, stage: str, content: str, filename: Optional[str] = None) -> str:
    stage = (stage or "").strip().lower()
    task_dir = ARTIFACTS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    file_name = sanitize_artifact_filename(filename, stage or "artifact")
    file_path = task_dir / file_name
    file_path.write_text(content or "", encoding="utf-8")
    return str(file_path)


def create_stage_artifact_and_reference(
    cursor: sqlite3.Cursor,
    task_id: str,
    stage: str,
    created_by: str,
    title: str,
    description: Optional[str],
):
    """Persist artifact metadata and reference it as a comment."""
    if stage not in (TaskStatus.PLANNING.value, TaskStatus.WORKING.value):
        return
    artifact_path = write_stage_markdown(task_id, stage, title, description)
    cursor.execute(
        """
        INSERT INTO task_artifacts (id, task_id, stage, path, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (str(uuid4()), task_id, stage, artifact_path, created_by),
    )
    insert_task_comment(
        cursor,
        task_id,
        created_by,
        f"{stage} artifact created: {artifact_path}",
    )


def has_stage_artifact(cursor: sqlite3.Cursor, task_id: str, stage: str) -> bool:
    """Return True when task has at least one linked artifact for the stage."""
    cursor.execute(
        """
        SELECT 1
        FROM task_artifacts
        WHERE task_id = ? AND lower(stage) = ?
        LIMIT 1
        """,
        (task_id, stage.strip().lower()),
    )
    return cursor.fetchone() is not None


def get_latest_stage_artifact(cursor: sqlite3.Cursor, task_id: str, stage: str) -> Optional[Dict]:
    """Return the latest linked artifact row for a task stage."""
    cursor.execute(
        """
        SELECT id, task_id, stage, path, created_by, created_at
        FROM task_artifacts
        WHERE task_id = ? AND lower(stage) = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (task_id, stage.strip().lower()),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def artifact_content_is_substantive(path: str) -> bool:
    """
    Heuristic quality check for stage artifact submissions.
    Accept if there is at least one explicit update section or substantial freeform content.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return False

    if "## Update (" in text:
        return True

    lines = [line.strip() for line in text.splitlines()]
    meaningful = [
        ln for ln in lines
        if ln and ln not in {"## Title", "## Description", "## Notes", "## Task Context"}
        and not ln.startswith("# Task ")
        and not ln.startswith("- Add plan/work details here.")
        and not ln.startswith("- Keep this file updated for review cycles.")
    ]
    return len(meaningful) >= 10 and sum(len(ln) for ln in meaningful) >= 240


def evaluate_stage_submission(
    cursor: sqlite3.Cursor,
    task_id: str,
    stage: str,
    to_status: Optional[str] = None,
) -> Dict:
    """Compute stage submission readiness with explicit reasons."""
    stage = (stage or "").strip().lower()
    if stage not in (TaskStatus.PLANNING.value, TaskStatus.WORKING.value):
        return {
            "task_id": task_id,
            "stage": stage,
            "task_status": None,
            "to_status": to_status,
            "transition_valid": False,
            "artifact_path": None,
            "artifact_exists": False,
            "artifact_quality_ok": False,
            "ready": False,
            "reason": "invalid_stage",
            "detail": "stage must be planning or working",
        }

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        return {
            "task_id": task_id,
            "stage": stage,
            "task_status": None,
            "to_status": to_status,
            "transition_valid": False,
            "artifact_path": None,
            "artifact_exists": False,
            "artifact_quality_ok": False,
            "ready": False,
            "reason": "task_not_found",
            "detail": "Task not found",
        }

    current_status = task["status"]
    if current_status != stage:
        return {
            "task_id": task_id,
            "stage": stage,
            "task_status": current_status,
            "to_status": to_status,
            "transition_valid": False,
            "artifact_path": None,
            "artifact_exists": False,
            "artifact_quality_ok": False,
            "ready": False,
            "reason": "status_mismatch",
            "detail": f"Task status must be '{stage}' for stage submission, found '{current_status}'",
        }

    transition_valid = True
    if to_status:
        transition_valid = to_status in ALLOWED_TRANSITIONS.get(current_status, set())
        if not transition_valid:
            return {
                "task_id": task_id,
                "stage": stage,
                "task_status": current_status,
                "to_status": to_status,
                "transition_valid": False,
                "artifact_path": None,
                "artifact_exists": False,
                "artifact_quality_ok": False,
                "ready": False,
                "reason": "invalid_transition",
                "detail": f"Invalid stage submit transition: {current_status} -> {to_status}",
            }

    artifact = get_latest_stage_artifact(cursor, task_id, stage)
    if not artifact:
        return {
            "task_id": task_id,
            "stage": stage,
            "task_status": current_status,
            "to_status": to_status,
            "transition_valid": transition_valid,
            "artifact_path": None,
            "artifact_exists": False,
            "artifact_quality_ok": False,
            "ready": False,
            "reason": "artifact_missing",
            "detail": f"No linked {stage} artifact found",
        }

    artifact_path = artifact.get("path") or ""
    exists = Path(artifact_path).exists()
    quality_ok = artifact_content_is_substantive(artifact_path)
    if not exists or not quality_ok:
        return {
            "task_id": task_id,
            "stage": stage,
            "task_status": current_status,
            "to_status": to_status,
            "transition_valid": transition_valid,
            "artifact_path": artifact_path,
            "artifact_exists": exists,
            "artifact_quality_ok": quality_ok,
            "ready": False,
            "reason": "artifact_too_minimal",
            "detail": f"{stage} artifact is missing or too minimal for submission: {artifact_path}",
        }

    return {
        "task_id": task_id,
        "stage": stage,
        "task_status": current_status,
        "to_status": to_status,
        "transition_valid": transition_valid,
        "artifact_path": artifact_path,
        "artifact_exists": exists,
        "artifact_quality_ok": quality_ok,
        "ready": True,
        "reason": None,
        "detail": "Stage is submit-ready",
    }

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


@app.get("/api/auth/roles")
async def get_role_permissions():
    return {
        "roles": ROLE_PERMISSIONS,
        "reviewer_roles": sorted(REVIEWER_ROLES),
        "override_roles": sorted(OVERRIDE_ROLES),
    }


@app.get("/api/auth/whoami")
async def whoami(
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
):
    expected = os.getenv("DISPATCH_API_TOKEN")
    token_auth_enabled = bool(expected)
    token_valid = (api_token or "") == expected if token_auth_enabled else True
    role = (actor_role or "").strip().lower()
    return {
        "actor_id": actor_id,
        "actor_role": role or None,
        "token_auth_enabled": token_auth_enabled,
        "token_valid": token_valid,
        "permissions": ROLE_PERMISSIONS.get(role, []),
    }


@app.post("/api/auth/login", response_model=LoginResponse)
async def auth_login(
    payload: LoginRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, display_name, global_role, password_hash, disabled
        FROM users
        WHERE lower(email) = lower(?)
        """,
        (payload.email.strip(),),
    )
    user = cursor.fetchone()
    if not user or int(user["disabled"] or 0) != 0:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if hash_password(payload.password) != str(user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = "human_admin" if str(user["global_role"]).strip().lower() == "admin" else "human_reviewer"
    return {
        "actor_id": user["id"],
        "actor_role": role,
        "email": user["email"],
        "display_name": user["display_name"],
    }


@app.get("/api/auth/me")
async def auth_me(
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    uid = (actor_id or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Missing X-Actor-Id")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, display_name, global_role, disabled, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (uid,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    data = dict(row)
    data["disabled"] = bool(data.get("disabled"))
    return {
        "user": data,
        "actor_role": (actor_role or "").strip().lower() or None,
        "permissions": ROLE_PERMISSIONS.get((actor_role or "").strip().lower(), []),
    }


@app.post("/api/auth/logout")
async def auth_logout():
    return {"ok": True}


@app.get("/api/users", response_model=List[UserResponse])
async def list_users(
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "User list")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, email, display_name, global_role, disabled, created_at, updated_at
        FROM users
        ORDER BY created_at DESC
        """
    )
    return [
        {
            **dict(row),
            "disabled": bool(row["disabled"]),
        }
        for row in cursor.fetchall()
    ]


@app.post("/api/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "User create")
    uid = generate_id()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, display_name, global_role, disabled)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                uid,
                user.email.strip().lower(),
                hash_password(user.password),
                user.display_name,
                (user.global_role or "member").strip().lower(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="User email already exists")
    cursor.execute(
        """
        SELECT id, email, display_name, global_role, disabled, created_at, updated_at
        FROM users WHERE id = ?
        """,
        (uid,),
    )
    created = cursor.fetchone()
    return {**dict(created), "disabled": bool(created["disabled"])}


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update: UserUpdate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "User update")
    updates = []
    params: List = []
    if update.display_name is not None:
        updates.append("display_name = ?")
        params.append(update.display_name)
    if update.global_role is not None:
        updates.append("global_role = ?")
        params.append(update.global_role.strip().lower())
    if update.disabled is not None:
        updates.append("disabled = ?")
        params.append(1 if update.disabled else 0)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    cursor.execute(
        """
        SELECT id, email, display_name, global_role, disabled, created_at, updated_at
        FROM users WHERE id = ?
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    return {**dict(row), "disabled": bool(row["disabled"])}


# Projects endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
async def get_projects(
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    allowed = get_authorized_project_ids(conn, actor_role, actor_id)
    if allowed is None:
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    elif not allowed:
        return []
    else:
        placeholders = ",".join("?" for _ in allowed)
        cursor.execute(
            f"SELECT * FROM projects WHERE id IN ({placeholders}) ORDER BY created_at DESC",
            tuple(sorted(allowed)),
        )
    projects = cursor.fetchall()
    return [dict(project) for project in projects]

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate, 
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db)
):
    ensure_actor_role(actor_role, {"human_admin"}, "Project create")
    project_id = generate_id()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (id, name, description)
        VALUES (?, ?, ?)
    """, (project_id, project.name, project.description))
    if actor_id:
        cursor.execute(
            """
            INSERT OR IGNORE INTO project_memberships (project_id, user_id, role)
            VALUES (?, ?, 'owner')
            """,
            (project_id, actor_id),
        )
    conn.commit()
    
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    created = cursor.fetchone()
    
    await notify_clients()
    return dict(created)


@app.get("/api/projects/{project_id}/members", response_model=List[ProjectMembershipResponse])
async def list_project_members(
    project_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    assert_project_visible(conn, project_id, actor_role, actor_id)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT project_id, user_id, role, created_at
        FROM project_memberships
        WHERE project_id = ?
        ORDER BY created_at DESC
        """,
        (project_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


@app.post("/api/projects/{project_id}/members", response_model=ProjectMembershipResponse)
async def add_project_member(
    project_id: str,
    payload: ProjectMembershipCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Project member add")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    cursor.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    cursor.execute(
        """
        INSERT OR REPLACE INTO project_memberships (project_id, user_id, role)
        VALUES (?, ?, ?)
        """,
        (project_id, payload.user_id, (payload.role or "member").strip().lower()),
    )
    conn.commit()
    cursor.execute(
        """
        SELECT project_id, user_id, role, created_at
        FROM project_memberships
        WHERE project_id = ? AND user_id = ?
        """,
        (project_id, payload.user_id),
    )
    row = cursor.fetchone()
    return dict(row)


@app.delete("/api/projects/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: str,
    user_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Project member remove")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM project_memberships WHERE project_id = ? AND user_id = ?",
        (project_id, user_id),
    )
    conn.commit()
    return {"ok": True, "removed": cursor.rowcount > 0}


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    assert_project_visible(conn, project_id, actor_role, actor_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@app.get("/api/models", response_model=List[ModelRegistryResponse])
async def list_models(
    enabled_only: bool = False,
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    query = "SELECT * FROM model_registry WHERE 1=1"
    params: List[Any] = []
    if enabled_only:
        query += " AND enabled = 1"
    query += " ORDER BY is_default DESC, created_at DESC"
    cursor.execute(query, params)
    return [serialize_model_row(row) for row in cursor.fetchall()]


@app.post("/api/models", response_model=ModelRegistryResponse)
async def create_model(
    payload: ModelRegistryCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Model create")
    model_id = generate_id()
    cursor = conn.cursor()
    if payload.is_default:
        cursor.execute("UPDATE model_registry SET is_default = 0 WHERE is_default = 1")
    cursor.execute(
        """
        INSERT INTO model_registry
        (id, label, provider, model_name, api_base, is_default, enabled, config_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            model_id,
            payload.label.strip(),
            payload.provider.strip(),
            payload.model_name.strip(),
            (payload.api_base or "").strip() or None,
            1 if payload.is_default else 0,
            1 if payload.enabled else 0,
            json.dumps(payload.config or {}),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM model_registry WHERE id = ?", (model_id,))
    return serialize_model_row(cursor.fetchone())


@app.put("/api/models/{model_id}", response_model=ModelRegistryResponse)
async def update_model(
    model_id: str,
    payload: ModelRegistryUpdate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Model update")
    updates: List[str] = []
    params: List[Any] = []
    if payload.label is not None:
        updates.append("label = ?")
        params.append(payload.label.strip())
    if payload.provider is not None:
        updates.append("provider = ?")
        params.append(payload.provider.strip())
    if payload.model_name is not None:
        updates.append("model_name = ?")
        params.append(payload.model_name.strip())
    if payload.api_base is not None:
        updates.append("api_base = ?")
        params.append((payload.api_base or "").strip() or None)
    if payload.is_default is not None:
        if payload.is_default:
            conn.execute("UPDATE model_registry SET is_default = 0 WHERE is_default = 1")
        updates.append("is_default = ?")
        params.append(1 if payload.is_default else 0)
    if payload.enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if payload.enabled else 0)
    if payload.config is not None:
        updates.append("config_json = ?")
        params.append(json.dumps(payload.config))
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(model_id)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE model_registry SET {', '.join(updates)} WHERE id = ?", params)
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Model not found")
    conn.commit()
    cursor.execute("SELECT * FROM model_registry WHERE id = ?", (model_id,))
    return serialize_model_row(cursor.fetchone())


@app.delete("/api/models/{model_id}")
async def delete_model(
    model_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Model delete")
    cursor = conn.cursor()
    cursor.execute("UPDATE agent_profiles SET model_id = NULL, updated_at = CURRENT_TIMESTAMP WHERE model_id = ?", (model_id,))
    cursor.execute("DELETE FROM model_registry WHERE id = ?", (model_id,))
    conn.commit()
    return {"ok": True, "deleted": cursor.rowcount > 0}


@app.get("/api/skills/catalog")
async def get_skills_catalog():
    return {"skills": scan_skills_catalog()}


@app.get("/api/projects/{project_id}/agent-profiles", response_model=List[AgentProfileResponse])
async def list_agent_profiles(
    project_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    assert_project_visible(conn, project_id, actor_role, actor_id)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM agent_profiles
        WHERE project_id = ?
        ORDER BY created_at DESC
        """,
        (project_id,),
    )
    return [serialize_agent_profile_row(row) for row in cursor.fetchall()]


@app.post("/api/projects/{project_id}/agent-profiles", response_model=AgentProfileResponse)
async def create_agent_profile(
    project_id: str,
    payload: AgentProfileCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Agent profile create")
    assert_project_visible(conn, project_id, actor_role, actor_id)
    profile_id = generate_id()
    cursor = conn.cursor()
    if payload.model_id:
        cursor.execute("SELECT id FROM model_registry WHERE id = ?", (payload.model_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Model not found")
    try:
        cursor.execute(
            """
            INSERT INTO agent_profiles
            (id, project_id, name, type, system_prompt, model_id, provider, tools_json, skills_json, context_policy_json, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                project_id,
                payload.name.strip(),
                payload.type.strip(),
                payload.system_prompt,
                payload.model_id,
                payload.provider,
                json.dumps(payload.tools or []),
                json.dumps(payload.skills or []),
                json.dumps(payload.context_policy or {}),
                1 if payload.enabled else 0,
            ),
        )
        sync_agent_profile_to_files(conn, profile_id)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync agent files: {exc}") from exc
    cursor.execute("SELECT * FROM agent_profiles WHERE id = ?", (profile_id,))
    return serialize_agent_profile_row(cursor.fetchone())


@app.post("/api/projects/{project_id}/agent-profiles/sync-files")
async def sync_agent_profiles_from_file_definitions(
    project_id: str,
    overwrite: bool = Query(False, description="When true, update same-name profiles from files."),
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Agent profile sync")
    assert_project_visible(conn, project_id, actor_role, actor_id)
    return sync_agent_profiles_from_files(conn, project_id, overwrite_existing=overwrite)


@app.post("/api/projects/{project_id}/agent-profiles/sync-db-to-files")
async def sync_agent_profiles_from_db_to_files(
    project_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Agent profile file export")
    assert_project_visible(conn, project_id, actor_role, actor_id)
    try:
        return sync_project_agent_profiles_to_files(conn, project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to sync DB profiles to files: {exc}") from exc


@app.put("/api/agent-profiles/{profile_id}", response_model=AgentProfileResponse)
async def update_agent_profile(
    profile_id: str,
    payload: AgentProfileUpdate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Agent profile update")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_profiles WHERE id = ?", (profile_id,))
    existing = cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    assert_project_visible(conn, str(existing["project_id"]), actor_role, actor_id)
    updates: List[str] = []
    params: List[Any] = []
    if payload.name is not None:
        updates.append("name = ?")
        params.append(payload.name.strip())
    if payload.type is not None:
        updates.append("type = ?")
        params.append(payload.type.strip())
    if payload.system_prompt is not None:
        updates.append("system_prompt = ?")
        params.append(payload.system_prompt)
    if payload.model_id is not None:
        if payload.model_id:
            cursor.execute("SELECT id FROM model_registry WHERE id = ?", (payload.model_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Model not found")
        updates.append("model_id = ?")
        params.append(payload.model_id or None)
    if payload.provider is not None:
        updates.append("provider = ?")
        params.append(payload.provider)
    if payload.tools is not None:
        updates.append("tools_json = ?")
        params.append(json.dumps(payload.tools))
    if payload.skills is not None:
        updates.append("skills_json = ?")
        params.append(json.dumps(payload.skills))
    if payload.context_policy is not None:
        updates.append("context_policy_json = ?")
        params.append(json.dumps(payload.context_policy))
    if payload.enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if payload.enabled else 0)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(profile_id)
    old_name = str(existing["name"] or "").strip()
    try:
        cursor.execute(f"UPDATE agent_profiles SET {', '.join(updates)} WHERE id = ?", params)
        sync_agent_profile_to_files(conn, profile_id)
        if payload.name is not None:
            new_name = payload.name.strip()
            if old_name and old_name.lower() != new_name.lower():
                sync_agent_profile_name_removal_from_files(conn, old_name)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync agent files: {exc}") from exc
    cursor.execute("SELECT * FROM agent_profiles WHERE id = ?", (profile_id,))
    return serialize_agent_profile_row(cursor.fetchone())


@app.delete("/api/agent-profiles/{profile_id}")
async def delete_agent_profile(
    profile_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Agent profile delete")
    cursor = conn.cursor()
    cursor.execute("SELECT project_id, name FROM agent_profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    assert_project_visible(conn, str(row["project_id"]), actor_role, actor_id)
    deleted_name = str(row["name"] or "").strip()
    try:
        cursor.execute("UPDATE agent_runtime_instances SET profile_id = NULL WHERE profile_id = ?", (profile_id,))
        cursor.execute("DELETE FROM agent_profiles WHERE id = ?", (profile_id,))
        sync_agent_profile_name_removal_from_files(conn, deleted_name)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync agent files: {exc}") from exc
    return {"ok": True, "deleted": cursor.rowcount > 0}


@app.get("/api/projects/{project_id}/agent-instances", response_model=List[AgentInstanceResponse])
async def list_agent_instances(
    project_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    assert_project_visible(conn, project_id, actor_role, actor_id)
    cursor = conn.cursor()
    query = "SELECT * FROM agent_runtime_instances WHERE project_id = ?"
    params: List[Any] = [project_id]
    if status:
        query += " AND status = ?"
        params.append(status.strip().lower())
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    cursor.execute(query, params)
    return [serialize_agent_instance_row(row) for row in cursor.fetchall()]


@app.post("/api/projects/{project_id}/agent-instances", response_model=AgentInstanceResponse)
async def create_agent_instance(
    project_id: str,
    payload: AgentInstanceCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin", "agent_runner"}, "Agent instance create")
    assert_project_visible(conn, project_id, actor_role, actor_id)
    cursor = conn.cursor()
    if payload.profile_id:
        cursor.execute("SELECT id FROM agent_profiles WHERE id = ? AND project_id = ?", (payload.profile_id, project_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Agent profile not found in project")
    if payload.task_id:
        cursor.execute("SELECT id FROM tasks WHERE id = ? AND project_id = ?", (payload.task_id, project_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Task not found in project")
    instance_id = generate_id()
    status = (payload.status or "pending").strip().lower()
    started_at = "CURRENT_TIMESTAMP" if status in {"running", "working"} else "NULL"
    cursor.execute(
        f"""
        INSERT INTO agent_runtime_instances
        (id, project_id, profile_id, container_name, status, task_id, started_at, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, {started_at}, ?)
        """,
        (
            instance_id,
            project_id,
            payload.profile_id,
            payload.container_name,
            status,
            payload.task_id,
            json.dumps(payload.meta or {}),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM agent_runtime_instances WHERE id = ?", (instance_id,))
    return serialize_agent_instance_row(cursor.fetchone())


@app.get("/api/agent-instances/{instance_id}", response_model=AgentInstanceResponse)
async def get_agent_instance(
    instance_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_runtime_instances WHERE id = ?", (instance_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    assert_project_visible(conn, str(row["project_id"]), actor_role, actor_id)
    return serialize_agent_instance_row(row)


@app.put("/api/agent-instances/{instance_id}", response_model=AgentInstanceResponse)
async def update_agent_instance(
    instance_id: str,
    payload: AgentInstanceUpdate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin", "agent_runner"}, "Agent instance update")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_runtime_instances WHERE id = ?", (instance_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    project_id = str(row["project_id"])
    assert_project_visible(conn, project_id, actor_role, actor_id)
    updates: List[str] = []
    params: List[Any] = []
    if payload.status is not None:
        status = payload.status.strip().lower()
        updates.append("status = ?")
        params.append(status)
        if status in {"running", "working"}:
            updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
        if status in {"stopped", "failed", "completed"}:
            updates.append("stopped_at = CURRENT_TIMESTAMP")
    if payload.task_id is not None:
        if payload.task_id:
            cursor.execute("SELECT id FROM tasks WHERE id = ? AND project_id = ?", (payload.task_id, project_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Task not found in project")
        updates.append("task_id = ?")
        params.append(payload.task_id or None)
    if payload.container_name is not None:
        updates.append("container_name = ?")
        params.append(payload.container_name or None)
    if payload.exit_code is not None:
        updates.append("exit_code = ?")
        params.append(payload.exit_code)
    if payload.meta is not None:
        updates.append("meta_json = ?")
        params.append(json.dumps(payload.meta))
    if payload.heartbeat:
        updates.append("last_heartbeat = CURRENT_TIMESTAMP")
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(instance_id)
    cursor.execute(f"UPDATE agent_runtime_instances SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    cursor.execute("SELECT * FROM agent_runtime_instances WHERE id = ?", (instance_id,))
    return serialize_agent_instance_row(cursor.fetchone())


@app.post("/api/agent-instances/{instance_id}/stop", response_model=AgentInstanceResponse)
async def stop_agent_instance(
    instance_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin"}, "Agent instance stop")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_runtime_instances WHERE id = ?", (instance_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    assert_project_visible(conn, str(row["project_id"]), actor_role, actor_id)
    cursor.execute(
        """
        UPDATE agent_runtime_instances
        SET status = 'stopped',
            stopped_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (instance_id,),
    )
    conn.commit()
    cursor.execute("SELECT * FROM agent_runtime_instances WHERE id = ?", (instance_id,))
    return serialize_agent_instance_row(cursor.fetchone())


@app.get("/api/projects/{project_id}/agent-activity", response_model=List[AgentActivityResponse])
async def list_agent_activity(
    project_id: str,
    limit: int = 200,
    since: Optional[str] = None,
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
    level: Optional[str] = None,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    assert_project_visible(conn, project_id, actor_role, actor_id)
    query = "SELECT * FROM agent_activity_events WHERE project_id = ?"
    params: List[Any] = [project_id]
    if since:
        query += " AND datetime(ts) >= datetime(?)"
        params.append(since)
    if agent_id:
        query += " AND agent_id = ?"
        params.append(agent_id)
    if task_id:
        query += " AND task_id = ?"
        params.append(task_id)
    if level:
        query += " AND level = ?"
        params.append(level.strip().lower())
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(max(1, min(limit, 1000)))
    cursor = conn.cursor()
    cursor.execute(query, params)
    return [serialize_agent_activity_row(row) for row in cursor.fetchall()]


@app.post("/api/projects/{project_id}/agent-activity", response_model=AgentActivityResponse)
async def create_agent_activity(
    project_id: str,
    payload: AgentActivityCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_actor_role(actor_role, {"human_admin", "agent_runner"}, "Agent activity create")
    assert_project_visible(conn, project_id, actor_role, actor_id)
    if not (payload.message or "").strip():
        raise HTTPException(status_code=422, detail="message is required")
    cursor = conn.cursor()
    if payload.instance_id:
        cursor.execute(
            "SELECT id FROM agent_runtime_instances WHERE id = ? AND project_id = ?",
            (payload.instance_id, project_id),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Agent instance not found in project")
    if payload.task_id:
        cursor.execute("SELECT id FROM tasks WHERE id = ? AND project_id = ?", (payload.task_id, project_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Task not found in project")
    event_id = generate_id()
    cursor.execute(
        """
        INSERT INTO agent_activity_events
        (id, project_id, instance_id, agent_id, task_id, level, message, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            project_id,
            payload.instance_id,
            payload.agent_id,
            payload.task_id,
            (payload.level or "info").strip().lower(),
            payload.message.strip(),
            json.dumps(payload.meta or {}),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM agent_activity_events WHERE id = ?", (event_id,))
    return serialize_agent_activity_row(cursor.fetchone())


@app.get("/api/projects/{project_id}/agent-activity/stream")
async def stream_agent_activity(
    project_id: str,
    since_id: Optional[str] = None,
    poll_ms: int = 1200,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    assert_project_visible(conn, project_id, actor_role, actor_id)
    poll_seconds = max(0.3, min(poll_ms / 1000.0, 10.0))

    async def event_generator():
        last_id = (since_id or "").strip()
        while True:
            local_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            local_conn.row_factory = sqlite3.Row
            cur = local_conn.cursor()
            if last_id:
                cur.execute(
                    """
                    SELECT *
                    FROM agent_activity_events
                    WHERE project_id = ? AND id > ?
                    ORDER BY ts ASC
                    LIMIT 100
                    """,
                    (project_id, last_id),
                )
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM agent_activity_events
                    WHERE project_id = ?
                    ORDER BY ts DESC
                    LIMIT 50
                    """,
                    (project_id,),
                )
            rows = cur.fetchall()
            local_conn.close()
            if rows:
                ordered = rows if last_id else list(reversed(rows))
                for row in ordered:
                    item = serialize_agent_activity_row(row)
                    last_id = str(item["id"])
                    yield f"data: {json.dumps(item)}\n\n"
            else:
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

# Tasks endpoints
@app.get("/api/tasks", response_model=List[TaskResponse])
async def get_tasks(
    project_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    assignee: Optional[str] = None,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
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
        params.append(status.value)
    
    if assignee:
        query += " AND assignee = ?"
        params.append(assignee)
    allowed = get_authorized_project_ids(conn, actor_role, actor_id)
    if allowed is not None:
        if not allowed:
            return []
        placeholders = ",".join("?" for _ in allowed)
        query += f" AND project_id IN ({placeholders})"
        params.extend(sorted(allowed))
    
    query += " ORDER BY priority DESC, created_at DESC"
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    normalized_tasks = []
    for task in tasks:
        try:
            normalized = serialize_task_row(task)
            # Pre-validate to avoid 500 due to one malformed legacy row.
            TaskResponse.model_validate(normalized)
            normalized_tasks.append(normalized)
        except Exception as exc:
            task_id = None
            try:
                task_id = task["id"]
            except Exception:
                pass
            print(f"Skipping invalid task row id={task_id}: {exc}")
    return normalized_tasks


@app.get("/api/hitl/queue")
async def get_hitl_queue(
    project_id: Optional[str] = None,
    include_dispatch: bool = False,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    query = """
        SELECT *
        FROM tasks
        WHERE status IN (?, ?)
    """
    params: List = [TaskStatus.HITL_REVIEW.value, TaskStatus.APPROVAL.value]
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    allowed = get_authorized_project_ids(conn, actor_role, actor_id)
    if allowed is not None:
        if not allowed:
            return []
        placeholders = ",".join("?" for _ in allowed)
        query += f" AND project_id IN ({placeholders})"
        params.extend(sorted(allowed))
    query += " ORDER BY priority DESC, updated_at ASC"
    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]

    if include_dispatch and tasks:
        for task in tasks:
            cursor.execute(
                """
                SELECT selected_agent, selected_model, provider, confidence, created_at
                FROM dispatch_decisions
                WHERE task_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (task["id"],),
            )
            decision = cursor.fetchone()
            task["latest_dispatch"] = dict(decision) if decision else None

    return tasks

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate, 
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db)
):
    task_id = generate_id()
    cursor = conn.cursor()
    
    # Verify project exists
    cursor.execute("SELECT id FROM projects WHERE id = ?", (task.project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    assert_project_visible(conn, task.project_id, actor_role, actor_id)
    
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
    return serialize_task_row(created)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    return serialize_task_row(task)


@app.get("/api/tasks/{task_id}/activity")
async def get_task_activity(
    task_id: str,
    limit: int = 100,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    query = """
        SELECT *
        FROM (
            SELECT
                'history' AS source,
                th.timestamp AS ts,
                th.status_from AS status_from,
                th.status_to AS status_to,
                th.changed_by AS changed_by,
                NULL AS level,
                NULL AS message
            FROM task_history th
            WHERE th.task_id = ?

            UNION ALL

            SELECT
                'log' AS source,
                l.timestamp AS ts,
                NULL AS status_from,
                NULL AS status_to,
                l.agent_id AS changed_by,
                l.level AS level,
                l.message AS message
            FROM logs l
            WHERE l.task_id = ?
        )
        ORDER BY ts DESC
        LIMIT ?
    """
    cursor.execute(query, (task_id, task_id, limit))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@app.get("/api/tasks/{task_id}/context")
async def get_task_context(
    task_id: str,
    comments_limit: int = 20,
    artifacts_limit: int = 20,
    activity_limit: int = 30,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Return a compact task-scoped context bundle for agents and reviews."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    cursor.execute(
        """
        SELECT id, task_id, author, comment, created_at
        FROM task_comments
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (task_id, comments_limit),
    )
    comments = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT id, task_id, stage, path, created_by, created_at
        FROM task_artifacts
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (task_id, artifacts_limit),
    )
    artifacts = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT *
        FROM (
            SELECT
                'history' AS source,
                th.timestamp AS ts,
                th.status_from AS status_from,
                th.status_to AS status_to,
                th.changed_by AS changed_by,
                NULL AS level,
                NULL AS message
            FROM task_history th
            WHERE th.task_id = ?

            UNION ALL

            SELECT
                'log' AS source,
                l.timestamp AS ts,
                NULL AS status_from,
                NULL AS status_to,
                l.agent_id AS changed_by,
                l.level AS level,
                l.message AS message
            FROM logs l
            WHERE l.task_id = ?
        )
        ORDER BY ts DESC
        LIMIT ?
        """,
        (task_id, task_id, activity_limit),
    )
    activity = [dict(row) for row in cursor.fetchall()]

    return {
        "task": serialize_task_row(task),
        "comments": comments,
        "artifacts": artifacts,
        "activity": activity,
    }


@app.post("/api/tasks/{task_id}/context/estimate", response_model=ContextEstimateResponse)
async def estimate_task_context(
    task_id: str,
    payload: ContextEstimateRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    bundle = collect_task_context_components(
        cursor=cursor,
        task_id=task_id,
        comments_limit=max(0, payload.comments_limit),
        artifacts_limit=max(0, payload.artifacts_limit),
        activity_limit=max(0, payload.activity_limit),
    )
    assert_project_visible(conn, str(bundle["task"]["project_id"]), actor_role, actor_id)

    task_text = json.dumps(bundle["task"], ensure_ascii=False)
    comments_text = json.dumps(bundle["comments"], ensure_ascii=False)
    artifacts_text = json.dumps(bundle["artifacts"], ensure_ascii=False)
    activity_text = json.dumps(bundle["activity"], ensure_ascii=False)
    prompt_template_text = (payload.prompt_template or "").strip()

    chars = {
        "task": len(task_text),
        "comments": len(comments_text),
        "artifacts": len(artifacts_text),
        "activity": len(activity_text),
        "prompt_template": len(prompt_template_text),
    }
    estimated_tokens = {
        "task": estimate_tokens_from_text(task_text),
        "comments": estimate_tokens_from_text(comments_text),
        "artifacts": estimate_tokens_from_text(artifacts_text),
        "activity": estimate_tokens_from_text(activity_text),
        "prompt_template": estimate_tokens_from_text(prompt_template_text),
    }
    return {
        "task_id": task_id,
        "counts": {
            "comments": len(bundle["comments"]),
            "artifacts": len(bundle["artifacts"]),
            "activity": len(bundle["activity"]),
        },
        "chars": chars,
        "estimated_tokens": estimated_tokens,
        "total_estimated_tokens": sum(estimated_tokens.values()),
    }


@app.get("/api/tasks/{task_id}/comments")
async def get_task_comments(
    task_id: str,
    limit: int = 100,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    cursor.execute(
        """
        SELECT id, task_id, author, comment, created_at
        FROM task_comments
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (task_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]


@app.post("/api/tasks/{task_id}/comments")
async def add_task_comment(
    task_id: str,
    payload: TaskCommentCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Add comment")
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    comment_text = (payload.comment or "").strip()
    if not comment_text:
        raise HTTPException(status_code=422, detail="Comment cannot be empty")

    comment_id = str(uuid4())
    author = actor_id or "unknown"
    cursor.execute(
        """
        INSERT INTO task_comments (id, task_id, author, comment)
        VALUES (?, ?, ?, ?)
        """,
        (comment_id, task_id, author, comment_text),
    )
    cursor.execute(
        """
        INSERT INTO logs (task_id, agent_id, message, level)
        VALUES (?, ?, ?, 'info')
        """,
        (task_id, author, f"Comment added: {comment_text}"),
    )
    conn.commit()
    await notify_clients()
    return {
        "id": comment_id,
        "task_id": task_id,
        "author": author,
        "comment": comment_text,
    }


@app.get("/api/tasks/{task_id}/artifacts")
async def get_task_artifacts(
    task_id: str,
    limit: int = 100,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    cursor.execute(
        """
        SELECT id, task_id, stage, path, created_by, created_at
        FROM task_artifacts
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (task_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]


@app.post("/api/tasks/{task_id}/artifacts")
async def add_task_artifact(
    task_id: str,
    payload: TaskArtifactCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Add artifact")
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    stage = (payload.stage or "").strip().lower()
    path = (payload.path or "").strip()
    if not stage or not path:
        raise HTTPException(status_code=422, detail="stage and path are required")
    artifact_id = str(uuid4())
    created_by = actor_id or "unknown"
    cursor.execute(
        """
        INSERT INTO task_artifacts (id, task_id, stage, path, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (artifact_id, task_id, stage, path, created_by),
    )
    insert_task_comment(cursor, task_id, created_by, f"{stage} artifact linked: {path}")
    conn.commit()
    await notify_clients()
    return {
        "id": artifact_id,
        "task_id": task_id,
        "stage": stage,
        "path": path,
        "created_by": created_by,
    }


@app.post("/api/tasks/{task_id}/artifacts/content")
async def create_task_artifact_content(
    task_id: str,
    payload: TaskArtifactContentCreate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Create artifact content")
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    stage = (payload.stage or "").strip().lower()
    if not stage:
        raise HTTPException(status_code=422, detail="stage is required")
    file_path = write_artifact_content_file(task_id, stage, payload.content or "", payload.filename)
    artifact_id = str(uuid4())
    created_by = actor_id or "unknown"
    cursor.execute(
        """
        INSERT INTO task_artifacts (id, task_id, stage, path, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (artifact_id, task_id, stage, file_path, created_by),
    )
    insert_task_comment(cursor, task_id, created_by, f"{stage} artifact created: {file_path}")
    conn.commit()
    await notify_clients()
    return {
        "id": artifact_id,
        "task_id": task_id,
        "stage": stage,
        "path": file_path,
        "created_by": created_by,
        "content": payload.content or "",
    }


@app.get("/api/tasks/{task_id}/artifacts/{artifact_id}/content")
async def get_task_artifact_content(
    task_id: str,
    artifact_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    cursor.execute(
        """
        SELECT id, task_id, stage, path, created_by, created_at
        FROM task_artifacts
        WHERE id = ? AND task_id = ?
        """,
        (artifact_id, task_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact = dict(row)
    path = Path(artifact["path"])
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact file not found: {artifact['path']}")
    return {**artifact, "content": path.read_text(encoding="utf-8")}


@app.put("/api/tasks/{task_id}/artifacts/{artifact_id}/content")
async def update_task_artifact_content(
    task_id: str,
    artifact_id: str,
    payload: TaskArtifactContentUpdate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Update artifact content")
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    cursor.execute(
        """
        SELECT id, task_id, stage, path, created_by, created_at
        FROM task_artifacts
        WHERE id = ? AND task_id = ?
        """,
        (artifact_id, task_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact = dict(row)
    path = Path(artifact["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content or "", encoding="utf-8")
    insert_task_comment(cursor, task_id, actor_id or "unknown", f"{artifact['stage']} artifact updated: {artifact['path']}")
    conn.commit()
    await notify_clients()
    return {**artifact, "content": payload.content or ""}


@app.get("/api/tasks/{task_id}/stage/check", response_model=StageCheckResponse)
async def check_task_stage(
    task_id: str,
    stage: str,
    to_status: Optional[TaskStatus] = None,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get backend-evaluated stage submission readiness."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if task:
        assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    readiness = evaluate_stage_submission(
        cursor=cursor,
        task_id=task_id,
        stage=stage,
        to_status=to_status.value if to_status else None,
    )
    if readiness["reason"] == "task_not_found":
        raise HTTPException(status_code=404, detail=readiness["detail"])
    if readiness["reason"] in {"invalid_stage", "invalid_transition"}:
        raise HTTPException(status_code=422, detail=readiness["detail"])
    return readiness


@app.post("/api/tasks/{task_id}/stage/submit", response_model=TaskResponse)
async def submit_task_stage(
    task_id: str,
    request: StageSubmitRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Atomically validate stage artifact and advance task status."""
    ensure_api_token(api_token, "Stage submit")
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if task:
        assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    readiness = evaluate_stage_submission(
        cursor=cursor,
        task_id=task_id,
        stage=request.stage,
        to_status=request.to_status.value,
    )
    reason = readiness.get("reason")
    if reason == "task_not_found":
        raise HTTPException(status_code=404, detail=readiness["detail"])
    if reason == "status_mismatch":
        raise HTTPException(status_code=409, detail=readiness["detail"])
    if reason in {"invalid_stage", "invalid_transition", "artifact_missing", "artifact_too_minimal"}:
        raise HTTPException(status_code=422, detail=readiness["detail"])
    if not readiness.get("ready"):
        raise HTTPException(status_code=422, detail=readiness["detail"])

    stage = readiness["stage"]
    current_status = readiness["task_status"]
    target_status = request.to_status.value
    artifact_path = readiness.get("artifact_path") or "-"

    cursor.execute(
        """
        UPDATE tasks
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (target_status, task_id),
    )
    cursor.execute(
        """
        INSERT INTO task_history (task_id, status_from, status_to, changed_by)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, current_status, target_status, f"stage_submit:{actor_id or 'system'}"),
    )
    summary = (
        f"{stage} submission for transition to {target_status}. Artifact: {artifact_path}"
        + (f" | Note: {request.note}" if request.note else "")
    )
    insert_task_comment(cursor, task_id, actor_id or "stage_submit", summary)
    cursor.execute(
        """
        INSERT INTO logs (task_id, message, level)
        VALUES (?, ?, 'info')
        """,
        (task_id, summary),
    )
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    await notify_clients()
    return serialize_task_row(updated)

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    update: TaskUpdate,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db)
):
    ensure_api_token(api_token, "Task update")
    cursor = conn.cursor()
    
    # Get current task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    
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
        new_status = update.status.value
        current_status = task["status"]
        if new_status != current_status and new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status transition: {current_status} -> {new_status}",
            )
        if current_status == TaskStatus.PLANNING.value and new_status == TaskStatus.HITL_REVIEW.value:
            if not has_stage_artifact(cursor, task_id, TaskStatus.PLANNING.value):
                raise HTTPException(
                    status_code=422,
                    detail="Cannot move planning -> hitl_review without a linked planning artifact",
                )
        if current_status == TaskStatus.WORKING.value and new_status == TaskStatus.READY_TO_IMPLEMENT.value:
            if not has_stage_artifact(cursor, task_id, TaskStatus.WORKING.value):
                raise HTTPException(
                    status_code=422,
                    detail="Cannot move working -> ready_to_implement without a linked working artifact",
                )
        # Log status change
        cursor.execute("""
            INSERT INTO task_history (task_id, status_from, status_to, changed_by)
            VALUES (?, ?, ?, 'system')
        """, (task_id, current_status, new_status))
        if new_status in (TaskStatus.PLANNING.value, TaskStatus.WORKING.value):
            create_stage_artifact_and_reference(
                cursor=cursor,
                task_id=task_id,
                stage=new_status,
                created_by="system",
                title=update.title if update.title is not None else task["title"],
                description=update.description if update.description is not None else task["description"],
            )
        updates.append("status = ?")
        params.append(new_status)
    
    assignee_provided = "assignee" in update.model_fields_set
    if assignee_provided:
        normalized_assignee = update.assignee
        if isinstance(normalized_assignee, str):
            normalized_assignee = normalized_assignee.strip()
            if not normalized_assignee:
                normalized_assignee = None
        updates.append("assignee = ?")
        params.append(normalized_assignee)
    
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
    return serialize_task_row(updated)


@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Task delete")
    ensure_actor_role(actor_role, {"human_admin"}, "Task delete")

    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    cursor.execute("SELECT path FROM task_artifacts WHERE task_id = ?", (task_id,))
    artifact_paths = [str(r["path"]) for r in cursor.fetchall() if r["path"]]

    cursor.execute("DELETE FROM task_comments WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM task_history WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM logs WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM dispatch_decisions WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM task_artifacts WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

    removed_files = 0
    for p in artifact_paths:
        fp = Path(p)
        try:
            if fp.exists() and fp.is_file():
                fp.unlink()
                removed_files += 1
        except Exception:
            pass

    task_dir = ARTIFACTS_DIR / task_id
    try:
        if task_dir.exists():
            for child in task_dir.iterdir():
                if child.is_file():
                    child.unlink(missing_ok=True)
            task_dir.rmdir()
    except Exception:
        pass

    await notify_clients()
    return {"task_id": task_id, "deleted": True, "artifact_files_removed": removed_files}


@app.post("/api/tasks/{task_id}/dispatch", response_model=DispatchDecisionResponse)
async def dispatch_task(
    task_id: str,
    request: DispatchRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Dispatch")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    task_dict = dict(task)
    decision = build_dispatch_decision(task_dict, conn)
    if request.context_file or request.context_bundle is not None:
        decision.setdefault("prompt_pack", {})
        decision["prompt_pack"]["external_context"] = {
            "context_file": request.context_file,
            "context_bundle": request.context_bundle,
            "attached_at": datetime.now().isoformat(),
        }
        decision["rationale"] += " External context attached."

    decision_id = str(uuid4())
    cursor.execute(
        """
        INSERT INTO dispatch_decisions
        (id, task_id, task_status, selected_agent, selected_model, provider, confidence, rationale, prompt_pack, candidate_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            task_id,
            task_dict["status"],
            decision["selected_agent"],
            decision["selected_model"],
            decision["provider"],
            decision["confidence"],
            decision["rationale"],
            json.dumps(decision["prompt_pack"]),
            json.dumps(decision["candidate_scores"]),
        ),
    )

    resulting_status = task_dict["status"]
    executed = False
    if request.execute:
        if task_dict["status"] != TaskStatus.TODO.value:
            raise HTTPException(
                status_code=409,
                detail=f"Dispatch execute requires status 'todo', found '{task_dict['status']}'",
            )

        resulting_status = TaskStatus.PLANNING.value
        cursor.execute(
            """
            UPDATE tasks
            SET assignee = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (decision["selected_agent"], resulting_status, task_id),
        )
        cursor.execute(
            """
            INSERT INTO task_history (task_id, status_from, status_to, changed_by)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, task_dict["status"], resulting_status, "dispatcher"),
        )
        create_stage_artifact_and_reference(
            cursor=cursor,
            task_id=task_id,
            stage=resulting_status,
            created_by="dispatcher",
            title=task_dict.get("title"),
            description=task_dict.get("description"),
        )
        executed = True

    conn.commit()

    if executed:
        await notify_clients()

    return {
        "task_id": task_id,
        "selected_agent": decision["selected_agent"],
        "selected_model": decision["selected_model"],
        "provider": decision["provider"],
        "confidence": decision["confidence"],
        "rationale": decision["rationale"],
        "prompt_pack": decision["prompt_pack"],
        "candidate_scores": decision["candidate_scores"],
        "executed": executed,
        "resulting_status": resulting_status,
    }


@app.get("/api/tasks/{task_id}/dispatch/latest")
async def get_latest_dispatch_decision(
    task_id: str,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_id FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)
    cursor.execute(
        """
        SELECT *
        FROM dispatch_decisions
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (task_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No dispatch decision found for task")

    record = dict(row)
    record["prompt_pack"] = json.loads(record["prompt_pack"])
    record["candidate_scores"] = json.loads(record["candidate_scores"])
    return record


@app.post("/api/tasks/{task_id}/hitl/approve", response_model=TaskResponse)
async def hitl_approve_task(
    task_id: str,
    request: HitlApproveRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "HITL approve")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    current_status = task["status"]
    next_status_map = {
        TaskStatus.HITL_REVIEW.value: TaskStatus.WORKING.value,
        TaskStatus.APPROVAL.value: TaskStatus.COMPLETED.value,
    }
    if current_status not in next_status_map:
        raise HTTPException(
            status_code=409,
            detail=f"HITL approve is only valid from hitl_review or approval, found '{current_status}'",
        )

    next_status = next_status_map[current_status]
    cursor.execute(
        """
        UPDATE tasks
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (next_status, task_id),
    )
    cursor.execute(
        """
        INSERT INTO task_history (task_id, status_from, status_to, changed_by)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, current_status, next_status, "hitl_approve"),
    )
    if next_status == TaskStatus.WORKING.value:
        create_stage_artifact_and_reference(
            cursor=cursor,
            task_id=task_id,
            stage=next_status,
            created_by=actor_id or "hitl_approve",
            title=task["title"],
            description=task["description"],
        )
    cursor.execute(
        """
        INSERT INTO logs (task_id, message, level)
        VALUES (?, ?, 'info')
        """,
        (task_id, f"HITL approved transition {current_status} -> {next_status}. {request.comment or ''}".strip()),
    )
    insert_task_comment(cursor, task_id, actor_id or "hitl_approve", request.comment)
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    await notify_clients()
    return serialize_task_row(updated)


@app.post("/api/tasks/{task_id}/hitl/reject", response_model=TaskResponse)
async def hitl_reject_task(
    task_id: str,
    request: HitlRejectRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "HITL reject")
    ensure_actor_role(actor_role, REVIEWER_ROLES, "HITL reject")

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    current_status = task["status"]
    if current_status not in (TaskStatus.HITL_REVIEW.value, TaskStatus.APPROVAL.value):
        raise HTTPException(
            status_code=409,
            detail=f"HITL reject is only valid from hitl_review or approval, found '{current_status}'",
        )

    default_target_map = {
        TaskStatus.HITL_REVIEW.value: TaskStatus.PLANNING.value,
        TaskStatus.APPROVAL.value: TaskStatus.WORKING.value,
    }
    target_status = (request.target_status.value if request.target_status else default_target_map[current_status])
    if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid reject target transition: {current_status} -> {target_status}",
        )

    cursor.execute(
        """
        UPDATE tasks
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (target_status, task_id),
    )
    cursor.execute(
        """
        INSERT INTO task_history (task_id, status_from, status_to, changed_by)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, current_status, target_status, f"hitl_reject:{actor_id or actor_role}"),
    )
    cursor.execute(
        """
        INSERT INTO logs (task_id, message, level)
        VALUES (?, ?, 'warning')
        """,
        (task_id, f"HITL rejected transition {current_status} -> {target_status}. {request.comment or ''}".strip()),
    )
    insert_task_comment(cursor, task_id, actor_id or actor_role or "hitl_reject", request.comment)
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    await notify_clients()
    return serialize_task_row(updated)


@app.post("/api/tasks/{task_id}/dispatch/pause", response_model=TaskResponse)
async def pause_dispatch_task(
    task_id: str,
    request: DispatchPauseRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Dispatch pause")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    current_status = task["status"]
    if current_status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause task in terminal state '{current_status}'",
        )

    if TaskStatus.BLOCKED.value not in ALLOWED_TRANSITIONS.get(current_status, set()) and current_status != TaskStatus.BLOCKED.value:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid pause transition: {current_status} -> blocked",
        )

    if current_status != TaskStatus.BLOCKED.value:
        cursor.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (TaskStatus.BLOCKED.value, task_id),
        )
        cursor.execute(
            """
            INSERT INTO task_history (task_id, status_from, status_to, changed_by)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, current_status, TaskStatus.BLOCKED.value, "dispatch_pause"),
        )
    cursor.execute(
        """
        INSERT INTO logs (task_id, message, level)
        VALUES (?, ?, 'warning')
        """,
        (task_id, f"Dispatch paused. {request.reason or 'No reason provided.'}"),
    )
    insert_task_comment(cursor, task_id, "dispatch_pause", request.reason)
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    await notify_clients()
    return serialize_task_row(updated)


@app.post("/api/tasks/{task_id}/dispatch/override", response_model=TaskResponse)
async def override_dispatch_task(
    task_id: str,
    request: DispatchOverrideRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Dispatch override")
    ensure_actor_role(actor_role, OVERRIDE_ROLES, "Dispatch override")

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    current_status = task["status"]
    target_status = current_status
    if request.move_to_planning:
        if TaskStatus.PLANNING.value not in ALLOWED_TRANSITIONS.get(current_status, set()) and current_status != TaskStatus.PLANNING.value:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid override transition: {current_status} -> planning",
            )
        target_status = TaskStatus.PLANNING.value

    cursor.execute(
        """
        UPDATE tasks
        SET assignee = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (request.agent_id, target_status, task_id),
    )
    if target_status != current_status:
        cursor.execute(
            """
            INSERT INTO task_history (task_id, status_from, status_to, changed_by)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, current_status, target_status, f"dispatch_override:{actor_id or actor_role}"),
        )

    profiles = {p["name"]: p for p in load_agent_profiles()}
    profile = profiles.get(request.agent_id.lower())
    selected_model = profile["model"] if profile else "unknown"
    provider = profile["provider"] if profile else "unknown"
    rationale = f"Manual override by {actor_id or actor_role} to agent {request.agent_id}. {request.reason or ''}".strip()
    cursor.execute(
        """
        INSERT INTO dispatch_decisions
        (id, task_id, task_status, selected_agent, selected_model, provider, confidence, rationale, prompt_pack, candidate_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            task_id,
            target_status,
            request.agent_id,
            selected_model,
            provider,
            1.0,
            rationale,
            json.dumps({"manual_override": True}),
            json.dumps([]),
        ),
    )
    cursor.execute(
        """
        INSERT INTO logs (task_id, message, level)
        VALUES (?, ?, 'warning')
        """,
        (task_id, rationale),
    )
    insert_task_comment(cursor, task_id, actor_id or actor_role or "dispatch_override", request.reason)
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    await notify_clients()
    return serialize_task_row(updated)


@app.post("/api/tasks/{task_id}/dispatch/reassign", response_model=TaskResponse)
async def reassign_dispatch_task(
    task_id: str,
    request: DispatchReassignRequest,
    actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    api_token: Optional[str] = Header(None, alias="X-API-Token"),
    conn: sqlite3.Connection = Depends(get_db),
):
    ensure_api_token(api_token, "Dispatch reassign")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assert_project_visible(conn, str(task["project_id"]), actor_role, actor_id)

    cursor.execute(
        """
        UPDATE tasks
        SET assignee = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (request.agent_id, task_id),
    )

    note = f"Dispatch reassigned to {request.agent_id}. {request.reason or ''}".strip()
    cursor.execute(
        """
        INSERT INTO logs (task_id, message, level)
        VALUES (?, ?, 'info')
        """,
        (task_id, note),
    )
    insert_task_comment(cursor, task_id, "dispatch_reassign", request.reason)
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated = cursor.fetchone()
    await notify_clients()
    return serialize_task_row(updated)

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
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find tasks that haven't been updated in 35 minutes
            stale_time = datetime.now() - timedelta(minutes=35)
            cursor.execute("""
                SELECT id, status, assignee 
                FROM tasks 
                WHERE status IN (?, ?) 
                AND datetime(updated_at) < datetime(?)
            """, (
                ACTIVE_WORK_STATUSES[0],
                ACTIVE_WORK_STATUSES[1],
                stale_time.strftime("%Y-%m-%d %H:%M:%S"),
            ))
            
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
