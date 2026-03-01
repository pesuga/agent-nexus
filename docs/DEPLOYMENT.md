# Deployment Guide

## 📋 Overview

This guide covers deployment options for the Agent Task Manager, from local development to production environments.

## 🏠 Local Development

### Quick Start
```bash
# 1. Clone or create project
cd agent-task-manager

# 2. Run setup
python3 setup.py

# 3. Start backend
cd backend && python3 main.py

# 4. Open frontend
cd ../frontend && open index.html
```

### Development Configuration
```bash
# Create development environment file
cat > backend/.env.dev << 'EOF'
DATABASE_URL=sqlite:///agent_tasks.db
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
LOG_LEVEL=DEBUG
EOF

# Run with environment
export $(cat backend/.env.dev | xargs)
python3 backend/main.py
```

## 🐳 Docker Deployment

### Docker Compose (Recommended)
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
      - agent_data:/data
    environment:
      - DATABASE_URL=sqlite:///data/agent_tasks.db
      - API_HOST=0.0.0.0
      - API_PORT=8000
    restart: unless-stopped
  
  frontend:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./frontend:/usr/share/nginx/html
    depends_on:
      - backend

volumes:
  agent_data:
```

### Build and Run
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /data

# Create non-root user
RUN useradd -m -u 1000 agent && chown -R agent:agent /app /data
USER agent

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🐧 Linux Service Deployment

### Systemd Service
```ini
# /etc/systemd/system/agent-task-manager.service
[Unit]
Description=Agent Task Manager Backend
After=network.target
Wants=network.target

[Service]
Type=simple
User=pesu
Group=pesu
WorkingDirectory=/opt/agent-task-manager/backend
Environment="PATH=/opt/agent-task-manager/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DATABASE_URL=sqlite:////opt/agent-task-manager/data/agent_tasks.db"
ExecStart=/opt/agent-task-manager/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=agent-task-manager

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/agent-task-manager/data

[Install]
WantedBy=multi-user.target
```

### Installation Script
```bash
#!/bin/bash
# install-systemd.sh

set -e

echo "Installing Agent Task Manager as systemd service..."

# Create directories
sudo mkdir -p /opt/agent-task-manager/{backend,frontend,data,logs}
sudo chown -R pesu:pesu /opt/agent-task-manager

