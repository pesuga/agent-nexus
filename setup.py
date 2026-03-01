#!/usr/bin/env python3
"""
Setup script for Agent Nexus
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and print output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Stderr: {result.stderr}")
    return result.returncode

def setup_backend():
    """Setup backend environment"""
    print("\n" + "="*60)
    print("Setting up Backend")
    print("="*60)
    
    backend_dir = Path("backend")
    
    # Create virtual environment
    venv_path = backend_dir / "venv"
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}")
        venv.create(venv_path, with_pip=True)
    
    # Install requirements
    pip_path = venv_path / "bin" / "pip"
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
    
    requirements = backend_dir / "requirements.txt"
    if requirements.exists():
        print("Installing Python dependencies...")
        run_command(f"{pip_path} install -r {requirements}")
    
    print("✓ Backend setup complete")

def setup_frontend():
    """Setup frontend"""
    print("\n" + "="*60)
    print("Setting up Frontend")
    print("="*60)
    
    frontend_dir = Path("frontend")
    
    # No build step needed for vanilla JS frontend
    print("Frontend is ready to use (vanilla JavaScript)")
    print("✓ Frontend setup complete")

def setup_cli():
    """Setup CLI tool"""
    print("\n" + "="*60)
    print("Setting up CLI")
    print("="*60)
    
    cli_dir = Path("cli")
    
    # Make CLI executable
    cli_script = cli_dir / "task_cli.py"
    if cli_script.exists():
        os.chmod(cli_script, 0o755)
        print(f"Made {cli_script} executable")
    
    # Create symlink or alias suggestion
    print("\nTo use the CLI globally, you can:")
    print(f"1. Add alias: alias task='python3 {cli_script.absolute()}'")
    print(f"2. Create symlink: ln -s {cli_script.absolute()} ~/.local/bin/task")
    print(f"3. Run directly: python3 {cli_script.absolute()} --help")
    
    print("✓ CLI setup complete")

def create_database():
    """Initialize the database"""
    print("\n" + "="*60)
    print("Initializing Database")
    print("="*60)
    
    # The database will be created automatically when the backend starts
    print("Database will be created automatically on first run")
    print("✓ Database initialization ready")

def create_example_data():
    """Create example data for testing"""
    print("\n" + "="*60)
    print("Creating Example Data")
    print("="*60)
    
    example_file = Path("database") / "example_data.sql"
    example_file.parent.mkdir(exist_ok=True)
    
    example_data = """
-- Example data for Agent Task Manager

-- Insert example projects
INSERT OR IGNORE INTO projects (id, name, description) VALUES
('default', 'Default Project', 'Main project for agent orchestration'),
('agent-os', 'Agent OS Development', 'Building the agent orchestration system'),
('client-a', 'Client A Project', 'Example client project');

-- Insert example tasks
INSERT OR IGNORE INTO tasks (id, project_id, title, description, status, priority) VALUES
('task-001', 'agent-os', 'Design database schema', 'Design the SQLite database schema for tasks, projects, and agents', 'done', 2),
('task-002', 'agent-os', 'Implement backend API', 'Create FastAPI endpoints for task management', 'wip', 2),
('task-003', 'agent-os', 'Build frontend UI', 'Create HTML/JS frontend with drag-and-drop', 'todo', 1),
('task-004', 'agent-os', 'Create CLI tool', 'Build command-line interface for task management', 'planning', 1),
('task-005', 'agent-os', 'Implement agent integration', 'Connect with OpenClaw agents', 'backlog', 0),
('task-006', 'client-a', 'Analyze requirements', 'Gather and analyze client requirements', 'todo', 2),
('task-007', 'client-a', 'Create project plan', 'Develop detailed project plan with milestones', 'backlog', 1);

-- Insert example agents
INSERT OR IGNORE INTO agents (id, name, type, status, capabilities) VALUES
('ren-grunt', 'Ren', 'grunt', 'idle', 'infrastructure,maintenance,cron'),
('aki-partner', 'Aki', 'partner', 'working', 'coordination,reporting,orchestration'),
('kuro-coder', 'Kuro', 'coder', 'idle', 'development,architecture,security'),
('shin-strategist', 'Shin', 'strategist', 'offline', 'planning,analysis,roadmapping'),
('sora-creative', 'Sora', 'creative', 'idle', 'brainstorming,innovation,design');
"""
    
    with open(example_file, 'w') as f:
        f.write(example_data)
    
    print(f"Example data created at {example_file}")
    print("✓ Example data created")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("Next Steps")
    print("="*60)
    
    print("\n1. Start the backend server:")
    print("   cd backend")
    print("   python3 main.py")
    print("   # Or with uvicorn: uvicorn main:app --reload --port 8000")
    
    print("\n2. Open the frontend in your browser:")
    print("   Open frontend/index.html in your browser")
    print("   # Or serve with Python: python3 -m http.server 8080")
    
    print("\n3. Use the CLI tool:")
    print("   cd cli")
    print("   python3 task_cli.py --help")
    print("   # Example: python3 task_cli.py list")
    
    print("\n4. Test the system:")
    print("   - Create tasks via web interface or CLI")
    print("   - Move tasks between statuses (drag & drop)")
    print("   - Watch real-time updates")
    
    print("\n5. Integrate with OpenClaw:")
    print("   - Agents can use the CLI via OpenClaw skills")
    print("   - Implement heartbeat for crash recovery")
    print("   - Add semantic knowledge base integration")

def main():
    """Main setup function"""
    print("Agent Task Manager - Setup")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run setup steps
    setup_backend()
    setup_frontend()
    setup_cli()
    create_database()
    create_example_data()
    
    print_next_steps()
    
    print("\n" + "="*60)
    print("Setup Complete! 🎉")
    print("="*60)

if __name__ == "__main__":
    main()