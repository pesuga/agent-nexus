#!/usr/bin/env python3
"""
Basic Workflow Example
Demonstrates a complete workflow using the Agent Task Manager API
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_step(step, description):
    """Print a step with formatting"""
    print(f"\n{'='*60}")
    print(f"Step {step}: {description}")
    print(f"{'='*60}")

def check_health():
    """Check if the API is healthy"""
    print_step(1, "Checking API Health")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?")
        return False

def create_project():
    """Create a new project"""
    print_step(2, "Creating Project")
    
    project_data = {
        "name": "Example Project",
        "description": "Project for demonstration purposes"
    }
    
    response = requests.post(f"{BASE_URL}/api/projects", json=project_data)
    
    if response.status_code == 200:
        project = response.json()
        print(f"✅ Project created: {project['name']} (ID: {project['id']})")
        return project['id']
    else:
        print(f"❌ Failed to create project: {response.text}")
        return None

def create_tasks(project_id):
    """Create example tasks"""
    print_step(3, "Creating Example Tasks")
    
    tasks = [
        {
            "title": "Design database schema",
            "description": "Design the SQLite database schema for the application",
            "project_id": project_id,
            "priority": 2
        },
        {
            "title": "Implement backend API",
            "description": "Create FastAPI endpoints for task management",
            "project_id": project_id,
            "priority": 2
        },
        {
            "title": "Build frontend UI",
            "description": "Create HTML/JS frontend with drag-and-drop",
            "project_id": project_id,
            "priority": 1
        },
        {
            "title": "Create CLI tool",
            "description": "Build command-line interface for task management",
            "project_id": project_id,
            "priority": 1
        },
        {
            "title": "Write documentation",
            "description": "Create comprehensive documentation and examples",
            "project_id": project_id,
            "priority": 0
        }
    ]
    
    created_tasks = []
    
    for task_data in tasks:
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data)
        
        if response.status_code == 200:
            task = response.json()
            print(f"✅ Task created: {task['title']} (ID: {task['id'][:8]}...)")
            created_tasks.append(task)
        else:
            print(f"❌ Failed to create task: {response.text}")
    
    return created_tasks

def list_tasks(project_id):
    """List all tasks in the project"""
    print_step(4, "Listing Tasks")
    
    params = {"project_id": project_id}
    response = requests.get(f"{BASE_URL}/api/tasks", params=params)
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"Found {len(tasks)} tasks:")
        
        for task in tasks:
            print(f"  • {task['title']} ({task['status']}) - Priority: {task['priority']}")
        
        return tasks
    else:
        print(f"❌ Failed to list tasks: {response.text}")
        return []

def simulate_workflow(tasks):
    """Simulate a workflow moving tasks through statuses"""
    print_step(5, "Simulating Workflow")
    
    # Assign first task to agent
    if tasks:
        task = tasks[0]
        update_data = {
            "assignee": "ren-grunt",
            "status": "planning"
        }
        
        response = requests.put(f"{BASE_URL}/api/tasks/{task['id']}", json=update_data)
        
        if response.status_code == 200:
            print(f"✅ Task assigned to ren-grunt and moved to planning")
        
        # Simulate heartbeat
        heartbeat_data = {
            "agent_id": "ren-grunt",
            "task_id": task['id']
        }
        
        response = requests.post(f"{BASE_URL}/api/tasks/{task['id']}/heartbeat", json=heartbeat_data)
        
        if response.status_code == 200:
            print(f"✅ Heartbeat sent for task")
        
        # Move through workflow
        statuses = ["wip", "implemented", "done"]
        
        for status in statuses:
            time.sleep(1)  # Simulate work time
            
            update_data = {"status": status}
            response = requests.put(f"{BASE_URL}/api/tasks/{task['id']}", json=update_data)
            
            if response.status_code == 200:
                print(f"✅ Task moved to {status}")
            
            # Send heartbeat
            response = requests.post(f"{BASE_URL}/api/tasks/{task['id']}/heartbeat", json=heartbeat_data)

def watch_events():
    """Watch for real-time events"""
    print_step(6, "Watching Real-time Events")
    
    print("Connecting to event stream...")
    print("(Events will appear as tasks are updated)")
    print("Press Ctrl+C to stop watching\n")
    
    try:
        import sseclient
        
        response = requests.get(f"{BASE_URL}/api/events", stream=True)
        client = sseclient.SSEClient(response)
        
        event_count = 0
        max_events = 3  # Show 3 events then stop
        
        for event in client.events():
            if event.data:
                data = json.loads(event.data)
                if data.get('event') == 'state_change':
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] State changed - task updated")
                    event_count += 1
                    
                    if event_count >= max_events:
                        print(f"\nStopped after {max_events} events")
                        break
    except ImportError:
        print("⚠️ sseclient-py not installed. Install with: pip install sseclient-py")
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"❌ Error watching events: {str(e)}")

def generate_report(project_id):
    """Generate a simple report"""
    print_step(7, "Generating Report")
    
    params = {"project_id": project_id}
    response = requests.get(f"{BASE_URL}/api/tasks", params=params)
    
    if response.status_code == 200:
        tasks = response.json()
        
        # Count by status
        status_counts = {}
        for task in tasks:
            status = task['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("Task Status Summary:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        # Count by priority
        priority_map = {0: "Low", 1: "Medium", 2: "High"}
        priority_counts = {0: 0, 1: 0, 2: 0}
        
        for task in tasks:
            priority = task['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        print("\nPriority Summary:")
        for priority, count in priority_counts.items():
            print(f"  {priority_map[priority]}: {count}")
        
        # Assigned tasks
        assigned_tasks = [t for t in tasks if t['assignee']]
        print(f"\nAssigned Tasks: {len(assigned_tasks)}/{len(tasks)}")
        
        for task in assigned_tasks:
            print(f"  • {task['title']} → {task['assignee']}")

def main():
    """Main workflow"""
    print("Agent Task Manager - Basic Workflow Example")
    print("="*60)
    
    # Check health
    if not check_health():
        return
    
    # Create project
    project_id = create_project()
    if not project_id:
        return
    
    # Create tasks
    tasks = create_tasks(project_id)
    if not tasks:
        return
    
    # List tasks
    list_tasks(project_id)
    
    # Simulate workflow
    simulate_workflow(tasks)
    
    # Watch events
    watch_events()
    
    # Generate report
    generate_report(project_id)
    
    print("\n" + "="*60)
    print("Workflow Complete! 🎉")
    print("="*60)
    print("\nNext steps:")
    print("1. Open frontend/index.html to see the tasks")
    print("2. Use the CLI: python3 cli/task_cli.py list")
    print("3. Try creating your own tasks via API or CLI")

if __name__ == "__main__":
    main()