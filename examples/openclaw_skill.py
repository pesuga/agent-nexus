#!/usr/bin/env python3
"""
OpenClaw Skill Example
Example skill for OpenClaw agents to interact with the Agent Task Manager.
"""

import subprocess
import json
from typing import Dict, Any, Optional

class TaskManagerSkill:
    """
    OpenClaw skill for Agent Task Manager.
    
    This skill allows OpenClaw agents to:
    - List tasks
    - Create tasks
    - Update task status
    - Send heartbeats
    - Get task details
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the skill.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.cli_path = self.config.get("cli_path", "task")
        
        # Test CLI availability
        self._test_cli()
    
    def _test_cli(self):
        """Test if CLI is available"""
        try:
            subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                check=True
            )
            print(f"✅ CLI tool available at: {self.cli_path}")
        except:
            print(f"⚠️ CLI tool not found at: {self.cli_path}")
            print("Using python3 cli/task_cli.py as fallback")
            self.cli_path = "python3 cli/task_cli.py"
    
    def run_cli(self, args: list, json_output: bool = False) -> Any:
        """
        Run CLI command.
        
        Args:
            args: List of CLI arguments
            json_output: Whether to parse output as JSON
            
        Returns:
            Command output as string or parsed JSON
        """
        cmd = [self.cli_path] + args
        
        if json_output:
            cmd.append("--json")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if json_output:
                return json.loads(result.stdout)
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            print(f"CLI command failed: {e}")
            print(f"Stderr: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None
    
    def handle_command(self, command: str, args: list) -> str:
        """
        Handle a skill command.
        
        Args:
            command: Command name
            args: Command arguments
            
        Returns:
            Response string
        """
        handlers = {
            "list": self.handle_list,
            "create": self.handle_create,
            "show": self.handle_show,
            "update": self.handle_update,
            "move": self.handle_move,
            "assign": self.handle_assign,
            "heartbeat": self.handle_heartbeat,
            "health": self.handle_health,
            "help": self.handle_help,
        }
        
        handler = handlers.get(command)
        if not handler:
            return f"Unknown command: {command}. Use 'help' for available commands."
        
        return handler(args)
    
    def handle_list(self, args: list) -> str:
        """Handle list command"""
        cli_args = ["list"]
        
        # Parse filters
        filters = {}
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ["--project", "-p"]:
                filters["project"] = args[i + 1]
                cli_args.extend(["--project", args[i + 1]])
                i += 2
            elif arg in ["--status", "-s"]:
                filters["status"] = args[i + 1]
                cli_args.extend(["--status", args[i + 1]])
                i += 2
            elif arg in ["--assignee", "-a"]:
                filters["assignee"] = args[i + 1]
                cli_args.extend(["--assignee", args[i + 1]])
                i += 2
            elif arg == "--limit":
                cli_args.extend(["--limit", args[i + 1]])
                i += 2
            else:
                i += 1
        
        tasks = self.run_cli(cli_args, json_output=True)
        
        if not tasks:
            return "No tasks found or error occurred."
        
        response = f"Found {len(tasks)} tasks:\n\n"
        
        for task in tasks[:10]:  # Limit to 10 for readability
            status_emoji = {
                "backlog": "📦",
                "todo": "📝",
                "planning": "🧠",
                "hitl_review": "👥",
                "wip": "🔧",
                "implemented": "✅",
                "done": "🎉",
                "blocked": "🚧",
                "cancelled": "❌"
            }.get(task['status'], "❓")
            
            priority_emoji = {
                0: "🔹",
                1: "🔸",
                2: "🔺"
            }.get(task['priority'], "▪️")
            
            assignee = task['assignee'] or "Unassigned"
            
            response += f"{status_emoji} {priority_emoji} **{task['title']}**\n"
            response += f"   ID: {task['id'][:8]}... | Status: {task['status']}\n"
            response += f"   Assignee: {assignee} | Priority: {task['priority']}\n"
            
            if task.get('description'):
                desc = task['description']
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                response += f"   Description: {desc}\n"
            
            response += "\n"
        
        if len(tasks) > 10:
            response += f"... and {len(tasks) - 10} more tasks\n"
        
        return response
    
    def handle_create(self, args: list) -> str:
        """Handle create command"""
        if not args:
            return "Usage: create \"Title\" [--desc \"Description\"] [--project PROJECT] [--priority 0|1|2]"
        
        # Parse title (first non-flag argument)
        title = None
        cli_args = ["create"]
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ["--desc", "--description", "-d"]:
                cli_args.extend(["--desc", args[i + 1]])
                i += 2
            elif arg in ["--project", "-p"]:
                cli_args.extend(["--project", args[i + 1]])
                i += 2
            elif arg in ["--priority", "-P"]:
                cli_args.extend(["--priority", args[i + 1]])
                i += 2
            elif arg in ["--parent", "--parent-id"]:
                cli_args.extend(["--parent", args[i + 1]])
                i += 2
            elif not arg.startswith("-") and title is None:
                title = arg
                cli_args.append(title)
                i += 1
            else:
                i += 1
        
        if not title:
            return "Error: Task title is required."
        
        task = self.run_cli(cli_args, json_output=True)
        
        if not task:
            return "Failed to create task."
        
        return f"✅ Task created successfully!\n\n" \
               f"**Title**: {task['title']}\n" \
               f"**ID**: {task['id']}\n" \
               f"**Status**: {task['status']}\n" \
               f"**Project**: {task['project_id']}\n" \
               f"**Priority**: {task['priority']}"
    
    def handle_show(self, args: list) -> str:
        """Handle show command"""
        if not args:
            return "Usage: show TASK_ID"
        
        task_id = args[0]
        task = self.run_cli(["show", task_id], json_output=True)
        
        if not task:
            return f"Task {task_id} not found."
        
        status_emoji = {
            "backlog": "📦",
            "todo": "📝",
            "planning": "🧠",
            "hitl_review": "👥",
            "wip": "🔧",
            "implemented": "✅",
            "done": "🎉",
            "blocked": "🚧",
            "cancelled": "❌"
        }.get(task['status'], "❓")
        
        priority_text = {0: "Low", 1: "Medium", 2: "High"}.get(task['priority'], "Unknown")
        
        response = f"{status_emoji} **{task['title']}**\n\n"
        response += f"**ID**: {task['id']}\n"
        response += f"**Status**: {task['status']}\n"
        response += f"**Project**: {task['project_id']}\n"
        response += f"**Assignee**: {task['assignee'] or 'Unassigned'}\n"
        response += f"**Priority**: {priority_text} ({task['priority']})\n"
        response += f"**Created**: {task['created_at']}\n"
        response += f"**Updated**: {task['updated_at']}\n\n"
        
        if task.get('description'):
            response += f"**Description**:\n{task['description']}\n"
        
        return response
    
    def handle_update(self, args: list) -> str:
        """Handle update command"""
        if len(args) < 2:
            return "Usage: update TASK_ID [--title \"New Title\"] [--desc \"New Description\"] [--status STATUS] [--assignee AGENT_ID] [--priority 0|1|2]"
        
        task_id = args[0]
        cli_args = ["update", task_id]
        
        i = 1
        while i < len(args):
            arg = args[i]
            if arg in ["--title", "-t"]:
                cli_args.extend(["--title", args[i + 1]])
                i += 2
            elif arg in ["--desc", "--description", "-d"]:
                cli_args.extend(["--desc", args[i + 1]])
                i += 2
            elif arg in ["--status", "-s"]:
                cli_args.extend(["--status", args[i + 1]])
                i += 2
            elif arg in ["--assignee", "-a"]:
                cli_args.extend(["--assignee", args[i + 1]])
                i += 2
            elif arg in ["--priority", "-P"]:
                cli_args.extend(["--priority", args[i + 1]])
                i += 2
            else:
                i += 1
        
        task = self.run_cli(cli_args, json_output=True)
        
        if not task:
            return "Failed to update task."
        
        return f"✅ Task updated successfully!\n\n" \
               f"**Title**: {task['title']}\n" \
               f"**Status**: {task['status']}\n" \
               f"**Assignee**: {task['assignee'] or 'Unassigned'}\n" \
               f"**Updated**: {task['updated_at']}"
    
    def handle_move(self, args: list) -> str:
        """Handle move command"""
        if len(args) < 2:
            return "Usage: move TASK_ID STATUS"
        
        task_id = args[0]
        status = args[1]
        
        cli_args = ["move", task_id, status]
        task = self.run_cli(cli_args, json_output=True)
        
        if not task:
            return "Failed to move task."
        
        return f"✅ Task moved to {status}!"
    
    def handle_assign(self, args: list) -> str:
        """Handle assign command"""
        if len(args) < 2:
            return "Usage: assign TASK_ID AGENT_ID"
        
        task_id = args[0]
        agent_id = args[1]
        
        cli_args = ["assign", task_id, agent_id]
        task = self.run_cli(cli_args, json_output=True)
        
        if not task:
            return "Failed to assign task."
        
        return f"✅ Task assigned to {agent_id}!"
    
    def handle_heartbeat(self, args: list) -> str:
        """Handle heartbeat command"""
        cli_args = ["heartbeat"]
        
        agent_id = None
        task_id = None
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ["--agent", "-a"]:
                agent_id = args[i + 1]
                cli_args.extend(["--agent", agent_id])
                i += 2
            elif arg in ["--task", "-t"]:
                task_id = args[i + 1]
                cli_args.extend(["--task", task_id])
                i += 2
            else:
                i += 1
        
        result = self.run_cli(cli_args)
        
        if result and "heartbeat_received" in result.lower():
            if task_id and agent_id:
                return f"✅ Heartbeat sent for task {task_id} by {agent_id}"
            elif agent_id:
                return f"✅ Heartbeat sent by {agent_id}"
            else:
                return "✅ Heartbeat sent"
        else:
            return "Failed to send heartbeat."
    
    def handle_health(self, args: list) -> str:
        """Handle health command"""
        result = self.run_cli(["health"], json_output=True)
        
        if not result:
            return "❌ Health check failed"
        
        return f"✅ System is healthy\n" \
               f"Status: {result.get('status', 'unknown')}\n" \
               f"Timestamp: {result.get('timestamp', 'unknown')}"
    
    def handle_help(self, args: list) -> str:
        """Handle help command"""
        return """
