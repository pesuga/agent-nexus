#!/usr/bin/env python3
"""
Test script for Agent CLI System

This script tests the complete workflow:
1. Create test tasks
2. Test agent polling and assignment
3. Test task execution
4. Test heartbeat system
5. Test crash recovery
"""

import os
import sys
import time
import sqlite3
import uuid
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set simulation mode
os.environ["AGENT_CLI_SIMULATE"] = "true"

def run_cli_command(cmd):
    """Run CLI command and return output"""
    full_cmd = ["python3", str(PROJECT_ROOT / "cli" / "agent-cli.py")] + cmd
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def setup_test_database():
    """Set up test database with clean state"""
    db_path = PROJECT_ROOT / "backend" / "agent_tasks.db"
    
    # Backup original database
    backup_path = db_path.with_suffix('.db.backup')
    if db_path.exists():
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backed up database to {backup_path}")
    
    # Create fresh database
    if db_path.exists():
        db_path.unlink()
    
    # Run database setup via CLI
    print("Setting up fresh database...")
    returncode, stdout, stderr = run_cli_command(["agents", "list"])
    
    if returncode != 0:
        print(f"Error setting up database: {stderr}")
        return False
    
    return True

def create_test_tasks():
    """Create test tasks in database"""
    db_path = PROJECT_ROOT / "backend" / "agent_tasks.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test project
    project_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
        (project_id, "Test Project", "Test project for CLI system")
    )
    
    # Create test tasks
    test_tasks = [
        {
            "id": f"test-ren-{int(time.time())}",
            "title": "Ren: Check system status",
            "description": "Check disk space, memory, and running services",
            "assignee": "ren",
            "priority": 1
        },
        {
            "id": f"test-aki-{int(time.time() + 1)}",
            "title": "Aki: Coordinate team tasks",
            "description": "Review pending tasks and assign priorities",
            "assignee": "aki",
            "priority": 2
        },
        {
            "id": f"test-unassigned-{int(time.time() + 2)}",
            "title": "Unassigned: General maintenance",
            "description": "General system maintenance tasks",
            "assignee": None,  # Will be claimed by Aki
            "priority": 3
        }
    ]
    
    for task in test_tasks:
        cursor.execute(
            """INSERT INTO tasks (id, project_id, title, description, status, assignee, priority)
            VALUES (?, ?, ?, ?, 'todo', ?, ?)""",
            (task["id"], project_id, task["title"], task["description"], task["assignee"], task["priority"])
        )
        print(f"Created task: {task['title']} (ID: {task['id']})")
    
    conn.commit()
    conn.close()
    
    return [task["id"] for task in test_tasks]

def test_agent_polling():
    """Test that agents can poll for tasks"""
    print("\n=== Testing Agent Polling ===")
    
    # Test Ren polling (should find assigned task)
    print("\n1. Testing Ren agent polling...")
    returncode, stdout, stderr = run_cli_command(["poll", "--agent", "ren"])
    
    if returncode == 0 and "Task assigned:" in stdout:
        print("✅ Ren polling successful")
        # Extract task ID from output
        import re
        match = re.search(r'ID: (\S+)\)', stdout)
        if match:
            ren_task_id = match.group(1)
            print(f"   Task ID: {ren_task_id}")
            return ren_task_id
    else:
        print("❌ Ren polling failed")
        print(f"   Output: {stdout}")
        print(f"   Error: {stderr}")
    
    return None

def test_task_execution(task_id):
    """Test task execution"""
    print("\n=== Testing Task Execution ===")
    
    print(f"\n1. Executing task {task_id} with Ren...")
    returncode, stdout, stderr = run_cli_command(["execute", "--task", task_id, "--agent", "ren"])
    
    if returncode == 0 and "Task completed successfully" in stdout:
        print("✅ Task execution successful")
        
        # Verify task status in database
        db_path = PROJECT_ROOT / "backend" / "agent_tasks.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        status = cursor.fetchone()[0]
        conn.close()
        
        if status == "done":
            print(f"✅ Task status updated to: {status}")
        else:
            print(f"❌ Task status is {status}, expected 'done'")
        
        return True
    else:
        print("❌ Task execution failed")
        print(f"   Output: {stdout}")
        print(f"   Error: {stderr}")
        return False

def test_heartbeat_system():
    """Test heartbeat system"""
    print("\n=== Testing Heartbeat System ===")
    
    print("\n1. Testing Ren heartbeat...")
    returncode, stdout, stderr = run_cli_command(["heartbeat", "--agent", "ren"])
    
    if returncode == 0 and "ren is alive" in stdout:
        print("✅ Heartbeat successful")
        
        # Check health status
        print("\n2. Checking system health...")
        returncode, stdout, stderr = run_cli_command(["health"])
        
        if returncode == 0 and "healthy_agents" in stdout:
            print("✅ Health check successful")
            
            # Parse JSON output
            import json
            try:
                health_data = json.loads(stdout)
                ren_status = next((a for a in health_data["agents"] if a["name"] == "ren"), None)
                if ren_status and ren_status.get("last_heartbeat"):
                    print(f"✅ Ren last heartbeat: {ren_status['last_heartbeat']}")
                    return True
            except json.JSONDecodeError:
                print("❌ Could not parse health JSON")
        else:
            print("❌ Health check failed")
    else:
        print("❌ Heartbeat failed")
    
    return False

