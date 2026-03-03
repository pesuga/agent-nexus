"use client";

import { useEffect, useState, useCallback } from "react";
import { useSSE } from "@/hooks/useSSE";
import { useParams } from "next/navigation";
import { IconPlayerStop, IconRefresh, IconTimeline } from "@tabler/icons-react";
import { useAppContext } from "@/context/AppContext";
import { AgentActivityEvent, AgentInstance } from "@/types/dispatch";

export default function AgentInstancesPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  
  const { config, user } = useAppContext();
  const [instances, setInstances] = useState<AgentInstance[]>([]);
  const [activity, setActivity] = useState<AgentActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const headers = {
        'X-Actor-Role': user?.actor_role || '',
        'X-Actor-Id': user?.actor_id || '',
        'X-API-Token': config.apiToken,
      };

      const [instancesResp, activityResp] = await Promise.all([
        fetch(`${config.apiBaseUrl}/api/projects/${projectId}/agent-instances`, { headers }),
        fetch(`${config.apiBaseUrl}/api/projects/${projectId}/agent-activity?limit=50`, { headers })
      ]);

      if (instancesResp.ok) setInstances((await instancesResp.json()) as AgentInstance[]);
      if (activityResp.ok) setActivity((await activityResp.json()) as AgentActivityEvent[]);
    } catch (e) {
      console.error("Failed to fetch agent instances/activity", e);
    } finally {
      setLoading(false);
    }
  }, [projectId, config, user]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useSSE(fetchData);

  const handleStopInstance = async (instanceId: string) => {
    try {
      await fetch(`${config.apiBaseUrl}/api/agent-instances/${instanceId}/stop`, {
        method: 'POST',
        headers: {
          'X-Actor-Role': user?.actor_role || '',
          'X-Actor-Id': user?.actor_id || '',
          'X-API-Token': config.apiToken,
        }
      });
      fetchData();
    } catch (e) {
      console.error("Failed to stop instance", e);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error': return 'text-danger';
      case 'warning': return 'text-warning';
      default: return 'text-info';
    }
  };

  return (
    <div className="container-xl py-4">
      <div className="page-header mb-4">
        <div className="row align-items-center">
          <div className="col">
            <h2 className="page-title">Runtime Instances: {projectId}</h2>
            <div className="text-muted small mt-1">Manage active agent containers and view real-time activity logs.</div>
          </div>
          <div className="col-auto">
            <button className="btn btn-icon btn-white" onClick={fetchData}>
              <IconRefresh size={18} />
            </button>
          </div>
        </div>
      </div>

      {!loading && <div className="row row-cards mb-4">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Active Containers</h3>
            </div>
            <div className="table-responsive">
              <table className="table card-table table-vcenter">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Profile</th>
                    <th>Status</th>
                    <th>Current Task</th>
                    <th>Started</th>
                    <th className="w-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {instances.map(inst => (
                    <tr key={inst.id}>
                      <td className="small font-monospace">{inst.id.slice(0, 8)}</td>
                      <td>{inst.profile_id}</td>
                      <td>
                        <span className={`badge bg-${inst.status === 'running' ? 'green' : 'secondary'}-lt`}>
                          {inst.status}
                        </span>
                      </td>
                      <td className="small text-muted">{inst.task_id || "Idle"}</td>
                      <td className="small text-muted">
                        {inst.started_at ? new Date(inst.started_at).toLocaleString() : "-"}
                      </td>
                      <td>
                        {inst.status === 'running' && (
                          <button className="btn btn-icon btn-white text-danger" onClick={() => handleStopInstance(inst.id)}>
                            <IconPlayerStop size={18} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {instances.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-4 text-muted">No active agent instances.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>}

      <div className="card">
        <div className="card-header">
          <h3 className="card-title"><IconTimeline size={18} className="me-2" /> Activity Feed</h3>
        </div>
        <div className="card-body p-0">
          <div className="list-group list-group-flush list-group-hoverable" style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {activity.map(event => (
              <div key={event.id} className="list-group-item">
                <div className="row align-items-center">
                  <div className="col-auto text-muted small font-monospace">
                    {new Date(event.ts).toLocaleTimeString()}
                  </div>
                  <div className="col-auto">
                    <span className={`badge badge-dot bg-${event.level === 'error' ? 'danger' : event.level === 'warning' ? 'warning' : 'info'}`}></span>
                  </div>
                  <div className="col text-truncate">
                    <span className="fw-bold me-2">{event.agent_id}</span>
                    <span className={getLevelColor(event.level)}>{event.message}</span>
                  </div>
                  {event.task_id && (
                    <div className="col-auto">
                      <span className="badge bg-blue-lt small">Task: {event.task_id.slice(0, 8)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {activity.length === 0 && (
              <div className="p-4 text-center text-muted">No recent activity events.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
