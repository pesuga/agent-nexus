// Agent Nexus Workflow Dashboard JS (stable build)

const UI_CONFIG_KEY = 'dispatch_ui_config_v1';
let API_BASE = 'http://localhost:8000';
let uiConfig = null;

let currentProject = 'default';
let agents = [];
let tasks = [];
let eventSource = null;
let draggedTask = null;
let kanbanFilters = { search: '', assignee: '', priority: '' };
let kanbanSort = 'updated_desc';
let sseState = 'disconnected';

function loadUiConfig() {
  const defaults = {
    apiBaseUrl: 'http://localhost:8000',
    actorRole: 'human_admin',
    actorId: 'frontend-ui',
    apiToken: '',
  };
  try {
    const parsed = JSON.parse(localStorage.getItem(UI_CONFIG_KEY) || '{}');
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

function saveUiConfig(next) {
  uiConfig = { ...uiConfig, ...next };
  API_BASE = uiConfig.apiBaseUrl || 'http://localhost:8000';
  localStorage.setItem(UI_CONFIG_KEY, JSON.stringify(uiConfig));
}

function getApiHeaders(extra = {}) {
  return {
    'Content-Type': 'application/json',
    'X-Actor-Role': uiConfig?.actorRole || '',
    'X-Actor-Id': uiConfig?.actorId || '',
    'X-API-Token': uiConfig?.apiToken || '',
    ...extra,
  };
}

async function apiFetch(path, options = {}) {
  const opts = { ...options };
  opts.headers = getApiHeaders(options.headers || {});
  return fetch(`${API_BASE}${path}`, opts);
}

function getTaskAssignee(task) {
  return task.assignee || task.assigned_to || null;
}

function getPriorityNum(task) {
  if (task.priority === undefined || task.priority === null) return 1;
  const n = Number(task.priority);
  if (Number.isNaN(n)) return 1;
  return n;
}

function getPriorityLabel(priorityNum) {
  if (priorityNum >= 2) return 'HIGH';
  if (priorityNum <= 0) return 'LOW';
  return 'MEDIUM';
}

function applyTaskFilters(input) {
  return input.filter((task) => {
    const hay = `${task.id || ''} ${task.title || ''} ${task.description || ''}`.toLowerCase();
    const assignee = getTaskAssignee(task) || '';
    const priority = String(getPriorityNum(task));

    if (kanbanFilters.search && !hay.includes(kanbanFilters.search)) return false;
    if (kanbanFilters.assignee && assignee !== kanbanFilters.assignee) return false;
    if (kanbanFilters.priority && priority !== kanbanFilters.priority) return false;
    return true;
  });
}

function applyTaskSort(input) {
  const items = [...input];
  if (kanbanSort === 'priority_desc') {
    items.sort((a, b) => getPriorityNum(b) - getPriorityNum(a));
    return items;
  }
  if (kanbanSort === 'title_asc') {
    items.sort((a, b) => String(a.title || '').localeCompare(String(b.title || '')));
    return items;
  }
  items.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')));
  return items;
}

function refreshAssigneeFilterOptions() {
  const sel = document.getElementById('filterAssignee');
  if (!sel) return;
  const current = sel.value;
  const assignees = [...new Set(tasks.map((t) => getTaskAssignee(t)).filter(Boolean))].sort();
  sel.innerHTML = '<option value="">All Assignees</option>' + assignees.map((a) => `<option value="${escapeHtml(a)}">${escapeHtml(a)}</option>`).join('');
  if (assignees.includes(current)) sel.value = current;
}

function setupKanbanFilters() {
  const search = document.getElementById('kanbanSearch');
  const assignee = document.getElementById('filterAssignee');
  const priority = document.getElementById('filterPriority');
  const filterBtn = document.getElementById('kanbanFilterBtn');
  const sortBtn = document.getElementById('kanbanSortBtn');
  const newTaskBtn = document.getElementById('kanbanNewTaskBtn');
  if (search) {
    search.addEventListener('input', () => {
      kanbanFilters.search = search.value.trim().toLowerCase();
      updateKanbanBoard();
    });
  }
  if (assignee) {
    assignee.addEventListener('change', () => {
      kanbanFilters.assignee = assignee.value;
      updateKanbanBoard();
    });
  }
  if (priority) {
    priority.addEventListener('change', () => {
      kanbanFilters.priority = priority.value;
      updateKanbanBoard();
    });
  }
  if (filterBtn) {
    filterBtn.addEventListener('click', () => {
      kanbanFilters = { search: '', assignee: '', priority: '' };
      if (search) search.value = '';
      if (assignee) assignee.value = '';
      if (priority) priority.value = '';
      updateKanbanBoard();
      showNotification('Filters cleared', 'info');
    });
  }
  if (sortBtn) {
    sortBtn.addEventListener('click', () => {
      const cycle = ['updated_desc', 'priority_desc', 'title_asc'];
      const idx = cycle.indexOf(kanbanSort);
      kanbanSort = cycle[(idx + 1) % cycle.length];
      const labels = {
        updated_desc: 'Sort: Recently Updated',
        priority_desc: 'Sort: Priority',
        title_asc: 'Sort: Title',
      };
      sortBtn.innerHTML = `<i class="fas fa-sort"></i>${labels[kanbanSort]}`;
      updateKanbanBoard();
    });
  }
  if (newTaskBtn) {
    newTaskBtn.addEventListener('click', openCreateTaskModal);
  }
}

function setupSidebarToggle() {
  const toggle = document.getElementById('sidebarToggle');
  const container = document.querySelector('.container');
  if (!toggle || !container) return;
  toggle.addEventListener('click', () => container.classList.toggle('sidebar-collapsed'));
}

function setupTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      tabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      tabContents.forEach((content) => {
        content.classList.remove('active');
        if (content.id === `${tabId}-tab`) content.classList.add('active');
      });
      if (tabId === 'kanban') updateKanbanBoard();
      if (tabId === 'agents') updateAgentsTab();
      if (tabId === 'dashboard') updateDashboardTab();
    });
  });
}

function setupConfigPanel() {
  const btn = document.getElementById('openConfigBtn');
  if (!btn) return;
  btn.addEventListener('click', openConfigModal);
}

function openConfigModal() {
  const existing = document.getElementById('configModal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = 'configModal';
  modal.className = 'task-modal-backdrop';
  modal.innerHTML = `
    <div class="task-modal" style="max-width:760px;">
      <div class="task-modal-header">
        <h3>API / Auth Settings</h3>
        <button class="task-modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="task-modal-body">
        <label class="task-meta-line"><strong>API Base URL</strong></label>
        <input id="cfgApiBase" class="search-input" value="${escapeHtml(uiConfig.apiBaseUrl || '')}">
        <label class="task-meta-line"><strong>Actor Role</strong></label>
        <input id="cfgRole" class="search-input" value="${escapeHtml(uiConfig.actorRole || '')}">
        <label class="task-meta-line"><strong>Actor ID</strong></label>
        <input id="cfgActorId" class="search-input" value="${escapeHtml(uiConfig.actorId || '')}">
        <label class="task-meta-line"><strong>API Token</strong></label>
        <input id="cfgToken" class="search-input" type="password" value="${escapeHtml(uiConfig.apiToken || '')}">
        <div style="display:flex; gap:8px; margin-top:10px;">
          <button id="cfgTest" class="btn btn-secondary">Test whoami</button>
          <button id="cfgSave" class="btn btn-primary">Save & Reload</button>
        </div>
        <div id="cfgResult" class="task-meta-line"></div>
      </div>
    </div>
  `;

  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.classList.contains('task-modal-close')) modal.remove();
  });
  document.body.appendChild(modal);

  document.getElementById('cfgSave')?.addEventListener('click', async () => {
    saveUiConfig({
      apiBaseUrl: (document.getElementById('cfgApiBase')?.value || '').trim() || 'http://localhost:8000',
      actorRole: (document.getElementById('cfgRole')?.value || '').trim(),
      actorId: (document.getElementById('cfgActorId')?.value || '').trim(),
      apiToken: document.getElementById('cfgToken')?.value || '',
    });
    await Promise.all([loadAgents(), loadTasks()]);
    updateDashboardTab();
    updateKanbanBoard();
    updateAgentsTab();
    const result = document.getElementById('cfgResult');
    if (result) result.textContent = 'Saved and reloaded.';
  });

  document.getElementById('cfgTest')?.addEventListener('click', async () => {
    const result = document.getElementById('cfgResult');
    try {
      saveUiConfig({
        apiBaseUrl: (document.getElementById('cfgApiBase')?.value || '').trim() || 'http://localhost:8000',
        actorRole: (document.getElementById('cfgRole')?.value || '').trim(),
        actorId: (document.getElementById('cfgActorId')?.value || '').trim(),
        apiToken: document.getElementById('cfgToken')?.value || '',
      });
      const resp = await apiFetch('/api/auth/whoami');
      const text = await resp.text();
      if (result) result.textContent = resp.ok ? `OK: ${text}` : `Error ${resp.status}: ${text}`;
    } catch (err) {
      if (result) result.textContent = `Request failed: ${err}`;
    }
  });
}

function initializeKanbanBoard() {
  const kanbanBoard = document.getElementById('kanbanBoard');
  if (!kanbanBoard) return;
  const columns = [
    { id: 'backlog', title: 'Backlog', color: 'var(--status-backlog)' },
    { id: 'todo', title: 'Todo', color: 'var(--status-todo)' },
    { id: 'planning', title: 'Planning', color: 'var(--status-planning)' },
    { id: 'hitl_review', title: 'HITL Review', color: 'var(--status-hitl-review)' },
    { id: 'working', title: 'Working', color: 'var(--status-working)' },
    { id: 'ready_to_implement', title: 'Ready', color: 'var(--status-ready)' },
    { id: 'approval', title: 'Approval', color: 'var(--status-approval)' },
    { id: 'completed', title: 'Completed', color: 'var(--status-completed)' },
    { id: 'blocked', title: 'Blocked', color: 'var(--status-blocked)' },
  ];

  kanbanBoard.innerHTML = '';
  columns.forEach((column) => {
    const columnEl = document.createElement('div');
    columnEl.className = `kanban-column ${column.id}`;
    columnEl.dataset.status = column.id;
    columnEl.innerHTML = `
      <div class="column-header">
        <div class="column-title" style="color:${column.color}">${column.title}</div>
        <div class="column-count">0</div>
      </div>
      <div class="tasks-column" data-status="${column.id}"></div>
    `;
    kanbanBoard.appendChild(columnEl);
  });
}

async function loadAgents() {
  try {
    const response = await apiFetch('/api/agents');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    agents = await response.json();
    return agents;
  } catch (error) {
    console.warn('Failed to load agents, using defaults:', error);
    agents = getDefaultAgents();
    return agents;
  }
}

async function loadTasks() {
  try {
    const response = await apiFetch(`/api/tasks?project_id=${encodeURIComponent(currentProject)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    tasks = await response.json();
    refreshAssigneeFilterOptions();
    return tasks;
  } catch (error) {
    console.warn('Failed to load tasks, using samples:', error);
    tasks = getSampleTasks();
    refreshAssigneeFilterOptions();
    return tasks;
  }
}

function updateDashboardTab() {
  updateDashboardTasks();
  updateDashboardStats();
  updateSystemHealth();
}

function updateDashboardTasks() {
  const container = document.getElementById('dashboardTasks');
  if (!container) return;
  const activeTasks = tasks.filter((t) => t.status !== 'completed' && t.status !== 'blocked').slice(0, 8);
  container.innerHTML = '';

  activeTasks.forEach((task, index) => {
    const taskEl = document.createElement('div');
    taskEl.className = `task-row ${task.status === 'completed' ? 'completed' : ''}`;
    const assignee = getTaskAssignee(task);
    const agent = agents.find((a) => a.id === assignee || a.name === assignee);
    const agentInitial = agent ? agent.name.charAt(0).toUpperCase() : '';

    taskEl.innerHTML = `
      <div class="task-number">${String(index + 1).padStart(2, '0')}</div>
      <div class="task-title">${escapeHtml(task.title || '(untitled)')}</div>
      <div class="task-meta"></div>
      <div class="task-assignee">${agentInitial}</div>
      <div class="task-status ${task.status === 'completed' ? 'completed' : ''}">
        <i class="fas fa-${task.status === 'completed' ? 'check' : 'circle'}"></i>
      </div>
    `;

    taskEl.querySelector('.task-status')?.addEventListener('click', () => toggleTaskStatus(task.id));
    container.appendChild(taskEl);
  });
}

function updateKanbanBoard() {
  const columns = ['backlog', 'todo', 'planning', 'hitl_review', 'working', 'ready_to_implement', 'approval', 'completed', 'blocked'];
  const filtered = applyTaskSort(applyTaskFilters(tasks));

  columns.forEach((status) => {
    const column = document.querySelector(`.tasks-column[data-status="${status}"]`);
    if (!column) return;

    const columnTasks = filtered.filter((task) => task.status === status);
    const countEl = column.parentElement?.querySelector('.column-count');
    if (countEl) countEl.textContent = String(columnTasks.length);

    column.innerHTML = '';
    columnTasks.forEach((task) => column.appendChild(createKanbanTaskElement(task)));

    if (columnTasks.length === 0) {
      const emptyEl = document.createElement('div');
      emptyEl.className = 'empty-state';
      emptyEl.innerHTML = `
        <div style="text-align:center; padding:20px; color:var(--text-muted);">
          <i class="fas fa-inbox" style="font-size:24px; margin-bottom:8px; opacity:0.5;"></i>
          <div style="font-size:12px;">No tasks</div>
        </div>
      `;
      column.appendChild(emptyEl);
    }
  });

  const taskCountEl = document.querySelector('.tab-btn[data-tab="kanban"] .task-count');
  if (taskCountEl) taskCountEl.textContent = String(filtered.length);
}

function createKanbanTaskElement(task) {
  const taskEl = document.createElement('div');
  taskEl.className = `kanban-task ${task.status}`;
  taskEl.dataset.taskId = task.id;
  taskEl.draggable = true;

  const assignee = getTaskAssignee(task);
  const agent = agents.find((a) => a.id === assignee || a.name === assignee);
  const agentName = agent ? agent.name.split(' ')[0] : 'Unassigned';
  const p = getPriorityNum(task);
  const pCls = p >= 2 ? 'priority-high' : p <= 0 ? 'priority-low' : 'priority-medium';
  const pLbl = getPriorityLabel(p);

  taskEl.innerHTML = `
    <div class="${pCls} task-priority">${pLbl}</div>
    <div class="task-title">${escapeHtml(task.title || '(untitled)')}</div>
    <div class="task-assignee"><i class="fas fa-user"></i>${escapeHtml(agentName)}</div>
  `;

  taskEl.addEventListener('dragstart', handleDragStart);
  taskEl.addEventListener('dragend', handleDragEnd);
  taskEl.addEventListener('click', (e) => {
    if (!e.target.closest('.task-priority')) showTaskDetails(task.id);
  });
  return taskEl;
}

function updateAgentsTab() {
  const container = document.getElementById('agentsGrid');
  if (!container) return;
  container.innerHTML = '';

  agents.forEach((agent) => {
    const agentEl = document.createElement('div');
    agentEl.className = `agent-card-large ${agent.status === 'working' ? 'working' : agent.status === 'offline' ? 'offline' : ''}`;

    const agentTasks = tasks.filter((t) => getTaskAssignee(t) === agent.id || getTaskAssignee(t) === agent.name);
    const activeTasks = agentTasks.filter((t) => ['todo', 'planning', 'hitl_review', 'working', 'ready_to_implement'].includes(t.status));

    agentEl.innerHTML = `
      <div class="agent-header">
        <div class="agent-avatar">${escapeHtml(agent.name.charAt(0))}</div>
        <div class="agent-info">
          <div class="agent-name">${escapeHtml(agent.name)}</div>
          <div class="agent-role">${escapeHtml(agent.role || 'AI Agent')}</div>
        </div>
        <div class="agent-status ${agent.status === 'working' ? 'status-working' : agent.status === 'offline' ? 'status-offline' : 'status-online'}">
          ${agent.status === 'working' ? 'Working' : agent.status === 'offline' ? 'Offline' : 'Online'}
        </div>
      </div>
      <div class="agent-details">
        <div class="detail-row"><span class="detail-label">Model</span><span class="detail-value">${escapeHtml(agent.model || 'GPT-4')}</span></div>
        <div class="detail-row"><span class="detail-label">Tasks</span><span class="detail-value">${agentTasks.length} total, ${activeTasks.length} active</span></div>
        <div class="detail-row"><span class="detail-label">Specialty</span><span class="detail-value">${escapeHtml(agent.specialty || 'General')}</span></div>
      </div>
    `;

    container.appendChild(agentEl);
  });

  const agentCountEl = document.querySelector('.tab-btn[data-tab="agents"] .task-count');
  if (agentCountEl) agentCountEl.textContent = String(agents.length);
}

function updateDashboardStats() {
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.status === 'completed').length;
  const inProgressTasks = tasks.filter((t) => ['todo', 'planning', 'hitl_review', 'working', 'ready_to_implement'].includes(t.status)).length;

  const progressBar = document.querySelector('.progress-fill');
  if (progressBar && totalTasks > 0) {
    const progressPercent = Math.round((completedTasks / totalTasks) * 100);
    progressBar.style.width = `${progressPercent}%`;
    const progressText = document.querySelector('.progress-text');
    if (progressText) progressText.innerHTML = `<span>Task Done:</span><span>${completedTasks} / ${totalTasks}</span>`;
  }

  const taskCountBadge = document.querySelector('.task-count');
  if (taskCountBadge) taskCountBadge.textContent = String(inProgressTasks);
}

function setupDragAndDrop() {
  const columns = document.querySelectorAll('.tasks-column');
  columns.forEach((column) => {
    column.addEventListener('dragover', handleDragOver);
    column.addEventListener('dragenter', handleDragEnter);
    column.addEventListener('dragleave', handleDragLeave);
    column.addEventListener('drop', handleDrop);
  });
}

function handleDragStart(e) {
  draggedTask = e.target;
  e.target.style.opacity = '0.5';
  e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
  e.dataTransfer.effectAllowed = 'move';
}

function handleDragEnd(e) {
  e.target.style.opacity = '1';
  draggedTask = null;
  document.querySelectorAll('.tasks-column').forEach((col) => col.classList.remove('drag-over'));
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
}

function handleDragEnter(e) {
  e.preventDefault();
  e.target.closest('.tasks-column')?.classList.add('drag-over');
}

function handleDragLeave(e) {
  e.target.closest('.tasks-column')?.classList.remove('drag-over');
}

async function handleDrop(e) {
  e.preventDefault();
  const column = e.target.closest('.tasks-column');
  if (!column) return;

  column.classList.remove('drag-over');
  const taskId = e.dataTransfer.getData('text/plain');
  const newStatus = column.dataset.status;
  if (!taskId || !newStatus) return;

  try {
    const response = await apiFetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify({ status: newStatus }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const idx = tasks.findIndex((t) => t.id === taskId);
    if (idx !== -1) tasks[idx].status = newStatus;

    updateKanbanBoard();
    updateDashboardTab();
    updateAgentsTab();
    showNotification(`Task moved to ${newStatus.replace('_', ' ')}`, 'success');
  } catch (error) {
    console.error('Failed to update task status:', error);
    showNotification('Failed to move task', 'error');
  }
}

function setupFormHandlers() {
  document.querySelectorAll('.btn').forEach((btn) => {
    if ((btn.textContent || '').trim() === 'New Task' && !btn.id) {
      btn.addEventListener('click', openCreateTaskModal);
    }
  });
}

async function createTaskFromInput(title, description, priority) {
  if (!title.trim()) {
    showNotification('Task title is required', 'error');
    return false;
  }

  const taskData = {
    title: title.trim(),
    description: description.trim(),
    priority: priority === 'high' ? 2 : priority === 'low' ? 0 : 1,
    project_id: currentProject,
  };

  try {
    const response = await apiFetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(taskData),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const created = await response.json();
    tasks.unshift(created);
    refreshAssigneeFilterOptions();
    updateKanbanBoard();
    updateDashboardTab();
    updateAgentsTab();
    showNotification('Task created successfully', 'success');
    return true;
  } catch (error) {
    console.error('Failed to create task:', error);
    const message = String(error).includes('404') ? 'Project not found. Check config/project.' : 'Failed to create task';
    showNotification(message, 'error');
    return false;
  }
}

function openCreateTaskModal() {
  const existing = document.getElementById('createTaskModal');
  if (existing) existing.remove();
  ensureTaskDetailModalStyles();

  const modal = document.createElement('div');
  modal.id = 'createTaskModal';
  modal.className = 'task-modal-backdrop';
  modal.innerHTML = `
    <div class="task-modal">
      <div class="task-modal-header">
        <h3>Create Task</h3>
        <button class="task-modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="task-modal-body">
        <label class="task-meta-line"><strong>Title</strong></label>
        <input id="newTaskTitle" class="search-input" placeholder="Task title">
        <label class="task-meta-line"><strong>Description</strong></label>
        <textarea id="newTaskDescription" class="search-input" style="min-height:120px; resize:vertical;" placeholder="Task description"></textarea>
        <label class="task-meta-line"><strong>Priority</strong></label>
        <select id="newTaskPriority" class="search-input">
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="low">Low</option>
        </select>
        <div class="task-stage-actions">
          <button class="btn btn-primary" id="createTaskConfirm">Create</button>
        </div>
      </div>
    </div>
  `;
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.classList.contains('task-modal-close')) modal.remove();
  });
  document.body.appendChild(modal);

  modal.querySelector('#createTaskConfirm')?.addEventListener('click', async () => {
    const title = modal.querySelector('#newTaskTitle')?.value || '';
    const description = modal.querySelector('#newTaskDescription')?.value || '';
    const priority = modal.querySelector('#newTaskPriority')?.value || 'medium';
    const ok = await createTaskFromInput(title, description, priority);
    if (ok) modal.remove();
  });
}

async function showTaskDetails(taskId) {
  const task = tasks.find((t) => t.id === taskId);
  if (!task) {
    showNotification('Task not found', 'error');
    return;
  }

  let fullTask = task;
  let readiness = null;

  try {
    const taskResp = await apiFetch(`/api/tasks/${taskId}`);
    if (taskResp.ok) fullTask = await taskResp.json();
  } catch (error) {
    console.warn('Failed to fetch full task details:', error);
  }

  if (fullTask.status === 'planning' || fullTask.status === 'working') {
    const target = fullTask.status === 'planning' ? 'hitl_review' : 'ready_to_implement';
    try {
      const checkResp = await apiFetch(`/api/tasks/${taskId}/stage/check?stage=${fullTask.status}&to_status=${target}`);
      if (checkResp.ok) readiness = await checkResp.json();
    } catch (error) {
      console.warn('Failed to fetch stage readiness:', error);
    }
  }

  let comments = [];
  try {
    const commentsResp = await apiFetch(`/api/tasks/${taskId}/comments?limit=30`);
    if (commentsResp.ok) comments = await commentsResp.json();
  } catch (error) {
    console.warn('Failed to fetch comments:', error);
  }

  ensureTaskDetailModalStyles();
  renderTaskDetailModal(fullTask, readiness, comments);
}

function stageTargetFor(status) {
  if (status === 'planning') return 'hitl_review';
  if (status === 'working') return 'ready_to_implement';
  return '';
}

function renderTaskDetailModal(task, readiness, comments = []) {
  const existing = document.getElementById('taskDetailModal');
  if (existing) existing.remove();

  const priorityLabel = getPriorityLabel(getPriorityNum(task));
  const stage = task.status === 'planning' || task.status === 'working' ? task.status : '';

  const stageActions = stage ? `
    <div class="task-stage-actions">
      <button class="btn btn-secondary" data-action="stage-check">Stage Check</button>
      <button class="btn btn-primary" data-action="submit-stage">Submit ${stage}</button>
    </div>
  ` : `
    <div class="task-stage-actions">
      <button class="btn btn-secondary" data-action="start-planning">Start Planning</button>
      <button class="btn btn-secondary" data-action="start-working">Start Working</button>
    </div>
  `;

  const readinessCard = readiness ? `
    <section class="task-readiness-card ${readiness.ready ? 'ready' : 'not-ready'}">
      <div class="task-readiness-header">
        <span class="task-readiness-title">Submit Readiness</span>
        <span class="task-readiness-pill">${readiness.ready ? 'READY' : 'BLOCKED'}</span>
      </div>
      <div class="task-readiness-grid">
        <div><strong>Stage:</strong> ${readiness.stage}</div>
        <div><strong>Target:</strong> ${readiness.to_status || '-'}</div>
        <div><strong>Transition:</strong> ${readiness.transition_valid ? 'Valid' : 'Invalid'}</div>
        <div><strong>Artifact Exists:</strong> ${readiness.artifact_exists ? 'Yes' : 'No'}</div>
        <div><strong>Quality:</strong> ${readiness.artifact_quality_ok ? 'Pass' : 'Fail'}</div>
      </div>
      <div class="task-readiness-detail">${escapeHtml(readiness.detail || '')}</div>
      ${readiness.artifact_path ? `<div class="task-readiness-path">${escapeHtml(readiness.artifact_path)}</div>` : ''}
    </section>
  ` : '';

  const modal = document.createElement('div');
  modal.id = 'taskDetailModal';
  modal.className = 'task-modal-backdrop';
  modal.innerHTML = `
    <div class="task-modal">
      <div class="task-modal-header">
        <h3>${escapeHtml(task.title || 'Untitled Task')}</h3>
        <button class="task-modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="task-modal-body">
        <div class="task-meta-line"><strong>ID:</strong> ${task.id}</div>
        <div class="task-meta-line"><strong>Status:</strong> ${task.status}</div>
        <div class="task-meta-line"><strong>Priority:</strong> ${priorityLabel}</div>
        <div class="task-meta-line"><strong>Assignee:</strong> ${escapeHtml(getTaskAssignee(task) || 'Unassigned')}</div>
        <div class="task-description">${escapeHtml(task.description || 'No description')}</div>
        ${stageActions}
        ${readinessCard}
        <section class="task-comments">
          <div class="task-readiness-header">
            <span class="task-readiness-title">Comments</span>
          </div>
          <div id="taskCommentsList" class="task-comments-list">
            ${comments.length ? comments.map((c) => `
              <div class="task-comment-item">
                <div class="task-comment-head">
                  <strong>${escapeHtml(c.author || 'unknown')}</strong>
                  <span>${escapeHtml(c.created_at || '')}</span>
                </div>
                <div>${escapeHtml(c.comment || '')}</div>
              </div>
            `).join('') : '<div class="task-meta-line">No comments yet.</div>'}
          </div>
          <textarea id="taskCommentInput" class="search-input" style="min-height:78px; resize:vertical;" placeholder="Add review note or guidance..."></textarea>
          <div class="task-stage-actions">
            <button class="btn btn-secondary" data-action="add-comment">Add Comment</button>
          </div>
        </section>
      </div>
    </div>
  `;

  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.classList.contains('task-modal-close')) modal.remove();
  });

  modal.querySelector('[data-action="start-planning"]')?.addEventListener('click', () => runTaskStageAction(task.id, 'planning'));
  modal.querySelector('[data-action="start-working"]')?.addEventListener('click', () => runTaskStageAction(task.id, 'working'));
  modal.querySelector('[data-action="stage-check"]')?.addEventListener('click', () => rerenderTaskDetails(task.id));
  modal.querySelector('[data-action="submit-stage"]')?.addEventListener('click', () => submitTaskStage(task.id, stage));
  modal.querySelector('[data-action="add-comment"]')?.addEventListener('click', () => addCommentFromModal(task.id, modal));

  document.body.appendChild(modal);
}

async function addCommentFromModal(taskId, modal) {
  const input = modal.querySelector('#taskCommentInput');
  const comment = (input?.value || '').trim();
  if (!comment) {
    showNotification('Comment is empty', 'warning');
    return;
  }
  try {
    const resp = await apiFetch(`/api/tasks/${taskId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(txt || `HTTP ${resp.status}`);
    }
    showNotification('Comment added', 'success');
    input.value = '';
    await rerenderTaskDetails(taskId);
  } catch (err) {
    showNotification(`Failed to add comment: ${err}`, 'error');
  }
}

async function runTaskStageAction(taskId, stage) {
  try {
    const resp = await apiFetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify({ status: stage }),
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(txt || `HTTP ${resp.status}`);
    }
    showNotification(`Moved task to ${stage}`, 'success');
    await Promise.all([loadTasks(), loadAgents()]);
    updateKanbanBoard();
    updateDashboardTab();
    updateAgentsTab();
    rerenderTaskDetails(taskId);
  } catch (err) {
    showNotification(`Failed to start ${stage}: ${err}`, 'error');
  }
}

