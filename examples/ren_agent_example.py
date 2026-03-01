#!/usr/bin/env python3
"""
Ren Agent Example
Example of how Ren (Infrastructure Sentinel) interacts with the task manager.
"""

import subprocess
import json
import time
import logging
from datetime import datetime, timedelta

class RenAgent:
    """
    Ren - Infrastructure Sentinel
    Handles infrastructure, maintenance, and cron tasks.
    """
    
    def __init__(self, agent_id="ren-grunt"):
        self.agent_id = agent_id
        self.current_task = None
        self.heartbeat_interval = 30  # seconds
        self.last_heartbeat = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f"ren-agent")
    
    def run_cli(self, args):
        """Run CLI command and return output"""
        cmd = ["python3", "cli/task_cli.py"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"CLI command failed: {e}")
            return None
    
    def get_next_task(self):
        """Get next infrastructure task from todo list"""
        # Look for tasks with infrastructure keywords
        output = self.run_cli(["list", "--status", "todo", "--json"])
        
        if not output:
            return None
        
        try:
            tasks = json.loads(output)
            
            # Filter for infrastructure-related tasks
            infrastructure_keywords = [
                "infrastructure", "maintenance", "cron", "backup",
                "monitor", "server", "deploy", "database", "backup",
                "security", "update", "upgrade", "install"
            ]
            
            for task in tasks:
                title_lower = task['title'].lower()
                desc_lower = task.get('description', '').lower()
                
                for keyword in infrastructure_keywords:
                    if keyword in title_lower or keyword in desc_lower:
                        self.logger.info(f"Found infrastructure task: {task['title']}")
                        return task
            
            # If no infrastructure tasks, take any task
            if tasks:
                self.logger.info(f"No infrastructure tasks, taking: {tasks[0]['title']}")
                return tasks[0]
            
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse task list: {e}")
            return None
    
    def assign_task(self, task_id):
        """Assign task to this agent"""
        self.current_task = task_id
        
        # Assign via CLI
        self.run_cli(["assign", task_id, self.agent_id])
        self.logger.info(f"Assigned task {task_id} to {self.agent_id}")
        
        # Move to planning
        self.run_cli(["move", task_id, "planning"])
        self.logger.info(f"Moved task {task_id} to planning")
        
        # Start heartbeat
        self.start_heartbeat()
    
    def start_heartbeat(self):
        """Start sending heartbeats for current task"""
        self.last_heartbeat = datetime.now()
        
        # In a real implementation, this would run in a separate thread
        # For this example, we'll just send one heartbeat
        if self.current_task:
            self.run_cli([
                "heartbeat",
                "--task", self.current_task,
                "--agent", self.agent_id
            ])
            self.logger.info(f"Heartbeat sent for task {self.current_task}")
    
    def work_on_task(self, task):
        """Simulate working on a task"""
        task_id = task['id']
        title = task['title']
        
        self.logger.info(f"Starting work on: {title}")
        
        # Move to WIP
        self.run_cli(["move", task_id, "wip"])
        
        # Simulate different types of infrastructure work
        if "cron" in title.lower():
            self.handle_cron_task(task)
        elif "backup" in title.lower():
            self.handle_backup_task(task)
        elif "monitor" in title.lower():
            self.handle_monitoring_task(task)
        elif "deploy" in title.lower():
            self.handle_deployment_task(task)
        else:
            self.handle_general_task(task)
        
        # Send periodic heartbeats while working
        for i in range(3):
            time.sleep(2)  # Simulate work time
            self.run_cli([
                "heartbeat",
                "--task", task_id,
                "--agent", self.agent_id
            ])
            self.logger.debug(f"Heartbeat {i+1}/3 sent")
        
        # Mark as implemented
        self.run_cli(["move", task_id, "implemented"])
        self.logger.info(f"Completed work on: {title}")
        
        # Clear current task
        self.current_task = None
    
    def handle_cron_task(self, task):
        """Handle cron-related infrastructure task"""
        self.logger.info("Setting up cron job...")
        
        # Simulate cron job setup
        cron_content = """# Agent Task Manager - Heartbeat cron
*/5 * * * * /usr/bin/curl -X POST http://localhost:8000/api/tasks/{task_id}/heartbeat"""
        
        # In a real implementation, this would write to crontab
        # For this example, just log it
        self.logger.info(f"Would create cron job:\n{cron_content}")
        
        # Simulate work time
        time.sleep(1)
    
    def handle_backup_task(self, task):
        """Handle backup-related infrastructure task"""
        self.logger.info("Creating backup...")
        
        # Simulate backup creation
        backup_script = """#!/bin/bash
# Backup script for Agent Task Manager
BACKUP_DIR="/backups/agent-task-manager"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/agent_tasks_$DATE.db"

mkdir -p $BACKUP_DIR
sqlite3 /path/to/agent_tasks.db ".backup '$BACKUP_FILE'"
gzip $BACKUP_FILE
"""
        
        self.logger.info(f"Would create backup script:\n{backup_script}")
        time.sleep(1)
    
    def handle_monitoring_task(self, task):
        """Handle monitoring-related infrastructure task"""
        self.logger.info("Setting up monitoring...")
        
        # Simulate monitoring setup
        monitoring_config = """# Prometheus monitoring config
- job_name: 'agent-task-manager'
  static_configs:
    - targets: ['localhost:8000']
  metrics_path: '/metrics'
"""
        
        self.logger.info(f"Would create monitoring config:\n{monitoring_config}")
        time.sleep(1)
    
    def handle_deployment_task(self, task):
        """Handle deployment-related infrastructure task"""
        self.logger.info("Handling deployment...")
        
        # Simulate deployment script
        deploy_script = """#!/bin/bash
# Deployment script for Agent Task Manager

# Pull latest changes
git pull origin main

# Install dependencies
pip install -r backend/requirements.txt

# Restart service
systemctl restart agent-task-manager
"""
        
        self.logger.info(f"Would create deployment script:\n{deploy_script}")
        time.sleep(1)
    
    def handle_general_task(self, task):
        """Handle general infrastructure task"""
        self.logger.info(f"Working on general infrastructure task: {task['title']}")
        
        # Simulate generic infrastructure work
        steps = [
            "Analyzing requirements",
            "Planning implementation",
            "Executing changes",
            "Verifying results",
            "Documenting work"
        ]
        
        for step in steps:
            self.logger.info(f"  - {step}")
            time.sleep(0.5)
    
    def run(self, max_tasks=None):
        """
        Main agent loop.
        
        Args:
            max_tasks: Maximum number of tasks to process (None for infinite)
        """
        self.logger.info(f"Starting Ren Agent ({self.agent_id})")
        
        tasks_processed = 0
        
        while True:
            if max_tasks and tasks_processed >= max_tasks:
                self.logger.info(f"Processed {tasks_processed} tasks, stopping")
                break
            
            # Check for new tasks
            task = self.get_next_task()
            
            if task:
                self.assign_task(task['id'])
                self.work_on_task(task)
                tasks_processed += 1
            else:
                self.logger.info("No tasks available, waiting...")
                time.sleep(10)  # Wait before checking again

def main():
    """Main function for the example"""
    print("Ren Agent Example")
    print("="*60)
    
    # Check if system is running
    print("Checking system health...")
    try:
        subprocess.run(
            ["python3", "cli/task_cli.py", "health"],
            capture_output=True,
            check=True
        )
        print("✅ System is healthy")
    except:
        print("❌ System is not ready. Please start the backend first.")
        print("   Run: cd backend && python3 main.py")
        return
    
    # Create and run agent
    agent = RenAgent()
    
    print("\nStarting Ren agent...")
    print("This agent will:")
    print("  1. Look for infrastructure tasks")
    print("  2. Assign tasks to itself")
    print("  3. Work on tasks")
    print("  4. Send heartbeats")
    print("  5. Mark tasks as implemented")
    
    print("\nRunning for 2 example tasks...")
    print("Press Ctrl+C to stop early\n")
    
    try:
        agent.run(max_tasks=2)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()