# Copy files
cp -r backend/* /opt/agent-task-manager/backend/
cp -r frontend/* /opt/agent-task-manager/frontend/

# Setup virtual environment
cd /opt/agent-task-manager/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install systemd service
sudo cp agent-task-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable agent-task-manager
sudo systemctl start agent-task-manager

echo "✅ Installation complete!"
echo "Check status: sudo systemctl status agent-task-manager"
echo "View logs: sudo journalctl -u agent-task-manager -f"
```

## ☁️ Cloud Deployment

### AWS EC2
```bash
# Launch EC2 instance
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t2.micro \
    --key-name my-key-pair \
    --security-group-ids sg-123456 \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=agent-task-manager}]'

# Install on EC2
ssh -i my-key.pem ec2-user@ec2-instance
sudo yum update -y
sudo yum install -y python3 python3-pip git
git clone https://github.com/your-org/agent-task-manager.git
cd agent-task-manager
python3 setup.py
```

### Google Cloud Run
```yaml
# cloudbuild.yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/agent-task-manager', '.']
  
  # Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/agent-task-manager']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'agent-task-manager'
      - '--image'
      - 'gcr.io/$PROJECT_ID/agent-task-manager'
      - '--platform'
      - 'managed'
      - '--region'
      - 'us-central1'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/agent-task-manager'
```

## 🔒 Security Configuration

### Production Environment
```bash
# .env.production
DATABASE_URL=sqlite:///data/agent_tasks.db
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secure-secret-key-here
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com
RATE_LIMIT=100/hour
```

### SSL/TLS Configuration
```python
# SSL configuration for production
import ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('/path/to/cert.pem', '/path/to/key.pem')

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    ssl=ssl_context
)
```

### Authentication Middleware
```python
# Add authentication for production
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token != os.getenv("API_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return token

@app.get("/api/tasks", dependencies=[Depends(verify_token)])
async def get_tasks():
    # Your endpoint logic
```

## 📊 Monitoring & Logging

### Log Configuration
```python
# logging_config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                'logs/agent_task_manager.log',
                maxBytes=10485760,  # 10MB
                backupCount=10
            ),
            logging.StreamHandler()
        ]
    )
```

### Health Monitoring
```bash
# Health check script
#!/bin/bash
# health-check.sh

API_URL="http://localhost:8000/health"
MAX_RETRIES=3
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
    response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)
    
    if [ "$response" = "200" ]; then
        echo "✅ Service is healthy"
        exit 0
    fi
    
    echo "⚠️ Attempt $i failed (HTTP $response)"
    
    if [ $i -lt $MAX_RETRIES ]; then
        sleep $RETRY_DELAY
    fi
done

echo "❌ Service is unhealthy after $MAX_RETRIES attempts"
exit 1
```

### Metrics Collection
```python
# metrics.py
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['endpoint'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(endpoint=request.url.path).observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🔄 Database Management

### Backup Strategy
```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/backups/agent-task-manager"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/agent_tasks_$DATE.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sqlite3 /data/agent_tasks.db ".backup '$BACKUP_FILE'"

# Compress backup
gzip $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.db.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### Migration Script
```python
# migrations/migrate_v1_to_v2.py
import sqlite3
import sys

def migrate_v1_to_v2(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add new columns
    cursor.execute("ALTER TABLE tasks ADD COLUMN tags TEXT")
    cursor.execute("ALTER TABLE tasks ADD COLUMN due_date TIMESTAMP")
    
    # Create new table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            author TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Migration completed successfully")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_v1_to_v2.py /path/to/database.db")
        sys.exit(1)
    
    migrate_v1_to_v2(sys.argv[1])
```

## 🔧 Performance Tuning

### Database Optimization
```sql
-- Optimize SQLite database
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -2000; -- 2MB cache
PRAGMA temp_store = MEMORY;
```

### Connection Pooling
```python
# Use connection pooling for production
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

### Caching Layer
```python
# Add Redis caching
import redis
from functools import lru_cache

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_tasks_cached(project_id=None, status=None):
    cache_key = f"tasks:{project_id}:{status}"
    
    # Try cache first
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Get from database
    tasks = get_tasks_from_db(project_id, status)
    
    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(tasks))
    
    return tasks
```

## 🚀 Scaling Strategies

### Horizontal Scaling
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-task-manager
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-task-manager
  template:
    metadata:
      labels:
        app: agent-task-manager
    spec:
      containers:
      - name: backend
        image: your-registry/agent-task-manager:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://user:password@postgres:5432/agent_tasks"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: agent-task-manager
spec:
  selector:
    app: agent-task-manager
  ports:
  - port: 80
    targetPort: 8000
```

### Load Balancer Configuration
```nginx
# nginx.conf
upstream agent_task_manager {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 80;
    server_name task-manager.your-domain.com;
    
    location / {
        proxy_pass http://agent_task_manager;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    location /health {
        access_log off;
        proxy_pass http://agent_task_manager/health;
    }
}
```

## 📦 Package Distribution

### PyPI Package
```python
# setup.py for PyPI
from setuptools import setup, find_packages

setup(
    name="agent-task-manager",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "sqlite3>=3.35.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "task=cli.task_cli:app",
        ],
    },
    python_requires=">=3.8",
)
```

### Build Script
```bash
#!/bin/bash
# build-release.sh

set -e

VERSION=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")

echo "Building version $VERSION..."

# Build frontend
cd frontend
npm run build

# Build backend
cd ../backend
python3 -m build

# Create release archive
cd ..
tar -czf "agent-task-manager-$VERSION.tar.gz" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude=".env" \
    --exclude="node_modules" \
    .

echo "✅ Release built: agent-task-manager-$VERSION.tar.gz"
```

## 🧪 Testing Deployment

### Deployment Test Script
```bash
#!/bin/bash
# test-deployment.sh

set -e

echo "Testing deployment..."
echo "===================="

# Test 1: Service is running
echo "1. Testing service health..."
curl -f http://localhost:8000/health || {
    echo "❌ Service health check failed"
    exit 1
}

# Test 2: Database is accessible
echo "2. Testing database..."
curl -f http://localhost:8000/api/projects || {
    echo "❌ Database access failed"
    exit 1
}

# Test 3