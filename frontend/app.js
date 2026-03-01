// Complete the JavaScript functionality

// Create task
async function createTask(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    
    const taskData = {
        title: formData.get('title'),
        description: formData.get('description'),
        project_id: formData.get('project_id') || currentProject,
        priority: parseInt(formData.get('priority'))
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(taskData)
        });
        
        if (response.ok) {
            resetForm();
            loadTasks(); // Will be updated via SSE
            showNotification('Task created successfully!', 'success');
        } else {
            throw new Error('Failed to create task');
        }
    } catch (error) {
        console.error('Error creating task:', error);
        showNotification('Failed to create task', 'error');
    }
}

function resetForm() {
    document.getElementById('createTaskForm').reset();
    document.getElementById('taskTitle').focus();
}

// Drag and drop setup
function setupDragAndDrop() {
    // Prevent default drag behaviors
    document.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
    
    document.addEventListener('drop', (e) => {
        e.preventDefault();
    });
}

function attachDragEvents() {
    const taskCards = document.querySelectorAll('.task-card');
    
    taskCards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });
    
    const columns = document.querySelectorAll('.task-list');
    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
    });
}

let draggedTask = null;

function handleDragStart(e) {
    draggedTask = e.target;
    draggedTask.classList.add('dragging');
    e.dataTransfer.setData('text/plain', draggedTask.dataset.taskId);
}

function handleDragEnd(e) {
    draggedTask.classList.remove('dragging');
    draggedTask = null;
}

function handleDragOver(e) {
    e.preventDefault();
    const column = e.target.closest('.task-list');
    if (column) {
        column.style.backgroundColor = '#f0f8ff';
    }
}

async function handleDrop(e) {
    e.preventDefault();
    const column = e.target.closest('.task-list');
    if (!column) return;
    
    column.style.backgroundColor = '';
    
    const taskId = e.dataTransfer.getData('text/plain');
    const newStatus = column.id.replace('task-list-', '');
    
    try {
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error('Failed to update task status');
        }
        
        // Task will be updated via SSE
        showNotification(`Task moved to ${statusColumns.find(s => s.id === newStatus)?.title || newStatus}`, 'success');
    } catch (error) {
        console.error('Error updating task:', error);
        showNotification('Failed to update task status', 'error');
        loadTasks(); // Force reload on error
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Remove existing notification
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Load agents (placeholder - will be implemented when agent API is ready)
async function loadAgents() {
    try {
        // This will be implemented when we have agent endpoints
        agents = [
            { id: 'ren-grunt', name: 'Ren', type: 'grunt', status: 'idle', last_heartbeat: new Date().toISOString() },
            { id: 'aki-partner', name: 'Aki', type: 'partner', status: 'working', last_heartbeat: new Date().toISOString() },
            { id: 'kuro-coder', name: 'Kuro', type: 'coder', status: 'idle', last_heartbeat: new Date().toISOString() },
            { id: 'shin-strategist', name: 'Shin', type: 'strategist', status: 'offline', last_heartbeat: null },
            { id: 'sora-creative', name: 'Sora', type: 'creative', status: 'idle', last_heartbeat: new Date().toISOString() }
        ];
        renderAgents();
    } catch (error) {
        console.error('Error loading agents:', error);
    }
}

function renderAgents() {
    const grid = document.getElementById('agentsGrid');
    grid.innerHTML = '';
    
    agents.forEach(agent => {
        const statusClass = `status-${agent.status}`;
        const statusText = agent.status.charAt(0).toUpperCase() + agent.status.slice(1);
        
        const card = document.createElement('div');
        card.className = 'agent-card';
        card.innerHTML = `
            <div class="agent-name">${agent.name}</div>
            <div class="agent-status ${statusClass}">${statusText}</div>
            <div class="agent-type" style="font-size: 12px; color: #666; margin-bottom: 5px;">${agent.type}</div>
            <div class="agent-task" style="font-size: 11px; color: #888;">
                ${agent.last_heartbeat ? `Last active: ${formatTime(agent.last_heartbeat)}` : 'Never active'}
            </div>
        `;
        grid.appendChild(card);
    });
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

// Initialize agents panel
loadAgents();
setInterval(loadAgents, 30000); // Refresh agents every 30 seconds

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + N to focus new task form
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        document.getElementById('taskTitle').focus();
    }
    
    // Escape to clear form
    if (e.key === 'Escape') {
        resetForm();
    }
});

// Add help tooltip
const helpButton = document.createElement('button');
helpButton.textContent = '?';
helpButton.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #3498db;
    color: white;
    border: none;
    font-size: 18px;
    cursor: pointer;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    z-index: 100;
`;
helpButton.onclick = () => {
    showNotification('Shortcuts: Ctrl+N (new task), Esc (clear form), Drag & Drop (move tasks)', 'info');
};
document.body.appendChild(helpButton);