**Agent Task Manager Skill - Available Commands:**

**Task Management:**
- `list [--project PROJECT] [--status STATUS] [--assignee AGENT]` - List tasks
- `create "Title" [--desc "Description"] [--project PROJECT] [--priority 0|1|2]` - Create task
- `show TASK_ID` - Show task details
- `update TASK_ID [--title "New Title"] [--desc "New Desc"] [--status STATUS] [--assignee AGENT]` - Update task
- `move TASK_ID STATUS` - Move task to new status
- `assign TASK_ID AGENT_ID` - Assign task to agent

**Agent Operations:**
- `heartbeat [--agent AGENT_ID] [--task TASK_ID]` - Send heartbeat

**System:**
- `health` - Check system health
- `help` - Show this help message

**Examples:**
- `list --status todo` - List all todo tasks
- `create "Fix bug" --desc "Important bug fix" --priority 2`
- `update task-001 --status wip --assignee ren-grunt`
- `heartbeat --agent ren-grunt --task task-001`
"""

# Example usage with OpenClaw
def create_openclaw_skill():
    """
    Create an OpenClaw skill instance.
    
    Usage in OpenClaw:
    1. Save this file as a skill
    2. Register it in OpenClaw
    3. Agents can use: `task list`, `task create`, etc.
    """
    skill = TaskManagerSkill()
    
    # Example: Register command handlers
    # In OpenClaw, this would be done via skill registration
    return skill

def example_usage():
    """Example standalone usage"""
    print("Task Manager Skill - Example Usage")
    print("="*60)
    
    skill = TaskManagerSkill()
    
    # Test health
    print("1. Testing health check:")
    print(skill.handle_health([]))
    print()
    
    # List tasks
    print("2. Listing tasks:")
    print(skill.handle_list([]))
    print()
    
    # Create task
    print("3. Creating example task:")
    print(skill.handle_create([
        "Test from OpenClaw Skill",
        "--desc", "Created by example skill",
        "--priority", "1"
    ]))
    print()
    
    # Show help
    print("4. Showing help:")
    print(skill.handle_help([]))

if __name__ == "__main__":
    example_usage()