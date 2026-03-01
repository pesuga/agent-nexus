#!/usr/bin/env python3
"""
Agent CLI System for Agent Task Manager

This CLI enables AI agents (Ren, Aki, Kuro, Shin, Sora) to:
1. Poll for assigned tasks from the kanban system
2. Execute tasks via OpenClaw
3. Update task status and report results
4. Send heartbeats using local model
5. Handle crash detection and recovery

Usage:
    agent-cli.py poll --agent ren
    agent-cli.py execute --task TASK-123
    agent-cli.py heartbeat --agent ren
    agent-cli.py results --task TASK-123 --output "Task completed"
"""

import argparse
import sqlite3
import json
import time
import os
import sys
import subprocess
import fcntl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Configuration
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "backend" / "agent_tasks.db"
LOCK_FILE = DB_PATH.with_suffix('.lock')
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Agent configuration
AGENTS = {
    "ren": {
        "role": "infrastructure & maintenance",
        "model": "qwen-coder-local",
        "capabilities": ["shell", "file_ops", "monitoring", "cron"],
        "openclaw_agent": "ren-grunt"
    },
    "aki": {
        "role": "coordination & reporting",
        "model": "deepseek-chat",
        "capabilities": ["coordination", "reporting", "delegation", "analysis"],
        "openclaw_agent": "aki-partner",
        "can_claim_unassigned": True
    },
    "kuro": {
        "role": "technical execution",
        "model": "deepseek-chat",
        "capabilities": ["coding", "architecture", "security", "debugging"],
        "openclaw_agent": "kuro-coder"
    },
    "shin": {
        "role": "strategy & planning",
        "model": "deepseek-chat",
        "capabilities": ["strategy", "planning", "analysis", "roadmapping"],
        "openclaw_agent": "shin-strategist"
    },
    "sora": {
        "role": "creative brainstorming",
        "model": "gemini",
        "capabilities": ["creative", "brainstorming", "innovation", "design"],
        "openclaw_agent": "sora-creative"
    }
}

