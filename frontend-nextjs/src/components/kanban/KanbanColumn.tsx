"use client";

import { Task, TaskStatus } from "@/types/dispatch";
import TaskCard from "./TaskCard";

interface KanbanColumnProps {
  status: TaskStatus;
  label: string;
  tasks: Task[];
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, status: TaskStatus) => void;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onTaskClick: (task: Task) => void;
}

export default function KanbanColumn({
  status,
  label,
  tasks,
  onDragOver,
  onDrop,
  onDragStart,
  onTaskClick,
}: KanbanColumnProps) {
  const getStatusColor = (s: string) => {
    const statusMap: Record<string, string> = {
      backlog: "bg-secondary",
      todo: "bg-primary",
      planning: "bg-blue",
      hitl_review: "bg-warning",
      working: "bg-info",
      ready_to_implement: "bg-teal",
      approval: "bg-purple",
      completed: "bg-success",
      blocked: "bg-danger",
    };
    return statusMap[s] || "bg-secondary";
  };

  return (
    <div
      className="col-12 col-sm-6 col-lg-4 col-xl"
      style={{ minWidth: "290px" }}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, status)}
    >
      <div className={`card bg-light-lt h-100`}>
        <div className={`card-status-top ${getStatusColor(status)}`}></div>
        <div className="card-header py-2 px-3 d-flex align-items-center justify-content-between">
          <h3 className="card-title small fw-bold text-uppercase">{label}</h3>
          <span className="badge bg-secondary-lt text-secondary">{tasks.length}</span>
        </div>
        <div className="card-body p-2 overflow-y-auto" style={{ maxHeight: "calc(100vh - 260px)", minHeight: "250px" }}>
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onDragStart={onDragStart} onClick={() => onTaskClick(task)} />
          ))}
          {tasks.length === 0 && (
            <div className="text-center py-4 text-muted small border border-dashed rounded">
              No tasks
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
