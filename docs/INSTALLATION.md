# Installation Guide

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Node.js**: 14+ (optional, for development)
- **SQLite**: Built-in with Python
- **Web Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

### Hardware Requirements
- **RAM**: 512MB minimum, 1GB recommended
- **Storage**: 100MB free space
- **Network**: Localhost access only (no internet required)

## 🚀 Quick Installation

### Option 1: One-Line Setup (Recommended)
```bash
# Clone or navigate to agent-task-manager directory
cd agent-task-manager
python3 setup.py
```

### Option 2: Manual Setup
```bash
# 1. Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup frontend (no build needed)
cd ../frontend
# Frontend is ready to use

# 3. Setup CLI
cd ../cli
chmod +x task_cli.py
```

## 🔧 Detailed Installation

### Step 1: Clone or Create Project
```bash
# If you have the source code
cd agent-task-manager

# Or create from scratch
mkdir agent-task-manager
cd agent-task-manager
```

### Step 2: Backend Setup
```bash
# Create virtual environment
cd backend
python3 -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import fastapi; print('FastAPI version:', fastapi.__version__)"
```

### Step 3: Frontend Setup
```bash
cd frontend

# No build step needed - vanilla JavaScript
# Verify files exist
ls -la index.html app.js
```

### Step 4: CLI Setup
```bash
cd cli

# Make CLI executable
chmod +x task_cli.py

# Install CLI dependencies
pip install typer rich requests

# Test CLI
python3 task_cli.py --help
```

### Step 5: Database Initialization
```bash
cd backend

# Database will be created automatically on first run
# But you can initialize it manually:
python3 -c "
import sqlite3
conn = sqlite3.connect('agent_tasks.db')
print('Database created successfully')
conn.close()
"
```

## 🐳 Docker Installation (Optional)

### Build Docker Image
```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ .
COPY frontend/ ../frontend/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build image
docker build -t agent-task-manager .

# Run container
docker run -d -p 8000:8000 --name atm agent-task-manager
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./frontend:/frontend
    environment:
      - DATABASE_URL=sqlite:///app/agent_tasks.db
```

## 🖥️ Platform-Specific Instructions

### Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-venv python3-pip

# Follow general installation steps
```

### macOS
```bash
# Install Python via Homebrew
brew install python

# Or use system Python (usually 3.8+)
python3 --version

# Follow general installation steps
```

### Windows
```bash
# Install Python from python.org
# Make sure to check "Add Python to PATH"

# Open PowerShell or Command Prompt
python --version

# Follow general installation steps
# Use venv\Scripts\activate instead of source venv/bin/activate
```

## 🔍 Verification

### Verify Backend
```bash
cd backend
source venv/bin/activate
python3 main.py
# Should see: "Database initialized" and "Uvicorn running on http://0.0.0.0:8000"
```

### Verify Frontend
```bash
cd frontend
# Open index.html in browser
# Or serve with Python:
python3 -m http.server 8080
# Open http://localhost:8080
```

### Verify CLI
```bash
cd cli
python3 task_cli.py health
# Should see: "✓ API is healthy"
```

## ⚙️ Configuration

### Environment Variables
```bash
# Create .env file in backend directory
cat > backend/.env << 'EOF'
DATABASE_URL=sqlite:///agent_tasks.db
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here
EOF
```

### CLI Configuration
```bash
# Set default configuration
task config-set api_base_url http://localhost:8000
task config-set default_project default
task config-set agent_id ren-grunt
```

## 🧪 Test Installation

### Run Test Suite
```bash
cd backend
source venv/bin/activate
python3 -m pytest tests/ -v
```

### Manual Tests
```bash
# 1. Start backend
cd backend
python3 main.py

# 2. In another terminal, test API
curl http://localhost:8000/health
# Should return: {"status":"healthy","timestamp":"..."}

# 3. Test CLI
cd cli
python3 task_cli.py create "Test task" --desc "Installation test"
python3 task_cli.py list

# 4. Open frontend
open frontend/index.html  # Or open in browser
```

## 🔄 Updating

### Update from Source
```bash
# Pull latest changes
git pull origin main

# Re-run setup
python3 setup.py

# Or manually update dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Database Migrations
```bash
# Database schema updates automatically
# No manual migration needed
```

## ❓ Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'fastapi'"**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**"Address already in use"**
```bash
# Change port or kill existing process
pkill -f "python3 main.py"
# Or use different port:
python3 main.py --port 8001
```

**"Database is locked"**
```bash
# Only one instance should run at a time
pkill -f "python3 main.py"
# Restart
python3 main.py
```

**Frontend not connecting to backend**
```bash
# Check backend is running
curl http://localhost:8000/health

# Update frontend API URL in app.js
# Change const API_BASE = 'http://localhost:8000';
```

### Getting Help
1. Check logs in `backend/logs/`
2. Enable debug mode: `python3 main.py --debug`
3. Check browser console for frontend errors
4. Review [Troubleshooting Guide](../README.md#troubleshooting)

## 🎉 Next Steps

After successful installation:

1. **Start the system**:
   ```bash
   cd backend && python3 main.py
   ```

2. **Open the frontend**:
   ```bash
   cd frontend && open index.html
   ```

3. **Create your first task**:
   ```bash
   cd cli && python3 task_cli.py create "Welcome task" --desc "First task in the system"
   ```

4. **Explore features**:
   - Drag and drop tasks
   - Create projects
   - Assign tasks to agents
   - Watch real-time updates

## 📚 Additional Resources

- [API Documentation](API.md) - Complete API reference
- [CLI Guide](CLI.md) - Command-line interface reference
- [Agent Integration](AGENTS.md) - Guide for AI agent integration
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions