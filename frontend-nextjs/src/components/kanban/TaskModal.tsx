"use client";

import { useState, useEffect, useCallback } from "react";
import { Task, TaskStatus } from "@/types/dispatch";
import { IconDeviceFloppy, IconTrash, IconMessage, IconFileCode, IconInfoCircle, IconBolt } from "@tabler/icons-react";
import { useAppContext } from "@/context/AppContext";
import { useDispatchApi } from "@/hooks/useDispatchApi";

interface TaskModalProps {
  task?: Task | null;
  projectId: string;
  onClose: () => void;
  onSave: (task: Partial<Task>) => Promise<void>;
  onDelete?: (taskId: string) => Promise<void>;
}

export default function TaskModal({ task, projectId, onClose, onSave, onDelete }: TaskModalProps) {
  const { estimateContext, fetchAgents } = useDispatchApi();
  const { config, user } = useAppContext();

  const [formData, setFormData] = useState<Partial<Task>>({
    title: "",
    description: "",
    status: "backlog" as TaskStatus,
    priority: 1,
    assignee: "",
    project_id: projectId,
  });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "comments" | "artifacts" | "dispatch">("general");
  const [comments, setComments] = useState<Array<{ id: string; author?: string; comment: string; created_at: string }>>([]);
  const [artifacts, setArtifacts] = useState<Array<{ id: string; stage: string; path: string; created_at: string }>>([]);
  const [newComment, setNewComment] = useState("");
  const [contextEstimate, setContextEstimate] = useState<{
    total_estimated_tokens: number;
    estimated_tokens: Record<string, number>;
  } | null>(null);
  const [availableAgents, setAvailableAgents] = useState<Array<{ id: string; name: string; type?: string }>>([]);
  
  const fetchDetails = useCallback(async () => {
    if (!task) return;
    try {
      const headers = {
        'X-Actor-Role': user?.actor_role || '',
        'X-Actor-Id': user?.actor_id || '',
        'X-API-Token': config.apiToken,
      };
      const [commentsResp, artifactsResp, agentsData] = await Promise.all([
        fetch(`${config.apiBaseUrl}/api/tasks/${task.id}/comments`, { headers }),
        fetch(`${config.apiBaseUrl}/api/tasks/${task.id}/artifacts`, { headers }),
        fetchAgents()
      ]);
      if (commentsResp.ok) setComments(await commentsResp.json());
      if (artifactsResp.ok) setArtifacts(await artifactsResp.json());
      setAvailableAgents(agentsData);
    } catch (e) {
      console.error("Failed to fetch task details", e);
    }
  }, [task, config, user, fetchAgents]);

  const loadEstimate = useCallback(async () => {
    if (!task) return;
    try {
      const est = await estimateContext(task.id);
      setContextEstimate(est);
    } catch (e) {
      console.error("Failed to load context estimate", e);
    }
  }, [task, estimateContext]);

  useEffect(() => {
    if (task) {
      setFormData({
        ...task,
        assignee: task.assignee || "",
      });
      fetchDetails();
      loadEstimate();
    } else {
      setFormData({
        title: "",
        description: "",
        status: "backlog",
        priority: 1,
        assignee: "",
        project_id: projectId,
      });
      setComments([]);
      setArtifacts([]);
      setContextEstimate(null);
    }
  }, [task, projectId, fetchDetails, loadEstimate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      console.error("Failed to save task", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDispatchNow = async () => {
    setLoading(true);
    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      console.error("Failed to dispatch task", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddComment = async () => {
    if (!task || !newComment.trim()) return;
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/tasks/${task.id}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Actor-Role': user?.actor_role || '',
          'X-Actor-Id': user?.actor_id || '',
          'X-API-Token': config.apiToken,
        },
        body: JSON.stringify({ comment: newComment })
      });
      if (resp.ok) {
        setNewComment("");
        fetchDetails();
      }
    } catch (e) {
      console.error("Failed to add comment", e);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "priority" ? parseInt(value) : value,
    }));
  };

  return (
    <div className="modal modal-blur fade show d-block" tabIndex={-1} role="dialog" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg modal-dialog-centered" role="document">
        <div className="modal-content border-0 shadow-lg" style={{ backgroundColor: 'var(--tblr-card-bg)', minHeight: "620px" }}>
          <div className="modal-header py-3 px-4">
            <div>
              <h5 className="modal-title mb-1">{task ? task.title : "Create New Task"}</h5>
              {task && <div className="text-muted small">Task: {task.id}</div>}
            </div>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close"></button>
          </div>
          
          <div className="card-header px-4 pt-2">
            <ul className="nav nav-tabs card-header-tabs" data-bs-toggle="tabs">
              <li className="nav-item">
                <button 
                  className={`nav-link ${activeTab === 'general' ? 'active' : ''}`}
                  onClick={() => setActiveTab('general')}
                >
                  <IconInfoCircle size={18} className="me-2" /> General
                </button>
              </li>
              {task && (
                <>
                  <li className="nav-item">
                    <button 
                      className={`nav-link ${activeTab === 'dispatch' ? 'active' : ''}`}
                      onClick={() => setActiveTab('dispatch')}
                    >
                      <IconBolt size={18} className="me-2 text-warning" /> Dispatch
                    </button>
                  </li>
                  <li className="nav-item">
                    <button 
                      className={`nav-link ${activeTab === 'comments' ? 'active' : ''}`}
                      onClick={() => setActiveTab('comments')}
                    >
                      <IconMessage size={18} className="me-2" /> Comments
                    </button>
                  </li>
                  <li className="nav-item">
                    <button 
                      className={`nav-link ${activeTab === 'artifacts' ? 'active' : ''}`}
                      onClick={() => setActiveTab('artifacts')}
                    >
                      <IconFileCode size={18} className="me-2" /> Artifacts
                    </button>
                  </li>
                </>
              )}
            </ul>
          </div>

          <div className="card-body px-4 pb-4 pt-3 overflow-auto" style={{ minHeight: "480px" }}>
            {activeTab === 'general' && (
              <form onSubmit={handleSubmit} className="h-100 d-flex flex-column">
                <div className="mb-3">
                  <label className="form-label">Title</label>
                  <input
                    type="text"
                    name="title"
                    className="form-control"
                    value={formData.title}
                    onChange={handleChange}
                    placeholder="Task title"
                    required
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Description</label>
                  <textarea
                    name="description"
                    className="form-control"
                    rows={4}
                    value={formData.description}
                    onChange={handleChange}
                    placeholder="What needs to be done?"
                  ></textarea>
                </div>
                <div className="row">
                  <div className="col-lg-6">
                    <div className="mb-3">
                      <label className="form-label">Status</label>
                      <select name="status" className="form-select" value={formData.status} onChange={handleChange}>
                        <option value="backlog">Backlog</option>
                        <option value="todo">Todo</option>
                        <option value="planning">Planning</option>
                        <option value="hitl_review">HITL Review</option>
                        <option value="working">Working</option>
                        <option value="ready_to_implement">Ready to Implement</option>
                        <option value="approval">Approval</option>
                        <option value="completed">Completed</option>
                        <option value="blocked">Blocked</option>
                      </select>
                    </div>
                  </div>
                  <div className="col-lg-6">
                    <div className="mb-3">
                      <label className="form-label">Priority</label>
                      <select name="priority" className="form-select" value={formData.priority} onChange={handleChange}>
                        <option value={0}>Low</option>
                        <option value={1}>Medium</option>
                        <option value={2}>High</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div className="modal-footer d-flex justify-content-between px-0 pb-0 pt-3 mt-auto">
                  <div>
                    {task && onDelete && (
                      <button type="button" className="btn btn-outline-danger" onClick={() => onDelete(task.id)}>
                        <IconTrash size={18} className="me-2" />
                        Delete Task
                      </button>
                    )}
                  </div>
                  <div className="btn-list">
                    <button type="button" className="btn btn-link link-secondary" onClick={onClose}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                      <IconDeviceFloppy size={18} className="me-2" />
                      {task ? "Update Task" : "Create Task"}
                    </button>
                  </div>
                </div>
              </form>
            )}

            {activeTab === 'dispatch' && task && (
              <div className="dispatch-section h-100 d-flex flex-column">
                <div className="row mb-4">
                  <div className="col-md-6">
                    <label className="form-label">Assign Agent</label>
                    <select 
                      name="assignee" 
                      className="form-select" 
                      value={formData.assignee || ""} 
                      onChange={handleChange}
                    >
                      <option value="">Auto-select (Dispatcher)</option>
                      {availableAgents.map(a => (
                        <option key={a.id} value={a.id}>{a.name} ({a.type})</option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">&nbsp;</label>
                    <button type="button" className="btn btn-warning w-100" onClick={handleDispatchNow} disabled={loading}>
                      <IconBolt size={18} className="me-2" /> Dispatch Now
                    </button>
                  </div>
                </div>

                {contextEstimate && (
                  <div className="card bg-dark-lt">
                    <div className="card-body">
                      <h4 className="card-title text-info mb-3">Context Size Estimate</h4>
                      <div className="row mb-3">
                        <div className="col-auto">
                          <div className="h1 mb-0">{contextEstimate.total_estimated_tokens.toLocaleString()}</div>
                          <div className="text-muted small text-uppercase">Est. Tokens</div>
                        </div>
                      </div>
                      <div className="progress progress-sm mb-3">
                        {Object.entries(contextEstimate.estimated_tokens).map(([key, val], idx) => {
                          const percent = (val / contextEstimate.total_estimated_tokens) * 100;
                          const colors = ["bg-primary", "bg-success", "bg-warning", "bg-info", "bg-danger"];
                          return (
                            <div key={key} className={`progress-bar ${colors[idx % colors.length]}`} style={{ width: `${percent}%` }}></div>
                          );
                        })}
                      </div>
                      <div className="row g-2">
                        {Object.entries(contextEstimate.estimated_tokens).map(([key, val], idx) => (
                          <div key={key} className="col-6 col-sm-4">
                            <div className="d-flex align-items-center">
                              <span className={`badge badge-dot me-2 bg-${["primary", "success", "warning", "info", "danger"][idx % 5]}`}></span>
                              <span className="text-muted small text-capitalize me-auto">{key}</span>
                              <span className="small fw-bold">{val.toLocaleString()}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                <div className="modal-footer px-0 pb-0 pt-3 mt-auto justify-content-end">
                  <button type="button" className="btn btn-link link-secondary" onClick={onClose}>
                    Close
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'comments' && (
              <div className="comments-section h-100 d-flex flex-column">
                <div className="mb-3" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {comments.map((c) => (
                    <div key={c.id} className="mb-3 border-bottom pb-2">
                      <div className="d-flex justify-content-between mb-1">
                        <span className="fw-bold small">{c.author}</span>
                        <span className="text-muted small">{new Date(c.created_at).toLocaleString()}</span>
                      </div>
                      <div className="small">{c.comment}</div>
                    </div>
                  ))}
                  {comments.length === 0 && <div className="text-center text-muted py-4">No comments yet.</div>}
                </div>
                <div className="input-group">
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="Add a comment..." 
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                  />
                  <button className="btn btn-primary" onClick={handleAddComment}>Send</button>
                </div>
                <div className="modal-footer px-0 pb-0 pt-3 mt-auto justify-content-end">
                  <button type="button" className="btn btn-link link-secondary" onClick={onClose}>
                    Close
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'artifacts' && (
              <div className="artifacts-section h-100 d-flex flex-column">
                <div className="table-responsive">
                  <table className="table table-vcenter">
                    <thead>
                      <tr>
                        <th>Stage</th>
                        <th>Path</th>
                        <th>Created At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {artifacts.map((a) => (
                        <tr key={a.id}>
                          <td className="text-uppercase small"><span className="badge bg-azure-lt">{a.stage}</span></td>
                          <td className="small text-truncate" style={{ maxWidth: '200px' }}>{a.path}</td>
                          <td className="small text-muted">{new Date(a.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                      {artifacts.length === 0 && (
                        <tr>
                          <td colSpan={3} className="text-center text-muted py-4">No artifacts linked.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="modal-footer px-0 pb-0 pt-3 mt-auto justify-content-end">
                  <button type="button" className="btn btn-link link-secondary" onClick={onClose}>
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
