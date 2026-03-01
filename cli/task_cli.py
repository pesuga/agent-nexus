#!/usr/bin/env python3
"""
Agent Task Manager CLI
Command-line interface for managing tasks and interacting with agents
"""

import json
import sys
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

import typer
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint

# Configuration
API_BASE_URL = "http://localhost:8000"
CONFIG_FILE = os.path.expanduser("~/.agent_task_manager.json")

app = typer.Typer(
    name="task",
    help="Agent Task Manager CLI - Manage tasks and coordinate AI agents",
    add_completion=False,
)

console = Console()

# Status enum for validation
class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    PLANNING = "planning"
    HITL_REVIEW = "hitl_review"
    WIP = "wip"
    IMPLEMENTED = "implemented"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "api_base_url": API_BASE_URL,
        "default_project": "default",
        "agent_id": None
    }

def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def api_request(method: str, endpoint: str, **kwargs) -> Optional[Dict]:
    """Make API request with error handling"""
    config = load_config()
    url = f"{config['api_base_url']}{endpoint}"
    
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None
    except requests.exceptions.ConnectionError:
        console.print("[red]Error:[/red] Cannot connect to API server. Is it running?")
        console.print(f"[yellow]URL:[/yellow] {url}")
        return None
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]HTTP Error {e.response.status_code}:[/red] {e.response.text}")
        return None
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return None