def test_crash_recovery():
    """Test crash recovery system"""
    print("\n=== Testing Crash Recovery ===")
    
    # Create a task and simulate agent crash
    db_path = PROJECT_ROOT / "backend" / "agent_tasks.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create a task for Ren
    crash_task_id = f"test-crash-{int(time.time())}"
    cursor.execute(
        """INSERT INTO tasks (id, project_id, title, description, status, assignee, priority)
        VALUES (?, ?, ?, ?, 'in_progress', ?, 1)""",
        (crash_task_id, 
         cursor.execute("SELECT id FROM projects LIMIT 1").fetchone()[0],
         "Crash Test Task",
         "Test crash recovery system",
         "ren")
    )
    
    # Create assignment record
    cursor.execute(
        """INSERT INTO assignments (id, task_id, agent_name, status, started_at)
        VALUES (?, ?, ?, 'started', datetime('now', '-3 minutes'))""",
        (f"assign-{crash_task_id}", crash_task_id, "ren")
    )
    
    # Set Ren status to working with old heartbeat
    cursor.execute(
        "UPDATE agents SET status = 'working', current_task_id = ?, last_heartbeat = datetime('now', '-3 minutes') WHERE name = 'ren'",
        (crash_task_id,)
    )
    
    conn.commit()
    conn.close()
    
    print(f"\n1. Created crashed agent scenario for task: {crash_task_id}")
    
    # Check health (should detect crash)
    print("\n2. Checking for crashed agents...")
    returncode, stdout, stderr = run_cli_command(["health"])
    
    if returncode == 0 and "crashed" in stdout:
        import json
        health_data = json.loads(stdout)
        if "ren" in str(health_data.get("crashed", [])):
            print("✅ Crash detection working")
        else:
            print("❌ Crash not detected")
            return False
    else:
        print("❌ Health check failed")
        return False
    
    # Test recovery
    print("\n3. Testing crash recovery...")
    returncode, stdout, stderr = run_cli_command(["health", "--recover"])
    
    if returncode == 0 and "Recovered agents" in stdout:
        print("✅ Crash recovery successful")
        
        # Verify task was reassigned
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT assignee FROM tasks WHERE id = ?", (crash_task_id,))
        new_assignee = cursor.fetchone()[0]
        conn.close()
        
        if new_assignee == "aki":
            print("✅ Task reassigned to Aki (coordinator)")
            return True
        else:
            print(f"❌ Task assignee is {new_assignee}, expected 'aki'")
    else:
        print("❌ Crash recovery failed")
    
    return False

def test_aki_unassigned_task():
    """Test that Aki can claim unassigned tasks"""
    print("\n=== Testing Aki Unassigned Task Claim ===")
    
    # Aki should be able to poll and get unassigned task
    print("\n1. Testing Aki polling for unassigned task...")
    returncode, stdout, stderr = run_cli_command(["poll", "--agent", "aki"])
    
    if returncode == 0 and "Task assigned:" in stdout:
        print("✅ Aki successfully claimed unassigned task")
        
        # Extract task ID
        import re
        match = re.search(r'ID: (\S+)\)', stdout)
        if match:
            task_id = match.group(1)
            
            # Verify task was assigned to Aki
            db_path = PROJECT_ROOT / "backend" / "agent_tasks.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT assignee FROM tasks WHERE id = ?", (task_id,))
            assignee = cursor.fetchone()[0]
            conn.close()
            
            if assignee == "aki":
                print(f"✅ Task {task_id} assigned to Aki")
                return True
            else:
                print(f"❌ Task assignee is {assignee}, expected 'aki'")
    else:
        print("❌ Aki polling failed")
    
    return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Agent CLI System Test Suite")
    print("=" * 60)
    
    # Setup
    if not setup_test_database():
        print("❌ Database setup failed")
        return 1
    
    # Create test tasks
    task_ids = create_test_tasks()
    if not task_ids:
        print("❌ Failed to create test tasks")
        return 1
    
    # Run tests
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Agent Polling
    ren_task_id = test_agent_polling()
    if ren_task_id:
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 2: Task Execution
    if ren_task_id and test_task_execution(ren_task_id):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 3: Heartbeat System
    if test_heartbeat_system():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 4: Crash Recovery
    if test_crash_recovery():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 5: Aki Unassigned Task
    if test_aki_unassigned_task():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    
    if tests_failed == 0:
        print("\n🎉 All tests passed! Agent CLI system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())