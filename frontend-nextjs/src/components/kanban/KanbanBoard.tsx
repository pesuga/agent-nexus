"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useAppContext } from "@/context/AppContext";
import { useDispatchApi } from "@/hooks/useDispatchApi";
import { useSSE } from "@/hooks/useSSE";
import { Task, TaskStatus } from "@/types/dispatch";
import KanbanColumn from "./KanbanColumn";
import TaskModal from "./TaskModal";
import { 
  IconPlus, 
  IconRefresh, 
  IconSearch, 
  IconSortAscending, 
  IconX 
} from "@tabler/icons-react";

type SortOption = "updated_desc" | "priority_desc" | "title_asc";

const WORKFLOW_STATES: { status: TaskStatus; label: string }[] = [
  { status: "backlog", label: "Backlog" },
  { status: "todo", label: "Todo" },
  { status: "planning", label: "Planning" },
  { status: "hitl_review", label: "HITL Review" },
  { status: "working", label: "Working" },
  { status: "ready_to_implement", label: "Implemented" },
  { status: "approval", label: "Approval" },
  { status: "completed", label: "Completed" },
  { status: "blocked", label: "Blocked" },
];

interface KanbanBoardProps {
  projectId?: string;
}

export default function KanbanBoard({ projectId }: KanbanBoardProps) {
  const { currentProjectId: contextProjectId } = useAppContext();
  const activeProjectId = projectId || contextProjectId;
  
  const { fetchTasks, updateTask, createTask, deleteTask } = useDispatchApi();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggedTaskId, setDraggedTaskId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  // Filter & Sort State
  const [searchQuery, setSearchQuery] = useState("");
  const [filterAssignee, setFilterAssignee] = useState("");
  const [filterPriority, setFilterPriority] = useState<string>("");
  const [sortBy, setSortBy] = useState<SortOption>("updated_desc");

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchTasks(activeProjectId);
      setTasks(data);
    } catch (e) {
      console.error("Failed to load tasks", e);
    } finally {
      setLoading(false);
    }
  }, [activeProjectId, fetchTasks]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  useSSE(loadTasks);

  const onDragStart = (e: React.DragEvent, taskId: string) => {
    setDraggedTaskId(taskId);
    e.dataTransfer.setData("taskId", taskId);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onDrop = async (e: React.DragEvent, newStatus: TaskStatus) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData("taskId") || draggedTaskId;
    if (!taskId) return;

    const task = tasks.find((t) => t.id === taskId);
    if (task && task.status !== newStatus) {
      // Optimistic update
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
      );

      try {
        await updateTask(taskId, { status: newStatus });
      } catch (e) {
        console.error("Failed to update task status", e);
        // Rollback
        loadTasks();
      }
    }
    setDraggedTaskId(null);
  };

  const handleCreateTask = () => {
    setSelectedTask(null);
    setIsModalOpen(true);
  };

  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleSaveTask = async (taskData: Partial<Task>) => {
    if (selectedTask) {
      await updateTask(selectedTask.id, taskData);
    } else {
      await createTask({ ...taskData, project_id: activeProjectId });
    }
    loadTasks();
  };

  const handleDeleteTask = async (taskId: string) => {
    if (confirm("Are you sure you want to delete this task?")) {
      await deleteTask(taskId);
      setIsModalOpen(false);
      loadTasks();
    }
  };

  const clearFilters = () => {
    setSearchQuery("");
    setFilterAssignee("");
    setFilterPriority("");
  };

  const cycleSort = () => {
    const options: SortOption[] = ["updated_desc", "priority_desc", "title_asc"];
    const currentIndex = options.indexOf(sortBy);
    setSortBy(options[(currentIndex + 1) % options.length]);
  };

  const getSortLabel = () => {
    switch (sortBy) {
      case "updated_desc": return "Recently Updated";
      case "priority_desc": return "Priority";
      case "title_asc": return "Title";
    }
  };

  const assignees = useMemo(() => {
    return Array.from(new Set(tasks.map(t => t.assignee).filter(Boolean))).sort() as string[];
  }, [tasks]);

  const filteredAndSortedTasks = useMemo(() => {
    const result = tasks.filter(task => {
      const matchesSearch = 
        task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.id.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesAssignee = !filterAssignee || task.assignee === filterAssignee;
      const matchesPriority = !filterPriority || task.priority === parseInt(filterPriority);

      return matchesSearch && matchesAssignee && matchesPriority;
    });

    result.sort((a, b) => {
      if (sortBy === "updated_desc") {
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
      if (sortBy === "priority_desc") {
        return b.priority - a.priority;
      }
      if (sortBy === "title_asc") {
        return a.title.localeCompare(b.title);
      }
      return 0;
    });

    return result;
  }, [tasks, searchQuery, filterAssignee, filterPriority, sortBy]);

  const groupedTasks = useMemo(() => {
    const groups: Record<TaskStatus, Task[]> = {
      backlog: [],
      todo: [],
      planning: [],
      hitl_review: [],
      working: [],
      ready_to_implement: [],
      approval: [],
      completed: [],
      blocked: [],
    };
    filteredAndSortedTasks.forEach((task) => {
      if (groups[task.status]) {
        groups[task.status].push(task);
      }
    });
    return groups;
  }, [filteredAndSortedTasks]);

  return (
    <div className="kanban-wrapper">
      <div className="page-header d-print-none mb-4">
        <div className="row g-2 align-items-center mb-3">
          <div className="col">
            <h2 className="page-title">Kanban Board</h2>
          </div>
          <div className="col-auto ms-auto d-print-none">
            <div className="btn-list">
              <button className="btn btn-primary d-none d-sm-inline-block" onClick={handleCreateTask}>
                <IconPlus size={18} className="me-1" />
                Create new task
              </button>
              <button className="btn btn-icon btn-outline-secondary" onClick={loadTasks} disabled={loading}>
                <IconRefresh size={18} className={loading ? "spin" : ""} />
              </button>
            </div>
          </div>
        </div>

        {/* Filter & Sort Bar */}
        <div className="card bg-dark-lt border-0 shadow-none mb-0">
          <div className="card-body p-2">
            <div className="row g-2 align-items-center">
              <div className="col-md-3">
                <div className="input-icon">
                  <span className="input-icon-addon"><IconSearch size={16} /></span>
                  <input 
                    type="text" 
                    className="form-control form-control-sm" 
                    placeholder="Search tasks..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>
              <div className="col-auto">
                <select 
                  className="form-select form-select-sm" 
                  value={filterAssignee}
                  onChange={(e) => setFilterAssignee(e.target.value)}
                >
                  <option value="">All Assignees</option>
                  {assignees.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="col-auto">
                <select 
                  className="form-select form-select-sm"
                  value={filterPriority}
                  onChange={(e) => setFilterPriority(e.target.value)}
                >
                  <option value="">All Priorities</option>
                  <option value="2">High Priority</option>
                  <option value="1">Medium Priority</option>
                  <option value="0">Low Priority</option>
                </select>
              </div>
              <div className="col-auto">
                <button className="btn btn-sm btn-ghost-secondary" onClick={clearFilters} title="Clear Filters">
                  <IconX size={16} className="me-1" /> Clear
                </button>
              </div>
              <div className="col-auto ms-auto">
                <button className="btn btn-sm btn-outline-secondary" onClick={cycleSort}>
                  <IconSortAscending size={16} className="me-1" />
                  Sort: {getSortLabel()}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-3 flex-nowrap overflow-x-auto pb-4 px-1" style={{ minHeight: "calc(100vh - 220px)" }}>
        {WORKFLOW_STATES.map((state) => (
          <KanbanColumn
            key={state.status}
            status={state.status}
            label={state.label}
            tasks={groupedTasks[state.status]}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onDragStart={onDragStart}
            onTaskClick={handleEditTask}
          />
        ))}
      </div>

      {isModalOpen && (
        <TaskModal
          task={selectedTask}
          projectId={activeProjectId}
          onClose={() => setIsModalOpen(false)}
          onSave={handleSaveTask}
          onDelete={handleDeleteTask}
        />
      )}
    </div>
  );
}