@app.command()
def create(
    title: str = typer.Argument(..., help="Task title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    priority: int = typer.Option(1, "--priority", "-P", help="Priority (0=low, 1=medium, 2=high)"),
    parent: Optional[str] = typer.Option(None, "--parent", help="Parent task ID"),
):
    """Create a new task"""
    config = load_config()
    
    task_data = {
        "title": title,
        "description": description,
        "project_id": project or config.get("default_project", "default"),
        "priority": priority,
        "parent_id": parent
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Creating task...", total=None)
        result = api_request("POST", "/api/tasks", json=task_data)
    
    if result:
        console.print(Panel(
            f"[green]✓ Task created successfully![/green]\n\n"
            f"[bold]ID:[/bold] {result['id']}\n"
            f"[bold]Title:[/bold] {result['title']}\n"
            f"[bold]Status:[/bold] {result['status']}\n"
            f"[bold]Project:[/bold] {result['project_id']}",
            title="Task Created",
            border_style="green"
        ))
    else:
        console.print("[red]Failed to create task[/red]")

@app.command()
def list(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    status: Optional[TaskStatus] = typer.Option(None, "--status", "-s", help="Filter by status"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Filter by assignee"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of tasks to show"),
):
    """List tasks with filters"""
    params = {}
    if project:
        params["project_id"] = project
    if status:
        params["status"] = status.value
    if assignee:
        params["assignee"] = assignee
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Loading tasks...", total=None)
        tasks = api_request("GET", "/api/tasks", params=params)
    
    if tasks is None:
        return
    
    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return
    
    # Create table
    table = Table(title=f"Tasks ({len(tasks)})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Assignee", style="blue")
    table.add_column("Priority", style="yellow")
    table.add_column("Updated", style="dim")
    
    for task in tasks[:limit]:
        # Shorten ID for display
        short_id = task['id'][:8]
        
        # Format priority
        priority_map = {0: "Low", 1: "Medium", 2: "High"}
        priority = priority_map.get(task['priority'], "Unknown")
        
        # Format timestamp
        updated = datetime.fromisoformat(task['updated_at'].replace('Z', '+00:00'))
        time_ago = datetime.now() - updated
        if time_ago.days > 0:
            time_str = f"{time_ago.days}d"
        elif time_ago.seconds > 3600:
            time_str = f"{time_ago.seconds // 3600}h"
        else:
            time_str = f"{time_ago.seconds // 60}m"
        
        table.add_row(
            short_id,
            task['title'][:40] + ("..." if len(task['title']) > 40 else ""),
            task['status'],
            task['assignee'] or "-",
            priority,
            time_str
        )
    
    console.print(table)
    
    if len(tasks) > limit:
        console.print(f"[dim]Showing {limit} of {len(tasks)} tasks. Use --limit to show more.[/dim]")

@app.command()
def show(
    task_id: str = typer.Argument(..., help="Task ID"),
):
    """Show detailed information about a task"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Loading task details...", total=None)
        task = api_request("GET", f"/api/tasks/{task_id}")
    
    if not task:
        console.print(f"[red]Task not found: {task_id}[/red]")
        return
    
    # Get task history
    # Note: This endpoint doesn't exist yet, but we can add it later
    # history = api_request("GET", f"/api/tasks/{task_id}/history")
    
    console.print(Panel(
        f"[bold]Title:[/bold] {task['title']}\n"
        f"[bold]ID:[/bold] {task['id']}\n"
        f"[bold]Status:[/bold] {task['status']}\n"
        f"[bold]Project:[/bold] {task['project_id']}\n"
        f"[bold]Assignee:[/bold] {task['assignee'] or 'Unassigned'}\n"
        f"[bold]Priority:[/bold] {task['priority']}\n"
        f"[bold]Created:[/bold] {task['created_at']}\n"
        f"[bold]Updated:[/bold] {task['updated_at']}\n\n"
        f"[bold]Description:[/bold]\n{task['description'] or 'No description'}",
        title="Task Details",
        border_style="blue"
    ))

@app.command()
def update(
    task_id: str = typer.Argument(..., help="Task ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    status: Optional[TaskStatus] = typer.Option(None, "--status", "-s", help="New status"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="New assignee"),
    priority: Optional[int] = typer.Option(None, "--priority", "-P", help="New priority (0-2)"),
):
    """Update a task"""
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if status is not None:
        update_data["status"] = status.value
    if assignee is not None:
        update_data["assignee"] = assignee
    if priority is not None:
        update_data["priority"] = priority
    
    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Updating task...", total=None)
        result = api_request("PUT", f"/api/tasks/{task_id}", json=update_data)
    
    if result:
        console.print(f"[green]✓ Task {task_id} updated successfully[/green]")
    else:
        console.print(f"[red]Failed to update task {task_id}[/red]")

@app.command()
def assign(
    task_id: str = typer.Argument(..., help="Task ID"),
    agent_id: str = typer.Argument(..., help="Agent ID to assign"),
):
    """Assign a task to an agent"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Assigning task...", total=None)
        result = api_request("PUT", f"/api/tasks/{task_id}", json={"assignee": agent_id})
    
    if result:
        console.print(f"[green]✓ Task {task_id} assigned to {agent_id}[/green]")
    else:
        console.print(f"[red]Failed to assign task {task_id}[/red]")

@app.command()
def move(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: TaskStatus = typer.Argument(..., help="New status"),
):
    """Move a task to a different status"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Moving task...", total=None)
        result = api_request("PUT", f"/api/tasks/{task_id}", json={"status": status.value})
    
    if result:
        console.print(f"[green]✓ Task {task_id} moved to {status.value}[/green]")
    else:
        console.print(f"[red]Failed to move task {task_id}[/red]")

@app.command()
def heartbeat(
    task_id: Optional[str] = typer.Option(None, "--task", "-t", help="Task ID (if working on a task)"),
    agent_id: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID"),
):
    """Send a heartbeat for an agent (used by agents to show they're alive)"""
    config = load_config()
    
    if not agent_id and not config.get("agent_id"):
        console.print("[red]Error: No agent ID specified. Use --agent or set default agent in config.[/red]")
        return
    
    heartbeat_data = {
        "agent_id": agent_id or config["agent_id"],
        "task_id": task_id
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Sending heartbeat...", total=None)
        result = api_request("POST", f"/api/tasks/{task_id}/heartbeat", json=heartbeat_data)
    
    if result:
        console.print(f"[green]✓ Heartbeat sent for agent {heartbeat_data['agent_id']}[/green]")
    else:
        console.print(f"[red]Failed to send heartbeat[/red]")

@app.command()
def projects():
    """List all projects"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Loading projects...", total=None)
        projects = api_request("GET", "/api/projects")
    
    if projects is None:
        return
    
    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return
    
    table = Table(title="Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Description", style="dim")
    table.add_column("Created", style="dim")
    
    for project in projects:
        created = datetime.fromisoformat(project['created_at'].replace('Z', '+00:00'))
        created_str = created.strftime("%Y-%m-%d")
        
        table.add_row(
            project['id'],
            project['name'],
            project['description'] or "-",
            created_str
        )
    
    console.print(table)

@app.command()
def config_show():
    """Show current configuration"""
    config = load_config()
    
    console.print(Panel(
        f"[bold]API Base URL:[/bold] {config.get('api_base_url', 'Not set')}\n"
        f"[bold]Default Project:[/bold] {config.get('default_project', 'Not set')}\n"
        f"[bold]Agent ID:[/bold] {config.get('agent_id', 'Not set')}",
        title="Configuration",
        border_style="yellow"
    ))

@app.command()
def config_set(
    key: str = typer.Argument(..., help="Config key to set"),
    value: str = typer.Argument(..., help="Value to set"),
):
    """Set a configuration value"""
    config = load_config()
    
    valid_keys = ["api_base_url", "default_project", "agent_id"]
    if key not in valid_keys:
        console.print(f"[red]Invalid config key. Valid keys: {', '.join(valid_keys)}[/red]")
        return
    
    config[key] = value
    save_config(config)
    
    console.print(f"[green]✓ Configuration updated: {key} = {value}[/green]")

@app.command()
def health():
    """Check API health"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Checking health...", total=None)
        result = api_request("GET", "/health")
    
    if result:
        console.print(Panel(
            f"[green]✓ API is healthy[/green]\n"
            f"[bold]Status:[/bold] {result.get('status', 'unknown')}\n"
            f"[bold]Timestamp:[/bold] {result.get('timestamp', 'unknown')}",
            title="Health Check",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[red]✗ API is not responding[/red]",
            title="Health Check",
            border_style="red"
        ))

@app.command()
def watch(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project to watch"),
    interval: int = typer.Option(5, "--interval", "-i", help="Update interval in seconds"),
):
    """Watch tasks in real-time (SSE)"""
    config = load_config()
    url = f"{config['api_base_url']}/api/events"
    
    console.print(f"[yellow]Connecting to {url}...[/yellow]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")
    
    try:
        import sseclient
        
        response = requests.get(url, stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.data:
                data = json.loads(event.data)
                if data.get('event') == 'state_change':
                    console.print(f"[cyan]{datetime.now().strftime('%H:%M:%S')}[/cyan] State changed, tasks updated")
                    # In a real implementation, we would fetch and display updated tasks
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching[/yellow]")
    except ImportError:
        console.print("[red]Error: sseclient-py not installed. Install with: pip install sseclient-py[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    app()