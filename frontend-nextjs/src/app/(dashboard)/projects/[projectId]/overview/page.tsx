"use client";

import { useEffect, useState, useCallback } from "react";
import { useAppContext } from "@/context/AppContext";
import { useDispatchApi } from "@/hooks/useDispatchApi";
import { useSSE } from "@/hooks/useSSE";
import { Task, Agent } from "@/types/dispatch";
import { useParams } from "next/navigation";
import { 
  IconLayoutKanban, 
  IconUsers, 
  IconCheck, 
  IconExclamationCircle,
  IconDatabase,
  IconFingerprint,
  IconFolders,
  IconAccessPoint
} from "@tabler/icons-react";

export default function OverviewPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  
  const { config } = useAppContext();
  const { fetchTasks, fetchAgents } = useDispatchApi();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [sseStatus, setSseStatus] = useState<"connected" | "disconnected" | "error">("disconnected");
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [t, a] = await Promise.all([
        fetchTasks(projectId),
        fetchAgents(),
      ]);
      setTasks(t);
      setAgents(a);
      
      const healthResp = await fetch(`${config.apiBaseUrl}/health`);
      setBackendHealthy(healthResp.ok);
    } catch (e) {
      console.error("Failed to load overview data", e);
      setBackendHealthy(false);
    }
  }, [projectId, fetchTasks, fetchAgents, config.apiBaseUrl]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const { status } = useSSE(loadData);
  useEffect(() => {
    setSseStatus(status);
  }, [status]);

  const stats = [
    { label: "Active Tasks", value: tasks.filter(t => !["completed", "blocked", "backlog"].includes(t.status)).length, icon: <IconLayoutKanban className="text-primary" />, color: "bg-primary-lt" },
    { label: "Completed", value: tasks.filter(t => t.status === "completed").length, icon: <IconCheck className="text-success" />, color: "bg-success-lt" },
    { label: "Blocked", value: tasks.filter(t => t.status === "blocked").length, icon: <IconExclamationCircle className="text-danger" />, color: "bg-danger-lt" },
    { label: "Agents Online", value: agents.filter(a => a.status !== "offline").length, icon: <IconUsers className="text-info" />, color: "bg-info-lt" },
  ];

  return (
    <div className="container-xl py-4">
      <div className="page-header mb-4">
        <div className="row align-items-center">
          <div className="col">
            <h2 className="page-title">Mission Control: {projectId}</h2>
            <div className="text-muted small mt-1">Project-scoped overview of tasks, agents, and infrastructure health.</div>
          </div>
        </div>
      </div>

      <div className="row row-cards mb-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="col-sm-6 col-lg-3">
            <div className="card card-sm">
              <div className="card-body">
                <div className="row align-items-center">
                  <div className="col-auto">
                    <span className={`avatar ${stat.color} text-white`}>
                      {stat.icon}
                    </span>
                  </div>
                  <div className="col">
                    <div className="font-weight-medium">
                      {stat.value}
                    </div>
                    <div className="text-muted small">
                      {stat.label}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="row row-cards">
        <div className="col-lg-8">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Recent Task Activity</h3>
            </div>
            <div className="table-responsive">
              <table className="table card-table table-vcenter">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Status</th>
                    <th>Assignee</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.slice(0, 10).map(task => (
                    <tr key={task.id}>
                      <td>{task.title}</td>
                      <td>
                        <span className={`badge bg-${task.status === 'completed' ? 'success' : 'primary'}-lt text-uppercase`}>
                          {task.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="text-muted small">{task.assignee || "Unassigned"}</td>
                      <td className="text-muted small">{new Date(task.updated_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                  {tasks.length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-center py-4 text-muted">No task activity yet in this project.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">System Health</h3>
            </div>
            <div className="card-body">
              <div className="mb-3">
                <div className="d-flex align-items-center mb-2">
                  <IconDatabase size={18} className="me-2 text-muted" />
                  <span className="fw-bold me-auto">Backend API</span>
                  {backendHealthy === true ? (
                    <span className="badge bg-success">HEALTHY</span>
                  ) : backendHealthy === false ? (
                    <span className="badge bg-danger">OFFLINE</span>
                  ) : (
                    <span className="badge bg-warning">CHECKING...</span>
                  )}
                </div>
                <div className="text-muted small">{config.apiBaseUrl}</div>
              </div>

              <div className="mb-3">
                <div className="d-flex align-items-center mb-2">
                  <IconAccessPoint size={18} className="me-2 text-muted" />
                  <span className="fw-bold me-auto">SSE Connection</span>
                  <span className={`badge bg-${sseStatus === 'connected' ? 'success' : 'danger'}`}>
                    {sseStatus.toUpperCase()}
                  </span>
                </div>
              </div>

              <div className="mb-0">
                <div className="d-flex align-items-center mb-2">
                  <IconFolders size={18} className="me-2 text-muted" />
                  <span className="fw-bold me-auto">Current Project</span>
                  <span className="text-muted small">{projectId}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