class SQLiteLock:
    """File locking for SQLite concurrency control"""
    
    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.fd = None
        
    def acquire(self, timeout: int = 30) -> bool:
        """Acquire lock with timeout (seconds)"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.fd = open(self.lock_file, 'w')
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (BlockingIOError, IOError):
                time.sleep(0.1)
        return False
    
    def release(self):
        """Release lock"""
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
            self.fd = None

class Database:
    """Database operations with locking"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.lock = SQLiteLock(LOCK_FILE)
        
    def connect(self):
        """Get database connection with locking"""
        if not self.lock.acquire():
            raise Exception("Could not acquire database lock")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def disconnect(self, conn):
        """Close connection and release lock"""
        if conn:
            conn.close()
        self.lock.release()
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return results"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.disconnect(conn)
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Execute query and return single result"""
        results = self.execute(query, params)
        return results[0] if results else None

class AgentCLI:
    """Main CLI implementation"""
    
    def __init__(self):
        self.db = Database(DB_PATH)
        self.setup_database()
        
    def setup_database(self):
        """Ensure database has required tables and data"""
        conn = self.db.connect()
        try:
            cursor = conn.cursor()
            
            # Create assignments table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT CHECK (status IN ('pending', 'started', 'completed', 'failed')),
                    output TEXT,
                    error TEXT,
                    logs TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            """)
            
            # Create heartbeats table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS heartbeats (
                    agent_name TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT CHECK (status IN ('alive', 'warning', 'error'))
                )
            """)
            
            # Create locks table for advisory locking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locks (
                    resource TEXT PRIMARY KEY,
                    owner TEXT,
                    acquired_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # Ensure agents table has required columns
            cursor.execute("PRAGMA table_info(agents)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'current_task_id' not in columns:
                cursor.execute("ALTER TABLE agents ADD COLUMN current_task_id TEXT")
            
            if 'model' not in columns:
                cursor.execute("ALTER TABLE agents ADD COLUMN model TEXT")
            
            if 'config' not in columns:
                cursor.execute("ALTER TABLE agents ADD COLUMN config TEXT")
            
            # Seed agents if not exists
            for agent_name, config in AGENTS.items():
                cursor.execute(
                    "SELECT id FROM agents WHERE name = ?",
                    (agent_name,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO agents (id, name, type, status, capabilities, model, config)
                        VALUES (?, ?, ?, 'idle', ?, ?, ?)
                        """,
                        (
                            f"agent-{agent_name}",
                            agent_name,
                            config["role"],
                            json.dumps(config["capabilities"]),
                            config["model"],
                            json.dumps(config)
                        )
                    )
            
            conn.commit()
        finally:
            self.db.disconnect(conn)
    
    def poll(self, agent_name: str) -> Optional[Dict]:
        """Poll for next task for the agent"""
        if agent_name not in AGENTS:
            print(f"Error: Unknown agent '{agent_name}'")
            return None
        
        agent_config = AGENTS[agent_name]
        
        with self.db.connect() as conn:
            cursor = conn.cursor()
            
            # 1. Check for tasks specifically assigned to this agent
            cursor.execute("""
                SELECT t.* 
                FROM tasks t
                WHERE t.assignee = ? 
                  AND t.status = 'todo'
                ORDER BY t.priority DESC, t.created_at ASC
                LIMIT 1
            """, (agent_name,))
            
            task = cursor.fetchone()
            
            # 2. If Aki and no assigned tasks, check for unassigned tasks
            if not task and agent_name == 'aki' and agent_config.get('can_claim_unassigned'):
                cursor.execute("""
                    SELECT t.* 
                    FROM tasks t
                    WHERE t.assignee IS NULL 
                      AND t.status = 'todo'
                    ORDER BY t.priority DESC, t.created_at ASC
                    LIMIT 1
                """)
                task = cursor.fetchone()
                
                # If found unassigned task, assign it to Aki
                if task:
                    cursor.execute(
                        "UPDATE tasks SET assignee = ? WHERE id = ?",
                        (agent_name, task['id'])
                    )
            
            if task:
                # Create assignment record
                assignment_id = f"assign-{task['id']}-{agent_name}-{int(time.time())}"
                cursor.execute("""
                    INSERT INTO assignments (id, task_id, agent_name, status)
                    VALUES (?, ?, ?, 'pending')
                """, (assignment_id, task['id'], agent_name))
                
                # Update agent status
                cursor.execute("""
                    UPDATE agents 
                    SET status = 'working', current_task_id = ?
                    WHERE name = ?
                """, (task['id'], agent_name))
                
                conn.commit()
                
                print(f"Task assigned: {task['title']} (ID: {task['id']})")
                return dict(task)
        
        print("No tasks available")
        return None
    
    def execute(self, task_id: str, agent_name: str) -> bool:
        """Execute a task via OpenClaw"""
        if agent_name not in AGENTS:
            print(f"Error: Unknown agent '{agent_name}'")
            return False
        
        agent_config = AGENTS[agent_name]
        
        with self.db.connect() as conn:
            cursor = conn.cursor()
            
            # Get task details
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            
            if not task:
                print(f"Error: Task {task_id} not found")
                return False
            
            # Update task and assignment status
            cursor.execute(
                "UPDATE tasks SET status = 'in_progress' WHERE id = ?",
                (task_id,)
            )
            
            cursor.execute("""
                UPDATE assignments 
                SET status = 'started', started_at = CURRENT_TIMESTAMP
                WHERE task_id = ? AND agent_name = ?
            """, (task_id, agent_name))
            
            # Log the execution
            cursor.execute("""
                INSERT INTO logs (task_id, agent_id, message, level)
                VALUES (?, ?, ?, 'info')
            """, (task_id, f"agent-{agent_name}", f"Task execution started by {agent_name}"))
            
            conn.commit()
        
        # Execute via OpenClaw (or simulate for testing)
        openclaw_agent = agent_config["openclaw_agent"]
        task_description = f"{task['title']}\n\n{task['description'] or ''}"
        
        # Check if we should simulate (for testing)
        simulate = os.environ.get("AGENT_CLI_SIMULATE", "false").lower() == "true"
        
        if simulate:
            print(f"[SIMULATE] Would execute via OpenClaw: openclaw agent --agent {openclaw_agent}")
            
            # Simulate successful execution
            class SimulatedResult:
                def __init__(self):
                    self.returncode = 0
                    self.stdout = f"Task '{task['title']}' completed successfully by {agent_name}"
                    self.stderr = ""
            
            result = SimulatedResult()
            self._store_results(task_id, agent_name, result)
            return True
        else:
            # Build OpenClaw command
            cmd = [
                "openclaw", "agent",
                "--agent", openclaw_agent,
                "--message", task_description
            ]
            
            print(f"Executing task via OpenClaw: {' '.join(cmd)}")
            
            try:
                # Execute command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                # Store results
                self._store_results(task_id, agent_name, result)
                return True
                
            except subprocess.TimeoutExpired:
                print(f"Error: Task execution timed out")
                self._store_error(task_id, agent_name, "Execution timeout")
                return False
            except Exception as e:
                print(f"Error executing task: {e}")
                self._store_error(task_id, agent_name, str(e))
                return False
    
    def _store_results(self, task_id: str, agent_name: str, result: subprocess.CompletedProcess):
        """Store execution results"""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            
            success = result.returncode == 0
            
            # Update task status
            new_status = 'done' if success else 'blocked'
            cursor.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (new_status, task_id)
            )
            
            # Update assignment
            cursor.execute("""
                UPDATE assignments 
                SET status = ?, completed_at = CURRENT_TIMESTAMP,
                    output = ?, logs = ?
                WHERE task_id = ? AND agent_name = ?
            """, (
                'completed' if success else 'failed',
                result.stdout,
                result.stderr,
                task_id,
                agent_name
            ))
            
            # Update agent status
            cursor.execute("""
                UPDATE agents 
                SET status = 'idle', current_task_id = NULL
                WHERE name = ?
            """, (agent_name,))
            
            # Log result
            log_level = 'info' if success else 'error'
            log_message = f"Task completed {'successfully' if success else 'with errors'}"
            cursor.execute("""
                INSERT INTO logs (task_id, agent_id, message, level)
                VALUES (?, ?, ?, ?)
            """, (task_id, f"agent-{agent_name}", log_message, log_level))
            
            conn.commit()
        
        print(f"Task {'completed successfully' if success else 'failed'}")
        if result.stdout:
            print(f"Output: {result.stdout[:500]}...")
    
    def _store_error(self, task_id: str, agent_name: str, error: str):
        """Store error information"""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE assignments 
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
                    error = ?
                WHERE task_id = ? AND agent_name = ?
            """, (error, task_id, agent_name))
            
            cursor.execute("""
                UPDATE agents 
                SET status = 'idle', current_task_id = NULL
                WHERE name = ?
            """, (agent_name,))
            
            cursor.execute("""
                INSERT INTO logs (task_id, agent_id, message, level)
                VALUES (?, ?, ?, 'error')
            """, (task_id, f"agent-{agent_name}", f"Task failed: {error}"))
            
            conn.commit()
    
    def heartbeat(self, agent_name: str) -> bool:
        """Send heartbeat using local model"""
        if agent_name not in AGENTS:
            print(f"Error: Unknown agent '{agent_name}'")
            return False
        
        agent_config = AGENTS[agent_name]
        
        # Use local model for heartbeats if available
        if agent_config["model"] == "qwen-coder-local":
            return self._local_heartbeat(agent_name)
        else:
            # For non-local models, just update timestamp
            return self._simple_heartbeat(agent_name)
    
    def _local_heartbeat(self, agent_name: str) -> bool:
        """Send heartbeat using local qwen-coder model"""
        try:
            # Simple prompt for local model
            prompt = f"You are agent {agent_name}. Respond with 'ALIVE' if functioning normally."
            
            # Call local model via curl (adjust port as needed)
            cmd = [
                "curl", "-s", "-X", "POST",
                "http://127.0.0.1:8082/v1/chat/completions",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({
                    "model": "qwen2.5-coder-7b",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10,
                    "temperature": 0.1
                })
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if "ALIVE" in text.upper():
                    self._record_heartbeat(agent_name, "alive")
                    print(f"Heartbeat: {agent_name} is alive")
                    return True
                else:
                    self._record_heartbeat(agent_name, "warning")
                    print(f"Heartbeat: {agent_name} responded but not 'ALIVE'")
                    return False
            else:
                self._record_heartbeat(agent_name, "error")
                print(f"Heartbeat error: {result.stderr}")
                return False
                
        except Exception as e:
            self._record_heartbeat(agent_name, "error")
            print(f"Heartbeat exception: {e}")
            return False
    
    def _simple_heartbeat(self, agent_name: str) -> bool:
        """Simple heartbeat without model call"""
        self._record_heartbeat(agent_name, "alive")
        print(f"Heartbeat: {agent_name} updated")
        return True
    
    def _record_heartbeat(self, agent_name: str, status: str):
        """Record heartbeat in database"""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            
            # Record heartbeat
            cursor.execute("""
                INSERT INTO heartbeats (agent_name, status)
                VALUES (?, ?)
            """, (agent_name, status))
            
            # Update agent last_heartbeat
            cursor.execute("""
                UPDATE agents 
                SET last_heartbeat = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (agent_name,))
            
            conn.commit()
    
    def check_health(self) -> Dict[str, Any]:
        """Check health of all agents"""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            
            # Get all agents and their last heartbeat
            cursor.execute("""
                SELECT a.name, a.status, a.last_heartbeat,
                       MAX(h.timestamp) as last_heartbeat_time,
                       MAX(h.status) as last_heartbeat_status
                FROM agents a
                LEFT JOIN heartbeats h ON a.name = h.agent_name
                GROUP BY a.name, a.status, a.last_heartbeat
            """)
            
            agents = [dict(row) for row in cursor.fetchall()]
            
            # Check for crashed agents (no heartbeat in 2 minutes)
            crashed = []
            for agent in agents:
                last_heartbeat = agent.get('last_heartbeat')
                if last_heartbeat:
                    last_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                    if datetime.now() - last_time > timedelta(minutes=2):
                        crashed.append(agent['name'])
            
            return {
                "agents": agents,
                "crashed": crashed,
                "total_agents": len(agents),
                "healthy_agents": len(agents) - len(crashed)
            }
    
    def recover_crashed(self, agent_name: Optional[str] = None) -> List[str]:
        """Recover crashed agents and reassign their tasks"""
        recovered = []
        
        health = self.check_health()
        crashed_agents = health["crashed"]
        
        if agent_name:
            if agent_name not in crashed_agents:
                print(f"Agent {agent_name} is not marked as crashed")
                return []
            crashed_agents = [agent_name]
        
        for agent in crashed_agents:
            print(f"Recovering crashed agent: {agent}")
            
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                # Get tasks assigned to this agent
                cursor.execute("""
                    SELECT t.id, t.title
                    FROM tasks t
                    JOIN assignments a ON t.id = a.task_id
                    WHERE a.agent_name = ? 
                      AND a.status IN ('pending', 'started')
                      AND t.status = 'in_progress'
                """, (agent,))
                
                tasks = cursor.fetchall()
                
                # Reassign tasks to Aki (coordinator)
                for task in tasks:
                    task_id = task['id']
                    print(f"  Reassigning task: {task['title']}")
                    
                    # Create new assignment for Aki
                    assignment_id = f"recover-{task_id}-aki-{int(time.time())}"
                    cursor.execute("""
                        INSERT INTO assignments (id, task_id, agent_name, status)
                        VALUES (?, ?, ?, 'pending')
                    """, (assignment_id, task_id, 'aki'))
                    
                    # Update task assignee
                    cursor.execute("""
                        UPDATE tasks SET assignee = 'aki' WHERE id = ?
                    """, (task_id,))
                
                # Mark old assignments as failed
                cursor.execute("""
                    UPDATE assignments 
                    SET status = 'failed', 
                        error = 'Agent crashed, task reassigned'
                    WHERE agent_name = ? 
                      AND status IN ('pending', 'started')
                """, (agent,))
                
                # Reset agent status
                cursor.execute("""
                    UPDATE agents 
                    SET status = 'idle', current_task_id = NULL
                    WHERE name = ?
                """, (agent,))
                
                conn.commit()
            
            recovered.append(agent)
        
        return recovered

