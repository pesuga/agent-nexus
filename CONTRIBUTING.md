# Contributing to Agent Task Manager

First off, thank you for considering contributing to Agent Task Manager! 🎯

This document provides guidelines and instructions for contributing to the project. Please read it carefully before submitting issues or pull requests.

## 🎯 Project Goals

Agent Task Manager aims to be:

1. **Simple** - Easy to understand, install, and use
2. **Self-contained** - Minimal external dependencies
3. **Agent-focused** - Designed for AI agent orchestration
4. **Reliable** - Crash recovery and real-time updates
5. **Extensible** - Easy to add new features and integrations

## 📋 How Can I Contribute?

### Reporting Bugs
Before reporting a bug:
1. Check if the bug has already been reported in [GitHub Issues](https://github.com/your-org/agent-task-manager/issues)
2. Update to the latest version to see if the bug has been fixed
3. Collect relevant information (logs, screenshots, steps to reproduce)

**Bug Report Template:**
```markdown
**Description**
A clear and concise description of what the bug is.

**Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11.0]
- Browser: [e.g., Chrome 120]
- Backend Version: [e.g., 1.0.0]

**Additional Context**
Screenshots, logs, or any other relevant information.
```

### Suggesting Enhancements
We welcome feature suggestions! Please:
1. Check if the feature has already been suggested
2. Explain why this feature would be useful
3. Provide implementation details if possible

**Enhancement Template:**
```markdown
**Problem**
What problem does this solve?

**Solution**
Describe your proposed solution.

**Alternatives Considered**
Other ways to solve the problem.

**Additional Context**
Screenshots, mockups, or related issues.
```

### Code Contributions
#### Development Workflow
1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/your-username/agent-task-manager.git
   cd agent-task-manager
   ```
3. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```
4. **Make changes** following the coding standards
5. **Test your changes**
6. **Commit** with descriptive messages:
   ```bash
   git commit -m "Add feature: your feature description"
   ```
7. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request**

#### Pull Request Guidelines
- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation as needed
- Follow the PR template
- Ensure all tests pass

## 🛠️ Development Setup

### Prerequisites
- Python 3.8+
- Git
- SQLite 3.35+

### Local Setup
```bash
# 1. Clone repository
git clone https://github.com/your-org/agent-task-manager.git
cd agent-task-manager

# 2. Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 3. Setup frontend (no build needed)

# 4. Setup CLI
cd ../cli
chmod +x task_cli.py

# 5. Run tests
cd ../tests
pytest -v
```

### Running the Application
```bash
# Start backend
cd backend
python3 main.py

# Open frontend
cd ../frontend
python3 -m http.server 8080

# Use CLI
cd ../cli
python3 task_cli.py --help
```

## 📝 Coding Standards

### Python Code
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints where possible
- Keep functions small and focused
- Write docstrings for public functions

**Example:**
```python
def create_task(
    title: str,
    description: str = "",
    project_id: str = "default",
    priority: int = 1
) -> Dict[str, Any]:
    """
    Create a new task in the system.
    
    Args:
        title: Task title (required)
        description: Task description
        project_id: Project identifier
        priority: Priority level (0=low, 1=medium, 2=high)
    
    Returns:
        Dictionary containing the created task data
    
    Raises:
        ValueError: If title is empty or priority invalid
    """
    if not title:
        raise ValueError("Title cannot be empty")
    
    # Implementation...
```

### JavaScript Code
- Use ES6+ features
- Keep functions pure where possible
- Add comments for complex logic
- Handle errors gracefully

**Example:**
```javascript
/**
 * Update task status via drag and drop
 * @param {string} taskId - Task identifier
 * @param {string} newStatus - New status value
 * @returns {Promise<Object>} Updated task data
 */
async function updateTaskStatus(taskId, newStatus) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Failed to update task status:', error);
        throw error;
    }
}
```

### Documentation
- Keep README.md up to date
- Add docstrings for all public APIs
- Update examples when features change
- Use clear, concise language

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=backend --cov-report=html

# Run frontend tests (if available)
npm test  # in frontend directory
```

### Writing Tests
- Write tests for new functionality
- Test edge cases and error conditions
- Mock external dependencies
- Keep tests fast and isolated

**Example Test:**
```python
def test_create_task_success():
    """Test successful task creation."""
    # Setup
    task_data = {
        "title": "Test Task",
        "description": "Test description",
        "project_id": "default",
        "priority": 1
    }
    
    # Execute
    response = client.post("/api/tasks", json=task_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["status"] == "backlog"
    assert data["assignee"] is None

def test_create_task_missing_title():
    """Test task creation with missing title."""
    task_data = {
        "description": "No title provided"
    }
    
    response = client.post("/api/tasks", json=task_data)
    assert response.status_code == 422  # Validation error
```

## 🚀 Release Process

### Versioning
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
1. [ ] Update version in `pyproject.toml` or `package.json`
2. [ ] Update CHANGELOG.md
3. [ ] Run all tests
4. [ ] Update documentation
5. [ ] Create release tag
6. [ ] Build and publish (if applicable)

## 📁 Project Structure

```
agent-task-manager/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main application
│   ├── requirements.txt    # Production dependencies
│   ├── requirements-dev.txt # Development dependencies
│   └── agent_tasks.db      # SQLite database (generated)
├── frontend/               # HTML/JS frontend
│   ├── index.html          # Main interface
│   ├── app.js              # Frontend logic
│   └── style.css           # CSS styles
├── cli/                    # Command-line interface
│   └── task_cli.py         # CLI tool
├── database/               # Database scripts
│   ├── schema.sql          # Database schema
│   └── migrations/         # Migration scripts
├── docs/                   # Documentation
│   ├── API.md              # API reference
│   ├── CLI.md              # CLI guide
│   └── ...                 # Other docs
├── examples/               # Example code
├── tests/                  # Test suite
├── .github/                # GitHub workflows
├── ARCHITECTURE.md         # Architecture documentation
├── CONTRIBUTING.md         # This file
├── LICENSE                 # License file
└── README.md               # Project README
```

## 🤔 Frequently Asked Questions

### Q: Can I use a different database?
A: Currently only SQLite is supported, but the architecture allows for other databases. Contributions welcome!

### Q: How do I add custom fields to tasks?
A: Modify the database schema in `backend/main.py` and update the API endpoints, frontend, and CLI accordingly.

### Q: Can I deploy this in production?
A: Yes! See [Deployment Guide](docs/DEPLOYMENT.md) for production-ready configurations.

### Q: How do I add support for new AI agents?
A: Update the agent configuration in `docs/AGENTS.md` and add any agent-specific logic.

## 🆘 Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and discussions
- **Documentation**: Check the [docs directory](docs/)

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

---

Thank you for contributing to Agent Task Manager! Your efforts help make AI agent orchestration better for everyone. 🎯