async function submitTaskStage(taskId, stage) {
  const toStatus = stageTargetFor(stage);
  if (!toStatus) return;
  const note = window.prompt('Optional submission note:') || '';
  try {
    const resp = await apiFetch(`/api/tasks/${taskId}/stage/submit`, {
      method: 'POST',
      body: JSON.stringify({ stage, to_status: toStatus, note }),
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(txt || `HTTP ${resp.status}`);
    }
    showNotification(`Submitted ${stage} -> ${toStatus}`, 'success');
    await Promise.all([loadTasks(), loadAgents()]);
    updateKanbanBoard();
    updateDashboardTab();
    updateAgentsTab();
    rerenderTaskDetails(taskId);
  } catch (err) {
    showNotification(`Submit failed: ${err}`, 'error');
  }
}

async function rerenderTaskDetails(taskId) {
  const existing = document.getElementById('taskDetailModal');
  if (existing) existing.remove();
  await showTaskDetails(taskId);
}

function ensureTaskDetailModalStyles() {
  if (document.getElementById('taskDetailModalStyles')) return;
  const style = document.createElement('style');
  style.id = 'taskDetailModalStyles';
  style.textContent = `
    .task-modal-backdrop { position: fixed; inset: 0; background: rgba(8,12,20,.65); z-index: 1000; display:flex; align-items:center; justify-content:center; padding:20px; }
    .task-modal { width:min(760px,95vw); max-height:88vh; overflow:auto; background:#0e1728; color:#e7edf8; border:1px solid #24324a; border-radius:14px; box-shadow:0 24px 40px rgba(0,0,0,.45); }
    .task-modal-header { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid #24324a; }
    .task-modal-header h3 { margin:0; font-size:18px; }
    .task-modal-close { border:0; background:transparent; color:#9fb2ce; font-size:24px; cursor:pointer; }
    .task-modal-body { padding:16px; display:grid; gap:8px; }
    .task-meta-line { font-size:13px; color:#c6d4e8; }
    .task-description { margin-top:8px; padding:12px; background:#121f35; border-radius:8px; color:#dbe6f7; white-space:pre-wrap; }
    .task-stage-actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
    .task-readiness-card { margin-top:10px; border-radius:10px; padding:12px; border:1px solid; background:#0f1a2b; }
    .task-readiness-card.ready { border-color:#1f8b5c; box-shadow: inset 0 0 0 1px rgba(31,139,92,.25); }
    .task-readiness-card.not-ready { border-color:#b05b3a; box-shadow: inset 0 0 0 1px rgba(176,91,58,.25); }
    .task-readiness-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
    .task-readiness-title { font-weight:700; font-size:13px; letter-spacing:.3px; }
    .task-readiness-pill { font-size:11px; font-weight:700; padding:3px 8px; border-radius:999px; background:#22314a; }
    .task-readiness-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; font-size:12px; color:#c6d4e8; margin-bottom:8px; }
    .task-readiness-detail { font-size:12px; color:#f3d3b8; margin-bottom:6px; }
    .task-readiness-path { font-size:11px; color:#8ea5c4; word-break:break-all; }
    .task-comments { margin-top:8px; border-top:1px solid #24324a; padding-top:12px; }
    .task-comments-list { display:grid; gap:8px; max-height:220px; overflow:auto; padding-right:4px; }
    .task-comment-item { background:#121f35; border:1px solid #24324a; border-radius:8px; padding:8px 10px; font-size:12px; color:#dbe6f7; }
    .task-comment-head { display:flex; justify-content:space-between; color:#9fb2ce; margin-bottom:4px; font-size:11px; }
  `;
  document.head.appendChild(style);
}

async function toggleTaskStatus(taskId) {
  const task = tasks.find((t) => t.id === taskId);
  if (!task) return;
  const newStatus = task.status === 'completed' ? 'todo' : 'completed';
  try {
    const response = await apiFetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify({ status: newStatus }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    task.status = newStatus;
    updateDashboardTab();
    updateKanbanBoard();
    updateAgentsTab();
    showNotification(`Task marked ${newStatus}`, 'success');
  } catch (error) {
    showNotification('Failed to update task', 'error');
  }
}

function setupEventSource() {
  if (eventSource) eventSource.close();
  try {
    eventSource = new EventSource(`${API_BASE}/api/events`);
    sseState = 'connected';
    eventSource.onmessage = async () => {
      await loadTasks();
      updateDashboardTab();
      updateKanbanBoard();
      updateAgentsTab();
    };
    eventSource.onerror = () => {
      sseState = 'error';
      updateSystemHealth();
    };
  } catch (error) {
    console.warn('SSE unavailable:', error);
    sseState = 'unavailable';
  }
  updateSystemHealth();
}

async function updateSystemHealth() {
  const grid = document.getElementById('systemHealthGrid');
  if (!grid) return;
  let backend = 'down';
  let identity = 'unknown';
  try {
    const healthResp = await fetch(`${API_BASE}/health`);
    backend = healthResp.ok ? 'up' : `error ${healthResp.status}`;
  } catch {
    backend = 'down';
  }
  try {
    const who = await apiFetch('/api/auth/whoami');
    if (who.ok) {
      const data = await who.json();
      identity = `${data.actor_role || 'none'} / ${data.actor_id || 'none'}`;
    } else {
      identity = `error ${who.status}`;
    }
  } catch {
    identity = 'unreachable';
  }
  grid.innerHTML = `
    <div class="health-item"><strong>Backend</strong>${escapeHtml(backend)}</div>
    <div class="health-item"><strong>Identity</strong>${escapeHtml(identity)}</div>
    <div class="health-item"><strong>Project</strong>${escapeHtml(currentProject)}</div>
    <div class="health-item"><strong>Events</strong>${escapeHtml(sseState)}</div>
  `;
}

function getDefaultAgents() {
  return [
    { id: 'ren', name: 'Ren', role: 'Infrastructure', status: 'online', model: 'qwen-coder-local' },
    { id: 'aki', name: 'Aki', role: 'Coordinator', status: 'online', model: 'deepseek-chat' },
    { id: 'kuro', name: 'Kuro', role: 'Execution', status: 'working', model: 'deepseek-chat' },
    { id: 'shin', name: 'Shin', role: 'Strategy', status: 'online', model: 'deepseek-chat' },
    { id: 'sora', name: 'Sora', role: 'Creative', status: 'online', model: 'gemini' },
  ];
}

function getSampleTasks() {
  return [
    { id: 'sample-1', title: 'UI polish pass', description: 'Improve spacing and card hierarchy', status: 'todo', priority: 1, assignee: 'kuro' },
    { id: 'sample-2', title: 'Stage workflow guardrails', description: 'Validate planning/working submissions', status: 'planning', priority: 2, assignee: 'ren' },
    { id: 'sample-3', title: 'Dispatch transparency', description: 'Expose decision rationale in UI', status: 'working', priority: 1, assignee: 'aki' },
  ];
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showNotification(message, type = 'info') {
  document.querySelectorAll('.notification').forEach((n) => n.remove());
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = String(message);

  const bgColor = type === 'success'
    ? 'var(--badge-green)'
    : type === 'error'
      ? 'var(--badge-red)'
      : type === 'warning'
        ? 'var(--badge-orange)'
        : 'var(--bg-card)';

  notification.style.position = 'fixed';
  notification.style.top = '20px';
  notification.style.right = '20px';
  notification.style.padding = '12px 16px';
  notification.style.borderRadius = '8px';
  notification.style.background = bgColor;
  notification.style.color = '#fff';
  notification.style.fontWeight = '600';
  notification.style.zIndex = '1200';
  notification.style.maxWidth = '520px';
  notification.style.boxShadow = '0 10px 24px rgba(0,0,0,.25)';

  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 3500);
}

async function initializeWorkflowDashboard() {
  console.log('🚀 Initializing Agent Nexus Workflow Dashboard');
  try {
    uiConfig = loadUiConfig();
    API_BASE = uiConfig.apiBaseUrl;
    setupTabs();
    setupSidebarToggle();
    setupConfigPanel();
    setupKanbanFilters();
    initializeKanbanBoard();

    await Promise.all([loadAgents(), loadTasks()]);
    setupDragAndDrop();
    setupFormHandlers();
    setupEventSource();

    updateDashboardTab();
    updateKanbanBoard();
    updateAgentsTab();
    console.log('✅ Workflow dashboard initialized successfully');
  } catch (error) {
    console.error('❌ Dashboard initialization failed:', error);
    showNotification('Failed to initialize dashboard. Check backend connection.', 'error');
  }
}

document.addEventListener('DOMContentLoaded', initializeWorkflowDashboard);
