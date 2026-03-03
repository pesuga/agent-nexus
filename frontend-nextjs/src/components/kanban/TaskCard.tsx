"use client";

import { Task } from "@/types/dispatch";
import { IconUser } from "@tabler/icons-react";

interface TaskCardProps {
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onClick: () => void;
}

export default function TaskCard({ task, onDragStart, onClick }: TaskCardProps) {
  const getPriorityColor = (p: number) => {
    if (p >= 2) return "bg-red";
    if (p <= 0) return "bg-green";
    return "bg-orange";
  };

  const getPriorityLabel = (p: number) => {
    if (p >= 2) return "HIGH";
    if (p <= 0) return "LOW";
    return "MEDIUM";
  };

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
      className="card mb-2 cursor-pointer task-card"
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      onClick={onClick}
      style={{ borderLeft: `4px solid var(--tblr-${getStatusColor(task.status).replace('bg-', '')})` }}
    >
      <div className="card-body p-3">
        <div className="d-flex align-items-center justify-content-between mb-1">
          <span className="text-muted" style={{ fontSize: "0.68rem" }}>{task.id.slice(0, 8)}</span>
          <span className={`badge ${getPriorityColor(task.priority)} text-white`}>
            {getPriorityLabel(task.priority)}
          </span>
        </div>
        <h4 className="card-title mb-1" style={{ fontSize: '0.95rem' }}>{task.title}</h4>
        <div className="text-secondary small mb-2 task-card-description">
          {task.description || "No description"}
        </div>
        <div className="d-flex align-items-center mt-2">
          {task.assignee ? (
            <div className="d-flex align-items-center">
              <span className="avatar avatar-xs rounded-circle me-1 bg-blue-lt">
                {task.assignee.substring(0, 2).toUpperCase()}
              </span>
              <span className="small text-muted">{task.assignee}</span>
            </div>
          ) : (
            <div className="d-flex align-items-center text-muted">
              <IconUser size={14} className="me-1" />
              <span className="small">Unassigned</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
