"use client";

import { useEffect, useState, useCallback } from "react";
import { useSSE } from "@/hooks/useSSE";
import { Agent, AgentProfile, AgentInstance, ModelRecord } from "@/types/dispatch";
import { useParams } from "next/navigation";
import { IconCpu, IconActivity, IconCircleFilled, IconPlus, IconEdit, IconTrash } from "@tabler/icons-react";
import AgentProfileModal from "@/components/agents/AgentProfileModal";
import { useAppContext } from "@/context/AppContext";

export default function AgentsPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const { config, user, projects } = useAppContext();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [profiles, setProfiles] = useState<AgentProfile[]>([]);
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<any | null>(null);

  const getHeaders = useCallback(
    () => ({
      "Content-Type": "application/json",
      "X-Actor-Role": user?.actor_role || "",
      "X-Actor-Id": user?.actor_id || "",
      "X-API-Token": config.apiToken,
    }),
    [config.apiToken, user?.actor_id, user?.actor_role]
  );

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [instancesResp, profilesResp, modelsResp] = await Promise.all([
        fetch(`${config.apiBaseUrl}/api/projects/${projectId}/agent-instances`, { headers: getHeaders() }),
        fetch(`${config.apiBaseUrl}/api/projects/${projectId}/agent-profiles`, { headers: getHeaders() }),
        fetch(`${config.apiBaseUrl}/api/models`, { headers: getHeaders() }),
      ]);

      if (!instancesResp.ok || !profilesResp.ok || !modelsResp.ok) {
        const detail = `Failed to load agent data (${instancesResp.status}/${profilesResp.status}/${modelsResp.status})`;
        throw new Error(detail);
      }

      const [instancesData, profilesData, modelsData] = await Promise.all([
        instancesResp.json() as Promise<AgentInstance[]>,
        profilesResp.json() as Promise<AgentProfile[]>,
        modelsResp.json() as Promise<ModelRecord[]>,
      ]);
      const mappedAgents: Agent[] = (instancesData || []).map((instance) => ({
        id: instance.id,
        name: instance.container_name || `instance-${String(instance.id).slice(0, 8)}`,
        type: instance.profile_id ? `profile:${String(instance.profile_id).slice(0, 8)}` : "unbound",
        status: instance.status === "running" ? "working" : "offline",
        last_heartbeat: instance.last_heartbeat || instance.updated_at || undefined,
        capabilities: [],
      }));
      setAgents(mappedAgents);
      setProfiles(profilesData);
      setModels(modelsData);
    } catch (e) {
      console.error("Failed to load agents data", e);
      setError(e instanceof Error ? e.message : "Failed to load agents data");
    } finally {
      setLoading(false);
    }
  }, [config.apiBaseUrl, getHeaders, projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useSSE(loadData);

  const handleSaveProfile = async (profileData: Partial<AgentProfile>) => {
    setError(null);
    const method = selectedProfile ? "PUT" : "POST";
    const endpoint = selectedProfile
      ? `${config.apiBaseUrl}/api/agent-profiles/${selectedProfile.id}`
      : `${config.apiBaseUrl}/api/projects/${projectId}/agent-profiles`;

    const payload = {
      name: profileData.name,
      type: profileData.type,
      system_prompt: profileData.system_prompt || null,
      model_id: profileData.model_id || null,
      provider: profileData.provider || null,
      tools: profileData.tools || [],
      skills: profileData.skills || [],
      enabled: Boolean(profileData.enabled),
    };

    const resp = await fetch(endpoint, {
      method,
      headers: getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({ detail: "Failed to save profile" }));
      throw new Error(data.detail || "Failed to save profile");
    }

    await loadData();
  };

  const handleDeleteProfile = async (id: string) => {
    if (!confirm("Are you sure you want to delete this profile?")) return;
    setError(null);

    const resp = await fetch(`${config.apiBaseUrl}/api/agent-profiles/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({ detail: "Failed to delete profile" }));
      setError(data.detail || "Failed to delete profile");
      return;
    }

    await loadData();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "online":
        return <span className="badge bg-green-lt"><IconCircleFilled size={10} className="me-1 text-green" /> Online</span>;
      case "working":
        return <span className="badge bg-blue-lt"><IconActivity size={10} className="me-1 text-blue" /> Working</span>;
      default:
        return <span className="badge bg-secondary-lt">Offline</span>;
    }
  };

  const projectLabel = projects.find((project) => project.id === projectId)?.name || projectId;

  return (
    <div className="container-xl py-4">
      <div className="page-header mb-4">
        <div className="row align-items-center">
          <div className="col">
            <h2 className="page-title">Agent Fleet: {projectLabel}</h2>
            <div className="text-muted small mt-1">Manage agent profiles and monitor runtime instances.</div>
          </div>
          <div className="col-auto ms-auto">
            <button className="btn btn-primary" onClick={() => { setSelectedProfile(null); setShowProfileModal(true); }}>
              <IconPlus size={18} className="me-1" /> New Profile
            </button>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row mb-4">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Agent Profiles</h3>
            </div>
            <div className="table-responsive">
              <table className="table card-table table-vcenter">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Model</th>
                    <th>Status</th>
                    <th className="w-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {profiles.map((p) => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      <td className="text-uppercase small">{p.type}</td>
                      <td className="text-secondary small">{p.model_id || "Default"}</td>
                      <td>
                        {p.enabled ? <span className="badge bg-green">Enabled</span> : <span className="badge bg-secondary">Disabled</span>}
                      </td>
                      <td>
                        <div className="btn-list flex-nowrap">
                          <button className="btn btn-white btn-sm" onClick={() => { setSelectedProfile(p); setShowProfileModal(true); }}>
                            <IconEdit size={16} />
                          </button>
                          <button className="btn btn-white btn-sm text-danger" onClick={() => handleDeleteProfile(p.id)}>
                            <IconTrash size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {profiles.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center py-4 text-muted">No profiles defined for this project.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <h3 className="mb-3">Live Instances</h3>
      <div className="row row-cards">
        {agents.map((agent) => (
          <div key={agent.id} className="col-md-6 col-lg-3">
            <div className={`card ${agent.status === "offline" ? "opacity-75" : ""}`}>
              <div className="card-body">
                <div className="d-flex align-items-center mb-3">
                  <span className={`avatar avatar-lg rounded me-3 ${agent.status === "working" ? "bg-blue text-white" : "bg-light"}`}>
                    <IconCpu size={24} />
                  </span>
                  <div>
                    <h3 className="card-title mb-0">{agent.name}</h3>
                    <div className="text-muted small">{agent.type}</div>
                  </div>
                  <div className="ms-auto">{getStatusBadge(agent.status)}</div>
                </div>

                <div className="mb-3">
                  <div className="small text-muted mb-1">Capabilities</div>
                  <div className="d-flex flex-wrap gap-1">
                    {agent.capabilities?.map((cap) => (
                      <span key={cap} className="badge badge-outline text-secondary small">{cap}</span>
                    ))}
                    {!agent.capabilities?.length && <span className="text-muted small italic">General Purpose</span>}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-top d-flex justify-content-between align-items-center">
                  <span className="small text-muted">Last heartbeat</span>
                  <span className="small fw-bold">
                    {agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleTimeString() : "Never"}
                  </span>
                </div>
              </div>
              {agent.status === "working" && <div className="progress progress-sm card-progress"><div className="progress-bar progress-bar-indeterminate"></div></div>}
            </div>
          </div>
        ))}
        {agents.length === 0 && !loading && (
          <div className="col-12">
            <div className="alert alert-info text-center">No runtime agent instances detected.</div>
          </div>
        )}
      </div>

      {showProfileModal && (
        <AgentProfileModal
          profile={selectedProfile}
          models={models}
          onClose={() => setShowProfileModal(false)}
          onSave={handleSaveProfile}
        />
      )}
    </div>
  );
}
