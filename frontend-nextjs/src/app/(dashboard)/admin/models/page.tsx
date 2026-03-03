"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useAppContext } from "@/context/AppContext";
import { IconPlus, IconTrash, IconCheck } from "@tabler/icons-react";
import { ModelRecord } from "@/types/dispatch";

export default function ModelRegistryPage() {
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const [newModel, setNewProject] = useState({
    label: "",
    provider: "openai",
    model_name: "",
    api_base: "",
    api_key: "",
    is_default: false,
    enabled: true,
    config: {}
  });

  const { config, user } = useAppContext();

  const fetchModels = useCallback(async () => {
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/models`, {
        headers: {
          'X-Actor-Role': user?.actor_role || '',
          'X-Actor-Id': user?.actor_id || '',
          'X-API-Token': config.apiToken,
        }
      });
      if (resp.ok) {
        setModels((await resp.json()) as ModelRecord[]);
      }
    } catch (err) {
      console.error("Failed to fetch models", err);
    } finally {
      setLoading(false);
    }
  }, [config, user]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const handleCreateModel = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await fetch(`${config.apiBaseUrl}/api/models`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Actor-Role': user?.actor_role || '',
          'X-Actor-Id': user?.actor_id || '',
          'X-API-Token': config.apiToken,
        },
        body: JSON.stringify({
          ...newModel,
          config: {
            ...(newModel.config || {}),
            ...(newModel.api_key ? { api_key: newModel.api_key } : {}),
          },
        })
      });
      if (resp.ok) {
        setShowCreateModal(false);
        setNewProject({ label: "", provider: "openai", model_name: "", api_base: "", api_key: "", is_default: false, enabled: true, config: {} });
        fetchModels();
      }
    } catch (err) {
      console.error("Failed to create model", err);
    }
  };

  const handleDeleteModel = async (id: string) => {
    if (!confirm("Are you sure?")) return;
    try {
      await fetch(`${config.apiBaseUrl}/api/models/${id}`, {
        method: 'DELETE',
        headers: {
          'X-Actor-Role': user?.actor_role || '',
          'X-Actor-Id': user?.actor_id || '',
          'X-API-Token': config.apiToken,
        }
      });
      fetchModels();
    } catch (err) {
      console.error("Failed to delete model", err);
    }
  };

  if (loading) return <div>Loading models...</div>;

  return (
    <div className="page-wrapper">
      <div className="page-header d-print-none">
        <div className="container-xl">
          <div className="row g-2 align-items-center">
            <div className="col">
              <h2 className="page-title">
                Model Registry
              </h2>
            </div>
            <div className="col-auto ms-auto d-print-none">
              <div className="btn-list">
                <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                  <IconPlus size={18} />
                  Add model
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="container-xl">
          <div className="card">
            <div className="table-responsive">
              <table className="table table-vcenter card-table">
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Provider</th>
                    <th>Model Name</th>
                    <th>Default</th>
                    <th>API Key</th>
                    <th>Status</th>
                    <th className="w-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.id}>
                      <td>{m.label}</td>
                      <td className="text-secondary">{m.provider}</td>
                      <td className="text-secondary">{m.model_name}</td>
                      <td>
                        {m.is_default && <IconCheck size={18} className="text-success" />}
                      </td>
                      <td>
                        <span className={`badge ${m.config?.api_key ? "bg-azure-lt text-azure" : "bg-secondary-lt text-secondary"}`}>
                          {m.config?.api_key ? "Configured" : "Not set"}
                        </span>
                      </td>
                      <td>
                        {m.enabled ? <span className="badge bg-green-lt">Enabled</span> : <span className="badge bg-red-lt">Disabled</span>}
                      </td>
                      <td>
                        <button className="btn btn-icon btn-white text-danger" onClick={() => handleDeleteModel(m.id)}>
                          <IconTrash size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {showCreateModal && (
        <div className="modal modal-blur fade show" style={{ display: 'block' }} tabIndex={-1}>
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Add New Model</h5>
                <button type="button" className="btn-close" onClick={() => setShowCreateModal(false)}></button>
              </div>
              <form onSubmit={handleCreateModel}>
                <div className="modal-body">
                  <div className="row">
                    <div className="col-lg-6">
                      <div className="mb-3">
                        <label className="form-label">Friendly Label</label>
                        <input type="text" className="form-control" required value={newModel.label} onChange={e => setNewProject({...newModel, label: e.target.value})} placeholder="GPT-4o" />
                      </div>
                    </div>
                    <div className="col-lg-6">
                      <div className="mb-3">
                        <label className="form-label">Provider</label>
                        <select className="form-select" value={newModel.provider} onChange={e => setNewProject({...newModel, provider: e.target.value})}>
                          <option value="openai">OpenAI</option>
                          <option value="anthropic">Anthropic</option>
                          <option value="google">Google</option>
                          <option value="ollama">Ollama (local)</option>
                          <option value="vllm">vLLM (local)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Model Name (API ID)</label>
                    <input type="text" className="form-control" required value={newModel.model_name} onChange={e => setNewProject({...newModel, model_name: e.target.value})} placeholder="gpt-4o-2024-05-13" />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">API Base URL (optional)</label>
                    <input type="text" className="form-control" value={newModel.api_base} onChange={e => setNewProject({...newModel, api_base: e.target.value})} placeholder="https://api.openai.com/v1" />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">API Key (optional)</label>
                    <input
                      type="password"
                      className="form-control"
                      value={newModel.api_key}
                      onChange={e => setNewProject({...newModel, api_key: e.target.value})}
                      placeholder="sk-..."
                    />
                    <div className="form-hint">Stored in model config for backend runtime usage.</div>
                  </div>
                  <div className="mb-3">
                    <label className="form-check form-switch mt-2">
                      <input className="form-check-input" type="checkbox" checked={newModel.is_default} onChange={e => setNewProject({...newModel, is_default: e.target.checked})} />
                      <span className="form-check-label">Set as default model</span>
                    </label>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-link link-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary ms-auto">Add Model</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      {showCreateModal && <div className="modal-backdrop fade show"></div>}
    </div>
  );
}