def main():
    parser = argparse.ArgumentParser(description="Agent CLI System")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Poll command
    poll_parser = subparsers.add_parser("poll", help="Poll for tasks")
    poll_parser.add_argument("--agent", required=True, help="Agent name")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute a task")
    execute_parser.add_argument("--task", required=True, help="Task ID")
    execute_parser.add_argument("--agent", required=True, help="Agent name")
    
    # Heartbeat command
    heartbeat_parser = subparsers.add_parser("heartbeat", help="Send heartbeat")
    heartbeat_parser.add_argument("--agent", required=True, help="Agent name")
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Check system health")
    health_parser.add_argument("--recover", action="store_true", help="Recover crashed agents")
    
    # Results command
    results_parser = subparsers.add_parser("results", help="Submit task results")
    results_parser.add_argument("--task", required=True, help="Task ID")
    results_parser.add_argument("--agent", required=True, help="Agent name")
    results_parser.add_argument("--output", required=True, help="Task output")
    results_parser.add_argument("--status", default="completed", help="Task status")
    
    # Agents command
    agents_parser = subparsers.add_parser("agents", help="Manage agents")
    agents_parser.add_argument("action", choices=["list", "status", "restart"])
    agents_parser.add_argument("--agent", help="Specific agent")
    
    # Tasks command
    tasks_parser = subparsers.add_parser("tasks", help="Manage tasks")
    tasks_parser.add_argument("action", choices=["list", "create", "stuck"])
    tasks_parser.add_argument("--agent", help="Filter by agent")
    tasks_parser.add_argument("--title", help="Task title")
    tasks_parser.add_argument("--description", help="Task description")
    tasks_parser.add_argument("--assignee", help="Assign to agent")
    tasks_parser.add_argument("--fix", action="store_true", help="Fix stuck tasks")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = AgentCLI()
    
    try:
        if args.command == "poll":
            task = cli.poll(args.agent)
            if task:
                print(json.dumps(task, indent=2))
                
        elif args.command == "execute":
            success = cli.execute(args.task, args.agent)
            sys.exit(0 if success else 1)
            
        elif args.command == "heartbeat":
            success = cli.heartbeat(args.agent)
            sys.exit(0 if success else 1)
            
        elif args.command == "health":
            health = cli.check_health()
            print(json.dumps(health, indent=2))
            
            if args.recover:
                recovered = cli.recover_crashed()
                if recovered:
                    print(f"Recovered agents: {', '.join(recovered)}")
                else:
                    print("No crashed agents to recover")
                    
        elif args.command == "results":
            # This would store results in database
            print("Results submission not fully implemented yet")
            # TODO: Implement results storage
            
        elif args.command == "agents":
            if args.action == "list":
                print("Available agents:", ", ".join(AGENTS.keys()))
            elif args.action == "status":
                health = cli.check_health()
                for agent in health["agents"]:
                    status = "✅" if agent["name"] not in health["crashed"] else "❌"
                    print(f"{status} {agent['name']}: {agent['status']}")
                    
        elif args.command == "tasks":
            if args.action == "list":
                print("Task listing not fully implemented yet")
            elif args.action == "create":
                print("Task creation not fully implemented yet")
            elif args.action == "stuck":
                if args.fix:
                    recovered = cli.recover_crashed(args.agent)
                    if recovered:
                        print(f"Fixed stuck tasks for: {', '.join(recovered)}")
                    else:
                        print("No stuck tasks found")
                else:
                    health = cli.check_health()
                    if health["crashed"]:
                        print(f"Crashed agents with stuck tasks: {', '.join(health['crashed'])}")
                    else:
                        print("No stuck tasks found")
                        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()